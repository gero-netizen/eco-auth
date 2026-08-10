import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/auth/technician_session.dart';
import '../domain/assignment_notification.dart';

class AssignmentNotificationStore {
  const AssignmentNotificationStore();

  static const _storage = FlutterSecureStorage();

  String get _key =>
      'assignment_notifications_${TechnicianSession.technicianId ?? 'offline'}';

  Future<List<AssignmentNotification>> load() async {
    try {
      final encoded = await _storage.read(key: _key);
      if (encoded == null || encoded.isEmpty) return const [];
      final items = jsonDecode(encoded) as List<dynamic>;
      return items
          .map(
            (item) => AssignmentNotification.fromJson(
              (item as Map).cast<String, dynamic>(),
            ),
          )
          .toList(growable: false);
    } catch (_) {
      return const [];
    }
  }

  Future<void> add(AssignmentNotification notification) async {
    final current = await load();
    final updated = [notification, ...current].take(100).toList();
    await _write(updated);
  }

  Future<List<AssignmentNotification>> markAllRead() async {
    final updated = (await load())
        .map((item) => item.copyWith(read: true))
        .toList(growable: false);
    await _write(updated);
    return updated;
  }

  Future<void> _write(List<AssignmentNotification> notifications) async {
    try {
      await _storage.write(
        key: _key,
        value: jsonEncode(notifications.map((item) => item.toJson()).toList()),
      );
    } catch (_) {
      // O histórico não pode impedir a sincronização das ordens de serviço.
    }
  }
}
