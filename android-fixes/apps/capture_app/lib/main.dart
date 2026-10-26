import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'app.dart';
import 'android_app.dart';

// Keep the OS lock alive for this process. The OS releases it after a crash.
RandomAccessFile? _instanceLock;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    final root = await getApplicationSupportDirectory();
    await root.create(recursive: true);
    if (Platform.isWindows) {
      final who = await Process.run('whoami', [
        '/user',
        '/fo',
        'csv',
        '/nh',
      ], stdoutEncoding: latin1);
      if (who.exitCode != 0)
        throw StateError('Cannot determine local user SID');
      final sid = RegExp(
        r'S-1-[0-9-]+',
      ).firstMatch(who.stdout as String)?.group(0);
      if (sid == null) throw StateError('Cannot determine local user SID');
      final acl = await Process.run('icacls', [
        root.path,
        '/inheritance:r',
        '/grant:r',
        '*$sid:(OI)(CI)F',
      ]);
      if (acl.exitCode != 0)
        throw StateError('Cannot restrict capture directory permissions');
    } else if (!Platform.isAndroid) {
      final acl = await Process.run('chmod', ['700', root.path]);
      if (acl.exitCode != 0)
        throw StateError('Cannot restrict capture directory permissions');
    }
    _instanceLock = await File(
      '${root.path}/app.lock',
    ).open(mode: FileMode.append);
    try {
      await _instanceLock!.lock(FileLock.exclusive);
    } on FileSystemException {
      throw StateError(
        'HTTP Capture is already running, or the capture directory cannot be locked.',
      );
    }
    runApp(Platform.isAndroid ? AndroidCaptureApp(storePath: root.path) : CaptureApp(storePath: root.path));
  } catch (error) {
    await _instanceLock?.close();
    _instanceLock = null;
    runApp(
      MaterialApp(
        home: Scaffold(
          appBar: AppBar(title: const Text('HTTP Capture — Startup error')),
          body: Padding(
            padding: const EdgeInsets.all(24),
            child: SelectableText('$error'),
          ),
        ),
      ),
    );
  }
}
