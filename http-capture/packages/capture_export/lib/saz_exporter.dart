import 'dart:convert';
import 'dart:io';
import 'package:capture_core/capture_core.dart';
import 'package:xml/xml.dart';
import 'atomic_export.dart';
import 'zip_writer.dart';

class SazExporter {
  Future<void> export(
    SessionStore store,
    String path, {
    Set<String>? ids,
  }) => atomicExport(path, (file) async {
    final out = await file.open(mode: FileMode.write);
    try {
      final zip = ZipWriter(out);
      await zip.add(
        '[Content_Types].xml',
        Stream.value(
          utf8.encode(
            '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="txt" ContentType="text/plain"/><Default Extension="xml" ContentType="application/xml"/></Types>',
          ),
        ),
      );
      int index = 0;
      for (final session in store.all(ids: ids)) {
        index++;
        await zip.add(
          'raw/${index}_c.txt',
          message(store, session.request, true),
        );
        // Missing responses remain missing; no fabricated HTTP 0 or 502 response.
        if (session.response != null)
          await zip.add(
            'raw/${index}_s.txt',
            message(store, session.response!, false),
          );
        await zip.add(
          'raw/${index}_m.xml',
          Stream.value(utf8.encode(metadata(session, index))),
        );
      }
      await zip.finish();
    } finally {
      await out.close();
    }
  });
  Stream<List<int>> message(
    SessionStore store,
    HttpMessage m,
    bool request,
  ) async* {
    final isH2 =
        m.version.startsWith('HTTP/2') || m.version.startsWith('HTTP/3');
    final version = isH2 ? 'HTTP/1.1' : m.version;
    final line = request
        ? '${m.method} ${m.url} $version'
        : '$version ${m.status} ${m.reason ?? ''}';
    if (line.contains('\r') || line.contains('\n'))
      throw FormatException('Invalid start line');
    yield latin1.encode('$line\r\n');
    // mitmproxy removes chunk framing. Export a consistent entity representation.
    for (final h in m.headers) {
      if (h.name.startsWith(':') ||
          [
            'transfer-encoding',
            'content-length',
            'trailer',
          ].contains(h.name.toLowerCase()))
        continue;
      yield [...h.nameBytes, 58, 32, ...h.valueBytes, 13, 10];
    }
    if (request && m.header('host').isEmpty)
      yield latin1.encode('Host: ${Uri.parse(m.url!).authority}\r\n');
    if (m.body != null)
      yield latin1.encode('Content-Length: ${m.body!.size}\r\n');
    yield [13, 10];
    yield* store.body(m.body);
  }

  String metadata(CaptureSession s, int index) {
    final b = XmlBuilder();
    b.processing('xml', 'version="1.0" encoding="utf-8"');
    b.element(
      'Session',
      attributes: {
        'SID': '$index',
        'BitFlags': Uri.parse(s.request.url!).scheme == 'https' ? '1' : '0',
      },
      nest: () {
        b.element(
          'SessionTimers',
          attributes: {
            'ClientBeginRequest': s.startTime.toUtc().toIso8601String(),
            if (s.endTime != null)
              'ClientDoneResponse': s.endTime!.toUtc().toIso8601String(),
          },
        );
        b.element(
          'SessionFlags',
          nest: () {
            final flags = {
              'x-httpcapture-id': s.id,
              'x-httpcapture-status': s.captureStatus,
              'x-httpcapture-original-http-version': s.request.version,
              'x-httpcapture-normalization':
                  'Entity bytes; no chunk framing; H2 start lines mapped to HTTP/1.1',
              'x-httpcapture-original-request-headers': jsonEncode(
                s.request.headers.map((h) => h.toJson()).toList(),
              ),
              if (s.response != null)
                'x-httpcapture-original-response-headers': jsonEncode(
                  s.response!.headers.map((h) => h.toJson()).toList(),
                ),
              if (s.error != null) 'x-httpcapture-error': s.error!,
              'x-httpcapture-run': s.runId,
              'x-clientip': s.sourceDevice,
            };
            for (final e in flags.entries)
              b.element('SessionFlag', attributes: {'N': e.key, 'V': e.value});
          },
        );
      },
    );
    return b.buildDocument().toXmlString();
  }
}
