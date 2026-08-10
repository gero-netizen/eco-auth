class FeasibilityResult {
  const FeasibilityResult({
    required this.feasible,
    required this.ctoCode,
    required this.distanceMeters,
    required this.totalPorts,
    required this.availablePorts,
    required this.message,
    required this.simulated,
  });

  final bool feasible;
  final String ctoCode;
  final int distanceMeters;
  final int totalPorts;
  final int availablePorts;
  final String message;
  final bool simulated;

  factory FeasibilityResult.fromJson(Map<String, dynamic> json) {
    return FeasibilityResult(
      feasible: json['feasible'] as bool,
      ctoCode: json['cto_code'] as String,
      distanceMeters: json['distance_meters'] as int,
      totalPorts: json['total_ports'] as int,
      availablePorts: json['available_ports'] as int,
      message: json['message'] as String,
      simulated: json['simulated'] as bool? ?? false,
    );
  }
}
