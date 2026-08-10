import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TechnicianSession {
  TechnicianSession._();

  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'technician_access_token';
  static const _technicianIdKey = 'technician_id';
  static String? accessToken;
  static String? technicianId;

  static Future<bool> restore() async {
    accessToken = await _storage.read(key: _tokenKey);
    technicianId = await _storage.read(key: _technicianIdKey);
    return accessToken != null &&
        accessToken!.isNotEmpty &&
        technicianId != null;
  }

  static Future<void> save(String token, String id) async {
    accessToken = token;
    technicianId = id;
    await _storage.write(key: _tokenKey, value: token);
    await _storage.write(key: _technicianIdKey, value: id);
  }

  static Future<void> clear() async {
    accessToken = null;
    technicianId = null;
    await _storage.delete(key: _tokenKey);
    await _storage.delete(key: _technicianIdKey);
  }
}
