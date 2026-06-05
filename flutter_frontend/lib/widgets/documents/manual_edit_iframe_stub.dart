import 'package:flutter/material.dart';

Future<void> requestManualEditIFrameSave({required String viewKey}) async {}

class ManualEditIFrame extends StatelessWidget {
  final String viewKey;
  final String src;

  const ManualEditIFrame({
    super.key,
    required this.viewKey,
    required this.src,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFF8FAFC),
      alignment: Alignment.center,
      child: const Text(
        'Manual editor iframe chi ho tro tren Flutter Web.',
        textAlign: TextAlign.center,
      ),
    );
  }
}
