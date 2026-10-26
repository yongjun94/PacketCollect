import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:capture_app/platform/local_proxy_engine.dart';

SecurityContext identity() => SecurityContext()
  ..useCertificateChain('test/tls/leaf.pem')..usePrivateKey('test/tls/leaf.key');
SecurityContext trust() => SecurityContext(withTrustedRoots:false)..setTrustedCertificates('test/tls/ca.pem');
void main() {
  for(final mode in ['decrypt', 'upstream-rejected', 'client-rejected', 'tunnel']) {
    test('HTTPS $mode uses actual TLS sockets', () async {
      final root=await Directory.systemTemp.createTemp('https-test');
      final origin=await HttpServer.bindSecure(InternetAddress.loopbackIPv4,0,identity());
      origin.listen((r) async { await r.drain<void>();r.response.headers.add('Set-Cookie','a=1');r.response.headers.add('Set-Cookie','b=2');r.response.add([0,255,2]);await r.response.close(); },onError:(Object _){});
      final events=<Map<String,dynamic>>[];
      final engine=LocalProxyEngine(root,tlsIdentity:(_) async=>identity(),decryptHosts:{'127.0.0.1'},upstreamContext:mode=='upstream-rejected'?null:trust());
      final sub=engine.events.listen((e) { events.add(e); print('TLS fixture event: $e'); });
      final client=HttpClient(context:mode=='client-rejected'?null:trust());
      try {
        await engine.start(port:0,decrypt:mode!='tunnel');client.findProxy=(_)=>'PROXY 127.0.0.1:${engine.port}';
        Future<HttpClientResponse> send() async { final r=await client.postUrl(Uri.parse('https://127.0.0.1:${origin.port}/binary'));r.add([7,8]);return r.close(); }
        if(mode=='client-rejected') {
          await expectLater(send(),throwsA(isA<HandshakeException>()));
        } else {
          final response=await send();
          expect(response.statusCode,mode=='upstream-rejected'?502:200);
          final body=await response.fold<List<int>>([], (a,b)=>a..addAll(b));
          if(mode!='upstream-rejected') expect(body,[0,255,2]);
        }
        client.close(force:true);await engine.stop();
        if(mode=='decrypt') {
          final session=events.single['session'];
          expect(session['captureStatus'],'complete');
          expect(session['request']['url'],'https://127.0.0.1:${origin.port}/binary');
          expect(session['request']['body']['size'],2);
          expect(await File('${root.path}/${session['response']['body']['path']}').readAsBytes(),[0,255,2]);
        }
        if(mode=='upstream-rejected') expect(events.single['session']['captureStatus'],'error');
        if(mode=='tunnel') expect(events.single['session']['captureStatus'],'tunneled');
      } finally {client.close(force:true);await engine.stop();await sub.cancel();await origin.close(force:true);await root.delete(recursive:true);}
    },timeout:const Timeout(Duration(seconds:45)));
  }
}
