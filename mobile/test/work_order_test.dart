import 'package:flutter_test/flutter_test.dart';
import 'package:isp_field/features/work_orders/domain/work_order.dart';
import 'package:isp_field/core/navigation/route_launcher.dart';
import 'package:isp_field/features/provisioning/domain/onu_state.dart';
import 'package:isp_field/features/monitoring/domain/network_alert.dart';
import 'package:isp_field/features/access_test/domain/pppoe_test_result.dart';
import 'package:isp_field/features/feasibility/domain/feasibility_result.dart';

void main() {
  test('aceita OS vinculada ao MK-AUTH sem expor o vínculo no app', () {
    final order = WorkOrder.fromJson({
      'id': 'sim-os-linked',
      'code': 'OS-9999',
      'customer_name': 'Cliente MK-AUTH',
      'address': 'Rua da Bancada, 20',
      'status': 'assigned',
      'version': 1,
      'external_customer_id': 'customer-uuid-1',
    });

    expect(order.customerName, 'Cliente MK-AUTH');
    expect(order.status, WorkOrderStatus.assigned);
  });

  test('work order keeps its server version for optimistic sync', () {
    const order = WorkOrder(
      id: '1',
      code: 'OS-1',
      customerName: 'Teste',
      address: 'Bancada',
      status: WorkOrderStatus.assigned,
      version: 7,
    );
    expect(order.version, 7);
  });

  test('daily route keeps the displayed stop order', () {
    final uri = buildDirectionsUri([
      'Rua Primeiro Cliente, 10',
      'Rua Segundo Cliente, 20',
      'Rua Último Cliente, 30',
    ]);

    expect(uri, isNotNull);
    expect(uri!.queryParameters['destination'], 'Rua Último Cliente, 30');
    expect(
      uri.queryParameters['waypoints'],
      'Rua Primeiro Cliente, 10|Rua Segundo Cliente, 20',
    );
    expect(uri.queryParameters['travelmode'], 'driving');
  });

  test('daily route orders coordinate stops from the technician position', () {
    final ordered = orderStopsByProximity(
      const [
        RouteStop(label: 'Longe', latitude: -12.99, longitude: -38.52),
        RouteStop(label: 'Perto', latitude: -12.971, longitude: -38.501),
      ],
      startLatitude: -12.970,
      startLongitude: -38.500,
    );
    expect(ordered.map((item) => item.label), ['Perto', 'Longe']);
  });

  test('coordinate stops generate a route without unrelated addresses', () {
    const stops = [
      RouteStop(label: 'Centro', latitude: -12.9726, longitude: -38.5108),
      RouteStop(label: 'Comercio', latitude: -12.9718, longitude: -38.5133),
    ];
    final uri = buildDirectionsUri(
      stops.map((item) => item.mapValue).toList(growable: false),
    );
    expect(uri!.queryParameters['waypoints'], '-12.9726,-38.5108');
    expect(uri.queryParameters['destination'], '-12.9718,-38.5133');
  });

  test('ONU simulator response keeps signal and profile', () {
    final onu = OnuState.fromJson({
      'serial': 'SIMONU0001',
      'status': 'online',
      'signal_dbm': -19.2,
      'profile': 'ftth-500',
    });

    expect(onu.serial, 'SIMONU0001');
    expect(onu.signalDbm, -19.2);
    expect(onu.profile, 'ftth-500');
  });

  test('network alert remains explicitly labeled as simulated', () {
    final alert = NetworkAlert.fromJson({
      'id': 'alert-1',
      'severity': 'warning',
      'title': 'Oscilação',
      'area': 'Bancada',
      'simulated': true,
    });

    expect(alert.simulated, isTrue);
    expect(alert.area, 'Bancada');
  });

  test('PPPoE simulator response parses connection metrics', () {
    final result = PppoeTestResult.fromJson({
      'username': 'cliente.teste',
      'status': 'authenticated',
      'assigned_ip': '10.20.1.2',
      'latency_ms': 8,
      'download_mbps': 500.0,
      'upload_mbps': 250.0,
      'simulated': true,
    });

    expect(result.status, 'authenticated');
    expect(result.downloadMbps, 500);
    expect(result.simulated, isTrue);
  });

  test('FTTH feasibility response keeps CTO capacity', () {
    final result = FeasibilityResult.fromJson({
      'feasible': true,
      'cto_code': 'CTO-BENCH-01',
      'distance_meters': 120,
      'total_ports': 8,
      'available_ports': 3,
      'message': 'Porta disponível',
      'simulated': true,
    });

    expect(result.feasible, isTrue);
    expect(result.availablePorts, 3);
    expect(result.ctoCode, 'CTO-BENCH-01');
  });
}
