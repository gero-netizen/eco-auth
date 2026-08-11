import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_config.dart' as compile_time;

/// Endereço do servidor da Central deste provedor. Antes era fixo em tempo
/// de compilação (um APK por provedor); agora pode ser configurado pelo
/// técnico na tela de login e fica salvo no aparelho.
class ServerConfig {
  ServerConfig._();

  static const _storage = FlutterSecureStorage();
  static const _baseUrlKey = 'server_base_url';
  static String _baseUrl = compile_time.apiBaseUrl;

  static String get baseUrl => _baseUrl;

  static Future<void> restore() async {
    final stored = await _storage.read(key: _baseUrlKey);
    if (stored != null && stored.trim().isNotEmpty) {
      _baseUrl = _normalize(stored);
    }
  }

  static Future<void> save(String url) async {
    final normalized = _normalize(url);
    _baseUrl = normalized;
    await _storage.write(key: _baseUrlKey, value: normalized);
  }

  static String _normalize(String url) {
    final trimmed = url.trim();
    return trimmed.endsWith('/')
        ? trimmed.substring(0, trimmed.length - 1)
        : trimmed;
  }
}
