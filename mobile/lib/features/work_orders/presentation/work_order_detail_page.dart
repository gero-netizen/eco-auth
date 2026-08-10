import 'package:flutter/material.dart';
import 'dart:typed_data';

import '../../../core/location/location_service.dart';
import '../domain/work_order.dart';
import '../../capture/presentation/camera_capture_page.dart';
import '../../capture/presentation/qr_scanner_page.dart';
import '../../capture/presentation/signature_capture_page.dart';
import '../../inventory/domain/inventory_item.dart';
import '../../inventory/presentation/inventory_page.dart';
import '../../provisioning/domain/onu_state.dart';
import '../../provisioning/presentation/provisioning_page.dart';
import '../../access_test/domain/pppoe_test_result.dart';
import '../../access_test/presentation/pppoe_test_page.dart';
import '../../feasibility/domain/feasibility_result.dart';
import '../../feasibility/presentation/feasibility_page.dart';

class WorkOrderDetailPage extends StatefulWidget {
  const WorkOrderDetailPage({
    super.key,
    required this.order,
    required this.onTransition,
    required this.loadTransitionHistory,
    required this.onAddPhoto,
    required this.onAddSignature,
    required this.onAddEquipment,
    required this.loadEvidenceCount,
    required this.loadPhotoCount,
    required this.loadSignatureCount,
    required this.loadEquipmentCount,
    required this.loadInventory,
    required this.synchronizeInventory,
    required this.consumeInventory,
    required this.discoverOnus,
    required this.provisionOnu,
    required this.loadProvisioningHistory,
    required this.loadInventoryMovementCount,
    required this.testPppoe,
    required this.checkFeasibility,
  });

  final WorkOrder order;
  final Future<void> Function(WorkOrderTransition transition) onTransition;
  final Future<List<WorkOrderHistoryEntry>> Function() loadTransitionHistory;
  final Future<void> Function(String path) onAddPhoto;
  final Future<void> Function(Uint8List bytes) onAddSignature;
  final Future<void> Function(String serial) onAddEquipment;
  final Future<int> Function() loadEvidenceCount;
  final Future<int> Function() loadPhotoCount;
  final Future<int> Function() loadSignatureCount;
  final Future<int> Function() loadEquipmentCount;
  final Future<List<InventoryItem>> Function() loadInventory;
  final Future<List<InventoryItem>> Function() synchronizeInventory;
  final Future<void> Function(String itemId, double quantity) consumeInventory;
  final Future<List<OnuState>> Function() discoverOnus;
  final Future<OnuState> Function(String serial, String profile) provisionOnu;
  final Future<List<ProvisioningRecord>> Function() loadProvisioningHistory;
  final Future<int> Function() loadInventoryMovementCount;
  final Future<PppoeTestResult> Function(String username) testPppoe;
  final Future<FeasibilityResult> Function(String address) checkFeasibility;

  @override
  State<WorkOrderDetailPage> createState() => _WorkOrderDetailPageState();
}

class _WorkOrderDetailPageState extends State<WorkOrderDetailPage> {
  final _locationService = LocationService();
  bool _saving = false;
  int _evidenceCount = 0;
  int _equipmentCount = 0;
  int _photoCount = 0;
  int _signatureCount = 0;
  int _materialCount = 0;
  int? _provisioningCount;
  List<WorkOrderHistoryEntry> _history = const [];

  @override
  void initState() {
    super.initState();
    _refreshEvidenceCounts();
  }

  Future<void> _refreshEvidenceCounts() async {
    final evidence = await widget.loadEvidenceCount();
    final equipment = await widget.loadEquipmentCount();
    final photos = await widget.loadPhotoCount();
    final signatures = await widget.loadSignatureCount();
    final materials = await widget.loadInventoryMovementCount();
    final history = await widget.loadTransitionHistory();
    int? provisioning;
    try {
      provisioning = (await widget.loadProvisioningHistory()).length;
    } catch (_) {
      provisioning = null;
    }
    if (mounted) {
      setState(() {
        _evidenceCount = evidence;
        _equipmentCount = equipment;
        _photoCount = photos;
        _signatureCount = signatures;
        _materialCount = materials;
        _provisioningCount = provisioning;
        _history = history;
      });
    }
  }

  Future<void> _capturePhoto() async {
    final path = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const CameraCapturePage()),
    );
    if (path == null) return;
    await widget.onAddPhoto(path);
    await _refreshEvidenceCounts();
    _showSaved('Foto salva no aparelho');
  }

  Future<void> _captureSignature() async {
    final bytes = await Navigator.of(context).push<Uint8List>(
      MaterialPageRoute(builder: (_) => const SignatureCapturePage()),
    );
    if (bytes == null) return;
    await widget.onAddSignature(bytes);
    await _refreshEvidenceCounts();
    _showSaved('Assinatura salva no aparelho');
  }

  Future<void> _scanEquipment() async {
    final serial = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const QrScannerPage()),
    );
    if (serial == null) return;
    await widget.onAddEquipment(serial);
    await _refreshEvidenceCounts();
    _showSaved('Equipamento $serial vinculado à OS');
  }

  void _showSaved(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openInventory() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => InventoryPage(
          workOrderId: widget.order.id,
          loadCached: widget.loadInventory,
          synchronize: widget.synchronizeInventory,
          consume: widget.consumeInventory,
        ),
      ),
    );
    await _refreshEvidenceCounts();
  }

  Future<void> _openProvisioning() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => ProvisioningPage(
          discover: widget.discoverOnus,
          provision: widget.provisionOnu,
          loadHistory: widget.loadProvisioningHistory,
        ),
      ),
    );
    await _refreshEvidenceCounts();
  }

  Future<void> _openPppoeTest() {
    return Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => PppoeTestPage(runTest: widget.testPppoe),
      ),
    );
  }

  Future<void> _openFeasibility() {
    return Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => FeasibilityPage(
          address: widget.order.address,
          check: widget.checkFeasibility,
        ),
      ),
    );
  }

  List<String> get _missingChecklistItems => [
        if (_photoCount == 0) 'Foto da instalação',
        if (_signatureCount == 0) 'Assinatura do cliente',
        if (_equipmentCount == 0) 'Equipamento lido por QR Code',
        if (_materialCount == 0) 'Material utilizado',
        if (_provisioningCount == 0) 'Provisionamento da ONU',
      ];

  Future<bool> _confirmIncompleteChecklist() async {
    final missing = _missingChecklistItems;
    if (missing.isEmpty) return true;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Checklist incompleto'),
        content: Text(
          'Ainda faltam:\n\n• ${missing.join('\n• ')}\n\n'
          'Deseja concluir mesmo assim?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('VOLTAR'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('CONCLUIR MESMO ASSIM'),
          ),
        ],
      ),
    );
    return confirmed == true;
  }

  Future<void> _transitionTo(WorkOrderStatus status) async {
    if (status == WorkOrderStatus.completed &&
        !await _confirmIncompleteChecklist()) {
      return;
    }
    if (!mounted) return;
    var typedNote = '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(status.label),
        content: TextField(
          maxLines: 3,
          onChanged: (value) => typedNote = value,
          decoration: const InputDecoration(
            labelText: 'Observação (opcional)',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCELAR'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('CONFIRMAR'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _saving = true);
    final location = await _locationService.captureOptional();
    final note = typedNote.trim();
    try {
      await widget.onTransition(
        WorkOrderTransition(
          toStatus: status,
          note: note.isEmpty ? null : note,
          latitude: location?.latitude,
          longitude: location?.longitude,
        ),
      );
      if (mounted) Navigator.of(context).pop(true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.order.code)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            widget.order.customerName,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.location_on_outlined),
            title: const Text('Endereço'),
            subtitle: Text(widget.order.address),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.info_outline),
            title: const Text('Situação'),
            subtitle: Text(widget.order.status.label),
          ),
          const Divider(height: 32),
          Text('Evidências', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text('$_evidenceCount arquivo(s) • $_equipmentCount equipamento(s)'),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _saving ? null : _capturePhoto,
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('ADICIONAR FOTO'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _saving ? null : _captureSignature,
            icon: const Icon(Icons.draw_outlined),
            label: const Text('COLETAR ASSINATURA'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _saving ? null : _scanEquipment,
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('LER QR CODE'),
          ),
          const SizedBox(height: 24),
          FilledButton.tonalIcon(
            onPressed: _saving ? null : _openInventory,
            icon: const Icon(Icons.inventory_2_outlined),
            label: const Text('MATERIAIS UTILIZADOS'),
          ),
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            onPressed: _saving ? null : _openProvisioning,
            icon: const Icon(Icons.router_outlined),
            label: const Text('PROVISIONAR ONU (SIMULADOR)'),
          ),
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            onPressed: _saving ? null : _openPppoeTest,
            icon: const Icon(Icons.network_check),
            label: const Text('TESTAR ACESSO PPPOE (SIMULADOR)'),
          ),
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            onPressed: _saving ? null : _openFeasibility,
            icon: const Icon(Icons.cell_tower_outlined),
            label: const Text('CONSULTAR VIABILIDADE FTTH'),
          ),
          const SizedBox(height: 24),
          Text(
            'Checklist de encerramento',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          _checkItem('Foto da instalação', _photoCount > 0),
          _checkItem('Assinatura do cliente', _signatureCount > 0),
          _checkItem('Equipamento por QR Code', _equipmentCount > 0),
          _checkItem('Material utilizado', _materialCount > 0),
          _checkItem(
            'ONU provisionada',
            _provisioningCount == null ? null : _provisioningCount! > 0,
          ),
          const SizedBox(height: 12),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            leading: const Icon(Icons.history),
            title: const Text('Histórico da OS neste aparelho'),
            subtitle: Text('${_history.length} movimentação(ões)'),
            children: _history.isEmpty
                ? const [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('Nenhuma movimentação local registrada.'),
                    ),
                  ]
                : _history
                    .map(
                      (entry) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.timeline),
                        title: Text(
                          '${entry.fromStatus.label} → ${entry.toStatus.label}',
                        ),
                        subtitle: Text(
                          '${_formatHistoryDate(entry.occurredAt)}'
                          '${entry.note == null || entry.note!.isEmpty ? '' : '\n${entry.note}'}'
                          '${entry.latitude == null || entry.longitude == null ? '' : '\nGPS: ${entry.latitude!.toStringAsFixed(5)}, ${entry.longitude!.toStringAsFixed(5)}'}',
                        ),
                      ),
                    )
                    .toList(growable: false),
          ),
          const SizedBox(height: 24),
          ..._actionsForStatus(widget.order.status),
          if (_saving) ...[
            const SizedBox(height: 16),
            const LinearProgressIndicator(),
            const SizedBox(height: 8),
            const Text('Salvando e obtendo localização...'),
          ],
        ],
      ),
    );
  }

  Widget _checkItem(String label, bool? complete) {
    final color = complete == null
        ? Theme.of(context).colorScheme.outline
        : complete
            ? Colors.green
            : Theme.of(context).colorScheme.error;
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: Icon(
        complete == null
            ? Icons.help_outline
            : complete
                ? Icons.check_circle
                : Icons.radio_button_unchecked,
        color: color,
      ),
      title: Text(label),
      trailing: complete == null
          ? const Text('Indisponível offline')
          : Text(complete ? 'OK' : 'Pendente'),
    );
  }

  List<Widget> _actionsForStatus(WorkOrderStatus status) {
    if (_saving) return const [];
    return switch (status) {
      WorkOrderStatus.assigned => [
          _actionButton(
            label: 'INICIAR DESLOCAMENTO',
            icon: Icons.directions_car_outlined,
            toStatus: WorkOrderStatus.traveling,
          ),
        ],
      WorkOrderStatus.traveling => [
          _actionButton(
            label: 'CHEGUEI AO LOCAL',
            icon: Icons.location_on_outlined,
            toStatus: WorkOrderStatus.arrived,
          ),
        ],
      WorkOrderStatus.arrived => [
          _actionButton(
            label: 'INICIAR ATENDIMENTO',
            icon: Icons.play_arrow_outlined,
            toStatus: WorkOrderStatus.inProgress,
          ),
        ],
      WorkOrderStatus.inProgress => [
          _actionButton(
            label: 'CONCLUIR OS',
            icon: Icons.check_circle_outline,
            toStatus: WorkOrderStatus.completed,
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => _transitionTo(WorkOrderStatus.notCompleted),
            icon: const Icon(Icons.cancel_outlined),
            label: const Text('NÃO CONCLUÍDA'),
          ),
        ],
      WorkOrderStatus.blocked ||
      WorkOrderStatus.completed ||
      WorkOrderStatus.notCompleted =>
        const [],
    };
  }

  Widget _actionButton({
    required String label,
    required IconData icon,
    required WorkOrderStatus toStatus,
  }) {
    return FilledButton.icon(
      onPressed: () => _transitionTo(toStatus),
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

String _formatHistoryDate(DateTime value) {
  final local = value.toLocal();
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(local.day)}/${two(local.month)}/${local.year} '
      '${two(local.hour)}:${two(local.minute)}';
}
