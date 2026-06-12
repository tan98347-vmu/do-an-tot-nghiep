import 'package:flutter/material.dart';

class HelpVideoPlayer extends StatelessWidget {
  final String viewKey;
  final String assetPath;
  final String unavailableMessage;

  const HelpVideoPlayer({
    super.key,
    required this.viewKey,
    required this.assetPath,
    required this.unavailableMessage,
  });

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFF111827),
      child: Center(
        child: Text(
          unavailableMessage,
          style: const TextStyle(color: Colors.white70),
        ),
      ),
    );
  }
}
