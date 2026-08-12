import 'package:flutter/material.dart';

import '../core/auth/technician_session.dart';
import '../core/config/server_config.dart';
import '../features/auth/presentation/technician_login_page.dart';
import '../features/work_orders/data/work_order_repository.dart';
import '../features/work_orders/presentation/work_order_list_page.dart';

class IspFieldApp extends StatefulWidget {
  const IspFieldApp({super.key, this.workOrderRepository});

  final WorkOrderRepositoryContract? workOrderRepository;

  @override
  State<IspFieldApp> createState() => _IspFieldAppState();
}

class _IspFieldAppState extends State<IspFieldApp> {
  bool _entered = false;
  bool _restoringSession = true;

  @override
  void initState() {
    super.initState();
    if (widget.workOrderRepository != null) {
      _entered = true;
      _restoringSession = false;
    } else {
      _restoreSession();
    }
  }

  Future<void> _restoreSession() async {
    await ServerConfig.restore();
    final restored = await TechnicianSession.restore();
    if (!mounted) return;
    setState(() {
      _entered = restored;
      _restoringSession = false;
    });
  }

  Future<void> _logout() async {
    await TechnicianSession.clear();
    if (mounted) setState(() => _entered = false);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ISP Field',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
          colorSchemeSeed: const Color(0xFF075E54), useMaterial3: true),
      home: _restoringSession
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : widget.workOrderRepository != null || _entered
              ? WorkOrderListPage(
                  repository: widget.workOrderRepository,
                  onLogout: _logout,
                )
              : TechnicianLoginPage(
                  onAuthenticated: (token, technicianId, username) async {
                    await TechnicianSession.save(
                      token, technicianId,
                      username: username,
                    );
                    if (!mounted) return;
                    setState(() => _entered = true);
                  },
                  onOffline: () => setState(() => _entered = true),
                ),
    );
  }
}
