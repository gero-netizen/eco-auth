import 'package:geolocator/geolocator.dart';

class CapturedLocation {
  const CapturedLocation(this.latitude, this.longitude);

  final double latitude;
  final double longitude;
}

class LocationService {
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
