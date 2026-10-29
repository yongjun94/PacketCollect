import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:capture_app/platform/local_proxy_engine.dart';

SecurityContext identity() => SecurityContext()
  ..useCertificateChain('test/android/tls/leaf.pem')..usePrivateKey('test/android/tls/leaf.key');
SecurityContext trust() => SecurityContext(withTrustedRoots:false)..setTrustedCertificates('test/android/tls/ca.pem');
void main() {
  for(final mode in ['decrypt', 'decrypt-all', 'alpn', 'upstream-rejected', 'client-rejected', 'tunnel']) {
    test('HTTPS $mode uses actual TLS sockets', () async {
      final root=await Directory.systemTemp.createTemp('https-test');
      final seen=<String>[];
      final origin=await HttpServer.bindSecure(InternetAddress.loopbackIPv4,0,identity());
      origin.listen((r) async { seen.add(r.uri.toString()); await r.drain<void>();r.response.headers.add('Set-Cookie','a=1');r.response.headers.add('Set-Cookie','b=2');r.response.add([0,255,2]);await r.response.close(); },onError:(Object _){});
      final events=<Map<String,dynamic>>[];
      final engine=LocalProxyEngine(root,tlsIdentity:(_) async=>identity(),decryptHosts:mode=='decrypt-all'?{'localhost'}:{'127.0.0.1'},decryptAllHosts:mode=='decrypt-all',upstreamContext:mode=='upstream-rejected'?null:trust());
      final sub=engine.events.listen((e) { events.add(e); print('TLS fixture event: $e'); });
      final clientTrust = trust();
      if (mode == 'alpn') clientTrust.setAlpnProtocols(['h2', 'http/1.1'], false);
      final client=HttpClient(context:mode=='client-rejected'?null:clientTrust);
      try {
        await engine.start(port:0,decrypt:mode!='tunnel');client.findProxy=(_)=>'PROXY 127.0.0.1:${engine.port}';
        Future<HttpClientResponse> send() async { final r=await client.postUrl(Uri.parse('https://127.0.0.1:${origin.port}/binary%2Fpart?query=a%2Fb'));r.add([7,8]);return r.close(); }
        if(mode=='client-rejected') {
          await expectLater(send(),throwsA(isA<HandshakeException>()));
        } else {
          final response=await send();
          expect(response.statusCode,mode=='upstream-rejected'?502:200);
          final body=await response.fold<List<int>>([], (a,b)=>a..addAll(b));
          if(mode!='upstream-rejected') expect(body,[0,255,2]);
        }
        client.close(force:true);await engine.stop();
        if(mode=='decrypt' || mode=='decrypt-all' || mode=='alpn') {
          final session=events.single['session'];
          expect(session['captureStatus'],'complete');
          expect(session['tls']['mode'], 'decrypt');
          if (mode == 'alpn') expect(session['tls']['alpn'], 'http/1.1');
          expect(session['request']['url'],'https://127.0.0.1:${origin.port}/binary%2Fpart?query=a%2Fb');
          expect(seen.single,'/binary%2Fpart?query=a%2Fb');
          expect(session['request']['body']['size'],2);
          expect(await File('${root.path}/${session['response']['body']['path']}').readAsBytes(),[0,255,2]);
        }
        if(mode=='upstream-rejected') expect(events.single['session']['captureStatus'],'error');
        if(mode=='tunnel') {
          expect(events.single['session']['captureStatus'],'tunneled');
          expect(events.single['session']['error'], isNull);
          expect(events.single['session']['response'], isNull);
          expect(events.single['session']['tls']['contentsCaptured'], false);
        }
        if(mode=='client-rejected') {
          final session = events.single['session'];
          expect(session['captureStatus'], 'error');
          expect(session['tls']['failureStage'], 'client-tls-handshake');
          expect(session['tls']['detail'], isNotEmpty);
        }
      } finally {client.close(force:true);await engine.stop();await sub.cancel();await origin.close(force:true);await root.delete(recursive:true);}
    },timeout:const Timeout(Duration(seconds:45)));
  }
}

