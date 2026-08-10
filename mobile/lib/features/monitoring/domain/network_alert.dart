class NetworkAlert {
  const NetworkAlert({
    required this.id,
    required this.severity,
    required this.title,
    required this.area,
    required this.simulated,
  });

  final String id;
  final String severity;
  final String title;
  final String area;
  final bool simulated;

  factory NetworkAlert.fromJson(Map<String, dynamic> json) {
    return NetworkAlert(
      id: json['id'] as String,
      severity: json['severity'] as String,
      title: json['title'] as String,
      area: json['area'] as String,
      simulated: json['simulated'] as bool? ?? false,
    );
  }
}
