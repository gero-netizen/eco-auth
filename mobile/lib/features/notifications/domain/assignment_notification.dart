class AssignmentNotification {
  const AssignmentNotification({
    required this.id,
    required this.workOrderId,
    required this.orderCode,
    required this.customerName,
    required this.receivedAt,
    this.read = false,
  });

  final String id;
  final String workOrderId;
  final String orderCode;
  final String customerName;
  final DateTime receivedAt;
  final bool read;

  AssignmentNotification copyWith({bool? read}) => AssignmentNotification(
        id: id,
        workOrderId: workOrderId,
        orderCode: orderCode,
        customerName: customerName,
        receivedAt: receivedAt,
        read: read ?? this.read,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'work_order_id': workOrderId,
        'order_code': orderCode,
        'customer_name': customerName,
        'received_at': receivedAt.toIso8601String(),
        'read': read,
      };

  factory AssignmentNotification.fromJson(Map<String, dynamic> json) =>
      AssignmentNotification(
        id: json['id'] as String,
        workOrderId: json['work_order_id'] as String,
        orderCode: json['order_code'] as String,
        customerName: json['customer_name'] as String,
        receivedAt: DateTime.parse(json['received_at'] as String),
        read: json['read'] as bool? ?? false,
      );
}
