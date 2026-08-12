import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:image/image.dart' as img;
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
  /// Fotos maiores que isso (em pixels de largura) são redimensionadas.
  /// Suficiente pra qualquer comprovação de instalação, bem menor que o
  /// que a câmera captura por padrão em alta resolução.
  static const _maxPhotoWidth = 1600;
  static const _jpegQuality = 80;

  Future<StoredEvidenceFile> importFile(
    String sourcePath, {
    required String extension,
  }) async {
    final bytes = await File(sourcePath).readAsBytes();
    final processed = _isJpeg(extension) ? _compress(bytes) : bytes;
    return saveBytes(processed, extension: extension);
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

  static bool _isJpeg(String extension) {
    final normalized = extension.toLowerCase();
    return normalized == 'jpg' || normalized == 'jpeg';
  }

  /// Reduz o tamanho do arquivo antes de gravar — menos espaço no
  /// aparelho, envio mais rápido em sinal fraco de campo. Se a
  /// decodificação falhar por qualquer motivo, usa a foto original em vez
  /// de travar a captura.
  static Uint8List _compress(Uint8List bytes) {
    try {
      final decoded = img.decodeImage(bytes);
      if (decoded == null) return bytes;
      final resized = decoded.width > _maxPhotoWidth
          ? img.copyResize(decoded, width: _maxPhotoWidth)
          : decoded;
      return Uint8List.fromList(img.encodeJpg(resized, quality: _jpegQuality));
    } catch (_) {
      return bytes;
    }
  }
}
