import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

class StoredEvidenceFile {
  const StoredEvidenceFile({
    required this.id,
    required this.path,
    required this.sha256,
  });

  final String id;
  final String path;
  final String sha256;
}

class EvidenceFileStore {
  Future<StoredEvidenceFile> importFile(
    String sourcePath, {
    required String extension,
  }) async {
    final bytes = await File(sourcePath).readAsBytes();
    return saveBytes(bytes, extension: extension);
  }

  Future<StoredEvidenceFile> saveBytes(
    Uint8List bytes, {
    required String extension,
  }) async {
    final id = const Uuid().v4();
    final support = await getApplicationSupportDirectory();
    final directory = Directory(p.join(support.path, 'evidence'));
    await directory.create(recursive: true);
    final file = File(p.join(directory.path, '$id.$extension'));
    await file.writeAsBytes(bytes, flush: true);
    return StoredEvidenceFile(
      id: id,
      path: file.path,
      sha256: sha256.convert(bytes).toString(),
    );
  }
}
