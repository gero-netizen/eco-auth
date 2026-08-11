import 'package:flutter/material.dart';

import '../../../core/config/server_config.dart';
import '../domain/inventory_item.dart';

class InventoryPage extends StatefulWidget {
  const InventoryPage({
    super.key,
    required this.workOrderId,
    required this.loadCached,
    required this.synchronize,
    required this.consume,
  });

  final String workOrderId;
  final Future<List<InventoryItem>> Function() loadCached;
  final Future<List<InventoryItem>> Function() synchronize;
  final Future<void> Function(String itemId, double quantity) consume;

  @override
  State<InventoryPage> createState() => _InventoryPageState();
}

class _InventoryPageState extends State<InventoryPage> {
  List<InventoryItem> _items = const [];
  bool _loading = false;
  bool _online = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final cached = await widget.loadCached();
    if (mounted) setState(() => _items = cached);
    if (ServerConfig.baseUrl.isNotEmpty) await _synchronize();
  }

  Future<void> _synchronize() async {
    if (_loading) return;
    setState(() => _loading = true);
    try {
      final items = await widget.synchronize();
      if (mounted) {
        setState(() {
          _items = items;
          _online = true;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _online = false);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _consume(InventoryItem item) async {
    var typedQuantity = item.unit == 'un' ? '1' : '1.0';
    final quantity = await showDialog<double>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Usar ${item.description}'),
        content: TextFormField(
          initialValue: typedQuantity,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          onChanged: (value) => typedQuantity = value,
          decoration: InputDecoration(
            labelText: 'Quantidade (${item.unit})',
            helperText: 'Disponível: ${_format(item.quantity)} ${item.unit}',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('CANCELAR'),
          ),
          FilledButton(
            onPressed: () {
              final value = double.tryParse(typedQuantity.replaceAll(',', '.'));
              Navigator.pop(dialogContext, value);
            },
            child: const Text('CONFIRMAR'),
          ),
        ],
      ),
    );
    if (quantity == null) return;

    try {
      await widget.consume(item.id, quantity);
      final cached = await widget.loadCached();
      if (mounted) setState(() => _items = cached);
      if (ServerConfig.baseUrl.isNotEmpty) await _synchronize();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(error.toString().replaceFirst('Bad state: ', ''))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Materiais da OS')),
      body: Column(
        children: [
          MaterialBanner(
            content: Text(
                _online ? 'Estoque sincronizado' : 'Estoque local/offline'),
            leading: Icon(
                _online ? Icons.cloud_done_outlined : Icons.cloud_off_outlined),
            actions: [
              TextButton(
                onPressed: _loading ? null : _synchronize,
                child: Text(_loading ? 'AGUARDE' : 'SINCRONIZAR'),
              ),
            ],
          ),
          Expanded(
            child: _items.isEmpty
                ? const Center(child: Text('Nenhum material carregado'))
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final item = _items[index];
                      return Card(
                        child: ListTile(
                          title: Text(item.description),
                          subtitle: Text(
                            '${item.sku}\nSaldo: ${_format(item.quantity)} ${item.unit}'
                            '${item.serialNumber == null ? '' : '\nSérie: ${item.serialNumber}'}',
                          ),
                          isThreeLine: item.serialNumber != null,
                          trailing: FilledButton(
                            onPressed:
                                item.quantity > 0 ? () => _consume(item) : null,
                            child: const Text('USAR'),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

String _format(double value) => value == value.roundToDouble()
    ? value.toInt().toString()
    : value.toStringAsFixed(2);
