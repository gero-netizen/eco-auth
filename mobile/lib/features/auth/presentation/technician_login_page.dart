import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../../core/config/api_config.dart';

class TechnicianLoginPage extends StatefulWidget {
  const TechnicianLoginPage({
    super.key,
    required this.onAuthenticated,
    required this.onOffline,
  });

  final void Function(String token, String technicianId) onAuthenticated;
  final VoidCallback onOffline;

  @override
  State<TechnicianLoginPage> createState() => _TechnicianLoginPageState();
}

class _TechnicianLoginPageState extends State<TechnicianLoginPage> {
  final _username = TextEditingController(text: 'tecnico');
  final _password = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (apiBaseUrl.isEmpty) {
      setState(() => _error = 'Endereço da central não configurado.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await Dio(BaseOptions(baseUrl: apiBaseUrl))
          .post<Map<String, dynamic>>(
        '/api/v1/auth/technician/login',
        data: {'username': _username.text.trim(), 'password': _password.text},
      );
      final token = response.data?['access_token'] as String?;
      final technician = response.data?['technician'] as Map<String, dynamic>?;
      final technicianId = technician?['id'] as String?;
      if (token == null || token.isEmpty || technicianId == null) {
        throw StateError('Sessão incompleta');
      }
      widget.onAuthenticated(token, technicianId);
    } on DioException catch (error) {
      setState(() => _error = error.response?.statusCode == 401
          ? 'Usuário ou senha incorretos.'
          : 'Não foi possível acessar a central.');
    } catch (_) {
      setState(() => _error = 'Não foi possível entrar.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Acesso do técnico')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.engineering_outlined,
                    size: 72, color: Color(0xFF075E54)),
                const SizedBox(height: 24),
                TextField(
                  controller: _username,
                  decoration: const InputDecoration(
                      labelText: 'Usuário', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _password,
                  obscureText: true,
                  onSubmitted: (_) => _login(),
                  decoration: const InputDecoration(
                      labelText: 'Senha', border: OutlineInputBorder()),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error)),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _loading ? null : _login,
                  child: Text(_loading ? 'ENTRANDO...' : 'ENTRAR'),
                ),
                TextButton(
                  onPressed: _loading ? null : widget.onOffline,
                  child: const Text('CONTINUAR OFFLINE'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
