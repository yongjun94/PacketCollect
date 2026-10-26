import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:capture_core/capture_core.dart';
import 'package:path/path.dart' as p;

class DesktopEngine implements CaptureEngine {
  final String storePath;
  // Injection also permits testing the real stdio lifecycle without a proxy listener.
  final List<String>? launchCommand;
  final _events = StreamController<Map<String, dynamic>>.broadcast();
  final _pending = <int, Completer<dynamic>>{};
  Process? process;
  Future<void>? _exited;
  int _id = 0;

  DesktopEngine(this.storePath, {this.launchCommand});

  List<String> get _command {
    if (launchCommand != null) return launchCommand!;
    final python = Platform.environment['HTTP_CAPTURE_PYTHON'];
    if (python != null) return [python, '-m', 'capture_proxy.main'];
    return [
      Platform.environment['HTTP_CAPTURE_ENGINE'] ??
          p.join(
            p.dirname(Platform.resolvedExecutable),
            if (Platform.isMacOS) '..',
            if (Platform.isMacOS) 'Resources',
            'proxy',
            Platform.isWindows
                ? 'http-capture-proxy.exe'
                : 'http-capture-proxy',
          ),
    ];
  }

  @override
  Stream<Map<String, dynamic>> get events => _events.stream;

  @override
  Future<void> start({int port = 8877, bool decrypt = true}) async {
    if (process != null) throw StateError('Engine already running');
    final command = _command;
    final ready = Completer<void>();
    final current = await Process.start(command.first, [
      ...command.skip(1),
      '--store',
      storePath,
      '--port',
      '$port',
      if (!decrypt) '--no-decrypt',
    ]);
    process = current;
    final stdoutDone = Completer<void>();
    final stderrDone = current.stderr.drain<void>().catchError((Object _) {});

    void fail(Object error) {
      if (!ready.isCompleted) ready.completeError(error);
      _events.add({'type': 'fatal', 'error': '$error'});
    }

    current.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
          (line) {
            try {
              final event = jsonDecode(line) as Map<String, dynamic>;
              final type = event['type'];
              if (type == 'ready' && !ready.isCompleted) ready.complete();
              if (type == 'fatal' && !ready.isCompleted) {
                ready.completeError(StateError('${event['error']}'));
              }
              if (type == 'command_error') {
                _pending
                    .remove(event['id'])
                    ?.completeError(StateError('${event['error']}'));
              }
              if (type == 'ack')
                _pending.remove(event['id'])?.complete(event['result']);
              _events.add(event);
            } catch (error) {
              fail(StateError('Invalid engine event: $error'));
            }
          },
          onError: (Object error) => fail(error),
          onDone: () => stdoutDone.complete(),
        );

    // OS exit can precede delivery of the last pipe data on Windows. Drain both
    // pipes before marking the engine stopped or recovering unfinished sessions.
    Future<void> finish() async {
      final code = await current.exitCode;
      await Future.wait([stdoutDone.future, stderrDone]);
      if (identical(process, current)) process = null;
      if (!ready.isCompleted)
        ready.completeError(StateError('Engine exited ($code)'));
      for (final c in _pending.values) {
        c.completeError(StateError('Engine exited ($code)'));
      }
      _pending.clear();
      _events.add({'type': 'exit', 'code': code});
    }

    final finished = finish();
    _exited = finished;
    try {
      await ready.future.timeout(const Duration(seconds: 45));
    } catch (_) {
      current.kill();
      await finished;
      rethrow;
    }
  }

  Future<dynamic> command(
    String action, [
    Map<String, dynamic> data = const {},
  ]) async {
    final current = process;
    if (current == null) throw StateError('Start engine first');
    final id = ++_id;
    final completer = Completer<dynamic>();
    _pending[id] = completer;
    try {
      current.stdin.writeln(jsonEncode({'id': id, 'action': action, ...data}));
      return await completer.future.timeout(const Duration(seconds: 20));
    } finally {
      _pending.remove(id);
    }
  }

  Future<dynamic> settingsCommand(String action, [Map<String,dynamic> data=const{}]) async {
    if(process!=null) return command(action,data);
    final commandLine=_command;
    final child=await Process.start(commandLine.first,[...commandLine.skip(1),'--store',storePath,'--settings-action',action]);
    final output=child.stdout.transform(utf8.decoder).join();
    final errors=child.stderr.transform(utf8.decoder).join();
    child.stdin.writeln(jsonEncode(data));
    await child.stdin.close();
    final code=await child.exitCode.timeout(const Duration(seconds:30),onTimeout:(){child.kill();throw TimeoutException('Settings command timed out');});
    final text=await output;
    final stderr=await errors;
    final event=jsonDecode(text.trim().split('\n').last) as Map<String,dynamic>;
    if(code!=0||event['type']=='fatal')throw StateError(event['error']??stderr);
    return event['result'];
  }

  Future<void> recoverProxy() async {
    final command = _command;
    final result = await Process.run(command.first, [
      ...command.skip(1),
      '--store',
      storePath,
      '--recover-proxy',
    ]).timeout(const Duration(seconds: 30));
    if (result.exitCode != 0) {
      throw StateError('Proxy recovery failed: ${result.stdout}');
    }
  }

  @override
  Future<void> pause(bool paused) async {
    await command('pause', {'paused': paused});
  }

  @override
  Future<void> stop() async {
    final current = process;
    if (current == null) {
      await _exited;
      return;
    }
    await command('stop');
    await current.stdin.close();
    await _exited!.timeout(
      const Duration(seconds: 20),
      onTimeout: () async {
        current.kill();
        await _exited;
        throw TimeoutException('Engine forced to stop; check recovery journal');
      },
    );
  }

  Future<void> dispose() async {
    await stop();
    await _events.close();
  }
}
