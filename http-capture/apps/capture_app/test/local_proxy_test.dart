import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:capture_app/platform/local_proxy_engine.dart';

void main() {
  test('real HTTP binary body, duplicate headers, redirect and restart', () async {
    final root = await Directory.systemTemp.createTemp('capture-proxy-test');
    final origin = await HttpServer.bind(InternetAddress.loopbackIPv4,0);
    origin.listen((r) async {
      if(r.uri.path == '/redirect') { r.response.statusCode=302; r.response.headers.set('Location','/binary'); }
      r.response.headers.add('X-Duplicate','one'); r.response.headers.add('X-Duplicate','two');
      r.response.add([0,255,1,2]); await r.response.close();
    });
    final engine=LocalProxyEngine(root);
    final events=<Map<String,dynamic>>[];
    final sub=engine.events.listen(events.add);
    final client=HttpClient();
    try {
      for(var i=0;i<2;i++) {
        await engine.start(port:0);
        client.findProxy=(_)=>'PROXY 127.0.0.1:${engine.port}';
        final request=await client.getUrl(Uri.parse('http://127.0.0.1:${origin.port}/redirect'));
        request.followRedirects=false;
        final response=await request.close();
        expect(response.statusCode,302);
        expect(await response.fold<List<int>>([], (a,b)=>a..addAll(b)),[0,255,1,2]);
        await engine.stop();
      }
      expect(events.length,2);
      final session=events.first['session'] as Map;
      expect(session['captureStatus'],'complete');
      final body=session['response']['body'] as Map;
      expect(await File('${root.path}/${body['path']}').readAsBytes(),[0,255,1,2]);
      expect((session['response']['headers'] as List).length,greaterThan(2));
    } finally { client.close(force:true); await engine.stop(); await sub.cancel(); await origin.close(force:true); await root.delete(recursive:true); }
  });
  test('capture limit records partial but forwards full body', () async {
    final root=await Directory.systemTemp.createTemp('capture-limit');
    final origin=await HttpServer.bind(InternetAddress.loopbackIPv4,0);
    origin.listen((r) async { r.response.add([1,2,3,4]);await r.response.close(); });
    final engine=LocalProxyEngine(root,bodyLimit:2);
    final captured=engine.events.first;
    final client=HttpClient();
    try {
      await engine.start(port:0);client.findProxy=(_)=>'PROXY 127.0.0.1:${engine.port}';
      final response=await (await client.getUrl(Uri.parse('http://127.0.0.1:${origin.port}/'))).close();
      expect(await response.fold<List<int>>([], (a,b)=>a..addAll(b)),[1,2,3,4]);
      await engine.stop();
      final session=(await captured)['session'];
      expect(session['captureStatus'],'partial');expect(session['response']['body']['complete'],false);
    } finally { client.close(force:true);await engine.stop();await origin.close(force:true);await root.delete(recursive:true); }
  });
}
