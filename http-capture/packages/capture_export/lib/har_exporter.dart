import 'dart:convert';
import 'dart:io';
import 'package:capture_core/capture_core.dart';
import 'atomic_export.dart';

class HarExporter {
  Future<void> export(
    SessionStore store,
    String path, {
    Set<String>? ids,
  }) => atomicExport(path, (file) async {
    final out = await file.open(mode: FileMode.write);
    Future<void> text(String s) => out.writeString(s);
    try {
      await text(
        '{"log":{"version":"1.2","creator":{"name":"HTTP Capture","version":"0.1.0"},"entries":[',
      );
      bool first = true;
      for (final s in store.all(ids: ids)) {
        if (!first) await text(',');
        first = false;
        final req = s.request, res = s.response;
        final elapsed = s.endTime == null
            ? null
            : s.endTime!.difference(s.startTime).inMicroseconds / 1000;
        final send = (s.timing['send'] as num?) ?? -1,
            wait = (s.timing['wait'] as num?) ?? -1,
            receive = (s.timing['receive'] as num?) ?? -1;
        final timings = {
          'blocked': -1,
          'dns': -1,
          'connect': -1,
          'ssl': -1,
          'send': send,
          'wait': wait,
          'receive': receive,
        };
        final measured = [
          send,
          wait,
          receive,
        ].where((v) => v >= 0).fold<num>(0, (a, b) => a + b);
        final r = {
          'method': req.method,
          'url': req.url,
          'httpVersion': req.version,
          'cookies': requestCookies(req),
          'headers': headers(req),
          'queryString': Uri.parse(req.url!).queryParametersAll.entries
              .expand((e) => e.value.map((v) => {'name': e.key, 'value': v}))
              .toList(),
          'headersSize': -1,
          'bodySize': req.body?.size ?? -1,
        };
        await text(
          '{"startedDateTime":${jsonEncode(s.startTime.toUtc().toIso8601String())},"time":$measured,"request":',
        );
        var reqJson = jsonEncode(r);
        await text(reqJson.substring(0, reqJson.length - 1));
        if (req.body != null && req.body!.size > 0) {
          final mime = req.header('content-type');
          var textual =
              (mime.contains('json') ||
                  mime.startsWith('text/') ||
                  mime.contains('x-www-form-urlencoded')) &&
              req.header('content-encoding').isEmpty &&
              (!mime.contains('charset=') ||
                  mime.toLowerCase().contains('charset=utf-8'));
          if (textual) {
            try {
              await for (final _
                  in store.body(req.body).transform(utf8.decoder)) {}
            } catch (_) {
              textual = false;
            }
          }
          await text(
            ',"postData":{"mimeType":${jsonEncode(mime)},${textual ? '' : '"_encoding":"base64",'}"text":"',
          );
          if (textual) {
            await for (final chunk
                in store.body(req.body).transform(utf8.decoder)) {
              final encoded = jsonEncode(chunk);
              await text(encoded.substring(1, encoded.length - 1));
            }
          } else {
            await base64Body(store, req.body!, text);
          }
          await text('"}');
        }
        await text('},"response":');
        final response = {
          'status': res?.status ?? 0,
          'statusText': res?.reason ?? '',
          'httpVersion': res?.version ?? '',
          'cookies': res == null ? <dynamic>[] : responseCookies(res),
          'headers': res == null ? <dynamic>[] : headers(res),
          'redirectURL': res?.header('location') ?? '',
          'headersSize': -1,
          'bodySize': res?.body?.size ?? -1,
        };
        final encoded = jsonEncode(response);
        await text(encoded.substring(0, encoded.length - 1));
        final body = res?.body;
        final encoding = res?.header('content-encoding').toLowerCase() ?? '';
        var decodable =
            encoding.isEmpty || (encoding == 'gzip' && body?.complete == true);
        Stream<List<int>> decoded() => encoding == 'gzip'
            ? store.body(body).transform(gzip.decoder)
            : store.body(body);
        int decodedSize = body == null ? -1 : body.size;
        if (body != null && encoding == 'gzip' && decodable) {
          try {
            decodedSize = 0;
            await for (final chunk in decoded()) {
              decodedSize += chunk.length;
            }
          } catch (_) {
            decodable = false;
            decodedSize = -1;
          }
        }
        final content = {
          'size': decodable ? decodedSize : -1,
          'mimeType': res?.header('content-type') ?? '',
        };
        final cj = jsonEncode(content);
        await text(',"content":${cj.substring(0, cj.length - 1)}');
        if (body != null && decodable) {
          await text(',"encoding":"base64","text":"');
          await for (final chunk in decoded().transform(base64.encoder))
            await text(chunk);
          await text('"');
        }
        await text('}');
        if (body != null && encoding.isNotEmpty) {
          await text(
            ',"_httpCaptureRawContent":{"contentEncoding":${jsonEncode(encoding)},"encoding":"base64","text":"',
          );
          await base64Body(store, body, text);
          await text('"}');
        }
        await text(
          '},"cache":{},"timings":${jsonEncode(timings)},"_captureStatus":${jsonEncode(s.captureStatus)},"_elapsedMs":${jsonEncode(elapsed)},"_error":${jsonEncode(s.error)},"_sessionId":${jsonEncode(s.id)}}',
        );
      }
      await text(']}}');
      await out.flush();
    } finally {
      await out.close();
    }
  });
  Future<void> base64Body(
    SessionStore store,
    BodyReference body,
    Future<void> Function(String) text,
  ) async {
    await for (final chunk in store.body(body).transform(base64.encoder))
      await text(chunk);
  }

  List<Map<String, String>> headers(HttpMessage m) =>
      m.headers.map((h) => {'name': h.name, 'value': h.value}).toList();
  List<Map<String, String>> requestCookies(HttpMessage m) => m.headers
      .where((h) => h.name.toLowerCase() == 'cookie')
      .expand((h) => h.value.split(';'))
      .where((v) => v.contains('='))
      .map((v) {
        final i = v.indexOf('=');
        return {
          'name': v.substring(0, i).trim(),
          'value': v.substring(i + 1).trim(),
        };
      })
      .toList();
  List<Map<String, dynamic>> responseCookies(HttpMessage m) =>
      m.headers.where((h) => h.name.toLowerCase() == 'set-cookie').map((h) {
        final parts = h.value.split(';'), i = parts.first.indexOf('=');
        if (i < 0) return <String, dynamic>{'name': parts.first, 'value': ''};
        final c = <String, dynamic>{
          'name': parts.first.substring(0, i),
          'value': parts.first.substring(i + 1),
        };
        for (final a in parts.skip(1)) {
          final eq = a.indexOf('='),
              name = (eq < 0 ? a : a.substring(0, eq)).trim().toLowerCase();
          final value = eq < 0 ? '' : a.substring(eq + 1).trim();
          if (name == 'secure') c['secure'] = true;
          if (name == 'httponly') c['httpOnly'] = true;
          if (name == 'path' || name == 'domain') c[name] = value;
          if (name == 'expires') {
            try {
              c['expires'] = HttpDate.parse(value).toUtc().toIso8601String();
            } catch (_) {}
          }
        }
        return c;
      }).toList();
}
