enum WorkOrderStatus {
  assigned,
  traveling,
  arrived,
  inProgress,
  blocked,
  completed,
  notCompleted
}

class WorkOrder {
  const WorkOrder({
    required this.id,
    required this.code,
    required this.customerName,
    required this.address,
    required this.status,
    required this.version,
    this.latitude,
    this.longitude,
    this.priority = 'normal',
    this.scheduledAt,
  });

  final String id;
  final String code;
  final String customerName;
  final String address;
  final WorkOrderStatus status;
  final int version;
  final double? latitude;
  final double? longitude;
  final String priority;
  final DateTime? scheduledAt;

  factory WorkOrder.fromJson(Map<String, dynamic> json) {
    return WorkOrder(
      id: json['id'] as String,
      code: json['code'] as String,
      customerName: json['customer_name'] as String,
      address: json['address'] as String,
      status: workOrderStatusFromApi(json['status'] as String),
      version: json['version'] as int,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      priority: json['priority'] as String? ?? 'normal',
      scheduledAt: json['scheduled_at'] == null
          ? null
          : DateTime.parse(json['scheduled_at'] as String),
    );
  }

  String get priorityLabel => switch (priority) {
        'low' => 'Baixa',
        'high' => 'Alta',
        'urgent' => 'Urgente',
        _ => 'Normal',
      };
}

class WorkOrderTransition {
  const WorkOrderTransition({
    required this.toStatus,
    this.note,
    this.latitude,
    this.longitude,
  });

  final WorkOrderStatus toStatus;
  final String? note;
  final double? latitude;
  final double? longitude;
}

class WorkOrderHistoryEntry {
  const WorkOrderHistoryEntry({
    required this.fromStatus,
    required this.toStatus,
    required this.occurredAt,
    this.note,
    this.latitude,
    this.longitude,
  });

  final WorkOrderStatus fromStatus;
  final WorkOrderStatus toStatus;
  final DateTime occurredAt;
  final String? note;
  final double? latitude;
  final double? longitude;
}

WorkOrderStatus workOrderStatusFromApi(String value) {
  return switch (value) {
    'assigned' => WorkOrderStatus.assigned,
    'traveling' => WorkOrderStatus.traveling,
    'arrived' => WorkOrderStatus.arrived,
    'in_progress' => WorkOrderStatus.inProgress,
    'blocked' => WorkOrderStatus.blocked,
    'completed' => WorkOrderStatus.completed,
    'not_completed' => WorkOrderStatus.notCompleted,
    _ => throw FormatException('Estado de OS desconhecido: $value'),
  };
}

extension WorkOrderStatusApiValue on WorkOrderStatus {
  String get apiValue => switch (this) {
        WorkOrderStatus.assigned => 'assigned',
        WorkOrderStatus.traveling => 'traveling',
        WorkOrderStatus.arrived => 'arrived',
        WorkOrderStatus.inProgress => 'in_progress',
        WorkOrderStatus.blocked => 'blocked',
        WorkOrderStatus.completed => 'completed',
        WorkOrderStatus.notCompleted => 'not_completed',
      };

  String get label => switch (this) {
        WorkOrderStatus.assigned => 'Atribuída',
        WorkOrderStatus.traveling => 'Em deslocamento',
        WorkOrderStatus.arrived => 'No local',
        WorkOrderStatus.inProgress => 'Em atendimento',
        WorkOrderStatus.blocked => 'Bloqueada',
        WorkOrderStatus.completed => 'Concluída',
        WorkOrderStatus.notCompleted => 'Não concluída',
      };
}
