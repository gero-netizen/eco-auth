import 'package:flutter/services.dart';
import 'dart:math' as math;

class RouteStop {
  const RouteStop({required this.label, this.latitude, this.longitude});

  final String label;
  final double? latitude;
  final double? longitude;

  String get mapValue =>
      latitude == null || longitude == null ? label : '$latitude,$longitude';
}

List<RouteStop> orderStopsByProximity(
  List<RouteStop> stops, {
  required double startLatitude,
  required double startLongitude,
}) {
  final remaining = List<RouteStop>.of(stops);
  final ordered = <RouteStop>[];
  var latitude = startLatitude;
  var longitude = startLongitude;
  while (remaining.isNotEmpty) {
    var nearestIndex = 0;
    var nearestDistance = double.infinity;
    for (var index = 0; index < remaining.length; index++) {
      final stop = remaining[index];
      if (stop.latitude == null || stop.longitude == null) continue;
      final distance = math.pow(stop.latitude! - latitude, 2) +
          math.pow(stop.longitude! - longitude, 2);
      if (distance < nearestDistance) {
        nearestDistance = distance.toDouble();
        nearestIndex = index;
      }
    }
    final nearest = remaining.removeAt(nearestIndex);
    ordered.add(nearest);
    latitude = nearest.latitude ?? latitude;
    longitude = nearest.longitude ?? longitude;
  }
  return ordered;
}

class RouteLauncher {
  const RouteLauncher();

  static const _channel =
      MethodChannel('br.com.g7networks.isp_field/navigation');

  Future<void> open(List<String> addresses) async {
    final uri = buildDirectionsUri(addresses);
    if (uri == null) throw StateError('Nenhum endereço disponível para a rota');
    await _channel.invokeMethod<void>('openRoute', {'url': uri.toString()});
  }
}

Uri? buildDirectionsUri(List<String> addresses) {
  final stops = addresses
      .map((address) => address.trim())
      .where((address) => address.isNotEmpty)
      .take(10)
      .toList(growable: false);
  if (stops.isEmpty) return null;

  final parameters = <String, String>{
    'api': '1',
    'destination': stops.last,
    'travelmode': 'driving',
  };
  if (stops.length > 1) {
    parameters['waypoints'] = stops.take(stops.length - 1).join('|');
  }
  return Uri.https('www.google.com', '/maps/dir/', parameters);
}
