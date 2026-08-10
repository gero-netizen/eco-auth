class SyncOperation {
  const SyncOperation({
    required this.operationId,
    required this.entityType,
    required this.entityId,
    required this.kind,
    required this.occurredAt,
    required this.payload,
    this.baseVersion,
  });

  final String operationId;
  final String entityType;
  final String entityId;
  final String kind;
  final int? baseVersion;
  final DateTime occurredAt;
  final Map<String, Object?> payload;

  Map<String, Object?> toJson() => {
        'operation_id': operationId,
        'entity_type': entityType,
        'entity_id': entityId,
        'kind': kind,
        'base_version': baseVersion,
        'occurred_at': occurredAt.toUtc().toIso8601String(),
        'payload': payload,
      };
}

abstract interface class SyncQueue {
  Future<void> enqueue(SyncOperation operation);
  Future<List<SyncOperation>> pending({int limit = 100});
  Future<void> markAcknowledged(String operationId);
  Future<void> markConflict(String operationId, String reason);
}
