import 'package:flutter/material.dart';

Future<void> showBrowserAlert(BuildContext context, String message) async {
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Thông báo'),
      content: Text(message),
      actions: [
        FilledButton(
          onPressed: () => Navigator.pop(dialogContext),
          child: const Text('Đã hiểu'),
        ),
      ],
    ),
  );
}
