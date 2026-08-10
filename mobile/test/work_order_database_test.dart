import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isp_field/core/database/work_order_database.dart';
import 'package:isp_field/features/work_orders/domain/work_order.dart';
import 'package:isp_field/features/capture/domain/evidence.dart';
import 'package:isp_field/features/inventory/domain/inventory_item.dart';

void main() {
  test('offline transition updates the OS and enters the sync queue', () async {
    final database = WorkOrderDatabase(executor: NativeDatabase.memory());
    addTearDown(database.close);

    await database.replaceWorkOrders(const [
      WorkOrder(
        id: 'os-1',
        code: 'OS-1',
        customerName: 'Cliente',
        address: 'Bancada',
        status: WorkOrderStatus.assigned,
        version: 1,
      ),
    ]);

    await database.transitionWorkOrder(
      workOrderId: 'os-1',
      transition: const WorkOrderTransition(
        toStatus: WorkOrderStatus.traveling,
        note: 'Saída da central',
        latitude: -12.9,
        longitude: -38.5,
      ),
      operationId: 'operation-1',
    );

    final orders = await database.readWorkOrders();
    final pending = await database.pendingOperations();
    expect(orders.single.status, WorkOrderStatus.traveling);
    expect(orders.single.version, 2);
    expect(pending.single.operationId, 'operation-1');
    expect(await database.pendingOperationCount(), 1);
    expect(await database.transitionHistoryCount('os-1'), 1);
    final history = await database.readTransitionHistory('os-1');
    expect(history.single.fromStatus, WorkOrderStatus.assigned);
    expect(history.single.toStatus, WorkOrderStatus.traveling);
    expect(history.single.note, 'Saída da central');

    await database.addEvidence(
      LocalEvidence(
        id: 'evidence-1',
        workOrderId: 'os-1',
        category: 'installation_photo',
        localPath: 'photo.jpg',
        sha256: 'hash',
        state: 'pending',
        createdAt: DateTime.utc(2026, 8, 3),
      ),
    );
    await database.addEquipmentScan(
      id: 'scan-1',
      workOrderId: 'os-1',
      serial: 'ONU-123',
    );
    expect(await database.evidenceCount('os-1'), 1);
    expect(await database.equipmentScanCount('os-1'), 1);
    expect(await database.pendingEvidenceUploadCount(), 2);
    expect(
      await database.evidenceCategoryCount('os-1', 'installation_photo'),
      1,
    );
    await database.setEvidenceState('evidence-1', 'uploaded');
    await database.setEquipmentScanState('scan-1', 'uploaded');
    expect(await database.pendingEvidenceUploadCount(), 0);

    await database.replaceInventory(const [
      InventoryItem(
        id: 'connector',
        sku: 'CON-1',
        description: 'Conector',
        quantity: 5,
        unit: 'un',
        version: 1,
      ),
    ]);
    await database.consumeInventory(
      movementId: 'movement-1',
      workOrderId: 'os-1',
      itemId: 'connector',
      quantity: 2,
    );
    final inventory = await database.readInventory();
    expect(inventory.single.quantity, 3);
    expect(inventory.single.version, 2);
    expect(await database.pendingOperationCount(), 2);
    expect(await database.inventoryMovementCount('os-1'), 1);

    expect(await database.readSyncCursor(), isNull);
    await database.writeSyncCursor('12');
    expect(await database.readSyncCursor(), '12');

    await database.upsertWorkOrder(const WorkOrder(
      id: 'os-1',
      code: 'OS-1',
      customerName: 'Cliente atualizado',
      address: 'Bancada',
      status: WorkOrderStatus.completed,
      version: 3,
    ));
    expect((await database.readWorkOrders()).single.version, 3);

    await database.markOperationError(
      'operation-1',
      'version_conflict',
      'conflict',
    );
    expect(await database.pendingOperationCount(), 1);
    expect(await database.conflictedOperationCount(), 1);
    expect(await database.discardConflictedOperations(), 1);
    expect(await database.conflictedOperationCount(), 0);
  });
}
