import 'package:geolocator/geolocator.dart';

enum LocationStatus { ready, serviceDisabled, permissionDenied, permissionDeniedForever }

class CapturedLocation {
  const CapturedLocation(this.latitude, this.longitude);

  final double latitude;
  final double longitude;
}

class LocationService {
  /// Verifica o estado do GPS sem tentar capturar uma posição — usado
  /// para mostrar um aviso na tela quando o serviço está desligado, antes
  /// mesmo do técnico tentar registrar algo.
  Future<LocationStatus> checkStatus() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      return LocationStatus.serviceDisabled;
    }
    final permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.deniedForever) {
      return LocationStatus.permissionDeniedForever;
    }
    if (permission == LocationPermission.denied) {
      return LocationStatus.permissionDenied;
    }
    return LocationStatus.ready;
  }

  Future<CapturedLocation?> captureOptional() async {
    if (!await Geolocator.isLocationServiceEnabled()) return null;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return null;
    }

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
      return CapturedLocation(position.latitude, position.longitude);
    } catch (_) {
      return null;
    }
  }
}
