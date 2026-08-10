import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

class CameraCapturePage extends StatefulWidget {
  const CameraCapturePage({super.key});

  @override
  State<CameraCapturePage> createState() => _CameraCapturePageState();
}

class _CameraCapturePageState extends State<CameraCapturePage> {
  CameraController? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) throw StateError('Nenhuma câmera encontrada');
      final controller = CameraController(
        cameras.first,
        ResolutionPreset.high,
        enableAudio: false,
      );
      await controller.initialize();
      if (!mounted) return controller.dispose();
      setState(() => _controller = controller);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null || controller.value.isTakingPicture) return;
    final picture = await controller.takePicture();
    if (mounted) Navigator.pop(context, picture.path);
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    return Scaffold(
      appBar: AppBar(title: const Text('Fotografar evidência')),
      body: _error != null
          ? Center(child: Text('Não foi possível abrir a câmera.\n$_error'))
          : controller == null
              ? const Center(child: CircularProgressIndicator())
              : Center(child: CameraPreview(controller)),
      floatingActionButton: controller == null
          ? null
          : FloatingActionButton.large(
              onPressed: _capture,
              child: const Icon(Icons.camera_alt),
            ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}
