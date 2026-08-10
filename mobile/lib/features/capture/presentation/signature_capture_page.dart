import 'package:flutter/material.dart';
import 'package:signature/signature.dart';

class SignatureCapturePage extends StatefulWidget {
  const SignatureCapturePage({super.key});

  @override
  State<SignatureCapturePage> createState() => _SignatureCapturePageState();
}

class _SignatureCapturePageState extends State<SignatureCapturePage> {
  final _controller = SignatureController(
    penStrokeWidth: 3,
    penColor: Colors.black,
    exportBackgroundColor: Colors.white,
  );

  Future<void> _save() async {
    if (_controller.isEmpty) return;
    final bytes = await _controller.toPngBytes();
    if (bytes != null && mounted) Navigator.pop(context, bytes);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Assinatura do cliente')),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Assine dentro da área abaixo.'),
          ),
          Expanded(
            child: Signature(
              controller: _controller,
              backgroundColor: Colors.white,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _controller.clear,
                    child: const Text('LIMPAR'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _save,
                    child: const Text('SALVAR'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
