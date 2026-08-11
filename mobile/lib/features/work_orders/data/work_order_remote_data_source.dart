import 'package:dio/dio.dart';
import 'dart:io';

import '../../../core/config/server_config.dart';
import '../../../core/auth/technician_session.dart';
import '../domain/work_order.dart';
import '../../../core/sync/sync_operation.dart';
import '../../capture/domain/evidence.dart';
import '../../inventory/domain/inventory_item.dart';
import '../../provisioning/domain/onu_state.dart';
import '../../monitoring/domain/network_alert.dart';
import '../../access_test/domain/pppoe_test_result.dart';
import '../../feasibility/domain/feasibility_result.dart';
import 'package:uuid/uuid.dart';

class SyncPullResult {
  const SyncPullResult({
    required this.workOrders,
    required this.inventoryItems,
    required this.nextCursor,
  });

  final List<WorkOrder> workOrders;
  final List<InventoryItem> inventoryItems;
  final String nextCursor;
}

class WorkOrderRemoteDataSource {
  WorkOrderRemoteDataSource({Dio? dio}) : _dio = dio ?? _buildDefaultDio();

  static Dio _buildDefaultDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: ServerConfig.baseUrl,
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 10),
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = TechnicianSession.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
    return dio;
  }

  final Dio _dio;

  Future<List<WorkOrder>> fetchAll() async {
    if (ServerConfig.baseUrl.isEmpty) {
      throw StateError('API_BASE_URL não foi configurada');
    }

    final response = await _dio.get<List<dynamic>>('/api/v1/work-orders');
    final body = response.data ?? const [];
    return body
        .map((item) => WorkOrder.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> push(
    List<SyncOperation> operations,
  ) async {
    if (ServerConfig.baseUrl.isEmpty) {
      throw StateError('API_BASE_URL não foi configurada');
    }
    if (operations.isEmpty) return const [];

    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/sync/push',
      data: {
        'device_id': '00000000-0000-4000-8000-000000000001',
        'operations': operations.map((item) => item.toJson()).toList(),
      },
    );
    final results = response.data?['results'] as List<dynamic>? ?? const [];
    return results
        .map((item) => (item as Map).cast<String, dynamic>())
        .toList(growable: false);
  }

  Future<SyncPullResult> pull(String? cursor) async {
    if (ServerConfig.baseUrl.isEmpty) {
      throw StateError('API_BASE_URL não foi configurada');
    }
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/sync/pull',
      queryParameters: cursor == null ? null : {'cursor': cursor},
    );
    final body = response.data ?? const <String, dynamic>{};
    final changes = body['changes'] as List<dynamic>? ?? const [];
    final workOrders = <WorkOrder>[];
    final inventoryItems = <InventoryItem>[];
    for (final rawChange in changes) {
      final change = (rawChange as Map).cast<String, dynamic>();
      if (change['kind'] != 'upsert') continue;
      final payload = (change['payload'] as Map).cast<String, dynamic>();
      switch (change['entity_type']) {
        case 'work_order':
          workOrders.add(WorkOrder.fromJson(payload));
        case 'inventory_item':
          inventoryItems.add(InventoryItem.fromJson(payload));
      }
    }
    return SyncPullResult(
      workOrders: workOrders,
      inventoryItems: inventoryItems,
      nextCursor: body['next_cursor'] as String? ?? cursor ?? '0',
    );
  }

  Future<void> uploadEvidence(LocalEvidence evidence) async {
    final bytes = await File(evidence.localPath).readAsBytes();
    await _dio.post<Map<String, dynamic>>(
      '/api/v1/work-orders/${evidence.workOrderId}/evidence/${evidence.id}',
      data: bytes,
      options: Options(
        contentType: 'application/octet-stream',
        headers: {
          'X-Evidence-Category': evidence.category,
          'X-Content-SHA256': evidence.sha256,
        },
      ),
    );
  }

  Future<void> uploadEquipmentScan(LocalEquipmentScan scan) async {
    await _dio.post<Map<String, dynamic>>(
      '/api/v1/work-orders/${scan.workOrderId}/equipment/${scan.id}',
      data: {'serial': scan.serial},
    );
  }

  Future<List<InventoryItem>> fetchInventory() async {
    if (ServerConfig.baseUrl.isEmpty) {
      throw StateError('API_BASE_URL não foi configurada');
    }
    final response = await _dio.get<List<dynamic>>('/api/v1/inventory');
    return (response.data ?? const [])
        .map((item) => InventoryItem.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<OnuState>> discoverOnus() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/olt/onus');
    return (response.data ?? const [])
        .map((item) => OnuState.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<OnuState> provisionOnu(
    String workOrderId,
    String serial,
    String profile,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/olt/onus/provision',
      data: {
        'operation_id': const Uuid().v4(),
        'work_order_id': workOrderId,
        'serial': serial,
        'profile': profile,
      },
    );
    return OnuState.fromJson(response.data!);
  }

  Future<List<ProvisioningRecord>> provisioningHistory(
    String workOrderId,
  ) async {
    final response = await _dio.get<List<dynamic>>(
      '/api/v1/olt/provisioning',
      queryParameters: {'work_order_id': workOrderId},
    );
    return (response.data ?? const [])
        .map(
          (item) => ProvisioningRecord.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList(growable: false);
  }

  Future<List<NetworkAlert>> networkAlerts() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/network/alerts');
    return (response.data ?? const [])
        .map((item) => NetworkAlert.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<PppoeTestResult> testPppoe(
    String workOrderId,
    String username,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/access/pppoe/test',
      data: {'work_order_id': workOrderId, 'username': username},
    );
    return PppoeTestResult.fromJson(response.data!);
  }

  Future<FeasibilityResult> checkFeasibility(
    String workOrderId,
    String address,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/feasibility/check',
      data: {'work_order_id': workOrderId, 'address': address},
    );
    return FeasibilityResult.fromJson(response.data!);
  }
}
