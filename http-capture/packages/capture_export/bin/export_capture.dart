import 'dart:convert';
import 'dart:io';
import 'package:capture_core/capture_core.dart';
import 'package:capture_export/capture_export.dart';

Future<void> main(List<String> args) async {
  if (args.length != 2) {
    stderr.writeln(
      'Usage: dart run bin/export_capture.dart STORE OUTPUT_PREFIX',
    );
    exit(2);
  }
  final store = SessionStore(Directory(args[0]));
  try {
    final events = File('${args[0]}/events.ndjson');
    if (await events.exists()) {
      await for (final line
          in events
              .openRead()
              .transform(utf8.decoder)
              .transform(const LineSplitter())) {
        final event = jsonDecode(line);
        if (event['type'] == 'session')
          store.save(
            CaptureSession.fromJson(
              Map<String, dynamic>.from(event['session']),
            ),
          );
      }
    }
    store.recoverInterrupted();
    await SazExporter().export(store, '${args[1]}.saz');
    await HarExporter().export(store, '${args[1]}.har');
    stdout.writeln(
      jsonEncode({
        'sessions': store.count(),
        'harEntries': await validateHar(File('${args[1]}.har')),
      }),
    );
  } finally {
    store.close();
  }
}
