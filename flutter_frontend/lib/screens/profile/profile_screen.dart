// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/profile/profile_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/user.dart';
import '../../providers/auth_provider.dart';

// Mục đích: Widget `ProfileScreen` triển khai phần việc `Profile Screen` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

// Mục đích: Widget `_ProfileScreenState` triển khai phần việc `Profile Screen State` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _ctrls = <String, TextEditingController>{};
  final List<_ProfileAliasDraft> _aliases = [];
  final _passwordCtrl = TextEditingController();
  final _passwordConfirmCtrl = TextEditingController();
  bool _editing = false;
  bool _loading = false;
  bool _prefilling = false;
  bool _obscurePassword = true;
  DateTime? _ngaySinh;

  static const _keys = [
    'first_name',
    'last_name',
    'email',
    'chuc_danh',
    'ma_nhan_vien',
    'cccd',
    'so_dien_thoai',
    'dia_chi',
    'so_yeu_ly_lich',
  ];

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    for (final k in _keys) {
      _ctrls[k] = TextEditingController();
    }
    _fillFromUser();
  }

  void _setAliasesFromUser(AppUser user) {
    for (final alias in _aliases) {
      alias.dispose();
    }
    _aliases
      ..clear()
      ..addAll(
        (user.profile?.aliases ?? const <UserAlias>[]).map(
          (item) => _ProfileAliasDraft(
            value: item.alias,
            isPrimaryHint: item.isPrimaryHint,
          ),
        ),
      );
    _ensureAliasPrimaryHint();
  }

  // Mục đích: Phương thức `_fillFromUser` triển khai phần việc `fill From User` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _fillFromUser() {
    // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

    final user = ref.read(currentUserProvider);
    if (user == null) return;
    _setAliasesFromUser(user);
    _ctrls['first_name']!.text = user.firstName;
    _ctrls['last_name']!.text = user.lastName;
    _ctrls['email']!.text = user.email;
    _ctrls['chuc_danh']!.text = user.profile?.chucDanh ?? '';
    _ctrls['ma_nhan_vien']!.text = user.profile?.maNhanVien ?? '';
    _ctrls['cccd']!.text = user.profile?.cccd ?? '';
    _ctrls['so_dien_thoai']!.text = user.profile?.soDienThoai ?? '';
    _ctrls['dia_chi']!.text = user.profile?.diaChi ?? '';
    _ctrls['so_yeu_ly_lich']!.text = user.profile?.soYeuLyLich ?? '';
    // Parse ngay_sinh từ string YYYY-MM-DD
    final ns = user.profile?.ngaySinh ?? '';
    if (ns.isNotEmpty) {
      try {
        final parts = ns.split('-');
        if (parts.length == 3) {
          _ngaySinh = DateTime(
              int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
        }
      } catch (_) {}
    } else {
      _ngaySinh = null;
    }
    _passwordCtrl.clear();
    _passwordConfirmCtrl.clear();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);
    if (user == null) return const Center(child: CircularProgressIndicator());
    final isCompact = MediaQuery.sizeOf(context).width < 760;

    return SingleChildScrollView(
      padding: EdgeInsets.all(isCompact ? 14 : 24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: _editing || user.mustChangePassword
              ? _buildEditView(context, user)
              : _buildViewMode(context, user),
        ),
      ),
    );
  }

  // ── CHẾ ĐỘ XEM ─────────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildViewMode` triển khai phần việc `build View Mode` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildViewMode(BuildContext context, dynamic user) {
    final profile = user.profile;
    final isCompact = MediaQuery.sizeOf(context).width < 760;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header card
        Card(
          elevation: 1,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: EdgeInsets.all(isCompact ? 18 : 28),
            child: Flex(
              direction: isCompact ? Axis.vertical : Axis.horizontal,
              crossAxisAlignment: isCompact
                  ? CrossAxisAlignment.center
                  : CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: isCompact ? 42 : 48,
                  backgroundColor: const Color(0xFF3B82F6),
                  child: Text(
                    (user.fullName.isNotEmpty
                            ? user.fullName[0]
                            : user.username[0])
                        .toUpperCase(),
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: isCompact ? 32 : 36,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                SizedBox(width: isCompact ? 0 : 24, height: isCompact ? 16 : 0),
                (isCompact
                    ? SizedBox(
                        width: double.infinity,
                        child: Column(
                          crossAxisAlignment: isCompact
                              ? CrossAxisAlignment.center
                              : CrossAxisAlignment.start,
                          children: [
                            Flex(
                              direction:
                                  isCompact ? Axis.vertical : Axis.horizontal,
                              crossAxisAlignment: isCompact
                                  ? CrossAxisAlignment.center
                                  : CrossAxisAlignment.start,
                              children: [
                                Text(user.fullName,
                                    textAlign: isCompact
                                        ? TextAlign.center
                                        : TextAlign.start,
                                    style: const TextStyle(
                                        fontSize: 22,
                                        fontWeight: FontWeight.bold)),
                                SizedBox(
                                    width: isCompact ? 0 : 12,
                                    height: isCompact ? 12 : 0),
                                FilledButton.icon(
                                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                  onPressed: () =>
                                      setState(() => _editing = true),
                                  icon: const Icon(Icons.edit, size: 16),
                                  label: Text(AppStrings.of(context)
                                      .ui('Chỉnh sửa hồ sơ')),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            if (profile?.chucDanh?.isNotEmpty == true) ...[
                              Text(profile!.chucDanh!,
                                  textAlign: isCompact
                                      ? TextAlign.center
                                      : TextAlign.start,
                                  style: TextStyle(
                                      fontSize: 15,
                                      color: Colors.blue.shade700,
                                      fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                            ],
                            Wrap(
                              alignment: isCompact
                                  ? WrapAlignment.center
                                  : WrapAlignment.start,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                _RoleBadge(
                                    isStaff: user.isStaff,
                                    isSuperuser: user.isSuperuser),
                                Text('@${user.username}',
                                    style: TextStyle(
                                        color: Colors.grey.shade500,
                                        fontSize: 13)),
                              ],
                            ),
                          ],
                        ),
                      )
                    : Expanded(
                        child: Column(
                          crossAxisAlignment: isCompact
                              ? CrossAxisAlignment.center
                              : CrossAxisAlignment.start,
                          children: [
                            Flex(
                              direction:
                                  isCompact ? Axis.vertical : Axis.horizontal,
                              crossAxisAlignment: isCompact
                                  ? CrossAxisAlignment.center
                                  : CrossAxisAlignment.start,
                              children: [
                                Expanded(
                                  child: Text(user.fullName,
                                      textAlign: isCompact
                                          ? TextAlign.center
                                          : TextAlign.start,
                                      style: const TextStyle(
                                          fontSize: 22,
                                          fontWeight: FontWeight.bold)),
                                ),
                                SizedBox(
                                    width: isCompact ? 0 : 12,
                                    height: isCompact ? 12 : 0),
                                FilledButton.icon(
                                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                  onPressed: () =>
                                      setState(() => _editing = true),
                                  icon: const Icon(Icons.edit, size: 16),
                                  label: Text(AppStrings.of(context)
                                      .ui('Chỉnh sửa hồ sơ')),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            if (profile?.chucDanh?.isNotEmpty == true) ...[
                              Text(profile!.chucDanh!,
                                  textAlign: isCompact
                                      ? TextAlign.center
                                      : TextAlign.start,
                                  style: TextStyle(
                                      fontSize: 15,
                                      color: Colors.blue.shade700,
                                      fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                            ],
                            Wrap(
                              alignment: isCompact
                                  ? WrapAlignment.center
                                  : WrapAlignment.start,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                _RoleBadge(
                                    isStaff: user.isStaff,
                                    isSuperuser: user.isSuperuser),
                                Text('@${user.username}',
                                    style: TextStyle(
                                        color: Colors.grey.shade500,
                                        fontSize: 13)),
                              ],
                            ),
                          ],
                        ),
                      )),
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        LayoutBuilder(builder: (context, cs) {
          final wide = cs.maxWidth >= 760;
          final infoCard = _buildInfoCard(context, user);
          final bioCard = _buildBioCard(context, user);
          if (wide) {
            return IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 3, child: infoCard),
                  const SizedBox(width: 16),
                  Expanded(flex: 4, child: bioCard),
                ],
              ),
            );
          }
          return Column(
              children: [infoCard, const SizedBox(height: 16), bioCard]);
        }),
        const SizedBox(height: 16),
        _buildAliasCard(context, user),
        const SizedBox(height: 16),
        _buildKeysCard(context, user),
      ],
    );
  }

  // Mục đích: Phương thức `_buildInfoCard` triển khai phần việc `build Info Card` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildInfoCard(BuildContext context, dynamic user) {
    final profile = user.profile;
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _cardTitle(context, Icons.person_outline, 'Thông tin cá nhân'),
            const SizedBox(height: 16),
            _infoRow(Icons.email_outlined, 'Email', user.email),
            _infoRow(
                Icons.phone_outlined,
                'Số điện thoại',
                profile?.soDienThoai?.isNotEmpty == true
                    ? profile!.soDienThoai!
                    : '—'),
            _infoRow(Icons.home_outlined, 'Địa chỉ',
                profile?.diaChi?.isNotEmpty == true ? profile!.diaChi! : '—'),
            _infoRow(
                Icons.badge_outlined,
                'Mã nhân viên',
                profile?.maNhanVien?.isNotEmpty == true
                    ? profile!.maNhanVien!
                    : '—'),
            _infoRow(Icons.credit_card_outlined, 'Số CCCD / CMND',
                profile?.cccd?.isNotEmpty == true ? profile!.cccd! : '—'),
            _infoRow(
                Icons.cake_outlined,
                'Ngày sinh',
                profile?.ngaySinh?.isNotEmpty == true
                    ? _formatDate(profile!.ngaySinh!)
                    : '—'),
            _infoRow(
                Icons.work_outline,
                'Chức danh',
                profile?.chucDanh?.isNotEmpty == true
                    ? profile!.chucDanh!
                    : '—'),
          ],
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_buildBioCard` triển khai phần việc `build Bio Card` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildBioCard(BuildContext context, dynamic user) {
    final bio = user.profile?.soYeuLyLich ?? '';
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _cardTitle(context, Icons.article_outlined, 'Sơ yếu lý lịch'),
            const SizedBox(height: 12),
            if (bio.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  children: [
                    Icon(Icons.info_outline,
                        color: Colors.grey.shade400, size: 32),
                    const SizedBox(height: 8),
                    Text(
                        AppStrings.of(context).pick('Chua co so yeu ly lich.',
                            'No profile summary yet.'),
                        style: TextStyle(color: Colors.grey.shade500)),
                    const SizedBox(height: 4),
                    Text(
                        AppStrings.of(context).pick(
                            'Dien so yeu ly lich giup AI tu dong dien thong tin chinh xac hon.',
                            'Completing the profile summary helps AI fill information more accurately.'),
                        style: TextStyle(
                            color: Colors.grey.shade400, fontSize: 12),
                        textAlign: TextAlign.center),
                  ],
                ),
              )
            else
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Text(bio,
                    style: const TextStyle(fontSize: 13, height: 1.6)),
              ),
            if (bio.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(children: [
                Icon(Icons.auto_awesome, size: 13, color: Colors.blue.shade400),
                const SizedBox(width: 4),
                Text(
                    'AI sẽ dùng sơ yếu lý lịch này để tự động điền vào mẫu văn bản.',
                    style:
                        TextStyle(fontSize: 11.5, color: Colors.blue.shade600)),
              ]),
            ],
          ],
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_buildKeysCard` triển khai phần việc `build Keys Card` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildAliasCard(BuildContext context, dynamic user) {
    final aliases =
        user.profile?.aliases as List<UserAlias>? ?? const <UserAlias>[];
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _cardTitle(
                context, Icons.alternate_email_outlined, 'Alias nguoi nhan'),
            const SizedBox(height: 12),
            if (aliases.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Text(
                  AppStrings.of(context).pick(
                    'Chưa có alias nào. Thêm alias để trợ lý AI tìm đúng người nhận nhanh hơn khi bạn ra lệnh bằng giọng nói.',
                    'No aliases yet. Add aliases so the AI assistant can resolve recipients faster when you use voice commands.',
                  ),
                ),
              )
            else
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: aliases
                    .map(
                      (alias) => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: alias.isPrimaryHint
                              ? const Color(0xFFEFF6FF)
                              : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                            color: alias.isPrimaryHint
                                ? const Color(0xFF93C5FD)
                                : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (alias.isPrimaryHint) ...[
                              const Icon(Icons.star_rounded,
                                  size: 16, color: Color(0xFF2563EB)),
                              const SizedBox(width: 6),
                            ],
                            Text(
                              alias.alias,
                              style: TextStyle(
                                fontWeight: alias.isPrimaryHint
                                    ? FontWeight.w700
                                    : FontWeight.w500,
                                color: const Color(0xFF0F172A),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildKeysCard(BuildContext context, dynamic user) {
    final credentials = user.signingCredentials as List<dynamic>? ?? const [];
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _cardTitle(context, Icons.key_outlined, 'Khoa ky so'),
            const SizedBox(height: 12),
            if (credentials.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Text(
                  AppStrings.of(context).pick(
                    'Chưa có credential nào được cấp cho tài khoản này.',
                    'No credential has been issued for this account yet.',
                  ),
                ),
              )
            else
              ...credentials.map((credential) => Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              credential.provider.toString().isEmpty
                                  ? 'internal_pki'
                                  : credential.provider.toString(),
                              style:
                                  const TextStyle(fontWeight: FontWeight.w700),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 10, vertical: 5),
                              decoration: BoxDecoration(
                                color: credential.status == 'active'
                                    ? const Color(0xFFDCFCE7)
                                    : const Color(0xFFFEE2E2),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                credential.status == 'active'
                                    ? 'active'
                                    : credential.status.toString(),
                                style: TextStyle(
                                  color: credential.status == 'active'
                                      ? const Color(0xFF166534)
                                      : const Color(0xFF991B1B),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        _infoRow(
                            Icons.badge_outlined,
                            'Key alias',
                            credential.keyAlias.toString().isEmpty
                                ? '—'
                                : credential.keyAlias.toString()),
                        _infoRow(
                            Icons.fingerprint_outlined,
                            'Serial',
                            credential.serialNumber.toString().isEmpty
                                ? '—'
                                : credential.serialNumber.toString()),
                        _infoRow(
                            Icons.account_tree_outlined,
                            'Issuer',
                            credential.issuerDn.toString().isEmpty
                                ? '—'
                                : credential.issuerDn.toString()),
                        _infoRow(
                            Icons.verified_user_outlined,
                            'Subject',
                            credential.subjectDn.toString().isEmpty
                                ? '—'
                                : credential.subjectDn.toString()),
                        _infoRow(
                            Icons.verified_outlined,
                            'Fingerprint',
                            credential.fingerprintSha256.toString().isEmpty
                                ? '—'
                                : credential.fingerprintSha256.toString()),
                        _infoRow(Icons.schedule_outlined, 'Hieu luc',
                            '${_formatDateTime(credential.validFrom.toString())} -> ${_formatDateTime(credential.validTo.toString())}'),
                      ],
                    ),
                  )),
          ],
        ),
      ),
    );
  }

  // ── CHẾ ĐỘ CHỈNH SỬA ───────────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildEditView` triển khai phần việc `build Edit View` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildEditView(BuildContext context, dynamic user) {
    final strings = AppStrings.of(context);
    final forcePasswordChange = user.mustChangePassword == true;
    final isCompact = MediaQuery.sizeOf(context).width < 760;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Flex(
          direction: isCompact ? Axis.vertical : Axis.horizontal,
          crossAxisAlignment: isCompact
              ? CrossAxisAlignment.stretch
              : CrossAxisAlignment.center,
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back),
              tooltip: strings.ui('Quay lại xem hồ sơ'),
              onPressed: forcePasswordChange
                  ? null
                  : () {
                      _fillFromUser();
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      setState(() => _editing = false);
                    },
            ),
            const SizedBox(width: 8),
            Text(strings.ui('Chỉnh sửa hồ sơ'),
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 20),
        if (forcePasswordChange)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFDBA74)),
            ),
            child: Text(
              strings.pick(
                'Tai khoan nay phai doi mat khau truoc khi tiep tuc su dung he thong.',
                'This account must change its password before continuing.',
              ),
              style: TextStyle(
                  color: Color(0xFF9A3412), fontWeight: FontWeight.w600),
            ),
          ),
        LayoutBuilder(builder: (context, cs) {
          final wide = cs.maxWidth >= 760;
          final mainFields = _buildMainEditFields(context, user);
          final profileFields = _buildProfileEditFields();
          if (wide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: mainFields),
                const SizedBox(width: 16),
                Expanded(child: profileFields),
              ],
            );
          }
          return Column(children: [
            mainFields,
            const SizedBox(height: 16),
            profileFields
          ]);
        }),
        const SizedBox(height: 16),
        _buildAliasEditorCard(),
        const SizedBox(height: 24),
        Flex(
          direction: isCompact ? Axis.vertical : Axis.horizontal,
          crossAxisAlignment: isCompact
              ? CrossAxisAlignment.stretch
              : CrossAxisAlignment.center,
          children: [
            FilledButton.icon(
              onPressed: _loading ? null : _save,
              icon: _loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.save_outlined, size: 18),
              label: Text(strings.ui('Lưu thay đổi')),
            ),
            SizedBox(width: isCompact ? 0 : 12, height: isCompact ? 12 : 0),
            OutlinedButton(
              onPressed: _loading || forcePasswordChange
                  ? null
                  : () {
                      _fillFromUser();
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      setState(() => _editing = false);
                    },
              child: Text(strings.ui('Hủy')),
            ),
          ],
        ),
      ],
    );
  }

  // Mục đích: Phương thức `_buildMainEditFields` triển khai phần việc `build Main Edit Fields` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildMainEditFields(BuildContext context, dynamic user) {
    final strings = AppStrings.of(context);
    final isCompact = MediaQuery.sizeOf(context).width < 700;
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(strings.ui('Thông tin tài khoản'),
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 16),
            Flex(
                direction: isCompact ? Axis.vertical : Axis.horizontal,
                children: [
                  isCompact
                      ? _editField('first_name', 'Tên', Icons.person_outline)
                      : Expanded(
                          child: _editField(
                              'first_name', 'Tên', Icons.person_outline)),
                  SizedBox(
                      width: isCompact ? 0 : 12, height: isCompact ? 12 : 0),
                  isCompact
                      ? _editField('last_name', 'Họ', Icons.person_outline)
                      : Expanded(
                          child: _editField(
                              'last_name', 'Họ', Icons.person_outline)),
                ]),
            const SizedBox(height: 12),
            _editField('email', 'Email', Icons.email_outlined),
            const SizedBox(height: 12),
            TextFormField(
              controller: _passwordCtrl,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: user.mustChangePassword == true
                    ? AppStrings.of(context)
                        .pick('Mật khẩu mới bắt buộc', 'New password required')
                    : AppStrings.of(context)
                        .pick('Mật khẩu mới', 'New password'),
                prefixIcon: const Icon(Icons.lock_outline, size: 18),
                suffixIcon: IconButton(
                  onPressed: () =>
                      setState(() => _obscurePassword = !_obscurePassword),
                  icon: Icon(_obscurePassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined),
                ),
                border: const OutlineInputBorder(),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _passwordConfirmCtrl,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: strings.ui('Xác nhận mật khẩu mới'),
                prefixIcon: Icon(Icons.lock_reset_outlined, size: 18),
                border: const OutlineInputBorder(),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
            const SizedBox(height: 12),
            _editField('so_dien_thoai', 'Số điện thoại', Icons.phone_outlined),
            const SizedBox(height: 12),
            _editField('dia_chi', 'Địa chỉ', Icons.home_outlined),
            const SizedBox(height: 20),

            // Tự động điền từ sơ yếu lý lịch
            OutlinedButton.icon(
              onPressed: _prefilling ? null : _prefillFromBio,
              icon: _prefilling
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.auto_awesome, size: 16),
              label: Text(_prefilling
                  ? strings.pick('Dang trich xuat...', 'Extracting...')
                  : strings.ui('Tự động điền từ sơ yếu lý lịch')),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.blue.shade700,
                side: BorderSide(color: Colors.blue.shade300),
              ),
            ),
            const SizedBox(height: 4),
            Text(
                strings.pick(
                    'AI doc so yeu ly lich va dien vao cac truong ben duoi.',
                    'AI reads your profile summary and fills the fields below.'),
                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500)),

            const SizedBox(height: 16),
            Text(strings.ui('Thông tin nhân sự'),
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 16),
            _editField('chuc_danh', 'Chức danh', Icons.work_outline),
            const SizedBox(height: 12),
            _editField('ma_nhan_vien', 'Mã nhân viên', Icons.badge_outlined),
            const SizedBox(height: 12),
            _editField('cccd', 'Số CCCD / CMND', Icons.credit_card_outlined),
            const SizedBox(height: 12),
            // Date picker cho ngày sinh
            _buildDatePicker(context),
          ],
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_buildDatePicker` triển khai phần việc `build Date Picker` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildDatePicker(BuildContext context) {
    final strings = AppStrings.of(context);
    final label = _ngaySinh != null
        ? '${_ngaySinh!.day.toString().padLeft(2, '0')}/'
            '${_ngaySinh!.month.toString().padLeft(2, '0')}/'
            '${_ngaySinh!.year}'
        : strings.pick('Chua chon', 'Not set');

    return InkWell(
      borderRadius: BorderRadius.circular(4),
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: _ngaySinh ?? DateTime(1990),
          firstDate: DateTime(1940),
          lastDate: DateTime.now(),
          helpText: strings.pick('Chon ngay sinh', 'Select birth date'),
          cancelText: strings.ui('Hủy'),
          confirmText: strings.pick('Chon', 'Select'),
        );
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        if (picked != null) setState(() => _ngaySinh = picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: strings.ui('Ngày sinh'),
          prefixIcon: const Icon(Icons.cake_outlined, size: 18),
          border: const OutlineInputBorder(),
          isDense: true,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          suffixIcon: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (_ngaySinh != null)
                IconButton(
                  icon: const Icon(Icons.clear, size: 16),
                  tooltip: strings.pick('Xoa ngay sinh', 'Clear birth date'),
                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                  onPressed: () => setState(() => _ngaySinh = null),
                ),
              const Icon(Icons.calendar_today_outlined, size: 16),
              const SizedBox(width: 8),
            ],
          ),
        ),
        child: Text(label,
            style: TextStyle(
                fontSize: 14,
                color: _ngaySinh != null
                    ? Theme.of(context).textTheme.bodyMedium?.color
                    : Colors.grey.shade500)),
      ),
    );
  }

  // Mục đích: Phương thức `_buildProfileEditFields` triển khai phần việc `build Profile Edit Fields` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildProfileEditFields() {
    final strings = AppStrings.of(context);
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(strings.ui('Sơ yếu lý lịch'),
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 6),
            Row(children: [
              Icon(Icons.auto_awesome, size: 14, color: Colors.blue.shade400),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  strings.pick(
                    'AI dung thong tin nay de tu dong dien vao mau van ban va ho so. Cang day du cang chinh xac.',
                    'AI uses this information to prefill templates and profile fields. More detail leads to more accurate output.',
                  ),
                  style: TextStyle(fontSize: 12, color: Colors.blue.shade600),
                ),
              ),
            ]),
            const SizedBox(height: 12),
            TextFormField(
              controller: _ctrls['so_yeu_ly_lich'],
              maxLines: 18,
              decoration: InputDecoration(
                labelText: strings.ui('Sơ yếu lý lịch'),
                hintText: strings.pick(
                  'Vi du:\nHo ten: Nguyen Van A\nNgay sinh: 01/01/1990\nSo CCCD: 001234567890\nQue quan: Ha Noi\nChuc vu: Nhan vien kinh doanh\nMa nhan vien: NV001\nEmail: a@company.com\nTrinh do hoc van: Dai hoc\n...',
                  'Example:\nFull name: Nguyen Van A\nBirth date: 01/01/1990\nCitizen ID: 001234567890\nHometown: Hanoi\nTitle: Sales executive\nEmployee code: NV001\nEmail: a@company.com\nEducation: University\n...',
                ),
                border: const OutlineInputBorder(),
                alignLabelWithHint: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
              style: const TextStyle(fontSize: 13, height: 1.5),
            ),
          ],
        ),
      ),
    );
  }

  // ── AUTO-FILL TỪ SƠ YẾU LÝ LỊCH ────────────────────────────────────────────

  // Mục đích: Phương thức `_prefillFromBio` triển khai phần việc `prefill From Bio` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _setPrimaryAlias(int index) {
    for (var i = 0; i < _aliases.length; i += 1) {
      _aliases[i].isPrimaryHint = i == index;
    }
  }

  void _ensureAliasPrimaryHint() {
    if (_aliases.isEmpty) {
      return;
    }
    if (_aliases.any((alias) => alias.isPrimaryHint)) {
      return;
    }
    _aliases.first.isPrimaryHint = true;
  }

  Widget _buildAliasEditorCard() {
    final strings = AppStrings.of(context);
    final isCompact = MediaQuery.sizeOf(context).width < 700;
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              strings.pick('Alias hỗ trợ trợ lý AI', 'AI assistant aliases'),
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
            ),
            const SizedBox(height: 8),
            Text(
              strings.pick(
                'Thêm các tên gọi tắt, biệt danh, tài khoản quen dùng hoặc cách người khác hay nhắc đến bạn. Trợ lý AI sẽ dùng danh sách này để tìm người nhận chính xác hơn.',
                'Add nicknames, shorthand names, familiar usernames, or the ways other people usually refer to you. The AI assistant uses this list to resolve recipients more accurately.',
              ),
              style: TextStyle(height: 1.5, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 14),
            if (_aliases.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Text(
                  strings.pick(
                    'Chưa có alias nào. Bấm "Thêm alias" để bổ sung.',
                    'No aliases yet. Tap "Add alias" to create one.',
                  ),
                ),
              )
            else
              ..._aliases.asMap().entries.map((entry) {
                final index = entry.key;
                final alias = entry.value;
                return Container(
                  margin: EdgeInsets.only(
                      bottom: index == _aliases.length - 1 ? 0 : 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Flex(
                    direction: isCompact ? Axis.vertical : Axis.horizontal,
                    crossAxisAlignment: isCompact
                        ? CrossAxisAlignment.stretch
                        : CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: TextField(
                          controller: alias.controller,
                          decoration: InputDecoration(
                            labelText: strings.pick('Alias', 'Alias'),
                            hintText: strings.pick(
                              'Ví dụ: Lan HCNS, chị Lan, NV001...',
                              'Example: Lan HR, Ms. Lan, NV001...',
                            ),
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      SizedBox(
                          width: isCompact ? 0 : 12,
                          height: isCompact ? 12 : 0),
                      Row(
                        mainAxisSize:
                            isCompact ? MainAxisSize.max : MainAxisSize.min,
                        children: [
                          Radio<int>(
                            value: index,
                            groupValue: _aliases
                                .indexWhere((item) => item.isPrimaryHint),
                            onChanged: (_) =>
                                setState(() => _setPrimaryAlias(index)),
                          ),
                          Flexible(
                            child: Text(
                              strings.pick('Alias ưu tiên', 'Primary alias'),
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                          IconButton(
                            tooltip: strings.pick('Xóa alias', 'Delete alias'),
                            onPressed: () => setState(() {
                              alias.dispose();
                              _aliases.removeAt(index);
                              _ensureAliasPrimaryHint();
                            }),
                            icon: const Icon(Icons.delete_outline),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: () => setState(() {
                _aliases.add(
                  _ProfileAliasDraft(
                    isPrimaryHint: _aliases.isEmpty,
                  ),
                );
                _ensureAliasPrimaryHint();
              }),
              icon: const Icon(Icons.add, size: 18),
              label: Text(strings.pick('Thêm alias', 'Add alias')),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _prefillFromBio() async {
    final bioText = _ctrls['so_yeu_ly_lich']!.text.trim();
    if (bioText.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(AppStrings.of(context).pick(
                'Vui long nhap so yeu ly lich truoc.',
                'Please enter a profile summary first.'))),
      );
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _prefilling = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'auth/me/prefill-from-bio/',
            data: {'biography_text': bioText},
            options: ApiClient.ollamaOptions(),
          );
      final fields = resp.data['fields'] as Map<String, dynamic>? ?? {};
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        if ((fields['first_name'] as String? ?? '').isNotEmpty) {
          _ctrls['first_name']!.text = fields['first_name'];
        }
        if ((fields['last_name'] as String? ?? '').isNotEmpty) {
          _ctrls['last_name']!.text = fields['last_name'];
        }
        if ((fields['email'] as String? ?? '').isNotEmpty) {
          _ctrls['email']!.text = fields['email'];
        }
        if ((fields['chuc_danh'] as String? ?? '').isNotEmpty) {
          _ctrls['chuc_danh']!.text = fields['chuc_danh'];
        }
        if ((fields['ma_nhan_vien'] as String? ?? '').isNotEmpty) {
          _ctrls['ma_nhan_vien']!.text = fields['ma_nhan_vien'];
        }
        if ((fields['cccd'] as String? ?? '').isNotEmpty) {
          _ctrls['cccd']!.text = fields['cccd'];
        }
        if ((fields['so_dien_thoai'] as String? ?? '').isNotEmpty) {
          _ctrls['so_dien_thoai']!.text = fields['so_dien_thoai'];
        }
        if ((fields['dia_chi'] as String? ?? '').isNotEmpty) {
          _ctrls['dia_chi']!.text = fields['dia_chi'];
        }
        // Parse ngay_sinh YYYY-MM-DD
        final ns = fields['ngay_sinh'] as String? ?? '';
        if (ns.isNotEmpty) {
          try {
            final parts = ns.split('-');
            if (parts.length == 3) {
              _ngaySinh = DateTime(int.parse(parts[0]), int.parse(parts[1]),
                  int.parse(parts[2]));
            }
          } catch (_) {}
        }
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppStrings.of(context).pick(
                'Da tu dong dien thong tin tu so yeu ly lich.',
                'Profile details were auto-filled from the summary.')),
            backgroundColor: Colors.green,
          ),
        );
      }
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_prefillErrorMessage(error)),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              AppStrings.of(context).pick(
                'Không trích xuất được thông tin: $e',
                'Unable to extract information: $e',
              ),
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _prefilling = false);
    }
  }

  // ── HELPER WIDGETS ──────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_cardTitle` triển khai phần việc `card Title` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _cardTitle(BuildContext context, IconData icon, String title) {
    final strings = AppStrings.of(context);
    return Row(children: [
      Icon(icon, size: 18, color: Colors.blueGrey.shade600),
      const SizedBox(width: 8),
      Text(strings.ui(title),
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold, color: Colors.blueGrey.shade800)),
    ]);
  }

  // Mục đích: Phương thức `_infoRow` triển khai phần việc `info Row` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _infoRow(IconData icon, String label, String value) {
    final strings = AppStrings.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: Colors.grey.shade400),
          const SizedBox(width: 10),
          SizedBox(
            width: 110,
            child: Text(strings.ui(label),
                style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
          ),
          Expanded(
            child: Text(value,
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }

  // Mục đích: Phương thức `_editField` triển khai phần việc `edit Field` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _editField(String key, String label, IconData icon) {
    final strings = AppStrings.of(context);
    return TextFormField(
      controller: _ctrls[key],
      decoration: InputDecoration(
        labelText: strings.ui(label),
        prefixIcon: Icon(icon, size: 18),
        border: const OutlineInputBorder(),
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      ),
    );
  }

  // Mục đích: Phương thức `_formatDate` triển khai phần việc `format Date` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDate(String s) {
    try {
      final parts = s.split('-');
      if (parts.length == 3) return '${parts[2]}/${parts[1]}/${parts[0]}';
    } catch (_) {}
    return s;
  }

  // ── ACTIONS ─────────────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_formatDateTime` triển khai phần việc `format Date Time` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDateTime(String s) {
    if (s.trim().isEmpty) return '—';
    try {
      final d = DateTime.parse(s).toLocal();
      final day = d.day.toString().padLeft(2, '0');
      final month = d.month.toString().padLeft(2, '0');
      final hour = d.hour.toString().padLeft(2, '0');
      final minute = d.minute.toString().padLeft(2, '0');
      return '$day/$month/${d.year} $hour:$minute';
    } catch (_) {
      return s;
    }
  }

  String _normalizeAliasInput(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
  }

  String _prefillErrorMessage(Object error) {
    final strings = AppStrings.of(context);
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map) {
        if (data['detail'] != null) {
          return '${data['detail']}';
        }
        if (data['error'] != null) {
          return '${data['error']}';
        }
        if (data.isNotEmpty) {
          final firstValue = data.values.first;
          if (firstValue is List && firstValue.isNotEmpty) {
            return '${firstValue.first}';
          }
          return '$firstValue';
        }
      }
      if (error.response?.statusCode != null) {
        return strings.pick(
          'Không trích xuất được thông tin (${error.response!.statusCode}).',
          'Unable to extract information (${error.response!.statusCode}).',
        );
      }
    }
    return strings.pick(
      'Không trích xuất được thông tin từ sơ yếu lý lịch. Vui lòng thử lại.',
      'Unable to extract information from the profile summary. Please try again.',
    );
  }

  String? _validateProfileInputs() {
    final strings = AppStrings.of(context);
    final currentUser = ref.read(currentUserProvider);
    final email = _ctrls['email']!.text.trim();
    final cccd = _ctrls['cccd']!.text.trim();
    final maNhanVien = _ctrls['ma_nhan_vien']!.text.trim();
    final soDienThoai = _ctrls['so_dien_thoai']!.text.trim();
    final diaChi = _ctrls['dia_chi']!.text.trim();
    final password = _passwordCtrl.text;
    final passwordConfirm = _passwordConfirmCtrl.text;

    if (email.isNotEmpty &&
        !RegExp(r'^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$',
                caseSensitive: false)
            .hasMatch(email)) {
      return strings.pick('Email không hợp lệ.', 'Invalid email address.');
    }

    if (cccd.isNotEmpty && !RegExp(r'^\d{9}$|^\d{12}$').hasMatch(cccd)) {
      return strings.pick(
        'CCCD/CMND chỉ được gồm 9 hoặc 12 chữ số.',
        'Citizen ID must contain 9 or 12 digits.',
      );
    }

    if (maNhanVien.isNotEmpty &&
        !RegExp(r'^[A-Za-z0-9._\-/ ]{1,50}$').hasMatch(maNhanVien)) {
      return strings.pick(
        'Mã nhân viên chỉ được gồm chữ, số và . _ - /.',
        'Employee code may contain letters, numbers, and . _ - / only.',
      );
    }

    if (soDienThoai.isNotEmpty) {
      final normalizedPhone = soDienThoai.replaceAll(RegExp(r'[^\d+]'), '');
      if (RegExp(r'[A-Za-z]').hasMatch(soDienThoai) ||
          !RegExp(r'^\+?\d{9,15}$').hasMatch(normalizedPhone)) {
        return strings.pick(
          'Số điện thoại chỉ được gồm 9 đến 15 chữ số.',
          'Phone number must contain 9 to 15 digits.',
        );
      }
    }

    if (diaChi.isNotEmpty) {
      if (diaChi.length > 255) {
        return strings.pick(
          'Địa chỉ không được vượt quá 255 ký tự.',
          'Address must not exceed 255 characters.',
        );
      }
      if (!RegExp(r'[A-Za-z0-9À-ỹà-ỹ]').hasMatch(diaChi)) {
        return strings.pick('Địa chỉ không hợp lệ.', 'Invalid address.');
      }
    }

    if (_ngaySinh != null && _ngaySinh!.isAfter(DateTime.now())) {
      return strings.pick(
        'Ngày sinh không được ở tương lai.',
        'Birth date cannot be in the future.',
      );
    }

    final seenAliases = <String>{};
    var primaryAliasCount = 0;
    for (final alias in _aliases) {
      final value = alias.controller.text.trim();
      if (value.isEmpty) {
        return strings.pick(
            'Alias không được để trống.', 'Alias cannot be empty.');
      }
      final normalized = _normalizeAliasInput(value);
      if (normalized.isEmpty) {
        return strings.pick('Alias không hợp lệ.', 'Invalid alias.');
      }
      if (!seenAliases.add(normalized)) {
        return strings.pick(
          'Danh sách alias đang bị trùng.',
          'The alias list contains duplicates.',
        );
      }
      if (alias.isPrimaryHint) {
        primaryAliasCount += 1;
      }
    }

    if (primaryAliasCount > 1) {
      return strings.pick(
        'Chỉ được chọn một alias ưu tiên.',
        'Only one primary alias can be selected.',
      );
    }

    if (currentUser?.mustChangePassword == true && password.trim().isEmpty) {
      return strings.pick(
          'Bạn phải nhập mật khẩu mới.', 'You must enter a new password.');
    }

    if (password.isNotEmpty || passwordConfirm.isNotEmpty) {
      if (password.length < 8) {
        return strings.pick(
          'Mật khẩu mới phải có ít nhất 8 ký tự.',
          'The new password must be at least 8 characters long.',
        );
      }
      if (password != passwordConfirm) {
        return strings.pick(
          'Xác nhận mật khẩu không khớp.',
          'Password confirmation does not match.',
        );
      }
    }

    return null;
  }

  // Mục đích: Phương thức `_save` triển khai phần việc `save` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _profileErrorMessage(Object error) {
    final strings = AppStrings.of(context);
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map) {
        if (data['detail'] != null) {
          return '${data['detail']}';
        }
        if (data.isNotEmpty) {
          final firstValue = data.values.first;
          if (firstValue is List && firstValue.isNotEmpty) {
            return '${firstValue.first}';
          }
          return '$firstValue';
        }
      }
      if (error.response?.statusCode != null) {
        return strings.pick(
          'Không lưu được hồ sơ (${error.response!.statusCode}).',
          'Unable to save the profile (${error.response!.statusCode}).',
        );
      }
    }
    return strings.pick(
      'Không lưu được hồ sơ. Vui lòng thử lại.',
      'Unable to save the profile. Please try again.',
    );
  }

  Future<void> _save() async {
    _ensureAliasPrimaryHint();
    final validationError = _validateProfileInputs();
    if (validationError != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(validationError), backgroundColor: Colors.red),
      );
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    try {
      final data = <String, dynamic>{};
      _ctrls.forEach((k, c) => data[k] = c.text);
      data['aliases'] = _aliases
          .map(
            (alias) => {
              'alias': alias.controller.text.trim(),
              'is_primary_hint': alias.isPrimaryHint,
            },
          )
          .toList();
      // Thêm ngay_sinh dạng YYYY-MM-DD
      if (_ngaySinh != null) {
        data['ngay_sinh'] = '${_ngaySinh!.year.toString().padLeft(4, '0')}-'
            '${_ngaySinh!.month.toString().padLeft(2, '0')}-'
            '${_ngaySinh!.day.toString().padLeft(2, '0')}';
      } else {
        data['ngay_sinh'] = null;
      }
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final passwordChanged = _passwordCtrl.text.isNotEmpty;
      if (passwordChanged) {
        data['password'] = _passwordCtrl.text;
      }
      await ApiClient().dio.patch('auth/me/', data: data);
      // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

      await ref.read(authProvider.notifier).refreshUser();
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          _loading = false;
          _editing = false;
          _passwordCtrl.clear();
          _passwordConfirmCtrl.clear();
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              passwordChanged
                  ? AppStrings.of(context).pick(
                      'Da luu ho so va cap nhat mat khau thanh cong.',
                      'Saved the profile and updated the password.')
                  : AppStrings.of(context).pick('Da luu ho so thanh cong.',
                      'Saved the profile successfully.'),
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } on DioException catch (error) {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _loading = false);
        final e = _profileErrorMessage(error);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e), backgroundColor: Colors.red),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              AppStrings.of(context).pick(
                'Không lưu được hồ sơ. Vui lòng thử lại.',
                'Unable to save the profile. Please try again.',
              ),
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    for (final alias in _aliases) {
      alias.dispose();
    }
    _passwordCtrl.dispose();
    _passwordConfirmCtrl.dispose();
    super.dispose();
  }
}

// ── BADGE VAI TRÒ ────────────────────────────────────────────────────────────

// Mục đích: Lớp `_RoleBadge` triển khai phần việc `Role Badge` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ProfileAliasDraft {
  final TextEditingController controller;
  bool isPrimaryHint;

  _ProfileAliasDraft({
    String value = '',
    this.isPrimaryHint = false,
  }) : controller = TextEditingController(text: value);

  void dispose() {
    controller.dispose();
  }
}

class _RoleBadge extends StatelessWidget {
  final bool isStaff;
  final bool isSuperuser;
  const _RoleBadge({required this.isStaff, required this.isSuperuser});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/profile/profile_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, color) = isSuperuser
        ? (strings.pick('Quan tri vien', 'Administrator'), Colors.red)
        : isStaff
            ? (strings.pick('Nhan vien quan tri', 'Admin staff'), Colors.orange)
            : (strings.pick('Nguoi dung', 'User'), Colors.blue);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 12, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
