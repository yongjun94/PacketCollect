import 'dart:io';
import 'dart:typed_data';
import 'dart:convert';

/// Streaming STORE ZIP with data descriptors. Explicitly refuses ZIP64 limits.
class ZipWriter {
  final RandomAccessFile out;
  int position = 0;
  final List<List<int>> central = [];
  ZipWriter(this.out);
  List<int> fields(List<(int, int)> values) {
    final b = BytesBuilder();
    for (final (size, value) in values) {
      final d = ByteData(size);
      if (size == 2)
        d.setUint16(0, value, Endian.little);
      else
        d.setUint32(0, value, Endian.little);
      b.add(d.buffer.asUint8List());
    }
    return b.takeBytes();
  }

  Future<void> write(List<int> b) async {
    await out.writeFrom(b);
    position += b.length;
  }

  Future<void> add(String name, Stream<List<int>> data) async {
    if (central.length >= 65535 || position >= 0xffffffff)
      throw StateError('ZIP64 required; split capture');
    final n = utf8.encode(name), offset = position;
    await write(
      fields([
        (4, 0x04034b50),
        (2, 20),
        (2, 0x808),
        (2, 0),
        (2, 0),
        (2, 33),
        (4, 0),
        (4, 0),
        (4, 0),
        (2, n.length),
        (2, 0),
      ]),
    );
    await write(n);
    int crc = 0xffffffff, size = 0;
    await for (final chunk in data) {
      size += chunk.length;
      if (size >= 0xffffffff || position + chunk.length >= 0xffffffff)
        throw StateError('ZIP64 required; split capture');
      for (final byte in chunk) {
        crc ^= byte;
        for (int i = 0; i < 8; i++) {
          crc = (crc & 1) != 0 ? (crc >> 1) ^ 0xedb88320 : crc >> 1;
        }
      }
      await write(chunk);
    }
    crc ^= 0xffffffff;
    await write(fields([(4, 0x08074b50), (4, crc), (4, size), (4, size)]));
    central.add([
      ...fields([
        (4, 0x02014b50),
        (2, 20),
        (2, 20),
        (2, 0x808),
        (2, 0),
        (2, 0),
        (2, 33),
        (4, crc),
        (4, size),
        (4, size),
        (2, n.length),
        (2, 0),
        (2, 0),
        (2, 0),
        (2, 0),
        (4, 0),
        (4, offset),
      ]),
      ...n,
    ]);
  }

  Future<void> finish() async {
    final start = position;
    for (final c in central) {
      await write(c);
    }
    if (position >= 0xffffffff) throw StateError('ZIP64 required');
    await write(
      fields([
        (4, 0x06054b50),
        (2, 0),
        (2, 0),
        (2, central.length),
        (2, central.length),
        (4, position - start),
        (4, start),
        (2, 0),
      ]),
    );
    await out.flush();
  }
}
