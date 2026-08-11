import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../../core/config/server_config.dart';

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
    if (ServerConfig.baseUrl.isEmpty) {
      setState(() => _error = 'Endereço da central não configurado.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await Dio(BaseOptions(baseUrl: ServerConfig.baseUrl))
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

  Future<void> _configureServer() async {
    final controller = TextEditingController(text: ServerConfig.baseUrl);
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Endereço do servidor'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(
            labelText: 'Endereço da central do seu provedor',
            hintText: 'https://central.seuprovedor.com.br',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('CANCELAR'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(controller.text),
            child: const Text('SALVAR'),
          ),
        ],
      ),
    );
    if (result == null) return;
    final trimmed = result.trim();
    if (trimmed.isEmpty || !(trimmed.startsWith('http://') || trimmed.startsWith('https://'))) {
      setState(() => _error = 'Endereço inválido. Use http:// ou https://.');
      return;
    }
    await ServerConfig.save(trimmed);
    if (!mounted) return;
    setState(() => _error = null);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Acesso do técnico'),
        actions: [
          IconButton(
            tooltip: 'Configurar servidor',
            icon: const Icon(Icons.settings_ethernet),
            onPressed: _loading ? null : _configureServer,
          ),
        ],
      ),
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
                const SizedBox(height: 12),
                InkWell(
                  onTap: _loading ? null : _configureServer,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          ServerConfig.baseUrl.isEmpty
                              ? Icons.error_outline
                              : Icons.dns_outlined,
                          size: 16,
                          color: ServerConfig.baseUrl.isEmpty
                              ? Theme.of(context).colorScheme.error
                              : Colors.grey,
                        ),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            ServerConfig.baseUrl.isEmpty
                                ? 'Servidor não configurado — toque para configurar'
                                : ServerConfig.baseUrl,
                            style: const TextStyle(fontSize: 12, color: Colors.grey),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
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
