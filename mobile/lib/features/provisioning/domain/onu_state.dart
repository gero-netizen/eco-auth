class OnuState {
  const OnuState({
    required this.serial,
    required this.status,
    this.signalDbm,
    this.profile,
  });

  final String serial;
  final String status;
  final double? signalDbm;
  final String? profile;

  factory OnuState.fromJson(Map<String, dynamic> json) {
    return OnuState(
      serial: json['serial'] as String,
      status: json['status'] as String,
      signalDbm: (json['signal_dbm'] as num?)?.toDouble(),
      profile: json['profile'] as String?,
    );
  }
}

class ProvisioningRecord extends OnuState {
  const ProvisioningRecord({
    required super.serial,
    required super.status,
    required this.createdAt,
    super.signalDbm,
    super.profile,
  });

  final DateTime createdAt;

  factory ProvisioningRecord.fromJson(Map<String, dynamic> json) {
    final timestamp = json['created_at'] as String;
    return ProvisioningRecord(
      serial: json['serial'] as String,
      status: json['status'] as String,
      signalDbm: (json['signal_dbm'] as num?)?.toDouble(),
      profile: json['profile'] as String?,
      createdAt: DateTime.parse('${timestamp}Z').toLocal(),
    );
  }
}
