import 'package:flutter_test/flutter_test.dart';
import 'package:isp_field/app/app.dart';
import 'package:isp_field/features/work_orders/data/work_order_repository.dart';
import 'package:isp_field/features/work_orders/domain/work_order.dart';
import 'package:isp_field/features/inventory/domain/inventory_item.dart';
import 'package:isp_field/features/provisioning/domain/onu_state.dart';
import 'package:isp_field/features/monitoring/domain/network_alert.dart';
import 'package:isp_field/features/access_test/domain/pppoe_test_result.dart';
import 'package:isp_field/features/feasibility/domain/feasibility_result.dart';
import 'dart:typed_data';

class _FakeRepository implements WorkOrderRepositoryContract {
  @override
  Future<List<WorkOrder>> loadCached() async => const [];

  @override
  Future<List<WorkOrder>> synchronize() async => const [];

  @override
  Future<int> pendingCount() async => 0;

  @override
  Future<int> conflictCount() async => 0;

  @override
  Future<List<WorkOrder>> reconcileConflicts() async => const [];

  @override
  Future<void> transition(
    String workOrderId,
    WorkOrderTransition transition,
  ) async {}

  @override
  Future<List<WorkOrderHistoryEntry>> transitionHistory(
    String workOrderId,
  ) async =>
      const [];

  @override
  Future<void> addEquipmentScan(String workOrderId, String serial) async {}

  @override
  Future<void> addPhoto(String workOrderId, String sourcePath) async {}

  @override
  Future<void> addSignature(String workOrderId, Uint8List bytes) async {}

  @override
  Future<int> equipmentScanCount(String workOrderId) async => 0;

  @override
  Future<int> evidenceCount(String workOrderId) async => 0;

  @override
  Future<int> photoCount(String workOrderId) async => 0;

  @override
  Future<int> signatureCount(String workOrderId) async => 0;

  @override
  Future<int> pendingEvidenceUploadCount() async => 0;

  @override
  Future<List<InventoryItem>> loadCachedInventory() async => const [];

  @override
  Future<List<InventoryItem>> synchronizeInventory() async => const [];

  @override
  Future<void> consumeInventory({
    required String workOrderId,
    required String itemId,
    required double quantity,
  }) async {}

  @override
  Future<int> inventoryMovementCount(String workOrderId) async => 0;

  @override
  Future<List<OnuState>> discoverOnus() async => const [];

  @override
  Future<OnuState> provisionOnu(
    String workOrderId,
    String serial,
    String profile,
  ) async =>
      OnuState(serial: serial, status: 'online', profile: profile);

  @override
  Future<List<ProvisioningRecord>> provisioningHistory(
    String workOrderId,
  ) async =>
      const [];

  @override
  Future<List<NetworkAlert>> networkAlerts() async => const [];

  @override
  Future<PppoeTestResult> testPppoe(
    String workOrderId,
    String username,
  ) async =>
      PppoeTestResult(
        username: username,
        status: 'authenticated',
        assignedIp: '10.20.0.1',
        latencyMs: 8,
        downloadMbps: 500,
        uploadMbps: 250,
        simulated: true,
      );

  @override
  Future<FeasibilityResult> checkFeasibility(
    String workOrderId,
    String address,
  ) async =>
      const FeasibilityResult(
        feasible: true,
        ctoCode: 'CTO-TEST',
        distanceMeters: 100,
        totalPorts: 8,
        availablePorts: 2,
        message: 'Viável',
        simulated: true,
      );
}

void main() {
  testWidgets('shows the offline work-order dashboard', (tester) async {
    await tester
        .pumpWidget(IspFieldApp(workOrderRepository: _FakeRepository()));
    await tester.pump();

    expect(find.text('Ordens de serviço'), findsOneWidget);
    expect(find.textContaining('Modo offline'), findsOneWidget);
    expect(find.textContaining('OS-0001'), findsOneWidget);
    expect(find.text('Iniciar rota'), findsOneWidget);
    expect(find.text('Todas'), findsOneWidget);
    expect(find.text('Pendentes'), findsWidgets);
    expect(find.text('Finalizadas'), findsWidgets);
  });
}
