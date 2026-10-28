import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:sqlite3/sqlite3.dart';

/// Headers are byte pairs, never maps. No duplicate folding or charset guesses.
class Header {
  final List<int> nameBytes, valueBytes;
  Header(this.nameBytes, this.valueBytes) {
    if ([...nameBytes, ...valueBytes].any((b) => b == 10 || b == 13)) {
      throw FormatException('Header contains CR/LF');
    }
  }
  factory Header.text(String name, String value) =>
      Header(latin1.encode(name), latin1.encode(value));
  factory Header.fromJson(Map<String, dynamic> j) =>
      Header(base64.decode(j['name']), base64.decode(j['value']));
  String get name => latin1.decode(nameBytes);
  String get value => latin1.decode(valueBytes);
  Map<String, dynamic> toJson() => {
    'name': base64.encode(nameBytes),
    'value': base64.encode(valueBytes),
  };
}

class BodyReference {
  final String path;
  final int size;
  final bool complete;
  BodyReference(this.path, this.size, this.complete) {
    if (!RegExp(
          r'^bodies/[a-zA-Z0-9_-]+\.(request|response)\.bin$',
        ).hasMatch(path) ||
        size < 0) {
      throw FormatException('Invalid body reference');
    }
  }
  factory BodyReference.fromJson(Map<String, dynamic> j) =>
      BodyReference(j['path'], j['size'], j['complete']);
  Map<String, dynamic> toJson() => {
    'path': path,
    'size': size,
    'complete': complete,
  };
}

class HttpMessage {
  final String version;
  final List<Header> headers;
  final BodyReference? body;
  final String? method, url, reason;
  final int? status;
  HttpMessage({
    required this.version,
    required this.headers,
    this.body,
    this.method,
    this.url,
    this.reason,
    this.status,
  });
  factory HttpMessage.fromJson(Map<String, dynamic> j) => HttpMessage(
    version: j['version'],
    headers: (j['headers'] as List)
        .map((h) => Header.fromJson(Map<String, dynamic>.from(h)))
        .toList(),
    body: j['body'] == null
        ? null
        : BodyReference.fromJson(Map<String, dynamic>.from(j['body'])),
    method: j['method'],
    url: j['url'],
    reason: j['reason'],
    status: j['status'],
  );
  String header(String name) => headers
      .where((h) => h.name.toLowerCase() == name.toLowerCase())
      .map((h) => h.value)
      .join(', ');
  Map<String, dynamic> toJson() => {
    'version': version,
    'headers': headers.map((h) => h.toJson()).toList(),
    'body': body?.toJson(),
    'method': method,
    'url': url,
    'reason': reason,
    'status': status,
  };
}

class CaptureSession {
  final String id, runId, sourceDevice, captureStatus;
  final DateTime startTime;
  final DateTime? endTime;
  final HttpMessage request;
  final HttpMessage? response;
  final Map<String, dynamic> timing, connection, tls;
  final String? error;
  CaptureSession({
    required this.id,
    required this.runId,
    required this.sourceDevice,
    required this.startTime,
    this.endTime,
    required this.request,
    this.response,
    required this.captureStatus,
    this.error,
    this.timing = const {},
    this.connection = const {},
    this.tls = const {},
  }) {
    if (!RegExp(r'^[a-zA-Z0-9_-]+$').hasMatch(id))
      throw FormatException('Invalid session id');
    if (request.method == null || request.url == null)
      throw FormatException('Request missing method/url');
  }
  factory CaptureSession.fromJson(Map<String, dynamic> j) => CaptureSession(
    id: j['id'],
    runId: j['runId'],
    sourceDevice: j['sourceDevice'],
    startTime: DateTime.parse(j['startTime']),
    endTime: j['endTime'] == null ? null : DateTime.parse(j['endTime']),
    request: HttpMessage.fromJson(Map<String, dynamic>.from(j['request'])),
    response: j['response'] == null
        ? null
        : HttpMessage.fromJson(Map<String, dynamic>.from(j['response'])),
    captureStatus: j['captureStatus'],
    error: j['error'],
    timing: Map<String, dynamic>.from(j['timing'] ?? {}),
    connection: Map<String, dynamic>.from(j['connection'] ?? {}),
    tls: Map<String, dynamic>.from(j['tls'] ?? {}),
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'runId': runId,
    'sourceDevice': sourceDevice,
    'startTime': startTime.toUtc().toIso8601String(),
    'endTime': endTime?.toUtc().toIso8601String(),
    'request': request.toJson(),
    'response': response?.toJson(),
    'captureStatus': captureStatus,
    'error': error,
    'timing': timing,
    'connection': connection,
    'tls': tls,
  };
}

/// Body writes are finalized by the engine before terminal session events.
/// SQLite transactions + FULL synchronous WAL protect committed metadata.
class SessionStore {
  final Directory root;
  late final Database db;
  SessionStore(this.root) {
    root.createSync(recursive: true);
    Directory(p.join(root.path, 'bodies')).createSync();
    db = sqlite3.open(p.join(root.path, 'sessions.sqlite'));
    db.execute('PRAGMA journal_mode=WAL');
    db.execute('PRAGMA synchronous=FULL');
    db.execute(
      'CREATE TABLE IF NOT EXISTS sessions ('
      'ordinal INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,'
      'run_id TEXT NOT NULL, state TEXT NOT NULL, search TEXT NOT NULL, json TEXT NOT NULL)',
    );
  }
  void recoverInterrupted() {
    final rows = db.select(
      "SELECT json FROM sessions WHERE state IN ('receiving','pending')",
    );
    for (final row in rows) {
      final j = jsonDecode(row['json']) as Map<String, dynamic>;
      j['captureStatus'] = 'interrupted';
      j['error'] = 'Capture process ended before terminal event';
      save(CaptureSession.fromJson(j));
    }
  }

  void save(CaptureSession s) {
    db.execute(
      'INSERT INTO sessions(id,run_id,state,search,json) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,search=excluded.search,json=excluded.json',
      [
        s.id,
        s.runId,
        s.captureStatus,
        '${s.request.method} ${s.request.url} ${s.response?.status ?? ''}'
            .toLowerCase(),
        jsonEncode(s.toJson()),
      ],
    );
  }

  int count([String filter = '']) =>
      db.select('SELECT count(*) n FROM sessions WHERE instr(search,?)>0', [
            filter.toLowerCase(),
          ]).first['n']
          as int;
  List<CaptureSession> page({
    int offset = 0,
    int limit = 200,
    String filter = '',
  }) => db
      .select(
        'SELECT json FROM sessions WHERE instr(search,?)>0 ORDER BY ordinal LIMIT ? OFFSET ?',
        [filter.toLowerCase(), limit, offset],
      )
      .map((r) => CaptureSession.fromJson(jsonDecode(r['json'])))
      .toList();
  Iterable<CaptureSession> all({Set<String>? ids}) sync* {
    int offset = 0;
    while (true) {
      final rows = page(offset: offset, limit: 100);
      if (rows.isEmpty) break;
      for (final s in rows) {
        if (ids == null || ids.contains(s.id)) yield s;
      }
      offset += rows.length;
    }
  }

  File bodyFile(BodyReference b) {
    final path = p.join(root.path, b.path);
    if (FileSystemEntity.isLinkSync(path))
      throw StateError('Symlink body refused');
    final f = File(path);
    if (!p.isWithin(
      root.resolveSymbolicLinksSync(),
      f.resolveSymbolicLinksSync(),
    ))
      throw StateError('Body outside store');
    return f;
  }

  Stream<List<int>> body(BodyReference? b) async* {
    if (b == null) return;
    final f = bodyFile(b);
    if (await f.length() < b.size)
      throw StateError('Body file shorter than committed reference');
    yield* f.openRead(0, b.size);
  }

  void clear() {
    db.execute('DELETE FROM sessions');
    for (final file in Directory(p.join(root.path, 'bodies')).listSync()) {
      if (file is File) file.deleteSync();
    }
  }

  void close() => db.dispose();
}

abstract interface class CaptureEngine {
  Stream<Map<String, dynamic>> get events;
  Future<void> start({int port = 8877, bool decrypt = true});
  Future<void> pause(bool paused);
  Future<void> stop();
}
