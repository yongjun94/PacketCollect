import 'dart:io';
import 'dart:math';

Future<void> atomicExport(
  String target,
  Future<void> Function(File) write,
) async {
  final temp = File('$target.${Random.secure().nextInt(1 << 32)}.partial');
  if (await File(target).exists())
    throw FileSystemException('Destination already exists', target);
  try {
    await write(temp);
    await temp.rename(target);
  } catch (_) {
    if (await temp.exists()) await temp.delete();
    rethrow;
  }
}
