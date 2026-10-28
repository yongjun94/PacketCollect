import 'dart:convert';
import 'dart:io';

/// Lightweight preflight; the test suite also uses an independent JSON Schema.
Future<int> validateHar(File file) async {
  final j = jsonDecode(await file.readAsString()) as Map;
  if (j['log']['version'] != '1.2' || j['log']['entries'] is! List)
    throw FormatException('Invalid HAR root');
  for (final e in j['log']['entries']) {
    for (final key in [
      'startedDateTime',
      'time',
      'request',
      'response',
      'cache',
      'timings',
    ]) {
      if (!e.containsKey(key)) throw FormatException('Missing $key');
    }
  }
  return (j['log']['entries'] as List).length;
}
