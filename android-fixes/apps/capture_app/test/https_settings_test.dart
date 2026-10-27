import 'dart:io';
import 'package:capture_app/android_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('HTTPS settings report missing or invalid hosts and apply valid host', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200,1600));
    final dir=Directory.systemTemp.createTempSync('capture-settings-');
    const channel=MethodChannel('dev.httpcapture/android');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,(call) async {
      if(call.method=='caInfo') return {'path':'/tmp/root.crt','fingerprint':'TEST','trusted':false,'pem':''};
      return null;
    });
    try {
      await tester.pumpWidget(AndroidCaptureApp(storePath:dir.path));await tester.pumpAndSettle();
      await tester.tap(find.text('HTTPS settings'));await tester.pumpAndSettle();
      await tester.tap(find.byType(SwitchListTile));await tester.pumpAndSettle();
      await tester.tap(find.text('Apply'));await tester.pumpAndSettle();
      expect(find.text('Enter at least one host, for example example.com.'),findsOneWidget);
      await tester.enterText(find.byType(TextField).last,'https://example.com/path');await tester.pumpAndSettle();
      await tester.tap(find.text('Apply'));await tester.pumpAndSettle();
      expect(find.text('Enter host names only, without https://, ports, paths or wildcards.'),findsOneWidget);
      await tester.enterText(find.byType(TextField).last,'example.com');await tester.pumpAndSettle();
      await tester.tap(find.text('Apply'));await tester.pumpAndSettle();
      expect(find.text('HTTPS on'),findsOneWidget);
    } finally {
      await tester.pumpWidget(const SizedBox());
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,null);
      await tester.binding.setSurfaceSize(null);dir.deleteSync(recursive:true);
    }
  });
}
