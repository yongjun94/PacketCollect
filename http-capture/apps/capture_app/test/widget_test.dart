import 'dart:io';
import 'package:capture_app/app.dart';
import 'package:capture_core/capture_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Stored sessions are visible and open in the inspector', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    final dir = Directory.systemTemp.createTempSync('capture-widget-');
    final store = SessionStore(dir);
    store.save(
      CaptureSession(
        id: 'widget',
        runId: 'run',
        sourceDevice: 'local',
        startTime: DateTime.utc(2026),
        request: HttpMessage(
          version: 'HTTP/1.1',
          headers: [Header.text('X-Test', 'widget-value')],
          method: 'GET',
          url: 'https://example.test/test',
        ),
        captureStatus: 'error',
        error: 'Fixture without response',
      ),
    );
    store.close();
    await tester.pumpWidget(CaptureApp(storePath: dir.path));
    await tester.pump();
    expect(find.text('example.test'), findsOneWidget);
    await tester.tap(find.text('example.test'));
    await tester.pumpAndSettle();
    expect(find.text('X-Test: widget-value'), findsOneWidget);
    expect(find.text('Body not captured'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    dir.deleteSync(recursive: true);
  });
}
