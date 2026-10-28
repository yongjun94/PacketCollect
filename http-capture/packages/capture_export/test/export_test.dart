import 'dart:convert';
import 'dart:io';
import 'package:capture_core/capture_core.dart';
import 'package:capture_export/capture_export.dart';
import 'package:test/test.dart';

void main() {
  late Directory dir;
  late SessionStore store;
  setUp(() {
    dir = Directory.systemTemp.createTempSync('http-export-');
    store = SessionStore(dir);
  });
  tearDown(() {
    store.close();
    dir.deleteSync(recursive: true);
  });
  CaptureSession fixture({
    String id = 'one',
    String status = 'complete',
    bool response = true,
  }) {
    final raw = [0, 255, 13, 10, 128, 0];
    File('${dir.path}/bodies/$id.response.bin').writeAsBytesSync(raw);
    return CaptureSession(
      id: id,
      runId: 'run',
      sourceDevice: '127.0.0.1',
      startTime: DateTime.utc(2026),
      endTime: DateTime.utc(2026).add(const Duration(milliseconds: 10)),
      request: HttpMessage(
        version: 'HTTP/2.0',
        headers: [
          Header.text('Cookie', 'a=1; b=2'),
          Header.text('X-Multi', '1'),
          Header.text('X-Multi', '2'),
        ],
        method: 'GET',
        url: 'https://example.test/a?q=1&q=2',
      ),
      response: response
          ? HttpMessage(
              version: 'HTTP/2.0',
              headers: [
                Header.text('Content-Type', 'application/octet-stream'),
                Header.text('Set-Cookie', 'a=1; HttpOnly'),
                Header.text('Set-Cookie', 'b=2; Secure'),
              ],
              status: 200,
              reason: '',
              body: BodyReference('bodies/$id.response.bin', raw.length, true),
            )
          : null,
      captureStatus: status,
      timing: {'send': 2, 'wait': 3, 'receive': 5},
    );
  }

  test('SQLite roundtrip preserves duplicate order and raw bytes', () {
    store.save(fixture());
    store.close();
    store = SessionStore(dir);
    final s = store.all().single;
    expect(s.request.headers.map((h) => h.value), ['a=1; b=2', '1', '2']);
    expect(store.bodyFile(s.response!.body!).readAsBytesSync(), [
      0,
      255,
      13,
      10,
      128,
      0,
    ]);
  });
  test(
    'HAR retains binary bytes, cookies, duplicate query, measured timings',
    () async {
      store.save(fixture());
      await HarExporter().export(store, '${dir.path}/a.har');
      final e = jsonDecode(
        File('${dir.path}/a.har').readAsStringSync(),
      )['log']['entries'][0];
      expect(base64.decode(e['response']['content']['text']), [
        0,
        255,
        13,
        10,
        128,
        0,
      ]);
      expect(e['request']['queryString'].length, 2);
      expect(e['response']['cookies'].length, 2);
      expect(e['request']['cookies'].length, 2);
      expect(e['time'], 10);
      expect(await validateHar(File('${dir.path}/a.har')), 1);
    },
  );
  test('Missing response is explicit; no invented status success', () async {
    store.save(fixture(response: false, status: 'error'));
    await HarExporter().export(store, '${dir.path}/e.har');
    final e = jsonDecode(
      File('${dir.path}/e.har').readAsStringSync(),
    )['log']['entries'][0];
    expect(e['response']['status'], 0);
    expect(e['_captureStatus'], 'error');
    await SazExporter().export(store, '${dir.path}/e.saz');
  });
  test(
    'Failed export removes partial and does not replace destination',
    () async {
      store.save(fixture());
      File('${dir.path}/bodies/one.response.bin').deleteSync();
      await expectLater(
        SazExporter().export(store, '${dir.path}/bad.saz'),
        throwsA(isA<FileSystemException>()),
      );
      expect(dir.listSync().where((f) => f.path.endsWith('.partial')), isEmpty);
      expect(File('${dir.path}/bad.saz').existsSync(), false);
      File('${dir.path}/exists.har').writeAsStringSync('keep');
      await expectLater(
        HarExporter().export(store, '${dir.path}/exists.har'),
        throwsA(isA<FileSystemException>()),
      );
      expect(File('${dir.path}/exists.har').readAsStringSync(), 'keep');
    },
  );
  test('Crash recovery and filtering are durable', () {
    store.save(fixture(status: 'receiving'));
    store.recoverInterrupted();
    expect(store.all().single.captureStatus, 'interrupted');
    expect(store.count('EXAMPLE.TEST'), 1);
    expect(store.count('absent'), 0);
  });
  test('Body references reject traversal and headers reject CRLF', () {
    expect(() => BodyReference('../secret', 1, true), throwsFormatException);
    expect(() => Header.text('X-Test', 'a\r\nb'), throwsFormatException);
  });
  test('Selected and empty exports have correct entry counts', () async {
    store.save(fixture());
    store.save(fixture(id: 'two'));
    await HarExporter().export(store, '${dir.path}/selected.har', ids: {'two'});
    expect(await validateHar(File('${dir.path}/selected.har')), 1);
    await SazExporter().export(store, '${dir.path}/selected.saz', ids: {'two'});
    store.clear();
    await HarExporter().export(store, '${dir.path}/empty.har');
    expect(await validateHar(File('${dir.path}/empty.har')), 0);
  });
}
