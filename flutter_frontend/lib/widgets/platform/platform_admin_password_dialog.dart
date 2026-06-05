import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';

/// Hop thoai doi mat khau cho tai khoan admin quan tri nen tang.
/// Yeu cau mat khau cu, mat khau moi >= 6 ky tu va nhap lai khop.
Future<void> showPlatformAdminChangePasswordDialog(BuildContext context) async {
  final strings = AppStrings.of(context);
  String pick(String vi, String en) => strings.pick(vi, en);

  final oldCtrl = TextEditingController();
  final newCtrl = TextEditingController();
  final confirmCtrl = TextEditingController();
  bool saving = false;
  String? error;

  await showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setLocal) => AlertDialog(
        title: Text(pick('Đổi mật khẩu admin quản trị',
            'Change platform admin password')),
        content: SizedBox(
          width: 460,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: oldCtrl,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: pick('Mật khẩu cũ', 'Old password'),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: newCtrl,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: pick('Mật khẩu mới', 'New password'),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: confirmCtrl,
                obscureText: true,
                decoration: InputDecoration(
                  labelText:
                      pick('Nhập lại mật khẩu mới', 'Confirm new password'),
                  border: const OutlineInputBorder(),
                ),
              ),
              if (error != null) ...[
                const SizedBox(height: 12),
                Text(error!, style: const TextStyle(color: Colors.red)),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: saving ? null : () => Navigator.of(dialogContext).pop(),
            child: Text(pick('Đóng', 'Close')),
          ),
          FilledButton(
            onPressed: saving
                ? null
                : () async {
                    if (newCtrl.text.length < 6) {
                      setLocal(() => error = pick(
                          'Mật khẩu mới phải có ít nhất 6 ký tự.',
                          'New password must be at least 6 characters.'));
                      return;
                    }
                    if (newCtrl.text != confirmCtrl.text) {
                      setLocal(() => error = pick(
                          'Mật khẩu nhập lại không khớp.',
                          'Password confirmation does not match.'));
                      return;
                    }
                    setLocal(() {
                      saving = true;
                      error = null;
                    });
                    try {
                      await ApiClient().dio.post(
                        'platform/admin/change-password/',
                        data: {
                          'old_password': oldCtrl.text,
                          'new_password': newCtrl.text,
                        },
                      );
                      if (!dialogContext.mounted) return;
                      Navigator.of(dialogContext).pop();
                      ScaffoldMessenger.of(dialogContext).showSnackBar(
                        SnackBar(
                          content: Text(pick('Đã đổi mật khẩu thành công.',
                              'Password changed successfully.')),
                        ),
                      );
                    } on DioException catch (dioError) {
                      final payload = dioError.response?.data;
                      setLocal(() {
                        error = payload is Map && payload['detail'] is String
                            ? payload['detail'] as String
                            : pick('Không đổi được mật khẩu.',
                                'Unable to change the password.');
                        saving = false;
                      });
                    } catch (otherError) {
                      setLocal(() {
                        error =
                            '${pick('Không đổi được mật khẩu', 'Unable to change the password')}: $otherError';
                        saving = false;
                      });
                    }
                  },
            child: saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : Text(pick('Lưu', 'Save')),
          ),
        ],
      ),
    ),
  );

  oldCtrl.dispose();
  newCtrl.dispose();
  confirmCtrl.dispose();
}
