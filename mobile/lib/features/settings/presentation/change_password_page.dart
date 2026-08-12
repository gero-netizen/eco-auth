import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../../core/auth/technician_session.dart';
import '../../../core/config/server_config.dart';

class ChangePasswordPage extends StatefulWidget {
  const ChangePasswordPage({super.key, this.forced = false, this.onChanged});

  /// Quando true (senha temporária vinda de um reset do admin), a tela não
  /// pode ser fechada sem trocar a senha — sem botão de voltar, sem escapar.
  final bool forced;

  /// Chamado ao trocar com sucesso, no lugar de simplesmente fechar a tela
  /// (usado no fluxo obrigatório, onde não há para onde "voltar" ainda).
  final VoidCallback? onChanged;

  @override
  State<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends State<ChangePasswordPage> {
  final _currentPassword = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirmPassword = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _currentPassword.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    if (_newPassword.text.length < 8) {
      setState(() => _error = 'A nova senha precisa ter pelo menos 8 caracteres.');
      return;
    }
    if (_newPassword.text != _confirmPassword.text) {
      setState(() => _error = 'A confirmação não bate com a nova senha.');
      return;
    }
    if (ServerConfig.baseUrl.isEmpty) {
      setState(() => _error = 'Servidor não configurado.');
      return;
    }
    setState(() => _saving = true);
    try {
      await Dio(BaseOptions(
        baseUrl: ServerConfig.baseUrl,
        headers: {'Authorization': 'Bearer ${TechnicianSession.accessToken}'},
      )).post('/api/v1/auth/technician/change-password', data: {
        'current_password': _currentPassword.text,
        'new_password': _newPassword.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Senha alterada com sucesso.')),
        );
        if (widget.forced) {
          widget.onChanged?.call();
        } else {
          Navigator.of(context).pop();
        }
      }
    } on DioException catch (error) {
      setState(() => _error = error.response?.statusCode == 422
          ? 'Senha atual incorreta ou nova senha inválida.'
          : 'Não foi possível trocar a senha agora. Tente novamente mais tarde.');
    } catch (_) {
      setState(() => _error = 'Não foi possível trocar a senha.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !widget.forced,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Trocar senha'),
          automaticallyImplyLeading: !widget.forced,
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.forced) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.amber.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'Sua senha foi redefinida pela central. Defina uma nova '
                    'senha para continuar.',
                  ),
                ),
                const SizedBox(height: 16),
              ],
              TextField(
                controller: _currentPassword,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: widget.forced ? 'Senha temporária' : 'Senha atual',
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _newPassword,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Nova senha (mínimo 8 caracteres)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _confirmPassword,
                obscureText: true,
                onSubmitted: (_) => _submit(),
                decoration: const InputDecoration(
                  labelText: 'Confirmar nova senha',
                  border: OutlineInputBorder(),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _saving ? null : _submit,
                child: Text(_saving ? 'SALVANDO...' : 'SALVAR NOVA SENHA'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
