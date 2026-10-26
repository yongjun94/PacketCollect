import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'package:capture_core/capture_core.dart';

/// Explicit loopback proxy. HTTP headers are Dart's parsed representation;
/// packet bytes and original global header order are not available.
class LocalProxyEngine implements CaptureEngine {
  final Directory root;
  final int bodyLimit;
  final Future<SecurityContext> Function(String host)? tlsIdentity;
  final Set<String> decryptHosts;
  final SecurityContext? upstreamContext;
  final _tlsServers = <HttpServer>{};
  bool _decrypt = false;
  LocalProxyEngine(this.root, {this.bodyLimit = 64 * 1024 * 1024,
    this.tlsIdentity, this.decryptHosts = const {}, this.upstreamContext});
  final _events = StreamController<Map<String, dynamic>>.broadcast();
  final _sockets = <Socket>{};
  final _active = <Future<void>>{};
  HttpClient _client = HttpClient()..autoUncompress = false;
  HttpServer? _server;
  bool _paused = false;
  String _run = '';
  int get port => _server?.port ?? 0;
  @override
  Stream<Map<String, dynamic>> get events => _events.stream;
  @override
  Future<void> start({int port = 8877, bool decrypt = false}) async {
    if (decrypt && (tlsIdentity == null || decryptHosts.isEmpty)) throw StateError('Choose HTTPS hosts and configure a local CA first');
    _decrypt = decrypt;
    if (_server != null) throw StateError('Proxy already running');
    await Directory('${root.path}/bodies').create(recursive: true);
    _client = HttpClient(context: upstreamContext)..autoUncompress = false;
    _run = _id();
    _paused = false;
    _server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
    _server!.listen((request) {
      final work = _handle(request);
      _active.add(work);
      unawaited(work.whenComplete(() => _active.remove(work)));
    });
  }
  String _id() => '${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
  List<Header> _headers(HttpHeaders h) {
    final result = <Header>[];
    h.forEach((name, values) {
      for (final value in values) { result.add(Header.text(name, value)); }
    });
    return result;
  }
  static Set<String> _hop(HttpHeaders headers) => {
    'connection', 'proxy-connection', 'keep-alive', 'transfer-encoding',
    'te', 'trailer', 'upgrade', 'proxy-authorization', 'proxy-authenticate',
    ...?headers[HttpHeaders.connectionHeader]?.expand((v) => v.split(',')).map((s) => s.trim().toLowerCase()),
  };
  void _copy(HttpHeaders from, HttpHeaders to) {
    final excluded = _hop(from);
    from.forEach((name, values) {
      if (!excluded.contains(name.toLowerCase())) {
        for (final value in values) { to.add(name, value); }
      }
    });
  }
  Future<void> _handle(HttpRequest request, {Uri? tlsOrigin}) async {
    final record = !_paused;
    final id = _id();
    final start = DateTime.now().toUtc();
    HttpMessage? req, res;
    final requestBody = _Body(root, id, 'request', bodyLimit, record);
    final responseBody = _Body(root, id, 'response', bodyLimit, record);
    var state = 'complete';
    String? error;
    try {
      if (request.method == 'CONNECT') {
        if (tlsOrigin != null) throw FormatException('Nested CONNECT is not supported');
        final authority = (request.uri.hasAuthority ? request.uri : Uri.parse('//${request.uri}')).replace(scheme:'https');
        if(authority.host.isEmpty || authority.userInfo.isNotEmpty) throw FormatException('Invalid CONNECT authority');
        req = HttpMessage(version: 'HTTP/${request.protocolVersion}', headers: _headers(request.headers), method: 'CONNECT', url: authority.toString());
        if (_decrypt && decryptHosts.contains(authority.host.toLowerCase())) {
          await _intercept(request, authority);
          req = null; // Inner HTTP requests have their own complete/error sessions.
          return;
        }
        final upstream = await Socket.connect(authority.host, authority.hasPort ? authority.port : 443, timeout: const Duration(seconds: 15));
        _sockets.add(upstream);
        request.response.statusCode = 200;
        request.response.contentLength = 0;
        final downstream = await request.response.detachSocket();
        _sockets.add(downstream);
        state = 'tunneled';
        error = 'HTTPS tunnel only. TLS contents, headers and bodies were not decrypted.';
        // Socket backpressure is preserved; Stop closes both directions.
        try {
          await Future.wait([
            upstream.addStream(downstream).whenComplete(() => upstream.close()),
            downstream.addStream(upstream).whenComplete(() => downstream.close()),
          ]);
        } finally {
          _sockets.remove(upstream); _sockets.remove(downstream);
          upstream.destroy(); downstream.destroy();
        }
      } else {
        final uri = tlsOrigin == null ? request.uri : tlsOrigin.replace(path: request.uri.path, query: request.uri.hasQuery ? request.uri.query : null);
        if (tlsOrigin != null && request.uri.hasAuthority && (request.uri.host != tlsOrigin.host || request.uri.port != tlsOrigin.port)) throw FormatException('TLS request authority differs from CONNECT');
        if (!['http', 'https'].contains(uri.scheme) || uri.host.isEmpty) throw FormatException('An absolute http:// proxy URL is required');
        if (['127.0.0.1', 'localhost', '::1'].contains(uri.host) && uri.port == port) {
          throw StateError('Proxy loop refused');
        }
        req = HttpMessage(version: 'HTTP/${request.protocolVersion}', headers: _headers(request.headers), method: request.method, url: uri.toString());
        final outbound = await _client.openUrl(request.method, uri).timeout(const Duration(seconds: 20));
        outbound.followRedirects = false;
        outbound.persistentConnection = false;
        _copy(request.headers, outbound.headers);
        await outbound.addStream(request.map((bytes) { requestBody.add(bytes); return bytes; }));
        await requestBody.close();
        final incoming = await outbound.close().timeout(const Duration(seconds: 60));
        res = HttpMessage(version: 'HTTP/1.1', headers: _headers(incoming.headers), status: incoming.statusCode, reason: incoming.reasonPhrase);
        request.response.persistentConnection = false;
        request.response.statusCode = incoming.statusCode;
        request.response.reasonPhrase = incoming.reasonPhrase;
        _copy(incoming.headers, request.response.headers);
        await request.response.addStream(incoming.map((bytes) { responseBody.add(bytes); return bytes; }));
        await responseBody.close();
        await request.response.close();
        if (requestBody.truncated || responseBody.truncated) {
          state = 'partial'; error = 'Body capture exceeded $bodyLimit bytes; forwarding continued.';
        }
      }
    } catch (e) {
      state = 'error'; error = '$e';
      try { request.response.statusCode = 502; await request.response.close(); } catch (_) {}
    } finally {
      try {
        await requestBody.close(); await responseBody.close();
        if (record && req != null) {
          final r = req;
          final s = res;
          final session = CaptureSession(id: id, runId: _run, sourceDevice: 'android-local', startTime: start, endTime: DateTime.now().toUtc(),
            request: HttpMessage(version: r.version, headers: r.headers, method: r.method, url: r.url, body: request.method == 'CONNECT' ? null : requestBody.ref(state == 'complete')),
            response: s == null ? null : HttpMessage(version: s.version, headers: s.headers, status: s.status, reason: s.reason, body: responseBody.ref(state == 'complete')),
            captureStatus: state, error: error,
            connection: {'engine': 'dart-explicit-proxy', 'headerRepresentation': 'parsed; original order/casing unavailable', 'responseVersion': 'HTTP/1.1 normalized; upstream version unavailable', 'tlsDecrypted': tlsOrigin != null});
          _events.add({'type': 'session', 'session': session.toJson()});
        }
      } catch (e) { _events.add({'type': 'fatal', 'error': 'Session persistence failed: $e'}); }
    }
  }
  Future<void> _intercept(HttpRequest connect, Uri authority) async {
    if (_tlsServers.length >= 64) throw StateError('TLS connection limit reached');
    final context = await tlsIdentity!(authority.host);
    if (_server == null) throw StateError('Capture stopped');
    final server = await HttpServer.bindSecure(InternetAddress.loopbackIPv4, 0, context);
    _tlsServers.add(server);
    Object? tlsError;
    final listener = server.listen((request) {
      final work = _handle(request, tlsOrigin: authority);
      _active.add(work);
      unawaited(work.whenComplete(() => _active.remove(work)));
    }, onError: (Object e) { tlsError = e; });
    Socket? bridge, downstream;
    try {
      bridge = await Socket.connect(InternetAddress.loopbackIPv4, server.port);
      _sockets.add(bridge);
      connect.response.statusCode = 200;
      connect.response.contentLength = 0;
      downstream = await connect.response.detachSocket();
      _sockets.add(downstream);
      final a = bridge, b = downstream;
      await Future.wait([
        a.addStream(b).whenComplete(() => a.close()),
        b.addStream(a).whenComplete(() => b.close()),
      ]);
      if (tlsError != null) throw HandshakeException('Client rejected local CA or TLS handshake failed: $tlsError');
    } finally {
      if (bridge != null) { _sockets.remove(bridge); bridge.destroy(); }
      if (downstream != null) { _sockets.remove(downstream); downstream.destroy(); }
      await server.close(force: true); await listener.cancel(); _tlsServers.remove(server);
    }
  }
  @override
  Future<void> pause(bool paused) async { _paused = paused; }
  @override
  Future<void> stop() async {
    final server = _server;
    if (server == null) return;
    _server = null;
    await server.close(force: true);
    for (final tls in _tlsServers.toList()) { await tls.close(force: true); }
    for (final socket in _sockets.toList()) { socket.destroy(); }
    _client.close(force: true);
    await Future.wait(_active.toList()).timeout(const Duration(seconds: 10));
    _server = null;
  }
}

class _Body {
  final String path;
  final int limit;
  final bool enabled;
  IOSink? sink;
  int size = 0;
  bool truncated = false, closed = false;
  _Body(Directory root, String id, String side, this.limit, this.enabled)
      : path = 'bodies/$id.$side.bin' {
    if (enabled) sink = File('${root.path}/$path').openWrite();
  }
  void add(List<int> bytes) {
    if (!enabled) return;
    final remaining = limit - size;
    final count = min(remaining, bytes.length);
    if (count > 0) { sink!.add(count == bytes.length ? bytes : bytes.sublist(0, count)); size += count; }
    if (count < bytes.length) truncated = true;
  }
  Future<void> close() async {
    if (closed) return;
    closed = true;
    await sink?.flush(); await sink?.close();
  }
  BodyReference ref(bool complete) => BodyReference(path, size, complete && !truncated);
}
