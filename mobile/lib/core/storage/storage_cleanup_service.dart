import 'dart:io';

import '../../features/work_orders/data/work_order_local_data_source.dart';

class StorageCleanupService {
  StorageCleanupService(this._local);

  final WorkOrderLocalDataSource _local;

  /// Teto de armazenamento local para evidências, em bytes. Passado esse
  /// limite, o arquivo confirmado mais antigo é apagado do aparelho — o
  /// registro já está seguro no servidor, então isso é só liberar espaço,
  /// nunca perder dado.
  static const int maxStorageBytes = 300 * 1024 * 1024; // 300 MB

  /// Retorna quantos arquivos foram removidos.
  Future<int> enforceLimit({int maxBytes = maxStorageBytes}) async {
    final uploaded = await _local.uploadedEvidenceOrderedByAge();
    var totalBytes = 0;
    final sizes = <String, int>{};
    for (final evidence in uploaded) {
      final file = File(evidence.localPath);
      final size = await file.exists() ? await file.length() : 0;
      sizes[evidence.id] = size;
      totalBytes += size;
    }

    var removed = 0;
    var index = 0;
    while (totalBytes > maxBytes && index < uploaded.length) {
      final evidence = uploaded[index];
      final file = File(evidence.localPath);
      if (await file.exists()) {
        try {
          await file.delete();
        } catch (_) {
          index++;
          continue;
        }
      }
      await _local.deleteEvidenceRecord(evidence.id);
      totalBytes -= sizes[evidence.id] ?? 0;
      removed++;
      index++;
    }
    return removed;
  }
}