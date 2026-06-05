// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/auth/register_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';

// Mục đích: Widget `RegisterScreen` triển khai phần việc `Register Screen` trong flutter_frontend/lib/screens/auth/register_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

// Mục đích: Widget `_RegisterScreenState` triển khai phần việc `Register Screen State` trong flutter_frontend/lib/screens/auth/register_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
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
