import 'dart:html' as html;

import 'package:flutter/material.dart';

Future<void> showBrowserAlert(BuildContext context, String message) async {
  html.window.alert(message);
}
