// === MÀN HÌNH ĐĂNG KÝ ===
// Đăng ký tự do đã bị TẮT ở bản multi-company: màn hình chỉ hiển thị thông báo và điều hướng về /login.
// (Tài khoản do company-admin/platform-admin tạo, không tự đăng ký.)

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/auth/register_screen.dart.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';

// Widget màn ĐĂNG KÝ (đã tắt ở bản multi-company).

class RegisterScreen extends ConsumerStatefulWidget {
  // Widget màn ĐĂNG KÝ (đã bị tắt ở bản multi-company).
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

// State màn đăng ký: chỉ hiển thị thông báo không khả dụng + nút về /login.

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  // Dựng thông báo 'đăng ký tự do không khả dụng' + nút quay về /login.
  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Card(
            margin: const EdgeInsets.all(24),
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.lock_person_outlined,
                      size: 56, color: Colors.orange.shade700),
                  const SizedBox(height: 16),
                  Text(
                    strings.pick('Đăng ký tự do đã bị tắt',
                        'Self-registration is disabled'),
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    strings.pick(
                      'Tài khoản chính thức chỉ được tạo bởi platform admin, company admin hoặc qua import Excel theo công ty.',
                      'Official accounts can only be created by the platform admin, a company admin, or through company Excel import.',
                    ),
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: Colors.grey.shade700, height: 1.5),
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () => context.go('/login'),
                      icon: const Icon(Icons.arrow_back),
                      label: Text(
                          strings.pick('Quay về đăng nhập', 'Back to sign in')),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    strings.pick(
                      'Nếu bạn cần tài khoản mới, hãy liên hệ admin công ty hoặc quản trị nền tảng.',
                      'If you need a new account, contact your company admin or the platform administrator.',
                    ),
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
