import 'package:flutter/material.dart';

import '../data/assignment_notification_store.dart';
import '../domain/assignment_notification.dart';

class NotificationHistoryPage extends StatefulWidget {
  const NotificationHistoryPage({super.key});

  @override
  State<NotificationHistoryPage> createState() =>
      _NotificationHistoryPageState();
}

class _NotificationHistoryPageState extends State<NotificationHistoryPage> {
  final _store = const AssignmentNotificationStore();
  List<AssignmentNotification>? _notifications;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final notifications = await _store.markAllRead();
    if (mounted) setState(() => _notifications = notifications);
  }

  String _formattedDate(DateTime value) {
    final local = value.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(local.day)}/${two(local.month)}/${local.year} '
        '${two(local.hour)}:${two(local.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notificações')),
      body: _notifications == null
          ? const Center(child: CircularProgressIndicator())
          : _notifications!.isEmpty
              ? const Center(child: Text('Nenhuma notificação recebida'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _notifications!.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final item = _notifications![index];
                    return Card(
                      child: ListTile(
                        leading: const CircleAvatar(
                          child: Icon(Icons.assignment_add),
                        ),
                        title: Text('${item.orderCode} • ${item.customerName}'),
                        subtitle: Text(
                          'OS atribuída a você\n${_formattedDate(item.receivedAt)}',
                        ),
                        isThreeLine: true,
                      ),
                    );
                  },
                ),
    );
  }
}
