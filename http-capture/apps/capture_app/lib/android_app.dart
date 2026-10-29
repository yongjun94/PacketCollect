import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:capture_core/capture_core.dart';
import 'package:capture_export/capture_export.dart';
import 'platform/local_proxy_engine.dart';

const bouncyCastleLicense = '''Bouncy Castle bcpkix-jdk15to18, bcprov-jdk15to18, bcutil-jdk15to18 1.86
https://www.bouncycastle.org/license.html

Copyright (c) 2000 - 2026 The Legion of the Bouncy Castle Inc. (https://www.bouncycastle.org)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
''';

const androidBridge = MethodChannel('dev.httpcapture/android');

class AndroidCaptureApp extends StatelessWidget {
  final String storePath;
  const AndroidCaptureApp({super.key, required this.storePath});
  @override
  Widget build(BuildContext context) => MaterialApp(theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true), home: _Capture(root: storePath));
}
class _Capture extends StatefulWidget {
  final String root;
  const _Capture({required this.root});
  @override
  State<_Capture> createState() => _CaptureState();
}
class _CaptureState extends State<_Capture> {
  late final SessionStore store;
  LocalProxyEngine? engine;
  StreamSubscription<Map<String,dynamic>>? subscription;
  bool busy = false, running = false, paused = false;
  Timer? heartbeat;
  Future<void>? stopping;
  String status = 'Stopped', filter = '';
  bool decrypt = false;
  final identities = <String, Future<SecurityContext>>{};
  Future<SecurityContext> identity(String host) {
    if(identities.length >= 128) identities.clear();
    return identities.putIfAbsent(host, () async {
      final data = await androidBridge.invokeMapMethod<String,dynamic>('tlsIdentity', {'host':host});
      return SecurityContext()..useCertificateChainBytes(utf8.encode(data!['certificate'] as String))..usePrivateKeyBytes(utf8.encode(data['key'] as String));
    });
  }
  Future<void> httpsSettings() async {
    var info=(await androidBridge.invokeMapMethod<String,dynamic>('caInfo'))!;
    if(!mounted) return;
    String? message;
    await showDialog<void>(context:context,builder:(c)=>StatefulBuilder(builder:(c,update)=>AlertDialog(
      title:const Text('HTTPS 복호화'),
      content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
        SwitchListTile(title:const Text('모든 호스트 복호화'),value:decrypt,onChanged:(v){setState(()=>decrypt=v);update((){});}),
        const Text('프록시를 사용하는 모든 HTTPS 연결에 적용합니다. 사용자 CA를 신뢰하지 않거나 인증서 고정을 사용하는 앱은 연결이 실패할 수 있습니다. 문제가 생기면 이 기능을 끄고 캡처를 다시 시작하세요.'),
        Text(info['trusted']==true ? '인증서: 기기 저장소에서 확인됨' : '인증서: 설치 필요'),
        Text('인증서 준비를 누르면 Downloads에 HTTP-Capture-Root-${(info['fingerprint'] as String).replaceAll(":","").substring(56)}.crt를 저장하고 보안 설정을 엽니다. Android 11 이상에서는 설정에서 CA 인증서를 직접 선택해 설치해야 합니다.'),
        if(info['profileCurrent']==false) ...[
          const Text('이전 CA에는 SKI/AKI가 없습니다. 규격 업데이트 후 새 인증서를 설치해야 합니다.'),
          TextButton(onPressed:() async {
            final approved=await showDialog<bool>(context:c,builder:(d)=>AlertDialog(
              title:const Text('CA 인증서 규격 업데이트'),
              content:const Text('로컬 CA 키는 유지하고 공개 인증서를 다시 발급합니다. 지문이 바뀌므로 이전 HTTP Capture CA를 Android 설정에서 제거하고 새 CA를 설치해야 합니다. 캡처 데이터는 유지됩니다. 진행하시겠습니까?'),
              actions:[TextButton(onPressed:()=>Navigator.pop(d,false),child:const Text('취소')),
                FilledButton(onPressed:()=>Navigator.pop(d,true),child:const Text('업데이트'))]));
            if(approved!=true)return;
            try {
              final next=(await androidBridge.invokeMapMethod<String,dynamic>('caUpgrade',{'consent':true}))!;
              identities.clear();
              if(!mounted)return;
              setState(()=>decrypt=false);
              if(c.mounted)update((){info=next;message='규격 업데이트 완료. 인증서 준비 버튼으로 새 CA를 설치한 뒤 복호화를 다시 켜세요.';});
            } catch(e) { if(c.mounted)update(()=>message='규격 업데이트 실패: $e'); }
          },child:const Text('CA 규격 업데이트')),
        ],
        if(message!=null) Text(message!),
        FilledButton(onPressed:() async { try { final value=await androidBridge.invokeMethod<String>('prepareCa'); if(c.mounted) update(()=>message=value??'보안 설정에서 인증서를 설치해 주세요.'); } catch(e) { if(c.mounted) update(()=>message='인증서 준비 실패: $e'); } },child:const Text('인증서 준비 및 설정 열기')),
        TextButton(onPressed:() async {try {final next=(await androidBridge.invokeMapMethod<String,dynamic>('caInfo'))!;if(c.mounted)update((){info=next;message='인증서 상태를 확인했습니다.';});}catch(e){if(c.mounted)update(()=>message='상태 확인 실패: $e');}},child:const Text('설치 상태 확인')),
        ExpansionTile(title:const Text('인증서 정보 및 제거'),children:[SelectableText('SHA-256: ${info['fingerprint']}'),const Text('제거하려면 Android 사용자 인증서 설정에서 일치하는 지문을 확인하세요.'),TextButton(onPressed:()=>androidBridge.invokeMethod('securitySettings'),child:const Text('보안 설정 열기'))]),
      ])),actions:[FilledButton(onPressed:()=>Navigator.pop(c),child:const Text('완료'))])));
  }
  Future<void> selfTestHttps() async {
    await androidBridge.invokeMapMethod<String,dynamic>('certificateProfileCheck');
    final info=await androidBridge.invokeMapMethod<String,dynamic>('caInfo');
    final trust=SecurityContext(withTrustedRoots:false)..setTrustedCertificatesBytes(utf8.encode(info!['pem'] as String));
    final origin=await HttpServer.bindSecure(InternetAddress.loopbackIPv4,0,await identity('127.0.0.1'));
    origin.listen((r) async {
      await r.drain<void>();
      r.response.headers.add('Set-Cookie','test=one');r.response.headers.add('Set-Cookie','other=two');
      r.response.add([0,1,2,255]);await r.response.close();
    },onError:(Object _){});
    final proxy=LocalProxyEngine(Directory(widget.root),tlsIdentity:identity,decryptHosts:{'127.0.0.1'},upstreamContext:trust);
    final captured=<CaptureSession>[];
    final sub=proxy.events.listen((event){if(event['type']=='session'){final session=CaptureSession.fromJson(Map<String,dynamic>.from(event['session']));captured.add(session);store.save(session);}});
    final client=HttpClient(context:trust);
    try {
      await proxy.start(port:0,decrypt:true);
      client.findProxy=(_)=>'PROXY 127.0.0.1:${proxy.port}';
      final req=await client.postUrl(Uri.parse('https://127.0.0.1:${origin.port}/capture-https-self-test'));
      req.add([9,8,7]);final response=await req.close();
      final bytes=await response.fold<List<int>>([], (a,b)=>a..addAll(b));
      if(response.statusCode!=200 || bytes.join(',')!='0,1,2,255') throw StateError('HTTPS body mismatch');
      client.close(force:true);await proxy.stop();
      final hit=captured.singleWhere((s)=>s.request.url!.endsWith('/capture-https-self-test'));
      if(hit.captureStatus!='complete' || hit.request.body!.size!=3 || hit.response!.body!.size!=4) throw StateError('HTTPS session mismatch');
      // Untrusted upstream must fail, even when interception CA is trusted by client.
      final rejecting=LocalProxyEngine(Directory(widget.root),tlsIdentity:identity,decryptHosts:{'127.0.0.1'});
      final check=HttpClient(context:trust);
      try {
        await rejecting.start(port:0,decrypt:true);check.findProxy=(_)=>'PROXY 127.0.0.1:${rejecting.port}';
        final rejected=await (await check.getUrl(Uri.parse('https://127.0.0.1:${origin.port}/untrusted-origin'))).close();
        await rejected.drain<void>();
        if(rejected.statusCode!=502) throw StateError('Untrusted upstream was accepted');
      } finally { check.close(force:true);await rejecting.stop(); }
      if(mounted) setState(()=>status='HTTPS test passed · decrypted binary body · untrusted upstream rejected');
    } finally { client.close(force:true);await proxy.stop();await sub.cancel();await origin.close(force:true); }
  }
  CaptureSession? selected;
  @override
  void initState() {
    super.initState();
    LicenseRegistry.addLicense(() async* { yield const LicenseEntryWithLineBreaks(['Bouncy Castle 1.86'],bouncyCastleLicense); });
    store = SessionStore(Directory(widget.root))..recoverInterrupted();
    androidBridge.setMethodCallHandler((call) async { if(call.method == 'revoked') await stop(); });
  }
  Future<void> action(Future<void> Function() fn) async {
    setState(() => busy = true);
    try { await fn(); } catch(e) { if(mounted) setState(() => status = '$e'); }
    finally { if(mounted) setState(() => busy = false); }
  }
  Future<void> start() async {
    final proxy = LocalProxyEngine(Directory(widget.root), tlsIdentity:identity, decryptAllHosts:true);
    subscription = proxy.events.listen((event) {
      if (event['type'] == 'session') {
        store.save(CaptureSession.fromJson(Map<String,dynamic>.from(event['session'])));
      } else { status = '${event['error']}'; }
      if(mounted) setState(() {});
    });
    try {
      await proxy.start(port: 8877, decrypt:decrypt);
      engine = proxy;
      await androidBridge.invokeMethod('start', {'port': 8877});
      await Future<void>.delayed(const Duration(milliseconds:300));
      if (!mounted || WidgetsBinding.instance.lifecycleState != AppLifecycleState.resumed) {
        await stop(); return;
      }
      setState(() { running = true; paused = false; status = 'VPN proxy active · releases automatically on Stop'; });
      heartbeat?.cancel();
      heartbeat = Timer.periodic(const Duration(seconds:2), (_) async {
        try {
          if(await androidBridge.invokeMethod<bool>('heartbeat') != true) await stop();
        } catch(e) { heartbeat?.cancel(); try { await stop(); } catch(_) {} if(mounted) setState(() => status = '$e'); }
      });
    } catch(_) { try { await androidBridge.invokeMethod('stop'); } finally { await proxy.stop(); await subscription?.cancel(); engine = null; } rethrow; }
  }
  Future<void> stop() {
    if (stopping != null) return stopping!;
    final work = _stop();
    stopping = work;
    return work.whenComplete(() => stopping = null);
  }
  Future<void> _stop() async {
    // Keep the local listener alive until Android confirms its VPN proxy is gone.
    await androidBridge.invokeMethod('stop');
    heartbeat?.cancel(); heartbeat = null;
    await engine?.stop(); await subscription?.cancel(); engine = null;
    if(mounted) setState(() { running = false; paused = false; status = 'Stopped · VPN proxy released'; });
  }
  Future<void> export(bool saz) async {
    final approved = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Sensitive data'), content: const Text('The archive can contain cookies, tokens and personal data. Save only to an approved local location. Android document providers may include cloud destinations.'), actions: [TextButton(onPressed: () => Navigator.pop(c,false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(c,true), child: const Text('Continue'))]));
    if(approved != true) return;
    final path = '${widget.root}/capture.${saz ? 'saz' : 'har'}';
    if(saz) { await SazExporter().export(store,path); } else { await HarExporter().export(store,path); }
    try { await androidBridge.invokeMethod('export', {'path':path,'name':'capture.${saz ? 'saz' : 'har'}'}); }
    finally { await File(path).delete(); }
  }
  Future<void> selfTest() async {
    // Real HTTP request through the proxy to a device-local origin, no fixture session injection.
    final origin = await HttpServer.bind(InternetAddress.loopbackIPv4,0);
    final listener = origin.listen((r) { r.response.headers.set('Content-Type','application/octet-stream'); r.response.add([0,1,2,255]); unawaited(r.response.close()); });
    final client = HttpClient()..findProxy = (_) => 'PROXY 127.0.0.1:8877';
    try {
      final req = await client.getUrl(Uri.parse('http://127.0.0.1:${origin.port}/capture-self-test'));
      final response = await req.close();
      final bytes = await response.fold<List<int>>([], (a,b) => a..addAll(b));
      if(bytes.join(',') != '0,1,2,255') throw StateError('HTTP body mismatch');
      setState(() => status = 'Local proxy round trip passed · 4 binary bytes');
    } finally { client.close(force:true); await origin.close(force:true); await listener.cancel(); }
  }
  @override
  void dispose() {
    heartbeat?.cancel();
    androidBridge.setMethodCallHandler(null);
    unawaited(engine?.stop() ?? Future.value());
    subscription?.cancel(); store.close(); super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    final sessions = store.page(limit:200, filter:filter).reversed.toList();
    return PopScope(canPop: !running, onPopInvokedWithResult:(didPop,result) async { if(!didPop){await action(() async { await stop(); await SystemNavigator.pop(); });} }, child: Scaffold(appBar: AppBar(title: const Text('HTTP Capture · HTTPS Preview')), body: SafeArea(child: Column(children:[
      Padding(padding:const EdgeInsets.all(12),child: Text(status)),
      const Padding(padding:EdgeInsets.symmetric(horizontal:12),child:Text('HTTP + optional HTTPS decryption for all proxy-aware hosts. Switching apps keeps capture active.')),
      const Padding(padding:EdgeInsets.all(12),child:Text('Temporary VPN proxy only. Wi-Fi proxy settings must stay unchanged. Stop or closing this app releases the VPN; switching apps keeps capture active. Proxy-aware apps only; this replaces any existing VPN.')),
      Wrap(spacing:8,children:[
        TextButton(onPressed:()=>showLicensePage(context:context),child:const Text('Licenses')),
        TextButton(onPressed:running||busy?null:()=>action(httpsSettings),child:Text(decrypt?'HTTPS on':'HTTPS settings')),
        TextButton(onPressed:running||busy?null:()=>action(selfTestHttps),child:const Text('Test TLS')),
        FilledButton(onPressed:busy?null:()=>action(running?stop:start),child:Text(running?'Stop':'Start')),
        TextButton(onPressed:!running||busy?null:()=>action(() async { paused=!paused;await engine!.pause(paused);setState((){}); }),child:Text(paused?'Resume':'Pause')),
        TextButton(onPressed:!running||busy?null:()=>action(selfTest),child:const Text('Test HTTP')),
        TextButton(onPressed:running||busy?null:()=>action(()=>export(true)),child:const Text('SAZ')),
        TextButton(onPressed:running||busy?null:()=>action(()=>export(false)),child:const Text('HAR')),
        TextButton(onPressed:running||busy?null:() async { final yes=await showDialog<bool>(context:context,builder:(c)=>AlertDialog(content:const Text('Delete all stored sessions and bodies?'),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Cancel')),TextButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Delete'))]));if(yes==true){store.clear();setState(()=>selected=null);} },child:const Text('Clear')),
      ]),
      TextButton(onPressed:busy?null:()=>androidBridge.invokeMethod('wifiSettings'),child:const Text('Wi-Fi settings · remove old manual proxy once')),
      TextField(decoration:InputDecoration(labelText:'Filter · ${store.count(filter)} sessions (latest 200 shown)'),onChanged:(v)=>setState(()=>filter=v)),
      Expanded(child:ListView.builder(itemCount:sessions.length,itemBuilder:(c,i){final s=sessions[i];return ListTile(title:Text('${s.request.method} ${s.response?.status ?? s.captureStatus}'),subtitle:Text(s.request.url??''),onTap:()=>showDialog<void>(context:context,builder:(c)=>AlertDialog(title:const Text('Session'),content:SingleChildScrollView(child:SelectableText('${s.request.url}\n${s.captureStatus}\n${s.error??''}\n\nRequest\n${s.request.headers.map((h)=>'${h.name}: ${h.value}').join('\n')}\n\nResponse\n${s.response?.headers.map((h)=>'${h.name}: ${h.value}').join('\n')??''}\n${s.response == null ? (s.captureStatus == 'tunneled' ? 'HTTPS 터널 · 응답 내용 미수집 (복호화 꺼짐)' : '응답 내용 미수집') : 'Body: ${s.response?.body?.size??0} bytes'}\n\nTLS\n${s.tls.entries.map((e)=>'${e.key}: ${e.value}').join('\n')}')),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('Close'))]))); })),
    ]))));
  }
}


