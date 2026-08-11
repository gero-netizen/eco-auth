import '../domain/work_order.dart';
import 'package:uuid/uuid.dart';
import 'dart:typed_data';

import '../../capture/data/evidence_file_store.dart';
import '../../capture/domain/evidence.dart';
import '../../inventory/domain/inventory_item.dart';
import '../../provisioning/domain/onu_state.dart';
import '../../monitoring/domain/network_alert.dart';
import '../../access_test/domain/pppoe_test_result.dart';
import '../../feasibility/domain/feasibility_result.dart';
import 'work_order_local_data_source.dart';
import 'work_order_remote_data_source.dart';

abstract interface class WorkOrderRepositoryContract {
  Future<List<WorkOrder>> loadCached();
  Future<List<WorkOrder>> synchronize();
  Future<void> transition(String workOrderId, WorkOrderTransition transition);
  Future<List<WorkOrderHistoryEntry>> transitionHistory(String workOrderId);
  Future<int> pendingCount();
  Future<int> conflictCount();
  Future<List<WorkOrder>> reconcileConflicts();
  Future<void> addPhoto(String workOrderId, String sourcePath);
  Future<void> addSignature(String workOrderId, Uint8List bytes);
  Future<void> addEquipmentScan(String workOrderId, String serial);
  Future<int> evidenceCount(String workOrderId);
  Future<int> photoCount(String workOrderId);
  Future<int> signatureCount(String workOrderId);
  Future<int> equipmentScanCount(String workOrderId);
  Future<int> pendingEvidenceUploadCount();
  Future<List<InventoryItem>> loadCachedInventory();
  Future<List<InventoryItem>> synchronizeInventory();
  Future<void> consumeInventory({
    required String workOrderId,
    required String itemId,
    required double quantity,
  });
  Future<int> inventoryMovementCount(String workOrderId);
  Future<List<OnuState>> discoverOnus();
  Future<OnuState> provisionOnu(
    String workOrderId,
    String serial,
    String profile,
  );
  Future<List<ProvisioningRecord>> provisioningHistory(String workOrderId);
  Future<List<NetworkAlert>> networkAlerts();
  Future<PppoeTestResult> testPppoe(String workOrderId, String username);
  Future<FeasibilityResult> checkFeasibility(
    String workOrderId,
    String address,
  );
}

class WorkOrderRepository implements WorkOrderRepositoryContract {
  WorkOrderRepository({
    required WorkOrderLocalDataSource local,
    required WorkOrderRemoteDataSource remote,
  })  : _local = local,
        _remote = remote;

  final WorkOrderLocalDataSource _local;
  final WorkOrderRemoteDataSource _remote;
  final EvidenceFileStore _fileStore = EvidenceFileStore();

  @override
  Future<List<WorkOrder>> loadCached() => _local.fetchAll();

  @override
  Future<List<WorkOrder>> synchronize() async {
    final pending = await _local.pendingOperations();
    final results = await _remote.push(pending);
    final operationsById = {
      for (final operation in pending) operation.operationId: operation,
    };
    var refreshWorkOrders = false;
    var refreshInventory = false;
    for (final result in results) {
      final operationId = result['operation_id'] as String;
      final status = result['status'] as String;
      if (status == 'accepted' || status == 'duplicate') {
        await _local.acknowledge(operationId);
      } else {
        final operation = operationsById[operationId];
        refreshWorkOrders =
            refreshWorkOrders || operation?.entityType == 'work_order';
        refreshInventory =
            refreshInventory || operation?.entityType == 'inventory_movement';
        await _local.markError(
          operationId,
          result['reason'] as String? ?? status,
          status == 'conflict' ? 'conflict' : 'rejected',
        );
      }
    }

    await _uploadPendingEvidence();

    final cursor = await _local.readSyncCursor();
    if (cursor == null) {
      await _local.replaceAll(await _remote.fetchAll());
    }
    final pulled = await _remote.pull(cursor);
    for (final order in pulled.workOrders) {
      await _local.upsertWorkOrder(order);
    }
    for (final item in pulled.inventoryItems) {
      await _local.upsertInventoryItem(item);
    }
    await _local.writeSyncCursor(pulled.nextCursor);
    if (refreshWorkOrders) {
      await _local.replaceAll(await _remote.fetchAll());
    }
    if (refreshInventory) {
      await _local.replaceInventory(await _remote.fetchInventory());
    }
    return _local.fetchAll();
  }

  @override
  Future<void> transition(
    String workOrderId,
    WorkOrderTransition transition,
  ) {
    return _local.transition(
      workOrderId: workOrderId,
      transition: transition,
      operationId: const Uuid().v4(),
    );
  }

  @override
  Future<List<WorkOrderHistoryEntry>> transitionHistory(String workOrderId) =>
      _local.transitionHistory(workOrderId);

  @override
  Future<int> pendingCount() => _local.pendingCount();

  @override
  Future<int> conflictCount() => _local.conflictCount();

  @override
  Future<List<WorkOrder>> reconcileConflicts() async {
    await _local.discardConflicts();
    final orders = await _remote.fetchAll();
    final inventory = await _remote.fetchInventory();
    await _local.replaceAll(orders);
    await _local.replaceInventory(inventory);
    return _local.fetchAll();
  }

  @override
  Future<void> addPhoto(String workOrderId, String sourcePath) async {
    final stored = await _fileStore.importFile(sourcePath, extension: 'jpg');
    await _local.addEvidence(
      LocalEvidence(
        id: stored.id,
        workOrderId: workOrderId,
        category: 'installation_photo',
        localPath: stored.path,
        sha256: stored.sha256,
        state: 'pending',
        createdAt: DateTime.now().toUtc(),
      ),
    );
  }

  @override
  Future<void> addSignature(String workOrderId, Uint8List bytes) async {
    final stored = await _fileStore.saveBytes(bytes, extension: 'png');
    await _local.addEvidence(
      LocalEvidence(
        id: stored.id,
        workOrderId: workOrderId,
        category: 'customer_signature',
        localPath: stored.path,
        sha256: stored.sha256,
        state: 'pending',
        createdAt: DateTime.now().toUtc(),
      ),
    );
  }

  @override
  Future<void> addEquipmentScan(String workOrderId, String serial) {
    return _local.addEquipmentScan(
      id: const Uuid().v4(),
      workOrderId: workOrderId,
      serial: serial,
    );
  }

  @override
  Future<int> evidenceCount(String workOrderId) =>
      _local.evidenceCount(workOrderId);

  @override
  Future<int> photoCount(String workOrderId) =>
      _local.evidenceCategoryCount(workOrderId, 'installation_photo');

  @override
  Future<int> signatureCount(String workOrderId) =>
      _local.evidenceCategoryCount(workOrderId, 'customer_signature');

  @override
  Future<int> equipmentScanCount(String workOrderId) =>
      _local.equipmentScanCount(workOrderId);

  Future<void> _uploadPendingEvidence() async {
    for (final evidence in await _local.pendingEvidence()) {
      await _local.setEvidenceState(evidence.id, 'uploading');
      try {
        await _remote.uploadEvidence(evidence);
        await _local.setEvidenceState(evidence.id, 'uploaded');
      } catch (_) {
        // Falha em um anexo não pode travar o restante da fila nem a
        // sincronização geral (ordens de serviço, estoque). O item volta
        // para 'pending' e é reenviado automaticamente na próxima sync.
        await _local.setEvidenceState(evidence.id, 'pending');
      }
    }
    for (final scan in await _local.pendingEquipmentScans()) {
      await _local.setEquipmentScanState(scan.id, 'uploading');
      try {
        await _remote.uploadEquipmentScan(scan);
        await _local.setEquipmentScanState(scan.id, 'uploaded');
      } catch (_) {
        await _local.setEquipmentScanState(scan.id, 'pending');
      }
    }
  }

  @override
  Future<int> pendingEvidenceUploadCount() =>
      _local.pendingEvidenceUploadCount();

  @override
  Future<List<InventoryItem>> loadCachedInventory() => _local.readInventory();

  @override
  Future<List<InventoryItem>> synchronizeInventory() async {
    await synchronize();
    final items = await _remote.fetchInventory();
    await _local.replaceInventory(items);
    return items;
  }

  @override
  Future<void> consumeInventory({
    required String workOrderId,
    required String itemId,
    required double quantity,
  }) {
    return _local.consumeInventory(
      movementId: const Uuid().v4(),
      workOrderId: workOrderId,
      itemId: itemId,
      quantity: quantity,
    );
  }

  @override
  Future<int> inventoryMovementCount(String workOrderId) =>
      _local.inventoryMovementCount(workOrderId);

  @override
  Future<List<OnuState>> discoverOnus() => _remote.discoverOnus();

  @override
  Future<OnuState> provisionOnu(
    String workOrderId,
    String serial,
    String profile,
  ) =>
      _remote.provisionOnu(workOrderId, serial, profile);

  @override
  Future<List<ProvisioningRecord>> provisioningHistory(String workOrderId) =>
      _remote.provisioningHistory(workOrderId);

  @override
  Future<List<NetworkAlert>> networkAlerts() => _remote.networkAlerts();

  @override
  Future<PppoeTestResult> testPppoe(String workOrderId, String username) =>
      _remote.testPppoe(workOrderId, username);

  @override
  Future<FeasibilityResult> checkFeasibility(
    String workOrderId,
    String address,
  ) =>
      _remote.checkFeasibility(workOrderId, address);
}
