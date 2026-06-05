import 'dart:html' as html;

import 'package:flutter/material.dart';

Future<bool> showPlatformConfirmDialog({
  required BuildContext context,
  required String title,
  required String message,
  String cancelLabel = 'Dong',
  String confirmLabel = 'Xac nhan',
}) async {
  final prompt = StringBuffer(title.trim());
  final body = message.trim();
  if (body.isNotEmpty) {
    prompt.write('\n\n');
    prompt.write(body);
  }
  return html.window.confirm(prompt.toString());
}
