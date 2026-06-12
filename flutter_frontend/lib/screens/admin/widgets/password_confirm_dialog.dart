// === DIALOG XÁC NHẬN MẬT KHẨU BACKUP ===
// _submit() gọi 'settings/verify-password/' để xác minh mật khẩu trước khi tải/khôi phục backup đã mã hóa.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../../../core/api_client.dart';

/// Dialog xac nhan mat khau backup truoc khi thuc hien hanh dong nhay cam.
/// Tra ve password (String) neu xac thuc OK qua API, hoac null neu huy.
class PasswordConfirmDialog extends StatefulWidget {
  final String title;
  final String description;
  final String actionLabel;
  final Color? actionColor;

  const PasswordConfirmDialog({
    super.key,
    required this.title,
    this.description = '',
    this.actionLabel = 'Xác nhận',
    this.actionColor,
  });

  static Future<String?> show(BuildContext context, {
    required String title,
    String description = '',
    String actionLabel = 'Xác nhận',
    Color? actionColor,
  }) {
    return showDialog<String>(
      context: context,
      builder: (_) => PasswordConfirmDialog(
        title: title,
        description: description,
        actionLabel: actionLabel,
        actionColor: actionColor,
      ),
    );
  }

  @override
  State<PasswordConfirmDialog> createState() => _PasswordConfirmDialogState();
}

class _PasswordConfirmDialogState extends State<PasswordConfirmDialog> {
  final _ctrl = TextEditingController();
  bool _verifying = false;
  String? _error;
  bool _obscure = true;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final raw = _ctrl.text.trim();
    if (raw.isEmpty) {
      setState(() => _error = 'Vui lòng nhập mật khẩu backup.');
      return;
    }
    setState(() {
      _verifying = true;
      _error = null;
    });
    try {
      final resp = await ApiClient().dio.post(
        'admin/backups/settings/verify-password/',
        data: {'password': raw},
      );
      final data = resp.data as Map;
      if (data['valid'] == true) {
        if (mounted) Navigator.of(context).pop(raw);
      } else if (data['has_password'] != true) {
        setState(() => _error = 'Chưa thiết lập mật khẩu backup.');
      } else {
        setState(() => _error = 'Mật khẩu không đúng.');
      }
    } on DioException catch (e) {
      final detail = (e.response?.data is Map) ? e.response?.data['detail'] : null;
      setState(() => _error = detail?.toString() ?? e.message ?? 'Lỗi xác minh');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(children: [
        const Icon(Icons.lock_outline, size: 20),
        const SizedBox(width: 6),
        Expanded(child: Text(widget.title)),
      ]),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.description.isNotEmpty) ...[
              Text(widget.description, style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 10),
            ],
            TextField(
              controller: _ctrl,
              obscureText: _obscure,
              autofocus: true,
              decoration: InputDecoration(
                labelText: 'Mật khẩu backup',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off, size: 18),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
                errorText: _error,
              ),
              onSubmitted: (_) => _submit(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _verifying ? null : () => Navigator.of(context).pop(),
          child: const Text('Huỷ'),
        ),
        FilledButton.icon(
          icon: _verifying
              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.check, size: 16),
          label: Text(widget.actionLabel),
          style: widget.actionColor != null
              ? FilledButton.styleFrom(backgroundColor: widget.actionColor)
              : null,
          onPressed: _verifying ? null : _submit,
        ),
      ],
    );
  }
}
