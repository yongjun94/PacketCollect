import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:capture_core/capture_core.dart';
import 'package:capture_export/capture_export.dart';
import 'platform/local_proxy_engine.dart';

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
class _CaptureState extends State<_Capture> with WidgetsBindingObserver {
  late final SessionStore store;
  LocalProxyEngine? engine;
  StreamSubscription<Map<String,dynamic>>? subscription;
  bool busy = false, running = false, paused = false;
  Timer? heartbeat;
  Future<void>? stopping;
  String status = 'Stopped', filter = '';
  CaptureSession? selected;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    store = SessionStore(Directory(widget.root))..recoverInterrupted();
    androidBridge.setMethodCallHandler((call) async { if(call.method == 'revoked') await stop(); });
  }
  Future<void> action(Future<void> Function() fn) async {
    setState(() => busy = true);
    try { await fn(); } catch(e) { if(mounted) setState(() => status = '$e'); }
    finally { if(mounted) setState(() => busy = false); }
  }
  Future<void> start() async {
    final proxy = LocalProxyEngine(Directory(widget.root));
    subscription = proxy.events.listen((event) {
      if (event['type'] == 'session') {
        store.save(CaptureSession.fromJson(Map<String,dynamic>.from(event['session'])));
      } else { status = '${event['error']}'; }
      if(mounted) setState(() {});
    });
    try {
      await proxy.start(port: 8877);
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
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (running && (state == AppLifecycleState.paused || state == AppLifecycleState.hidden)) {
      unawaited(stop().catchError((Object e) { if(mounted) setState(() => status = '$e'); }));
    }
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
    WidgetsBinding.instance.removeObserver(this);
    heartbeat?.cancel();
    androidBridge.setMethodCallHandler(null);
    unawaited(engine?.stop() ?? Future.value());
    subscription?.cancel(); store.close(); super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    final sessions = store.page(limit:200, filter:filter).reversed.toList();
    return PopScope(canPop: !running, onPopInvokedWithResult:(didPop,result) async { if(!didPop){await action(() async { await stop(); await SystemNavigator.pop(); });} }, child: Scaffold(appBar: AppBar(title: const Text('HTTP Capture · Safe Preview')), body: SafeArea(child: Column(children:[
      Padding(padding:const EdgeInsets.all(12),child: Text(status)),
      const Padding(padding:EdgeInsets.symmetric(horizontal:12),child:Text('HTTP capture only. HTTPS is forwarded without decryption. No TCP/UDP packet capture. Keep this preview open while capturing.')),
      const Padding(padding:EdgeInsets.all(12),child:Text('Temporary VPN proxy only. Wi-Fi proxy settings must stay unchanged. Stop, leaving the app or closing it releases the VPN. Proxy-aware apps only; this replaces any existing VPN.')),
      Wrap(spacing:8,children:[
        FilledButton(onPressed:busy?null:()=>action(running?stop:start),child:Text(running?'Stop':'Start')),
        TextButton(onPressed:!running||busy?null:()=>action(() async { paused=!paused;await engine!.pause(paused);setState((){}); }),child:Text(paused?'Resume':'Pause')),
        TextButton(onPressed:!running||busy?null:()=>action(selfTest),child:const Text('Test HTTP')),
        TextButton(onPressed:running||busy?null:()=>action(()=>export(true)),child:const Text('SAZ')),
        TextButton(onPressed:running||busy?null:()=>action(()=>export(false)),child:const Text('HAR')),
        TextButton(onPressed:running||busy?null:() async { final yes=await showDialog<bool>(context:context,builder:(c)=>AlertDialog(content:const Text('Delete all stored sessions and bodies?'),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('Cancel')),TextButton(onPressed:()=>Navigator.pop(c,true),child:const Text('Delete'))]));if(yes==true){store.clear();setState(()=>selected=null);} },child:const Text('Clear')),
      ]),
      TextButton(onPressed:busy?null:()=>androidBridge.invokeMethod('wifiSettings'),child:const Text('Wi-Fi settings · remove old manual proxy once')),
      TextField(decoration:InputDecoration(labelText:'Filter · ${store.count(filter)} sessions (latest 200 shown)'),onChanged:(v)=>setState(()=>filter=v)),
      Expanded(child:ListView.builder(itemCount:sessions.length,itemBuilder:(c,i){final s=sessions[i];return ListTile(title:Text('${s.request.method} ${s.response?.status ?? s.captureStatus}'),subtitle:Text(s.request.url??''),onTap:()=>showDialog<void>(context:context,builder:(c)=>AlertDialog(title:const Text('Session'),content:SingleChildScrollView(child:SelectableText('${s.request.url}\n${s.captureStatus}\n${s.error??''}\n\nRequest\n${s.request.headers.map((h)=>'${h.name}: ${h.value}').join('\n')}\n\nResponse\n${s.response?.headers.map((h)=>'${h.name}: ${h.value}').join('\n')??''}\nBody: ${s.response?.body?.size??0} bytes')),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('Close'))]))); })),
    ]))));
  }
}
