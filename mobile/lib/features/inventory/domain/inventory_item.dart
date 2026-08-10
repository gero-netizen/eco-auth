class InventoryItem {
  const InventoryItem({
    required this.id,
    required this.sku,
    required this.description,
    required this.quantity,
    required this.unit,
    required this.version,
    this.serialNumber,
  });

  final String id;
  final String sku;
  final String description;
  final double quantity;
  final String unit;
  final String? serialNumber;
  final int version;

  factory InventoryItem.fromJson(Map<String, dynamic> json) => InventoryItem(
        id: json['id'] as String,
        sku: json['sku'] as String,
        description: json['description'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        unit: json['unit'] as String,
        serialNumber: json['serial_number'] as String?,
        version: json['version'] as int,
      );
}
