import 'dart:io';
import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../features/work_orders/domain/work_order.dart' as domain;
import '../../features/capture/domain/evidence.dart';
import '../../features/inventory/domain/inventory_item.dart';
import '../sync/sync_operation.dart';
import '../auth/technician_session.dart';

part 'work_order_database.g.dart';

class CachedWorkOrders extends Table {
  TextColumn get id => text()();
  TextColumn get code => text()();
  TextColumn get customerName => text()();
  TextColumn get address => text()();
  TextColumn get status => text()();
  IntColumn get version => integer()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();
  TextColumn get priority => text().withDefault(const Constant('normal'))();
  DateTimeColumn get scheduledAt => dateTime().nullable()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

class SyncQueueEntries extends Table {
  TextColumn get operationId => text()();
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  TextColumn get kind => text()();
  IntColumn get baseVersion => integer().nullable()();
  DateTimeColumn get occurredAt => dateTime()();
  TextColumn get payloadJson => text()();
  TextColumn get state => text().withDefault(const Constant('pending'))();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();

  @override
  Set<Column<Object>> get primaryKey => {operationId};
}

class WorkOrderTransitionEntries extends Table {
  TextColumn get operationId => text()();
  TextColumn get workOrderId => text()();
  TextColumn get fromStatus => text()();
  TextColumn get toStatus => text()();
  TextColumn get note => text().nullable()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();
  DateTimeColumn get occurredAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {operationId};
}

class EvidenceEntries extends Table {
  TextColumn get id => text()();
  TextColumn get workOrderId => text()();
  TextColumn get category => text()();
  TextColumn get localPath => text()();
  TextColumn get sha256 => text()();
  TextColumn get state => text().withDefault(const Constant('pending'))();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

class EquipmentScanEntries extends Table {
  TextColumn get id => text()();
  TextColumn get workOrderId => text()();
  TextColumn get serial => text()();
  TextColumn get state => text().withDefault(const Constant('pending'))();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

class InventoryItemEntries extends Table {
  TextColumn get id => text()();
  TextColumn get sku => text()();
  TextColumn get description => text()();
  RealColumn get quantity => real()();
  TextColumn get unit => text()();
  TextColumn get serialNumber => text().nullable()();
  IntColumn get version => integer()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

class InventoryMovementEntries extends Table {
  TextColumn get id => text()();
  TextColumn get workOrderId => text()();
  TextColumn get itemId => text()();
  RealColumn get quantity => real()();
  TextColumn get kind => text()();
  DateTimeColumn get occurredAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

class AppSettingEntries extends Table {
  TextColumn get key => text()();
  TextColumn get value => text()();

  @override
  Set<Column<Object>> get primaryKey => {key};
}

@DriftDatabase(
  tables: [
    CachedWorkOrders,
    SyncQueueEntries,
    WorkOrderTransitionEntries,
    EvidenceEntries,
    EquipmentScanEntries,
    InventoryItemEntries,
    InventoryMovementEntries,
    AppSettingEntries,
  ],
)
class WorkOrderDatabase extends _$WorkOrderDatabase {
  WorkOrderDatabase({QueryExecutor? executor})
      : super(executor ?? _openConnection());

  @override
  int get schemaVersion => 8;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (migrator) => migrator.createAll(),
        onUpgrade: (migrator, from, to) async {
          if (from < 2) await migrator.createTable(syncQueueEntries);
          if (from < 3) {
            await migrator.createTable(workOrderTransitionEntries);
          }
          if (from < 4) {
            await migrator.createTable(evidenceEntries);
            await migrator.createTable(equipmentScanEntries);
          }
          if (from < 5) {
            await migrator.createTable(inventoryItemEntries);
            await migrator.createTable(inventoryMovementEntries);
          }
          if (from < 6) await migrator.createTable(appSettingEntries);
          if (from < 7) {
            await migrator.addColumn(
                cachedWorkOrders, cachedWorkOrders.latitude);
            await migrator.addColumn(
                cachedWorkOrders, cachedWorkOrders.longitude);
          }
          if (from < 8) {
            await migrator.addColumn(
                cachedWorkOrders, cachedWorkOrders.priority);
            await migrator.addColumn(
              cachedWorkOrders,
              cachedWorkOrders.scheduledAt,
            );
          }
        },
      );

  Future<List<domain.WorkOrder>> readWorkOrders() async {
    final rows = await (select(cachedWorkOrders)
          ..orderBy([(row) => OrderingTerm.asc(row.code)]))
        .get();
    return rows
        .map(
          (row) => domain.WorkOrder(
            id: row.id,
            code: row.code,
            customerName: row.customerName,
            address: row.address,
            status: domain.workOrderStatusFromApi(row.status),
            version: row.version,
            latitude: row.latitude,
            longitude: row.longitude,
            priority: row.priority,
            scheduledAt: row.scheduledAt,
          ),
        )
        .toList(growable: false);
  }

  Future<void> replaceWorkOrders(List<domain.WorkOrder> orders) {
    return transaction(() async {
      await delete(cachedWorkOrders).go();
      await batch((batch) {
        batch.insertAll(
          cachedWorkOrders,
          orders
              .map(
                (order) => CachedWorkOrdersCompanion.insert(
                  id: order.id,
                  code: order.code,
                  customerName: order.customerName,
                  address: order.address,
                  status: order.status.apiValue,
                  version: order.version,
                  latitude: Value(order.latitude),
                  longitude: Value(order.longitude),
                  priority: Value(order.priority),
                  scheduledAt: Value(order.scheduledAt),
                  updatedAt: DateTime.now().toUtc(),
                ),
              )
              .toList(growable: false),
        );
      });
    });
  }

  Future<void> upsertWorkOrder(domain.WorkOrder order) {
    return into(cachedWorkOrders).insertOnConflictUpdate(
      CachedWorkOrdersCompanion.insert(
        id: order.id,
        code: order.code,
        customerName: order.customerName,
        address: order.address,
        status: order.status.apiValue,
        version: order.version,
        latitude: Value(order.latitude),
        longitude: Value(order.longitude),
        priority: Value(order.priority),
        scheduledAt: Value(order.scheduledAt),
        updatedAt: DateTime.now().toUtc(),
      ),
    );
  }

  Future<void> transitionWorkOrder({
    required String workOrderId,
    required domain.WorkOrderTransition transition,
    required String operationId,
  }) {
    return transaction(() async {
      final current = await (select(cachedWorkOrders)
            ..where((row) => row.id.equals(workOrderId)))
          .getSingle();
      await (update(cachedWorkOrders)
            ..where((row) => row.id.equals(workOrderId)))
          .write(
        CachedWorkOrdersCompanion(
          status: Value(transition.toStatus.apiValue),
          version: Value(current.version + 1),
          updatedAt: Value(DateTime.now().toUtc()),
        ),
      );
      await into(syncQueueEntries).insert(
        SyncQueueEntriesCompanion.insert(
          operationId: operationId,
          entityType: 'work_order',
          entityId: workOrderId,
          kind: 'transition',
          baseVersion: Value(current.version),
          occurredAt: DateTime.now().toUtc(),
          payloadJson: jsonEncode({
            'to_status': transition.toStatus.apiValue,
            'note': transition.note,
            'latitude': transition.latitude,
            'longitude': transition.longitude,
          }),
        ),
      );
      await into(workOrderTransitionEntries).insert(
        WorkOrderTransitionEntriesCompanion.insert(
          operationId: operationId,
          workOrderId: workOrderId,
          fromStatus: current.status,
          toStatus: transition.toStatus.apiValue,
          note: Value(transition.note),
          latitude: Value(transition.latitude),
          longitude: Value(transition.longitude),
          occurredAt: DateTime.now().toUtc(),
        ),
      );
    });
  }

  Future<int> transitionHistoryCount(String workOrderId) async {
    final count = workOrderTransitionEntries.operationId.count();
    final query = selectOnly(workOrderTransitionEntries)
      ..addColumns([count])
      ..where(workOrderTransitionEntries.workOrderId.equals(workOrderId));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<List<domain.WorkOrderHistoryEntry>> readTransitionHistory(
    String workOrderId,
  ) async {
    final rows = await (select(workOrderTransitionEntries)
          ..where((row) => row.workOrderId.equals(workOrderId))
          ..orderBy([(row) => OrderingTerm.desc(row.occurredAt)]))
        .get();
    return rows
        .map(
          (row) => domain.WorkOrderHistoryEntry(
            fromStatus: domain.workOrderStatusFromApi(row.fromStatus),
            toStatus: domain.workOrderStatusFromApi(row.toStatus),
            occurredAt: row.occurredAt,
            note: row.note,
            latitude: row.latitude,
            longitude: row.longitude,
          ),
        )
        .toList(growable: false);
  }

  Future<void> addEvidence(LocalEvidence evidence) {
    return into(evidenceEntries).insert(
      EvidenceEntriesCompanion.insert(
        id: evidence.id,
        workOrderId: evidence.workOrderId,
        category: evidence.category,
        localPath: evidence.localPath,
        sha256: evidence.sha256,
        state: Value(evidence.state),
        createdAt: evidence.createdAt,
      ),
    );
  }

  Future<int> evidenceCount(String workOrderId) async {
    final count = evidenceEntries.id.count();
    final query = selectOnly(evidenceEntries)
      ..addColumns([count])
      ..where(evidenceEntries.workOrderId.equals(workOrderId));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<int> evidenceCategoryCount(String workOrderId, String category) async {
    final count = evidenceEntries.id.count();
    final query = selectOnly(evidenceEntries)
      ..addColumns([count])
      ..where(
        evidenceEntries.workOrderId.equals(workOrderId) &
            evidenceEntries.category.equals(category),
      );
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<List<LocalEvidence>> pendingEvidence() async {
    final rows = await (select(evidenceEntries)
          ..where((row) => row.state.isIn(['pending', 'uploading']))
          ..orderBy([(row) => OrderingTerm.asc(row.createdAt)]))
        .get();
    return rows
        .map(
          (row) => LocalEvidence(
            id: row.id,
            workOrderId: row.workOrderId,
            category: row.category,
            localPath: row.localPath,
            sha256: row.sha256,
            state: row.state,
            createdAt: row.createdAt,
          ),
        )
        .toList(growable: false);
  }

  Future<void> setEvidenceState(String id, String state) {
    return (update(evidenceEntries)..where((row) => row.id.equals(id))).write(
      EvidenceEntriesCompanion(state: Value(state)),
    );
  }

  /// Evidências já confirmadas no servidor, da mais antiga para a mais
  /// nova — usado para liberar espaço local sem nunca apagar algo que
  /// ainda não foi sincronizado.
  Future<List<LocalEvidence>> uploadedEvidenceOrderedByAge() async {
    final rows = await (select(evidenceEntries)
          ..where((row) => row.state.equals('uploaded'))
          ..orderBy([(row) => OrderingTerm.asc(row.createdAt)]))
        .get();
    return rows
        .map(
          (row) => LocalEvidence(
            id: row.id,
            workOrderId: row.workOrderId,
            category: row.category,
            localPath: row.localPath,
            sha256: row.sha256,
            state: row.state,
            createdAt: row.createdAt,
          ),
        )
        .toList(growable: false);
  }

  Future<void> deleteEvidenceRecord(String id) {
    return (delete(evidenceEntries)..where((row) => row.id.equals(id))).go();
  }

  Future<void> addEquipmentScan({
    required String id,
    required String workOrderId,
    required String serial,
  }) {
    return into(equipmentScanEntries).insert(
      EquipmentScanEntriesCompanion.insert(
        id: id,
        workOrderId: workOrderId,
        serial: serial,
        createdAt: DateTime.now().toUtc(),
      ),
    );
  }

  Future<int> equipmentScanCount(String workOrderId) async {
    final count = equipmentScanEntries.id.count();
    final query = selectOnly(equipmentScanEntries)
      ..addColumns([count])
      ..where(equipmentScanEntries.workOrderId.equals(workOrderId));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<List<LocalEquipmentScan>> pendingEquipmentScans() async {
    final rows = await (select(equipmentScanEntries)
          ..where((row) => row.state.isIn(['pending', 'uploading']))
          ..orderBy([(row) => OrderingTerm.asc(row.createdAt)]))
        .get();
    return rows
        .map(
          (row) => LocalEquipmentScan(
            id: row.id,
            workOrderId: row.workOrderId,
            serial: row.serial,
            state: row.state,
            createdAt: row.createdAt,
          ),
        )
        .toList(growable: false);
  }

  Future<void> setEquipmentScanState(String id, String state) {
    return (update(equipmentScanEntries)..where((row) => row.id.equals(id)))
        .write(EquipmentScanEntriesCompanion(state: Value(state)));
  }

  Future<int> pendingEvidenceUploadCount() async {
    final evidenceCountColumn = evidenceEntries.id.count();
    final evidenceQuery = selectOnly(evidenceEntries)
      ..addColumns([evidenceCountColumn])
      ..where(evidenceEntries.state.isIn(['pending', 'uploading']));
    final scanCountColumn = equipmentScanEntries.id.count();
    final scanQuery = selectOnly(equipmentScanEntries)
      ..addColumns([scanCountColumn])
      ..where(equipmentScanEntries.state.isIn(['pending', 'uploading']));
    final evidence =
        (await evidenceQuery.getSingle()).read(evidenceCountColumn) ?? 0;
    final scans = (await scanQuery.getSingle()).read(scanCountColumn) ?? 0;
    return evidence + scans;
  }

  Future<List<InventoryItem>> readInventory() async {
    final rows = await (select(inventoryItemEntries)
          ..orderBy([(row) => OrderingTerm.asc(row.description)]))
        .get();
    return rows
        .map(
          (row) => InventoryItem(
            id: row.id,
            sku: row.sku,
            description: row.description,
            quantity: row.quantity,
            unit: row.unit,
            serialNumber: row.serialNumber,
            version: row.version,
          ),
        )
        .toList(growable: false);
  }

  Future<void> replaceInventory(List<InventoryItem> items) {
    return transaction(() async {
      await delete(inventoryItemEntries).go();
      await batch((batch) {
        batch.insertAll(
          inventoryItemEntries,
          items
              .map(
                (item) => InventoryItemEntriesCompanion.insert(
                  id: item.id,
                  sku: item.sku,
                  description: item.description,
                  quantity: item.quantity,
                  unit: item.unit,
                  serialNumber: Value(item.serialNumber),
                  version: item.version,
                ),
              )
              .toList(growable: false),
        );
      });
    });
  }

  Future<void> upsertInventoryItem(InventoryItem item) {
    return into(inventoryItemEntries).insertOnConflictUpdate(
      InventoryItemEntriesCompanion.insert(
        id: item.id,
        sku: item.sku,
        description: item.description,
        quantity: item.quantity,
        unit: item.unit,
        serialNumber: Value(item.serialNumber),
        version: item.version,
      ),
    );
  }

  Future<String?> readSyncCursor() async {
    final row = await (select(appSettingEntries)
          ..where((entry) => entry.key.equals('sync_cursor')))
        .getSingleOrNull();
    return row?.value;
  }

  Future<void> writeSyncCursor(String cursor) {
    return into(appSettingEntries).insertOnConflictUpdate(
      AppSettingEntriesCompanion.insert(
        key: 'sync_cursor',
        value: cursor,
      ),
    );
  }

  Future<void> consumeInventory({
    required String movementId,
    required String workOrderId,
    required String itemId,
    required double quantity,
  }) {
    return transaction(() async {
      final current = await (select(inventoryItemEntries)
            ..where((row) => row.id.equals(itemId)))
          .getSingle();
      if (quantity <= 0 || quantity > current.quantity) {
        throw StateError('Saldo insuficiente');
      }
      await (update(inventoryItemEntries)
            ..where((row) => row.id.equals(itemId)))
          .write(
        InventoryItemEntriesCompanion(
          quantity: Value(current.quantity - quantity),
          version: Value(current.version + 1),
        ),
      );
      final occurredAt = DateTime.now().toUtc();
      await into(inventoryMovementEntries).insert(
        InventoryMovementEntriesCompanion.insert(
          id: movementId,
          workOrderId: workOrderId,
          itemId: itemId,
          quantity: quantity,
          kind: 'consume',
          occurredAt: occurredAt,
        ),
      );
      await into(syncQueueEntries).insert(
        SyncQueueEntriesCompanion.insert(
          operationId: movementId,
          entityType: 'inventory_movement',
          entityId: movementId,
          kind: 'consume',
          baseVersion: Value(current.version),
          occurredAt: occurredAt,
          payloadJson: jsonEncode({
            'item_id': itemId,
            'work_order_id': workOrderId,
            'quantity': quantity,
          }),
        ),
      );
    });
  }

  Future<int> inventoryMovementCount(String workOrderId) async {
    final count = inventoryMovementEntries.id.count();
    final query = selectOnly(inventoryMovementEntries)
      ..addColumns([count])
      ..where(inventoryMovementEntries.workOrderId.equals(workOrderId));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<List<SyncOperation>> pendingOperations() async {
    final rows = await (select(syncQueueEntries)
          ..where((row) => row.state.equals('pending'))
          ..orderBy([(row) => OrderingTerm.asc(row.occurredAt)]))
        .get();
    return rows
        .map(
          (row) => SyncOperation(
            operationId: row.operationId,
            entityType: row.entityType,
            entityId: row.entityId,
            kind: row.kind,
            baseVersion: row.baseVersion,
            occurredAt: row.occurredAt,
            payload:
                (jsonDecode(row.payloadJson) as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  Future<int> pendingOperationCount() async {
    final count = syncQueueEntries.operationId.count();
    final query = selectOnly(syncQueueEntries)
      ..addColumns([count])
      ..where(syncQueueEntries.state.equals('pending'));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<int> conflictedOperationCount() async {
    final count = syncQueueEntries.operationId.count();
    final query = selectOnly(syncQueueEntries)
      ..addColumns([count])
      ..where(syncQueueEntries.state.isIn(['conflict', 'rejected']));
    return (await query.getSingle()).read(count) ?? 0;
  }

  Future<int> discardConflictedOperations() {
    return (update(syncQueueEntries)
          ..where(
            (row) => row.state.isIn(['conflict', 'rejected']),
          ))
        .write(
      const SyncQueueEntriesCompanion(state: Value('discarded')),
    );
  }

  Future<void> acknowledgeOperation(String operationId) {
    return (update(syncQueueEntries)
          ..where((row) => row.operationId.equals(operationId)))
        .write(const SyncQueueEntriesCompanion(state: Value('acknowledged')));
  }

  Future<void> markOperationError(
    String operationId,
    String reason,
    String state,
  ) async {
    final current = await (select(syncQueueEntries)
          ..where((row) => row.operationId.equals(operationId)))
        .getSingle();
    await (update(syncQueueEntries)
          ..where((row) => row.operationId.equals(operationId)))
        .write(
      SyncQueueEntriesCompanion(
        state: Value(state),
        attempts: Value(current.attempts + 1),
        lastError: Value(reason),
      ),
    );
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final directory = await getApplicationSupportDirectory();
    final technicianId = TechnicianSession.technicianId ?? 'bench-technician';
    final safeId = technicianId.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
    final filename = safeId == 'bench-technician'
        ? 'isp_field.sqlite'
        : 'isp_field_$safeId.sqlite';
    final file = File(p.join(directory.path, filename));
    return NativeDatabase.createInBackground(file);
  });
}
