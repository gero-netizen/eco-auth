import 'package:flutter/material.dart';

import '../../../core/auth/technician_session.dart';
import '../../../core/config/server_config.dart';
import 'change_password_page.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key, this.onLogout});

  final Future<void> Function()? onLogout;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  Future<void> _editServerAddress() async {
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
    if (trimmed.isEmpty ||
        !(trimmed.startsWith('http://') || trimmed.startsWith('https://'))) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Endereço inválido. Use http:// ou https://.')),
        );
      }
      return;
    }
    await ServerConfig.save(trimmed);
    if (mounted) setState(() {});
  }

  Future<void> _confirmLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Sair'),
        content: const Text('Deseja encerrar sua sessão neste aparelho?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('CANCELAR'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('SAIR'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await widget.onLogout?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Configurações')),
      body: ListView(
        children: [
          const ListTile(
            leading: Icon(Icons.person_outline),
            title: Text('Técnico'),
            subtitle: Text('Identificação da sessão atual'),
          ),
          ListTile(
            leading: const SizedBox(width: 24),
            title: const Text('Usuário'),
            subtitle: Text(TechnicianSession.username ?? 'Não identificado'),
          ),
          const Divider(),
          const ListTile(
            leading: Icon(Icons.dns_outlined),
            title: Text('Servidor'),
            subtitle: Text('Endereço da central deste provedor'),
          ),
          ListTile(
            leading: const SizedBox(width: 24),
            title: Text(
              ServerConfig.baseUrl.isEmpty
                  ? 'Não configurado'
                  : ServerConfig.baseUrl,
            ),
            trailing: const Icon(Icons.edit_outlined),
            onTap: _editServerAddress,
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.lock_outline),
            title: const Text('Trocar senha'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ChangePasswordPage()),
              );
            },
          ),
          if (widget.onLogout != null) ...[
            const Divider(),
            ListTile(
              leading: Icon(Icons.logout, color: Theme.of(context).colorScheme.error),
              title: Text(
                'Sair',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              onTap: _confirmLogout,
            ),
          ],
        ],
      ),
    );
  }
}
