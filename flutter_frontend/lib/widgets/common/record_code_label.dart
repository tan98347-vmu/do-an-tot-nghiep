import 'package:flutter/material.dart';

class RecordCodeLabel extends StatelessWidget {
  final String code;
  final bool compact;

  const RecordCodeLabel({
    super.key,
    required this.code,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.fingerprint, size: compact ? 12 : 13, color: color),
        const SizedBox(width: 4),
        Text(
          code,
          style: TextStyle(
            color: color,
            fontFamily: 'monospace',
            fontSize: compact ? 10.5 : 11.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
