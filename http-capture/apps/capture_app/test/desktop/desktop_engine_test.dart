import 'dart:io';
import 'package:capture_app/platform/desktop_engine.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late Directory root;
  late File script;
  setUp(() {
    root = Directory.systemTemp.createTempSync('http-capture-ipc-');
    script = File('${root.path}/engine_fixture.py')
      ..writeAsStringSync(r'''
import json, sys, time
if '--fail' in sys.argv:
    print(json.dumps({'type':'fatal','error':'fixture startup failure'}),flush=True)
    sys.exit(1)
print(json.dumps({'type':'ready'}),flush=True)
for line in sys.stdin:
    command=json.loads(line)
    if command['action']=='stop':
        # Final stdout must be delivered before the parent sees the exit event.
        print(json.dumps({'type':'session','marker':'last'}),flush=True)
        print(json.dumps({'type':'ack','id':command['id'],'result':None}),flush=True)
        break
    if command['action']=='bad':
        print(json.dumps({'type':'command_error','id':command['id'],'error':'fixture rejection'}),flush=True)
    else:
        print(json.dumps({'type':'ack','id':command['id'],'result':command.get('paused')}),flush=True)
''');
  });
  tearDown(() => root.deleteSync(recursive: true));
  DesktopEngine engine({bool fail = false}) => DesktopEngine(
    root.path,
    launchCommand: [
      Platform.environment['HTTP_CAPTURE_TEST_PYTHON'] ?? 'python',
      script.path,
      if (fail) '--fail',
    ],
  );

  test('Stop drains terminal events before exit and permits restart', () async {
    final client = engine();
    final events = <Map<String, dynamic>>[];
    final subscription = client.events.listen(events.add);
    await client.start();
    await client.pause(true);
    await client.pause(false);
    await client.stop();
    await Future<void>.delayed(Duration.zero);
    expect(events.where((e) => e['type'] == 'session').length, 1);
    expect(events.last['type'], 'exit');
    expect(client.process, isNull);
    await client.start();
    await client.stop();
    await client.dispose();
    await subscription.cancel();
  });

  test(
    'Startup failure exits cleanly instead of leaving a live process',
    () async {
      final client = engine(fail: true);
      await expectLater(client.start(), throwsStateError);
      expect(client.process, isNull);
      await client.dispose();
    },
  );

  test('Command rejection does not prevent a later graceful stop', () async {
    final client = engine();
    await client.start();
    await expectLater(client.command('bad'), throwsStateError);
    await client.stop();
    await client.dispose();
  });
}
