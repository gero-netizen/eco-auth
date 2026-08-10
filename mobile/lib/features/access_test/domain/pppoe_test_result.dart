class PppoeTestResult {
  const PppoeTestResult({
    required this.username,
    required this.status,
    required this.assignedIp,
    required this.latencyMs,
    required this.downloadMbps,
    required this.uploadMbps,
    required this.simulated,
  });

  final String username;
  final String status;
  final String assignedIp;
  final int latencyMs;
  final double downloadMbps;
  final double uploadMbps;
  final bool simulated;

  factory PppoeTestResult.fromJson(Map<String, dynamic> json) {
    return PppoeTestResult(
      username: json['username'] as String,
      status: json['status'] as String,
      assignedIp: json['assigned_ip'] as String,
      latencyMs: json['latency_ms'] as int,
      downloadMbps: (json['download_mbps'] as num).toDouble(),
      uploadMbps: (json['upload_mbps'] as num).toDouble(),
      simulated: json['simulated'] as bool? ?? false,
    );
  }
}
