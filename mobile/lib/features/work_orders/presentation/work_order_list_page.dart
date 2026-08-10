import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../../core/config/api_config.dart';
import '../../../core/auth/technician_session.dart';
import '../../../core/database/work_order_database.dart';
import '../../../core/navigation/route_launcher.dart';
import '../../../core/location/location_service.dart';
import '../../monitoring/domain/network_alert.dart';
import '../../notifications/data/assignment_notification_store.dart';
import '../../notifications/domain/assignment_notification.dart';
import '../../notifications/presentation/notification_history_page.dart';
import '../data/work_order_local_data_source.dart';
import '../data/work_order_remote_data_source.dart';
import '../data/work_order_repository.dart';
import '../domain/work_order.dart';
import 'work_order_detail_page.dart';

enum _OrderFilter { all, pending, finished }

class WorkOrderListPage extends StatefulWidget {
  const WorkOrderListPage({super.key, this.repository, this.onLogout});

  final WorkOrderRepositoryContract? repository;
  final Future<void> Function()? onLogout;

  @override
  State<WorkOrderListPage> createState() => _WorkOrderListPageState();
}

class _WorkOrderListPageState extends State<WorkOrderListPage> {
  static const _offlineOrders = [
    WorkOrder(
      id: 'sim-os-1',
      code: 'OS-0001',
      customerName: 'Cliente de Bancada',
      address: 'Ambiente de testes',
      status: WorkOrderStatus.assigned,
      version: 1,
    ),
  ];

  late final WorkOrderRepositoryContract _repository = widget.repository ??
      WorkOrderRepository(
        local: WorkOrderLocalDataSource(WorkOrderDatabase()),
        remote: WorkOrderRemoteDataSource(),
      );
  List<WorkOrder> _orders = _offlineOrders;
  bool _loading = false;
  bool _online = false;
  int _pendingCount = 0;
  int _conflictCount = 0;
  int _pendingEvidenceCount = 0;
  List<NetworkAlert> _networkAlerts = const [];
  final Set<String> _newOrderIds = {};
  Set<String> _knownOrderIds = {};
  final _notificationStore = const AssignmentNotificationStore();
  List<AssignmentNotification> _notifications = const [];
  String? _error;
  _OrderFilter _filter = _OrderFilter.all;

  bool _isFinished(WorkOrder order) =>
      order.status == WorkOrderStatus.completed ||
      order.status == WorkOrderStatus.notCompleted;

  List<WorkOrder> get _visibleOrders {
    final filtered = switch (_filter) {
      _OrderFilter.all => List<WorkOrder>.of(_orders),
      _OrderFilter.pending =>
        _orders.where((order) => !_isFinished(order)).toList(growable: false),
      _OrderFilter.finished =>
        _orders.where(_isFinished).toList(growable: false),
    };
    const priorityRank = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3};
    filtered.sort((left, right) {
      final byPriority = (priorityRank[left.priority] ?? 2)
          .compareTo(priorityRank[right.priority] ?? 2);
      if (byPriority != 0) return byPriority;
      final leftDate = left.scheduledAt;
      final rightDate = right.scheduledAt;
      if (leftDate == null && rightDate == null) {
        return left.code.compareTo(right.code);
      }
      if (leftDate == null) return 1;
      if (rightDate == null) return -1;
      return leftDate.compareTo(rightDate);
    });
    return filtered;
  }

  bool _isOverdue(WorkOrder order) =>
      !_isFinished(order) &&
      order.scheduledAt != null &&
      order.scheduledAt!.isBefore(DateTime.now());

  String _scheduleLabel(WorkOrder order) {
    final value = order.scheduledAt;
    if (value == null) return 'Sem horário definido';
    final local = value.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(local.day)}/${two(local.month)} '
        '${two(local.hour)}:${two(local.minute)}';
  }

  int get _pendingOrders =>
      _orders.where((order) => !_isFinished(order)).length;

  int get _finishedOrders => _orders.where(_isFinished).length;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
    _loadLocalThenSynchronize();
  }

  int get _unreadNotifications =>
      _notifications.where((notification) => !notification.read).length;

  Future<void> _loadNotifications() async {
    final notifications = await _notificationStore.load();
    if (mounted) setState(() => _notifications = notifications);
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => const NotificationHistoryPage(),
      ),
    );
    await _loadNotifications();
  }

  Future<void> _loadLocalThenSynchronize() async {
    try {
      final cached = await _repository.loadCached();
      final pendingCount = await _repository.pendingCount();
      final conflictCount = await _repository.conflictCount();
      final pendingEvidenceCount =
          await _repository.pendingEvidenceUploadCount();
      if (!mounted) return;
      setState(() {
        if (cached.isNotEmpty) _orders = cached;
        _knownOrderIds = cached.map((order) => order.id).toSet();
        _pendingCount = pendingCount;
        _conflictCount = conflictCount;
        _pendingEvidenceCount = pendingEvidenceCount;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }

    if (apiBaseUrl.isNotEmpty) await _synchronize();
  }

  Future<void> _synchronize() async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final orders = await _repository.synchronize();
      final newlyAssigned = orders
          .where((order) => !_knownOrderIds.contains(order.id))
          .map((order) => order.id)
          .toSet();
      for (final order in orders.where(
        (order) => newlyAssigned.contains(order.id),
      )) {
        final now = DateTime.now().toUtc();
        await _notificationStore.add(
          AssignmentNotification(
            id: '${order.id}_${now.microsecondsSinceEpoch}',
            workOrderId: order.id,
            orderCode: order.code,
            customerName: order.customerName,
            receivedAt: now,
          ),
        );
      }
      final notifications = await _notificationStore.load();
      List<NetworkAlert> alerts = const [];
      try {
        alerts = await _repository.networkAlerts();
      } catch (_) {
        alerts = _networkAlerts;
      }
      if (!mounted) return;
      setState(() {
        _orders = orders;
        _newOrderIds.addAll(newlyAssigned);
        _newOrderIds.removeWhere(
          (orderId) => !orders.any((order) => order.id == orderId),
        );
        _knownOrderIds = orders.map((order) => order.id).toSet();
        _notifications = notifications;
        _networkAlerts = alerts;
        _online = true;
      });
      if (newlyAssigned.isNotEmpty) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              content: Text(
                newlyAssigned.length == 1
                    ? 'Nova ordem de serviço recebida.'
                    : '${newlyAssigned.length} novas ordens de serviço recebidas.',
              ),
              action: SnackBarAction(
                label: 'VER',
                onPressed: () => setState(() => _filter = _OrderFilter.all),
              ),
            ),
          );
      }
      await _refreshPendingCount();
    } catch (error) {
      if (!mounted) return;
      if (TechnicianSession.accessToken != null &&
          error is DioException &&
          error.response?.statusCode == 401) {
        await widget.onLogout?.call();
        return;
      }
      setState(() {
        _online = false;
        _error = error.toString();
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refreshPendingCount() async {
    final count = await _repository.pendingCount();
    final conflictCount = await _repository.conflictCount();
    final evidenceCount = await _repository.pendingEvidenceUploadCount();
    if (mounted) {
      setState(() {
        _pendingCount = count;
        _conflictCount = conflictCount;
        _pendingEvidenceCount = evidenceCount;
      });
    }
  }

  Future<void> _reconcileConflicts() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Reconciliar alterações?'),
        content: Text(
          'As $_conflictCount alterações com conflito serão descartadas e os dados oficiais da central serão baixados novamente.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCELAR'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('RECONCILIAR'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _loading = true);
    try {
      final orders = await _repository.reconcileConflicts();
      if (!mounted) return;
      setState(() {
        _orders = orders;
        _conflictCount = 0;
        _online = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Dados reconciliados com a central.')),
      );
      await _refreshPendingCount();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não foi possível reconciliar agora.')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openOrder(WorkOrder order) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => WorkOrderDetailPage(
          order: order,
          onTransition: (transition) =>
              _repository.transition(order.id, transition),
          loadTransitionHistory: () => _repository.transitionHistory(order.id),
          onAddPhoto: (path) => _repository.addPhoto(order.id, path),
          onAddSignature: (bytes) => _repository.addSignature(order.id, bytes),
          onAddEquipment: (serial) =>
              _repository.addEquipmentScan(order.id, serial),
          loadEvidenceCount: () => _repository.evidenceCount(order.id),
          loadPhotoCount: () => _repository.photoCount(order.id),
          loadSignatureCount: () => _repository.signatureCount(order.id),
          loadEquipmentCount: () => _repository.equipmentScanCount(order.id),
          loadInventory: _repository.loadCachedInventory,
          synchronizeInventory: _repository.synchronizeInventory,
          consumeInventory: (itemId, quantity) => _repository.consumeInventory(
            workOrderId: order.id,
            itemId: itemId,
            quantity: quantity,
          ),
          discoverOnus: _repository.discoverOnus,
          provisionOnu: (serial, profile) =>
              _repository.provisionOnu(order.id, serial, profile),
          loadProvisioningHistory: () =>
              _repository.provisioningHistory(order.id),
          loadInventoryMovementCount: () =>
              _repository.inventoryMovementCount(order.id),
          testPppoe: (username) => _repository.testPppoe(order.id, username),
          checkFeasibility: (address) =>
              _repository.checkFeasibility(order.id, address),
        ),
      ),
    );
    if (changed == true) {
      final cached = await _repository.loadCached();
      if (mounted) setState(() => _orders = cached);
    }
    await _refreshPendingCount();
    if (changed == true && apiBaseUrl.isNotEmpty) await _synchronize();
  }

  Future<void> _startRoute() async {
    final activeOrders = _orders
        .where(
          (order) =>
              order.status != WorkOrderStatus.completed &&
              order.status != WorkOrderStatus.notCompleted,
        )
        .toList(growable: false);
    try {
      final location = await LocationService().captureOptional();
      final locatedStops = activeOrders
          .where((order) => order.latitude != null && order.longitude != null)
          .map(
            (order) => RouteStop(
              label: order.address,
              latitude: order.latitude,
              longitude: order.longitude,
            ),
          )
          .toList();
      final missingLocation = activeOrders
          .where((order) => order.latitude == null || order.longitude == null)
          .map((order) => RouteStop(label: order.address))
          .toList(growable: false);
      final ordered = locatedStops.isEmpty
          ? List<RouteStop>.of(missingLocation)
          : location == null
              ? locatedStops
              : orderStopsByProximity(
                  locatedStops,
                  startLatitude: location.latitude,
                  startLongitude: location.longitude,
                );
      if (missingLocation.isNotEmpty && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              locatedStops.isEmpty
                  ? 'Nenhuma OS possui coordenadas. A rota usará os endereços cadastrados.'
                  : '${missingLocation.length} OS sem coordenadas não entrou(aram) na rota otimizada.',
            ),
          ),
        );
      }
      await const RouteLauncher().open(
        ordered.map((stop) => stop.mapValue).toList(growable: false),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error is StateError
                ? error.message
                : 'Não foi possível abrir o aplicativo de mapas.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ordens de serviço'),
        actions: [
          IconButton(
            tooltip: 'Notificações',
            onPressed: _openNotifications,
            icon: Badge(
              isLabelVisible: _unreadNotifications > 0,
              label: Text('$_unreadNotifications'),
              child: const Icon(Icons.notifications_outlined),
            ),
          ),
          if (widget.onLogout != null)
            PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'logout') widget.onLogout!();
              },
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: 'logout',
                  child: ListTile(
                    leading: Icon(Icons.logout),
                    title: Text('Sair'),
                  ),
                ),
              ],
            ),
        ],
      ),
      body: Column(
        children: [
          MaterialBanner(
            content: Text(
              _online
                  ? 'Conectado à central • ${_orders.length} OS • '
                      '$_pendingEvidenceCount envios pendentes'
                  : 'Modo offline • $_pendingCount alterações • '
                      '$_pendingEvidenceCount evidências pendentes',
            ),
            leading: Icon(
              _online ? Icons.cloud_done_outlined : Icons.cloud_off_outlined,
            ),
            actions: [
              TextButton(
                onPressed: _loading ? null : _synchronize,
                child: Text(_loading ? 'AGUARDE' : 'SINCRONIZAR'),
              ),
            ],
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Text(
                'Central indisponível. Exibindo dados salvos neste aparelho.',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          if (_conflictCount > 0)
            Container(
              width: double.infinity,
              color: Theme.of(context).colorScheme.errorContainer,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Icon(
                    Icons.warning_amber_rounded,
                    color: Theme.of(context).colorScheme.onErrorContainer,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '$_conflictCount alteração(ões) precisa(m) de revisão da central.',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onErrorContainer,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: _loading ? null : _reconcileConflicts,
                    child: const Text('REVISAR'),
                  ),
                ],
              ),
            ),
          if (_networkAlerts.isNotEmpty)
            Container(
              width: double.infinity,
              color: Colors.orange.shade100,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.bolt_outlined, color: Colors.deepOrange),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '${_networkAlerts.first.simulated ? 'ALERTA SIMULADO • ' : ''}'
                      '${_networkAlerts.first.title}\n${_networkAlerts.first.area}',
                    ),
                  ),
                  if (_networkAlerts.length > 1)
                    Text('+${_networkAlerts.length - 1}'),
                ],
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    label: 'Total',
                    value: _orders.length,
                    icon: Icons.assignment_outlined,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    label: 'Pendentes',
                    value: _pendingOrders,
                    icon: Icons.pending_actions_outlined,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    label: 'Finalizadas',
                    value: _finishedOrders,
                    icon: Icons.task_alt_outlined,
                  ),
                ),
              ],
            ),
          ),
          if (_newOrderIds.isNotEmpty)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications_active_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      '${_newOrderIds.length} nova(s) OS atribuída(s) a você',
                    ),
                  ),
                ],
              ),
            ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SegmentedButton<_OrderFilter>(
              segments: const [
                ButtonSegment(value: _OrderFilter.all, label: Text('Todas')),
                ButtonSegment(
                  value: _OrderFilter.pending,
                  label: Text('Pendentes'),
                ),
                ButtonSegment(
                  value: _OrderFilter.finished,
                  label: Text('Finalizadas'),
                ),
              ],
              selected: {_filter},
              showSelectedIcon: false,
              onSelectionChanged: (selection) {
                setState(() => _filter = selection.single);
              },
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _synchronize,
              child: _visibleOrders.isEmpty
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: const [
                        SizedBox(height: 80),
                        Icon(Icons.inbox_outlined, size: 48),
                        SizedBox(height: 12),
                        Center(child: Text('Nenhuma OS neste filtro')),
                      ],
                    )
                  : ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(16),
                      itemCount: _visibleOrders.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final order = _visibleOrders[index];
                        final isNew = _newOrderIds.contains(order.id);
                        final overdue = _isOverdue(order);
                        return Card(
                          color: isNew
                              ? Theme.of(context).colorScheme.primaryContainer
                              : overdue || order.priority == 'urgent'
                                  ? Theme.of(context).colorScheme.errorContainer
                                  : null,
                          child: ListTile(
                            leading: CircleAvatar(
                              child: Icon(
                                overdue || order.priority == 'urgent'
                                    ? Icons.priority_high
                                    : Icons.build_outlined,
                              ),
                            ),
                            title: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '${order.code} • ${order.customerName}',
                                  ),
                                ),
                                if (isNew)
                                  const Chip(
                                    label: Text('NOVA'),
                                    visualDensity: VisualDensity.compact,
                                  ),
                              ],
                            ),
                            subtitle: Text(
                              '${order.address}\n${order.status.label} • '
                              '${order.priorityLabel} • ${_scheduleLabel(order)}'
                              '${overdue ? ' • ATRASADA' : ''}',
                            ),
                            isThreeLine: true,
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              setState(() => _newOrderIds.remove(order.id));
                              _openOrder(order);
                            },
                          ),
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _startRoute,
        icon: const Icon(Icons.route_outlined),
        label: const Text('Iniciar rota'),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final int value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
        child: Column(
          children: [
            Icon(icon, color: colors.primary),
            const SizedBox(height: 4),
            Text('$value', style: Theme.of(context).textTheme.titleLarge),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
      ),
    );
  }
}
