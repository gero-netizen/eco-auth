import 'package:flutter/material.dart';

import '../../capture/presentation/qr_scanner_page.dart';
import '../domain/onu_state.dart';

class ProvisioningPage extends StatefulWidget {
  const ProvisioningPage({
    super.key,
    required this.discover,
    required this.provision,
    required this.loadHistory,
  });

  final Future<List<OnuState>> Function() discover;
  final Future<OnuState> Function(String serial, String profile) provision;
  final Future<List<ProvisioningRecord>> Function() loadHistory;

  @override
  State<ProvisioningPage> createState() => _ProvisioningPageState();
}

class _ProvisioningPageState extends State<ProvisioningPage> {
  static const _profiles = [
    'ftth-100',
    'ftth-300',
    'ftth-500',
    'ftth-700',
    'ftth-1000',
  ];

  final _serialController = TextEditingController();
  String _profile = 'ftth-500';
  bool _loading = true;
  String? _error;
  List<OnuState> _discovered = const [];
  OnuState? _result;
  List<ProvisioningRecord> _history = const [];

  @override
  void initState() {
    super.initState();
    _discover();
  }

  @override
  void dispose() {
    _serialController.dispose();
    super.dispose();
  }

  Future<void> _discover() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await widget.discover();
      final history = await widget.loadHistory();
      if (!mounted) return;
      setState(() {
        _discovered = items;
        _history = history;
      });
      if (_serialController.text.isEmpty && items.isNotEmpty) {
        _serialController.text = items.first.serial;
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Simulador de OLT indisponível');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _scan() async {
    final serial = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const QrScannerPage()),
    );
    if (serial != null) _serialController.text = serial.trim().toUpperCase();
  }

  Future<void> _provision() async {
    final serial = _serialController.text.trim();
    if (serial.isEmpty) {
      setState(() => _error = 'Informe ou leia o serial da ONU');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await widget.provision(serial, _profile);
      final history = await widget.loadHistory();
      if (mounted) {
        setState(() {
          _result = result;
          _history = history;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Não foi possível provisionar a ONU');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Provisionar ONU')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            color: Theme.of(context).colorScheme.tertiaryContainer,
            child: const ListTile(
              leading: Icon(Icons.science_outlined),
              title: Text('MODO SIMULADOR'),
              subtitle: Text('Nenhum comando será enviado para uma OLT real.'),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _serialController,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: 'Serial da ONU/ONT',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                onPressed: _loading ? null : _scan,
                icon: const Icon(Icons.qr_code_scanner),
                tooltip: 'Ler QR Code',
              ),
            ),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _profile,
            decoration: const InputDecoration(
              labelText: 'Perfil de serviço',
              border: OutlineInputBorder(),
            ),
            items: _profiles
                .map((profile) => DropdownMenuItem(
                      value: profile,
                      child: Text(profile.toUpperCase()),
                    ))
                .toList(growable: false),
            onChanged: _loading
                ? null
                : (value) => setState(() => _profile = value ?? _profile),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _loading ? null : _provision,
            icon: const Icon(Icons.router_outlined),
            label: const Text('PROVISIONAR NO SIMULADOR'),
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
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.check)),
                title: Text('${_result!.serial} • ${_result!.status}'),
                subtitle: Text(
                  'Perfil: ${_result!.profile ?? '-'}\n'
                  'Sinal: ${_result!.signalDbm?.toStringAsFixed(1) ?? '-'} dBm',
                ),
                isThreeLine: true,
              ),
            ),
          ],
          const SizedBox(height: 24),
          Text(
            'ONU detectada na bancada',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (!_loading && _discovered.isEmpty)
            const Text('Nenhuma ONU detectada pelo simulador.'),
          ..._discovered.map(
            (onu) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.settings_input_antenna),
              title: Text(onu.serial),
              subtitle: Text(
                '${onu.status} • ${onu.signalDbm?.toStringAsFixed(1) ?? '-'} dBm',
              ),
              onTap: () => _serialController.text = onu.serial,
            ),
          ),
          const Divider(height: 32),
          Text(
            'HistÃ³rico desta OS',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (!_loading && _history.isEmpty)
            const Text('Nenhum provisionamento registrado nesta OS.'),
          ..._history.map(
            (record) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.history),
              title: Text('${record.serial} â€¢ ${record.profile ?? '-'}'),
              subtitle: Text(
                '${record.status} â€¢ ${_formatDate(record.createdAt)}',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _formatDate(DateTime value) {
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(value.day)}/${two(value.month)}/${value.year} '
      '${two(value.hour)}:${two(value.minute)}';
}
