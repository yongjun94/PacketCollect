import 'dart:io';
import 'package:capture_app/android_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  for (final approve in [false, true]) {
    testWidgets('Legacy CA upgrade requires explicit consent: $approve', (tester) async {
      await tester.binding.setSurfaceSize(const Size(1200, 2200));
      final dir = Directory.systemTemp.createTempSync('ca-upgrade-');
      const channel = MethodChannel('dev.httpcapture/android');
      final calls = <MethodCall>[];
      final legacy = {'path':'/tmp/root.crt', 'fingerprint':'A' * 64,
        'trusted':true, 'pem':'', 'profileCurrent':false};
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          calls.add(call);
          if (call.method == 'caInfo') return legacy;
          if (call.method == 'caUpgrade') {
            expect(call.arguments, {'consent':true});
            return {...legacy, 'fingerprint':'B' * 64, 'trusted':false, 'profileCurrent':true};
          }
          return null;
        });
      try {
        await tester.pumpWidget(AndroidCaptureApp(storePath:dir.path));
        await tester.pumpAndSettle();
        await tester.tap(find.text('HTTPS settings'));
        await tester.pumpAndSettle();
        await tester.tap(find.byType(SwitchListTile));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.text('CA 규격 업데이트'));
        await tester.tap(find.text('CA 규격 업데이트'));
        await tester.pumpAndSettle();
        // Merely opening the confirmation must never mutate the CA.
        expect(calls.where((c)=>c.method=='caUpgrade'), isEmpty);
        await tester.tap(find.text(approve ? '업데이트' : '취소'));
        await tester.pumpAndSettle();
        expect(calls.where((c)=>c.method=='caUpgrade').length, approve ? 1 : 0);
        if (approve) {
          expect(find.text('CA 규격 업데이트'), findsNothing);
          expect(find.text('인증서: 설치 필요'), findsOneWidget);
        }
        await tester.ensureVisible(find.text('완료'));
        await tester.tap(find.text('완료'));
        await tester.pumpAndSettle();
        expect(find.text(approve ? 'HTTPS settings' : 'HTTPS on'), findsOneWidget);
      } finally {
        await tester.pumpWidget(const SizedBox());
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel,null);
        await tester.binding.setSurfaceSize(null);
        dir.deleteSync(recursive:true);
      }
    });
  }
}
