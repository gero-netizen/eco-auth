import 'package:flutter/material.dart';

import '../domain/pppoe_test_result.dart';

class PppoeTestPage extends StatefulWidget {
  const PppoeTestPage({super.key, required this.runTest});

  final Future<PppoeTestResult> Function(String username) runTest;

  @override
  State<PppoeTestPage> createState() => _PppoeTestPageState();
}

class _PppoeTestPageState extends State<PppoeTestPage> {
  final _usernameController = TextEditingController(text: 'cliente.teste');
  bool _loading = false;
  String? _error;
  PppoeTestResult? _result;

  @override
  void dispose() {
    _usernameController.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    final username = _usernameController.text.trim();
    if (username.isEmpty) {
      setState(() => _error = 'Informe o login PPPoE');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await widget.runTest(username);
      if (mounted) setState(() => _result = result);
    } catch (_) {
      if (mounted) setState(() => _error = 'Simulador PPPoE indisponível');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Teste PPPoE')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            color: Theme.of(context).colorScheme.tertiaryContainer,
            child: const ListTile(
              leading: Icon(Icons.science_outlined),
              title: Text('MODO SIMULADOR'),
              subtitle: Text(
                'Não consulta o RADIUS/MikroTik real e não solicita senha.',
              ),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _usernameController,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Login PPPoE do cliente',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _loading ? null : _run,
            icon: const Icon(Icons.network_check),
            label: const Text('EXECUTAR TESTE SIMULADO'),
          ),
          if (_loading) ...[
            const SizedBox(height: 16),
            const LinearProgressIndicator(),
          ],
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (_result != null) ...[
            const SizedBox(height: 20),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.check)),
                    title: Text(_result!.username),
                    subtitle: Text('Status: ${_result!.status}'),
                  ),
                  const Divider(height: 1),
                  _metric('IP atribuído', _result!.assignedIp),
                  _metric('Latência', '${_result!.latencyMs} ms'),
                  _metric(
                    'Download',
                    '${_result!.downloadMbps.toStringAsFixed(1)} Mbps',
                  ),
                  _metric(
                    'Upload',
                    '${_result!.uploadMbps.toStringAsFixed(1)} Mbps',
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _metric(String label, String value) => ListTile(
        dense: true,
        title: Text(label),
        trailing: Text(value),
      );
}
