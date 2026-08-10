class LocalEvidence {
  const LocalEvidence({
    required this.id,
    required this.workOrderId,
    required this.category,
    required this.localPath,
    required this.sha256,
    required this.state,
    required this.createdAt,
  });

  final String id;
  final String workOrderId;
  final String category;
  final String localPath;
  final String sha256;
  final String state;
  final DateTime createdAt;
}

class LocalEquipmentScan {
  const LocalEquipmentScan({
    required this.id,
    required this.workOrderId,
    required this.serial,
    required this.state,
    required this.createdAt,
  });

  final String id;
  final String workOrderId;
  final String serial;
  final String state;
  final DateTime createdAt;
}
