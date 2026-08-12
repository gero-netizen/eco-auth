import '../../../core/database/work_order_database.dart';
import '../../../core/sync/sync_operation.dart';
import '../domain/work_order.dart';
import '../../capture/domain/evidence.dart';
import '../../inventory/domain/inventory_item.dart';

class WorkOrderLocalDataSource {
  WorkOrderLocalDataSource(this._database);

  final WorkOrderDatabase _database;

  Future<List<WorkOrder>> fetchAll() => _database.readWorkOrders();

  Future<void> replaceAll(List<WorkOrder> orders) =>
      _database.replaceWorkOrders(orders);

  Future<void> upsertWorkOrder(WorkOrder order) =>
      _database.upsertWorkOrder(order);

  Future<String?> readSyncCursor() => _database.readSyncCursor();

  Future<void> writeSyncCursor(String cursor) =>
      _database.writeSyncCursor(cursor);

  Future<void> transition({
    required String workOrderId,
    required WorkOrderTransition transition,
    required String operationId,
  }) =>
      _database.transitionWorkOrder(
        workOrderId: workOrderId,
        transition: transition,
        operationId: operationId,
      );

  Future<List<WorkOrderHistoryEntry>> transitionHistory(String workOrderId) =>
      _database.readTransitionHistory(workOrderId);

  Future<List<SyncOperation>> pendingOperations() =>
      _database.pendingOperations();

  Future<int> pendingCount() => _database.pendingOperationCount();

  Future<int> conflictCount() => _database.conflictedOperationCount();

  Future<int> discardConflicts() => _database.discardConflictedOperations();

  Future<void> acknowledge(String operationId) =>
      _database.acknowledgeOperation(operationId);

  Future<void> markError(String operationId, String reason, String state) =>
      _database.markOperationError(operationId, reason, state);

  Future<void> addEvidence(LocalEvidence evidence) =>
      _database.addEvidence(evidence);

  Future<int> evidenceCount(String workOrderId) =>
      _database.evidenceCount(workOrderId);

  Future<int> evidenceCategoryCount(String workOrderId, String category) =>
      _database.evidenceCategoryCount(workOrderId, category);

  Future<void> addEquipmentScan({
    required String id,
    required String workOrderId,
    required String serial,
  }) =>
      _database.addEquipmentScan(
        id: id,
        workOrderId: workOrderId,
        serial: serial,
      );

  Future<int> equipmentScanCount(String workOrderId) =>
      _database.equipmentScanCount(workOrderId);

  Future<List<LocalEvidence>> pendingEvidence() => _database.pendingEvidence();

  Future<void> setEvidenceState(String id, String state) =>
      _database.setEvidenceState(id, state);

  Future<List<LocalEvidence>> uploadedEvidenceOrderedByAge() =>
      _database.uploadedEvidenceOrderedByAge();

  Future<void> deleteEvidenceRecord(String id) =>
      _database.deleteEvidenceRecord(id);

  Future<List<LocalEquipmentScan>> pendingEquipmentScans() =>
      _database.pendingEquipmentScans();

  Future<void> setEquipmentScanState(String id, String state) =>
      _database.setEquipmentScanState(id, state);

  Future<int> pendingEvidenceUploadCount() =>
      _database.pendingEvidenceUploadCount();

  Future<List<InventoryItem>> readInventory() => _database.readInventory();

  Future<void> replaceInventory(List<InventoryItem> items) =>
      _database.replaceInventory(items);

  Future<void> upsertInventoryItem(InventoryItem item) =>
      _database.upsertInventoryItem(item);

  Future<void> consumeInventory({
    required String movementId,
    required String workOrderId,
    required String itemId,
    required double quantity,
  }) =>
      _database.consumeInventory(
        movementId: movementId,
        workOrderId: workOrderId,
        itemId: itemId,
        quantity: quantity,
      );

  Future<int> inventoryMovementCount(String workOrderId) =>
      _database.inventoryMovementCount(workOrderId);
}
