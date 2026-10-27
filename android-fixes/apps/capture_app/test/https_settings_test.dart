import 'dart:io';
import 'package:capture_app/android_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Enable all-host HTTPS without entering a host', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200,1600));
    final dir=Directory.systemTemp.createTempSync('capture-settings-');
    const channel=MethodChannel('dev.httpcapture/android');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,(call) async {
      if(call.method=='caInfo') return {'path':'/tmp/root.crt','fingerprint':'TEST','trusted':false,'pem':''};
      if(call.method=='prepareCa') return 'certificate prepared';
      return null;
    });
    try {
      await tester.pumpWidget(AndroidCaptureApp(storePath:dir.path));await tester.pumpAndSettle();
      await tester.tap(find.text('HTTPS settings'));await tester.pumpAndSettle();
      await tester.tap(find.byType(SwitchListTile));await tester.pumpAndSettle();
      await tester.tap(find.text('인증서 준비 및 설정 열기'));await tester.pumpAndSettle();
      expect(find.text('certificate prepared'),findsOneWidget);
      await tester.tap(find.text('완료'));await tester.pumpAndSettle();
      expect(find.text('HTTPS on'),findsOneWidget);
    } finally {
      await tester.pumpWidget(const SizedBox());
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,null);
      await tester.binding.setSurfaceSize(null);dir.deleteSync(recursive:true);
    }
  });
}
