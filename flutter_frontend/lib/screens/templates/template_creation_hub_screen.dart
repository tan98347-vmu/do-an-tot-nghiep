// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';

// Mục đích: Widget `TemplateCreationHubScreen` triển khai phần việc `Template Creation Hub Screen` trong flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateCreationHubScreen extends StatelessWidget {
  const TemplateCreationHubScreen({super.key});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isWide = MediaQuery.sizeOf(context).width >= 900;

    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(isWide ? 28 : 16, 24, isWide ? 28 : 16, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.createTemplateTitle,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            strings.createTemplateSubtitle,
            style: TextStyle(
              color: Colors.blueGrey.shade700,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 18,
            runSpacing: 18,
            children: [
              _CreateOptionCard(
                title: strings.quickCreateTemplate,
                subtitle: strings.quickCreateTemplateDescription,
                icon: Icons.edit_square,
                accent: const Color(0xFF1D4ED8),
                actionLabel: strings.pick('Mở form tạo mẫu', 'Open template form'),
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onTap: () => context.go('/templates/create?mode=quick'),
                width: isWide ? 360 : double.infinity,
              ),
              _CreateOptionCard(
                title: strings.bulkUploadTemplates,
                subtitle: strings.bulkUploadTemplateDescription,
                icon: Icons.folder_open_outlined,
                accent: const Color(0xFF0F766E),
                actionLabel: strings.pick('Đi tới tải lên nhiều mẫu', 'Open bulk upload'),
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onTap: () => context.go('/templates/bulk-upload'),
                width: isWide ? 360 : double.infinity,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_CreateOptionCard` triển khai phần việc `Create Option Card` trong flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _CreateOptionCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final String actionLabel;
  final IconData icon;
  final Color accent;
  final double width;
  final VoidCallback onTap;

  const _CreateOptionCard({
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.icon,
    required this.accent,
    required this.width,
    required this.onTap,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: accent.withOpacity(0.18)),
              boxShadow: [
                BoxShadow(
                  color: accent.withOpacity(0.08),
                  blurRadius: 22,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(icon, color: accent),
                ),
                const SizedBox(height: 18),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.blueGrey.shade700,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onTap,
                  icon: const Icon(Icons.arrow_forward, size: 18),
                  label: Text(actionLabel),
                  style: FilledButton.styleFrom(
                    backgroundColor: accent,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
