import 'package:flutter/material.dart';

import '../domain/feasibility_result.dart';

class FeasibilityPage extends StatefulWidget {
  const FeasibilityPage({
    super.key,
    required this.address,
    required this.check,
  });

  final String address;
  final Future<FeasibilityResult> Function(String address) check;

  @override
  State<FeasibilityPage> createState() => _FeasibilityPageState();
}

class _FeasibilityPageState extends State<FeasibilityPage> {
  late final _addressController = TextEditingController(text: widget.address);
  bool _loading = false;
  String? _error;
  FeasibilityResult? _result;

  @override
  void dispose() {
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _check() async {
    final address = _addressController.text.trim();
    if (address.isEmpty) {
      setState(() => _error = 'Informe o endereço da instalação');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await widget.check(address);
      if (mounted) setState(() => _result = result);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Simulador de viabilidade indisponível');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Viabilidade FTTH')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            color: Theme.of(context).colorScheme.tertiaryContainer,
            child: const ListTile(
              leading: Icon(Icons.science_outlined),
              title: Text('MODO SIMULADOR'),
              subtitle: Text('Não consulta nem reserva portas de CTO reais.'),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _addressController,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Endereço da instalação',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _loading ? null : _check,
            icon: const Icon(Icons.cell_tower_outlined),
            label: const Text('CONSULTAR VIABILIDADE'),
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
                    leading: CircleAvatar(
                      child: Icon(
                        _result!.feasible ? Icons.check : Icons.close,
                      ),
                    ),
                    title: Text(
                      _result!.feasible ? 'VIÁVEL' : 'SEM VIABILIDADE',
                    ),
                    subtitle: Text(_result!.message),
                  ),
                  const Divider(height: 1),
                  _item('CTO sugerida', _result!.ctoCode),
                  _item('Distância estimada', '${_result!.distanceMeters} m'),
                  _item(
                    'Portas disponíveis',
                    '${_result!.availablePorts}/${_result!.totalPorts}',
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _item(String label, String value) => ListTile(
        dense: true,
        title: Text(label),
        trailing: Text(value),
      );
}
