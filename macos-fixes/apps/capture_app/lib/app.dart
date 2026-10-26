import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:ui' show AppExitResponse;
import 'package:flutter/material.dart';
import 'package:file_selector/file_selector.dart';
import 'package:capture_core/capture_core.dart';
import 'package:capture_export/capture_export.dart';
import 'platform/desktop_engine.dart';

class CaptureApp extends StatelessWidget {
  final String storePath;
  const CaptureApp({super.key, required this.storePath});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'HTTP Capture',
    theme: ThemeData(
      colorSchemeSeed: const Color(0xff195c92),
      useMaterial3: true,
    ),
    home: CaptureScreen(storePath: storePath),
  );
}

class CaptureScreen extends StatefulWidget {
  final String storePath;
  const CaptureScreen({super.key, required this.storePath});
  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  late SessionStore store;
  late DesktopEngine engine;
  StreamSubscription<Map<String, dynamic>>? sub;
  late Timer timer;
  late AppLifecycleListener lifecycle;
  bool running = false,
      paused = false,
      busy = false,
      decrypt = true,
      dirty = false;
  String filter = '', status = 'Stopped', fingerprint = '', caPath = '';
  bool routeSystemTraffic=false;
  int port = 8877, total = 0;
  CaptureSession? selected;
  final pages = <int, List<CaptureSession>>{};
  @override
  void initState() {
    super.initState();
    store = SessionStore(Directory(widget.storePath));
    store.recoverInterrupted();
    total = store.count();
    engine = DesktopEngine(widget.storePath);
    sub = engine.events.listen((e) {
      try {
        dirty = true;
        if (e['type'] == 'session') {
          final session = CaptureSession.fromJson(
            Map<String, dynamic>.from(e['session']),
          );
          store.save(session);
          if (selected?.id == session.id) selected = session;
          dirty = true;
        }
        if (e['type'] == 'ca') {
          fingerprint = e['fingerprint'];
          caPath = e['path'];
        }
        if (['fatal', 'recovery_error', 'command_error'].contains(e['type']))
          status = 'Error: ${e['error']}';
        if (e['type'] == 'exit') {
          if (running)
            status = 'Engine stopped · check recovery if exit was unexpected';
          running = false;
          paused = false;
          store.recoverInterrupted();
          dirty = true;
        }
      } catch (error) {
        status = 'Storage/event error: $error';
      }
    });
    timer = Timer.periodic(const Duration(milliseconds: 250), (_) {
      if (dirty && mounted) {
        setState(() {
          pages.clear();
          total = store.count(filter);
          dirty = false;
        });
      }
    });
    if (File('${widget.storePath}/proxy-journal.json').existsSync()) {
      status = 'Previous proxy settings require recovery';
      WidgetsBinding.instance.addPostFrameCallback((_) {
        action(() async {
          await engine.recoverProxy();
          setState(() => status = 'Previous proxy settings restored');
        });
      });
    }
    lifecycle = AppLifecycleListener(
      onExitRequested: () async {
        try {
          await engine.stop();
          return AppExitResponse.exit;
        } catch (e) {
          if (mounted) await notice('Exit blocked: $e');
          return AppExitResponse.cancel;
        }
      },
    );
  }

  @override
  void dispose() {
    timer.cancel();
    lifecycle.dispose();
    sub?.cancel();
    store.close();
    super.dispose();
  }

  Future<void> notice(String text) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        content: Text(text),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Future<bool> confirm(String text) async =>
      await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          content: Text(text),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Continue'),
            ),
          ],
        ),
      ) ??
      false;
  Future<void> action(Future<void> Function() fn) async {
    setState(() => busy = true);
    try {
      await fn();
    } catch (e) {
      await notice('$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> start() async {
    await engine.start(port: port, decrypt: decrypt);
    if(routeSystemTraffic){try{await engine.command('proxy_enable');}catch(_){await engine.stop();rethrow;}}
    setState(() {
      running = true;
      paused = false;
      status = 'Capturing · 127.0.0.1:$port';
    });
  }

  Future<void> stop() async {
    await engine.stop();
    setState(() {
      running = false;
      paused = false;
      status = 'Stopped';
    });
    dirty = true;
  }

  Future<void> export(bool saz) async {
    if (!await confirm(
      'Exported files may include passwords, cookies, tokens and customer data. Save to a protected local location.',
    ))
      return;
    final location = await getSaveLocation(
      suggestedName: 'capture.${saz ? 'saz' : 'har'}',
    );
    if (location == null) return;
    final only = selected == null
        ? false
        : await confirm(
            'Export only the selected session? Cancel exports all sessions.',
          );
    final ids = only ? {selected!.id} : null;
    final root = widget.storePath, path = location.path;
    await Isolate.run(() async {
      final snapshot = SessionStore(Directory(root));
      try {
        if (saz) {
          await SazExporter().export(snapshot, path, ids: ids);
        } else {
          await HarExporter().export(snapshot, path, ids: ids);
        }
      } finally {
        snapshot.close();
      }
    });
    await notice('Saved $path');
  }

  Future<void> settings() async {
    try {
      final ca=await engine.settingsCommand('certificate_info');
      fingerprint=ca['fingerprint'];caPath=ca['path'];
    }catch(e){await notice('$e');}
    if(!mounted)return;
    final portText = TextEditingController(text: '$port');
    await showDialog<void>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (c, update) => AlertDialog(
          title: const Text('Capture settings'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: portText,
                    enabled: !running,
                    decoration: const InputDecoration(
                      labelText: 'Proxy port (1024–65535)',
                    ),
                    keyboardType: TextInputType.number,
                    onChanged: (v) {
                      final n = int.tryParse(v);
                      if (n != null && n >= 1024 && n <= 65535) port = n;
                    },
                  ),
                  SwitchListTile(
                    title: const Text('HTTPS decryption'),
                    subtitle: const Text(
                      'A trusted local CA is required. Pinning is not bypassed.',
                    ),
                    value: decrypt,
                    onChanged: running
                        ? null
                        : (v) {
                            setState(() => decrypt = v);
                            update(() {});
                          },
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Certificate · available while capture is stopped',
                  ),
                  SelectableText(
                    fingerprint.isEmpty
                        ? 'Not generated in this run'
                        : fingerprint,
                  ),
                  SelectableText(caPath),
                  if (Platform.isMacOS) ...[
                    const Text('macOS preview: CA trust is configured manually in Keychain Access. Import only the public certificate above, verify its SHA-256 fingerprint, then explicitly trust it for SSL. Never share mitmproxy-ca.pem (private key).'),
                    TextButton(onPressed: () async {
                      try {
                        final result = await Process.run('/usr/bin/open', ['-R', caPath]);
                        if(result.exitCode != 0) throw StateError('Could not reveal CA certificate');
                      } catch(e) { await notice('$e'); }
                    }, child: const Text('Show public CA in Finder')),
                  ],
                  if (!Platform.isMacOS)
                  Wrap(
                    spacing: 8,
                    children: [
                      TextButton(
                        onPressed: () async {
                                try {
                                  final r = await engine.settingsCommand(
                                    'certificate_status',
                                  );
                                  await notice(r['trusted']==true?'This installation CA is trusted.':'This installation CA is NOT trusted.');
                                } catch (e) {
                                  await notice('$e');
                                }
                              },
                        child: const Text('Check trust'),
                      ),
                      TextButton(
                        onPressed: () async {
                                if (await confirm(
                                  'Trust this installation’s Root CA in Current User Root? This allows this proxy to decrypt HTTPS when clients use it.',
                                )) {
                                  try {
                                    await engine.settingsCommand(
                                      'certificate_install',
                                      {'consent': true},
                                    );
                                    await notice('Certificate installed.');
                                  } catch (e) {
                                    await notice('$e');
                                  }
                                }
                              },
                        child: const Text('Install CA'),
                      ),
                      TextButton(
                        onPressed: () async {
                                if (await confirm(
                                  'Remove only the CA matching this installation’s fingerprint?',
                                )) {
                                  try {
                                    await engine.settingsCommand('certificate_remove', {
                                      'consent': true,
                                    });
                                    await notice('Certificate removed.');
                                  } catch (e) {
                                    await notice('$e');
                                  }
                                }
                              },
                        child: const Text('Remove CA'),
                      ),
                    ],
                  ),
                  const Divider(),
                  if (Platform.isMacOS)
                    Text('macOS preview: configure your browser proxy manually to 127.0.0.1:$port while capture is running. If changing macOS network proxy settings, record existing values and restore them BEFORE stopping capture. This build does not change or restore macOS system proxy settings.'),
                  if (!Platform.isMacOS) ...[
                  const Text('Windows current-user WinINet proxy'),
                  SwitchListTile(title:const Text('Use system proxy when capture starts'),subtitle:const Text('Can be configured while stopped. Applied after the listener starts and restored on Stop.'),value:routeSystemTraffic,onChanged:running?null:(v){setState(()=>routeSystemTraffic=v);update((){});}),
                  const Text(
                    'Use manual proxy configuration for WinHTTP, PAC or managed clients.',
                  ),
                  Wrap(
                    children: [
                      TextButton(
                        onPressed: () async {
                                if (await confirm(
                                  'Apply 127.0.0.1:$port as the current-user Windows proxy until capture stops?',
                                )) {
                                  try {
                                    if(!running)throw StateError('Start capture before enabling the system proxy.');
                                    await engine.command('proxy_enable');
                                    await notice('System proxy enabled.');
                                  } catch (e) {
                                    await notice('$e');
                                  }
                                }
                              },
                        child: const Text('Enable system proxy'),
                      ),
                      TextButton(
                        onPressed: () async {
                                try {
                                  await engine.settingsCommand('proxy_restore');
                                  await notice('Proxy restored.');
                                } catch (e) {
                                  await notice('$e');
                                }
                              },
                        child: const Text('Restore / recover proxy'),
                      ),
                    ],
                  ),
                  ],
                  const Divider(),
                  const Text(
                    'Remote capture: unavailable in this MVP. Listener is loopback only.',
                  ),
                  const Text(
                    'macOS automatic trust/proxy adapters and Android/iOS engines: pending.',
                  ),
                  const SizedBox(height: 12),
                  SelectableText('Local storage: ${widget.storePath}'),
                  TextButton(
                    onPressed: () => showLicensePage(
                      context: context,
                      applicationName: 'HTTP Capture',
                      applicationVersion: '0.1.0',
                    ),
                    child: const Text('Open source licenses'),
                  ),
                  const Text(
                    'Python dependencies: see distributed licenses/THIRD_PARTY_NOTICES.json. No cloud or telemetry features.',
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialog),
              child: const Text('Done'),
            ),
          ],
        ),
      ),
    );
    portText.dispose();
    if (mounted) setState(() {});
  }

  CaptureSession? sessionAt(int index) {
    final page = index ~/ 100;
    if (pages.length > 12 && !pages.containsKey(page))
      pages.remove(pages.keys.first);
    pages.putIfAbsent(
      page,
      () => store.page(offset: page * 100, limit: 100, filter: filter),
    );
    final data = pages[page]!;
    return index % 100 < data.length ? data[index % 100] : null;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('HTTP Capture'),
      actions: [
        IconButton(
          onPressed: busy ? null : settings,
          icon: const Icon(Icons.settings_outlined),
        ),
      ],
    ),
    body: Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              FilledButton.icon(
                onPressed: running || busy ? null : () => action(start),
                icon: const Icon(Icons.play_arrow),
                label: const Text('Start'),
              ),
              OutlinedButton(
                onPressed: !running || busy
                    ? null
                    : () => action(() async {
                        await engine.pause(!paused);
                        setState(() {
                          paused = !paused;
                          status = paused
                              ? 'Paused · traffic forwarded without recording'
                              : 'Capturing · 127.0.0.1:$port';
                        });
                      }),
                child: Text(paused ? 'Resume' : 'Pause'),
              ),
              OutlinedButton(
                onPressed: !running || busy ? null : () => action(stop),
                child: const Text('Stop'),
              ),
              TextButton(
                onPressed: running || busy
                    ? null
                    : () => action(() async {
                        if (await confirm(
                          'Delete all stored sessions and bodies?',
                        )) {
                          store.clear();
                          setState(() {
                            selected = null;
                            pages.clear();
                            total = 0;
                          });
                        }
                      }),
                child: const Text('Clear'),
              ),
              OutlinedButton(
                onPressed: running || busy
                    ? null
                    : () => action(() => export(true)),
                child: const Text('Export SAZ'),
              ),
              OutlinedButton(
                onPressed: running || busy
                    ? null
                    : () => action(() => export(false)),
                child: const Text('Export HAR'),
              ),
              SizedBox(
                width: 260,
                child: TextField(
                  decoration: const InputDecoration(
                    isDense: true,
                    prefixIcon: Icon(Icons.search),
                    hintText: 'Filter method, URL, status',
                  ),
                  onChanged: (v) {
                    setState(() {
                      filter = v;
                      pages.clear();
                      total = store.count(filter);
                    });
                  },
                ),
              ),
            ],
          ),
        ),
        Container(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              Icon(
                running ? Icons.circle : Icons.stop_circle_outlined,
                size: 12,
                color: running ? Colors.green : Colors.grey,
              ),
              const SizedBox(width: 8),
              Expanded(child: Text('$status · $total sessions')),
              if (busy)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              SizedBox(width: 90, child: Text('ID')),
              SizedBox(width: 70, child: Text('Status')),
              SizedBox(width: 80, child: Text('Method')),
              Expanded(flex: 2, child: Text('Host')),
              Expanded(flex: 4, child: Text('URL')),
              SizedBox(width: 100, child: Text('Size')),
              SizedBox(width: 90, child: Text('Time')),
            ],
          ),
        ),
        Expanded(
          flex: 3,
          child: ListView.builder(
            itemCount: total,
            itemExtent: 38,
            itemBuilder: (c, i) {
              final s = sessionAt(i);
              if (s == null) return const SizedBox.shrink();
              return Material(
                color: selected?.id == s.id
                    ? Theme.of(context).colorScheme.secondaryContainer
                    : null,
                child: InkWell(
                  onTap: () => setState(() => selected = s),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 90,
                          child: Text(
                            s.id.length > 8 ? s.id.substring(0, 8) : s.id,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        SizedBox(
                          width: 70,
                          child: Text(
                            '${s.response?.status ?? s.captureStatus}',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        SizedBox(
                          width: 80,
                          child: Text(
                            s.request.method!,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Expanded(
                          flex: 2,
                          child: Text(
                            Uri.parse(s.request.url!).host,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Expanded(
                          flex: 4,
                          child: Text(
                            s.request.url!,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        SizedBox(
                          width: 100,
                          child: Text('${s.response?.body?.size ?? 0} B'),
                        ),
                        SizedBox(
                          width: 90,
                          child: Text(
                            s.endTime == null
                                ? '—'
                                : '${s.endTime!.difference(s.startTime).inMilliseconds} ms',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const Divider(height: 1),
        Expanded(
          flex: 2,
          child: selected == null
              ? const Center(
                  child: Text('Select a session to inspect headers and body'),
                )
              : DefaultTabController(
                  length: 2,
                  child: Column(
                    children: [
                      const TabBar(
                        tabs: [
                          Tab(text: 'Request'),
                          Tab(text: 'Response'),
                        ],
                      ),
                      Expanded(
                        child: TabBarView(
                          children: [
                            details(selected!.request),
                            details(selected!.response),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
        ),
      ],
    ),
  );
  Widget details(HttpMessage? m) {
    if (m == null) return const Center(child: Text('Response not captured'));
    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SelectableText(
            '${m.version} · ${selected!.captureStatus}${selected!.error == null ? '' : ' · ${selected!.error}'}',
          ),
          SelectableText(
            m.headers.map((h) => '${h.name}: ${h.value}').join('\n'),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
          const Divider(),
          FutureBuilder<String>(
            future: preview(m.body),
            builder: (c, s) => SelectableText(
              s.data ?? 'Loading body…',
              style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Future<String> preview(BodyReference? body) async {
    if (body == null) return 'Body not captured';
    try {
      final f = await store.bodyFile(body).open();
      try {
        final bytes = await f.read(body.size < 65536 ? body.size : 65536);
        return '${body.size} bytes · raw entity bytes${body.size > 65536 ? ' · first 64 KiB only' : ''}\n${utf8.decode(bytes, allowMalformed: true)}';
      } finally {
        await f.close();
      }
    } catch (e) {
      return 'Cannot load body: $e';
    }
  }
}
