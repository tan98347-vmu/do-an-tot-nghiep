// === MÀN HÌNH QUẢN TRỊ CÔNG TY (company-admin) ===
// Quản lý người dùng / nhóm / phòng ban / chức danh của công ty qua các tab.
// - Users: _buildUsersTab + _showUserDialog (tạo/sửa), _confirmDeleteUser; import Excel ('admin/import-users/', tải template).
// - Groups: 'admin/groups/' + _showMembersDialog (thêm/bớt thành viên _MembersDialog).
// - Departments: 'admin/departments/'; Positions: 'admin/positions/'. _loadData() nạp toàn bộ.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/admin/admin_screen.dart.
// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';

// Widget màn QUẢN TRỊ (người dùng/nhóm/phòng ban/import) — ConsumerStatefulWidget.

class AdminScreen extends ConsumerStatefulWidget {
  const AdminScreen({super.key});

  @override
  ConsumerState<AdminScreen> createState() => _AdminScreenState();
}

// State màn quản trị: tab người dùng/nhóm/phòng ban + import Excel.

class _AdminScreenState extends ConsumerState<AdminScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  // Excel import
  PlatformFile? _excelFile;
  bool _importing = false;
  List<dynamic> _importResults = [];
  List<dynamic> _importLog = [];
  bool _importDone = false;

  // Users & Groups
  List<dynamic> _users = [];
  List<dynamic> _groups = [];
  List<dynamic> _departments = [];
  List<dynamic> _positions = [];
  bool _loading = true;
  String _userSearch = '';
  String _groupSearch = '';
  String _departmentSearch = '';
  String _positionSearch = '';

  AppStrings get _strings => AppStrings.of(context);
  String _ui(String value) => _strings.ui(value);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  @override
  // Mở màn: nạp dữ liệu quản trị (_loadData) + khởi tạo tab.

  void initState() {
    super.initState();
    // Nghiệp vụ NHÓM: bỏ tab Phòng ban + Chức vụ -> còn Người dùng / Nhóm / Import.
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  @override
  // Rời màn: dọn tab controller + controller form.

  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  // Nạp dữ liệu quản trị (người dùng, nhóm, phòng ban).

  Future<void> _loadData() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    try {
      final futures = await Future.wait([
        ApiClient().dio.get('admin/users/'),
        ApiClient().dio.get('admin/groups/'),
      ]);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _users = futures[0].data as List;
        _groups = futures[1].data as List;
        _loading = false;
      });
    } catch (e) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _loading = false);
    }
  }

  @override
  // Dựng màn: thanh tab + nội dung tab tương ứng.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(strings.accountsAndDepartments,
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          Card(
            elevation: 1,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                  child: Row(children: [
                    const Icon(Icons.dashboard_outlined, size: 18),
                    const SizedBox(width: 8),
                    Text(strings.accountsAndDepartments,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold)),
                  ]),
                ),
                TabBar(
                  controller: _tabController,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  tabs: [
                    Tab(
                      icon: const Icon(Icons.people_outline, size: 16),
                      text: '${_ui('Người dùng')} (${_users.length})',
                    ),
                    Tab(
                      icon: const Icon(Icons.group_outlined, size: 16),
                      text: '${_ui('Nhóm')} (${_groups.length})',
                    ),
                    Tab(
                      icon: const Icon(Icons.upload_file_outlined, size: 16),
                      text: _ui('Import Excel'),
                    ),
                  ],
                ),
                const Divider(height: 1),
                if (_loading)
                  const SizedBox(
                    height: 120,
                    child: Center(child: CircularProgressIndicator()),
                  )
                else
                  SizedBox(
                    height: 480,
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        _buildUsersTab(),
                        _buildGroupsTab(),
                        _buildImportTab(),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── TAB NGƯỜI DÙNG ────────────────────────────────────────────────────────

  // Tab Người dùng: danh sách + nút thêm/sửa/xóa.

  Widget _buildUsersTab() {
    final filtered = _users.where((u) {
      if (_userSearch.isEmpty) return true;
      final q = _userSearch.toLowerCase();
      final name =
          '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'.toLowerCase();
      return (u['username'] as String).toLowerCase().contains(q) ||
          name.contains(q) ||
          (u['email'] as String? ?? '').toLowerCase().contains(q);
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(children: [
            Expanded(
              child: TextField(
                decoration: InputDecoration(
                  hintText: _ui('Tìm kiếm người dùng...'),
                  prefixIcon: const Icon(Icons.search, size: 16),
                  isDense: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                onChanged: (v) => setState(() => _userSearch = v),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: () => _showUserDialog(),
              icon: const Icon(Icons.person_add_outlined, size: 16),
              label: Text(_ui('Thêm')),
              style: FilledButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                textStyle: const TextStyle(fontSize: 13),
              ),
            ),
          ]),
        ),
        const Divider(height: 1),
        Expanded(
          child: filtered.isEmpty
              ? Center(child: Text(_ui('Không có người dùng nào.')))
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 56),
                  itemBuilder: (_, i) => _buildUserTile(filtered[i]),
                ),
        ),
      ],
    );
  }

  // Dựng 1 dòng người dùng (thông tin + nút thao tác).

  Widget _buildUserTile(Map u) {
    final fullName = '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'.trim();
    final display = fullName.isEmpty ? u['username'] as String : fullName;
    final companyRole = (u['company_role'] as String? ?? '').toLowerCase();
    final isCompanyAdmin = companyRole == 'company_admin';
    final isSuperuser = isCompanyAdmin;
    final groups = (u['groups'] as List<dynamic>?) ?? [];
    final isLeader = groups.any((g) => g['role'] == 'leader');
    final groupNames = groups
        .map((g) => '${g['name']}${g['role'] == 'leader' ? ' (TN)' : ''}')
        .join(', ');

    return ListTile(
      dense: true,
      leading: CircleAvatar(
        radius: 18,
        backgroundColor: isCompanyAdmin
            ? Colors.orange.shade100
            : isLeader
                ? Colors.purple.shade100
                : Colors.blue.shade50,
        child: Text(
          (u['username'] as String).substring(0, 1).toUpperCase(),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 13,
            color: isCompanyAdmin
                ? Colors.orange.shade700
                : isLeader
                    ? Colors.purple.shade700
                    : Colors.blue.shade700,
          ),
        ),
      ),
      title: Row(children: [
        Flexible(child: Text(display, style: const TextStyle(fontSize: 13))),
        if (isCompanyAdmin) ...[
          const SizedBox(width: 6),
          _badge('Admin cong ty', Colors.orange)
        ],
        if (!isSuperuser && isLeader) ...[
          const SizedBox(width: 6),
          _badge('Trưởng nhóm', Colors.purple)
        ],
      ]),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(u['email'] ?? u['username'],
              style: const TextStyle(fontSize: 12)),
          if (groupNames.isNotEmpty)
            Text(groupNames,
                style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
        ],
      ),
      isThreeLine: groupNames.isNotEmpty,
      trailing: PopupMenuButton<String>(
        icon: const Icon(Icons.more_vert, size: 18),
        itemBuilder: (_) => [
          PopupMenuItem(
            value: 'edit',
            child: Row(children: [
              const Icon(Icons.edit_outlined, size: 16),
              const SizedBox(width: 8),
              Text(_ui('Chỉnh sửa')),
            ]),
          ),
          PopupMenuItem(
            value: 'delete',
            child: Row(children: [
              const Icon(Icons.delete_outline, size: 16, color: Colors.red),
              const SizedBox(width: 8),
              Text(_ui('Xóa'), style: const TextStyle(color: Colors.red)),
            ]),
          ),
        ],
        onSelected: (action) {
          if (action == 'edit') _showUserDialog(user: u);
          if (action == 'delete') _confirmDeleteUser(u);
        },
      ),
    );
  }

  // Dialog thêm/sửa người dùng.

  Future<void> _showUserDialog({Map? user}) async {
    final isEdit = user != null;
    final usernameCtrl =
        TextEditingController(text: isEdit ? user['username'] : '');
    final emailCtrl =
        TextEditingController(text: isEdit ? (user['email'] ?? '') : '');
    final firstNameCtrl =
        TextEditingController(text: isEdit ? (user['first_name'] ?? '') : '');
    final lastNameCtrl =
        TextEditingController(text: isEdit ? (user['last_name'] ?? '') : '');
    final passwordCtrl = TextEditingController();
    final chucDanhCtrl =
        TextEditingController(text: isEdit ? (user['chuc_danh'] ?? '') : '');
    bool isCompanyAdmin = isEdit
        ? ((user['company_role'] as String? ?? '').toLowerCase() ==
            'company_admin')
        : false;
    bool isStaff = isCompanyAdmin;
    bool isSuperuser = false;
    bool showPassword = false;
    bool saving = false;
    String? error;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(isEdit ? 'Chỉnh sửa người dùng' : 'Thêm người dùng'),
          content: SizedBox(
            width: 440,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                if (error != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(error!,
                        style: TextStyle(
                            color: Colors.red.shade700, fontSize: 13)),
                  ),
                if (!isEdit) ...[
                  _formField('Tên đăng nhập *', usernameCtrl),
                  const SizedBox(height: 10),
                ],
                _formField('Email', emailCtrl,
                    keyboardType: TextInputType.emailAddress),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: _formField('Họ', lastNameCtrl)),
                  const SizedBox(width: 10),
                  Expanded(child: _formField('Tên', firstNameCtrl)),
                ]),
                const SizedBox(height: 10),
                TextField(
                  controller: passwordCtrl,
                  obscureText: !showPassword,
                  decoration: InputDecoration(
                    labelText: isEdit
                        ? 'Mật khẩu mới (để trống nếu không đổi)'
                        : 'Mật khẩu *',
                    isDense: true,
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(
                        showPassword ? Icons.visibility_off : Icons.visibility,
                        size: 18,
                      ),
                      onPressed: () =>
                          setLocal(() => showPassword = !showPassword),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                _formField('Chức danh', chucDanhCtrl),
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Vai tro admin cong ty: bat checkbox ben duoi de cap quyen quan tri noi bo cho tai khoan nay.',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
                CheckboxListTile(
                  value: isCompanyAdmin,
                  dense: true,
                  title: const Text('Nhân viên quản trị (Staff)',
                      style: TextStyle(fontSize: 13)),
                  onChanged: (v) => setLocal(() {
                    isCompanyAdmin = v ?? false;
                    isStaff = isCompanyAdmin;
                  }),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
                Visibility(
                  visible: false,
                  maintainState: true,
                  child: CheckboxListTile(
                    value: isSuperuser,
                    dense: true,
                    title: const Text('Quản trị viên tối cao (Superuser)',
                        style: TextStyle(fontSize: 13)),
                    onChanged: (v) => setLocal(() {
                      isSuperuser = v ?? false;
                      if (isSuperuser) isStaff = true;
                    }),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ]),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(ctx),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (!isEdit && usernameCtrl.text.trim().isEmpty) {
                        setLocal(() => error = 'Cần nhập tên đăng nhập.');
                        return;
                      }
                      if (!isEdit && passwordCtrl.text.trim().isEmpty) {
                        setLocal(() => error = 'Cần nhập mật khẩu.');
                        return;
                      }
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      try {
                        final payload = {
                          'email': emailCtrl.text.trim(),
                          'first_name': firstNameCtrl.text.trim(),
                          'last_name': lastNameCtrl.text.trim(),
                          'is_staff': isStaff,
                          'is_superuser': false,
                          'chuc_danh': chucDanhCtrl.text.trim(),
                          if (!isEdit) 'username': usernameCtrl.text.trim(),
                          if (passwordCtrl.text.isNotEmpty)
                            'password': passwordCtrl.text,
                        };
                        if (isEdit) {
                          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

                          await ApiClient().dio.patch(
                              'admin/users/${user['id']}/',
                              data: payload);
                        } else {
                          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

                          await ApiClient()
                              .dio
                              .post('admin/users/', data: payload);
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        await _loadData();
                      } on DioException catch (e) {
                        setLocal(() {
                          error = e.response?.data['detail'] ??
                              'Lỗi không xác định.';
                          saving = false;
                        });
                      } catch (e) {
                        setLocal(() {
                          error = e.toString();
                          saving = false;
                        });
                      }
                    },
              child: saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : Text(isEdit ? 'Lưu' : 'Tạo'),
            ),
          ],
        ),
      ),
    );
  }

  // Hỏi xác nhận rồi xóa người dùng.

  Future<void> _confirmDeleteUser(Map user) async {
    final fullName =
        '${user['first_name'] ?? ''} ${user['last_name'] ?? ''}'.trim();
    final display = fullName.isEmpty ? user['username'] as String : fullName;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xóa người dùng'),
        content: Text(
            'Bạn có chắc muốn xóa người dùng "$display"?\nHành động này không thể hoàn tác.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Hủy')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.delete('admin/users/${user['id']}/');
      await _loadData();
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e.response?.data['detail'] ?? 'Lỗi xóa người dùng.'),
          backgroundColor: Colors.red,
        ));
      }
    }
  }

  // ── TAB NHÓM ────────────────────────────────────────────────────────────────

  // Tab Nhóm: danh sách nhóm + nút thêm/sửa/thành viên.

  Widget _buildGroupsTab() {
    final filtered = _groups.where((g) {
      if (_groupSearch.isEmpty) return true;
      final q = _groupSearch.toLowerCase();
      return (g['name'] as String? ?? '').toLowerCase().contains(q) ||
          (g['description'] as String? ?? '').toLowerCase().contains(q);
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(children: [
            Expanded(
              child: TextField(
                decoration: InputDecoration(
                  hintText: _ui('Tìm kiếm nhóm...'),
                  prefixIcon: const Icon(Icons.search, size: 16),
                  isDense: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                onChanged: (v) => setState(() => _groupSearch = v),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: () => _showGroupDialog(),
              icon: const Icon(Icons.group_add_outlined, size: 16),
              label: Text(_ui('Thêm')),
              style: FilledButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                textStyle: const TextStyle(fontSize: 13),
              ),
            ),
          ]),
        ),
        const Divider(height: 1),
        Expanded(
          child: filtered.isEmpty
              ? Center(child: Text(_ui('Không có nhóm nào.')))
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 56),
                  itemBuilder: (_, i) => _buildGroupTile(filtered[i]),
                ),
        ),
      ],
    );
  }

  // Dựng 1 dòng nhóm.

  Widget _buildGroupTile(Map g) {
    final count = g['member_count'] ?? 0;
    return ListTile(
      dense: true,
      leading: CircleAvatar(
        radius: 18,
        backgroundColor: Colors.teal.shade50,
        child:
            Icon(Icons.group_outlined, color: Colors.teal.shade600, size: 20),
      ),
      title: Text(g['name'] ?? '', style: const TextStyle(fontSize: 13)),
      subtitle: Text(
        g['description']?.isNotEmpty == true
            ? g['description']
            : _pick('Không có mô tả', 'No description'),
        style: const TextStyle(fontSize: 12),
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _badge('$count TV', Colors.teal),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert, size: 18),
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'members',
                child: Row(children: [
                  const Icon(Icons.people_outlined, size: 16),
                  const SizedBox(width: 8),
                  Text(_pick('Thành viên', 'Members')),
                ]),
              ),
              PopupMenuItem(
                value: 'edit',
                child: Row(children: [
                  const Icon(Icons.edit_outlined, size: 16),
                  const SizedBox(width: 8),
                  Text(_ui('Chỉnh sửa')),
                ]),
              ),
              PopupMenuItem(
                value: 'delete',
                child: Row(children: [
                  const Icon(Icons.delete_outline, size: 16, color: Colors.red),
                  const SizedBox(width: 8),
                  Text(_ui('Xóa'), style: const TextStyle(color: Colors.red)),
                ]),
              ),
            ],
            onSelected: (action) {
              if (action == 'members') _showMembersDialog(g);
              if (action == 'edit') _showGroupDialog(group: g);
              if (action == 'delete') _confirmDeleteGroupV2(g);
            },
          ),
        ],
      ),
    );
  }

  // Dialog thêm/sửa nhóm.

  Future<void> _showGroupDialog({Map? group}) async {
    final isEdit = group != null;
    final nameCtrl = TextEditingController(text: isEdit ? group['name'] : '');
    final descCtrl =
        TextEditingController(text: isEdit ? (group['description'] ?? '') : '');
    bool saving = false;
    String? error;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(isEdit
              ? _pick('Chỉnh sửa nhóm', 'Edit group')
              : _pick('Thêm nhóm', 'Add group')),
          content: SizedBox(
            width: 380,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (error != null)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(error!,
                      style:
                          TextStyle(color: Colors.red.shade700, fontSize: 13)),
                ),
              _formField(_pick('Tên nhóm *', 'Group name *'), nameCtrl),
              const SizedBox(height: 10),
              TextField(
                controller: descCtrl,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: _pick('Mô tả', 'Description'),
                  isDense: true,
                  border: const OutlineInputBorder(),
                ),
              ),
            ]),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(ctx),
              child: Text(_ui('Hủy')),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (nameCtrl.text.trim().isEmpty) {
                        setLocal(() => error = _pick(
                            'Cần nhập tên nhóm.', 'Group name is required.'));
                        return;
                      }
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      try {
                        final payload = {
                          'name': nameCtrl.text.trim(),
                          'description': descCtrl.text.trim(),
                        };
                        if (isEdit) {
                          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

                          await ApiClient().dio.patch(
                              'admin/groups/${group['id']}/',
                              data: payload);
                        } else {
                          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

                          await ApiClient()
                              .dio
                              .post('admin/groups/', data: payload);
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        await _loadData();
                      } on DioException catch (e) {
                        setLocal(() {
                          error = e.response?.data['detail'] ??
                              'Lỗi không xác định.';
                          saving = false;
                        });
                      } catch (e) {
                        setLocal(() {
                          error = e.toString();
                          saving = false;
                        });
                      }
                    },
              child: saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : Text(isEdit ? _ui('Lưu') : _ui('Tạo')),
            ),
          ],
        ),
      ),
    );
  }

  // Dialog quản lý thành viên nhóm.

  Future<void> _showMembersDialog(Map group) async {
    await showDialog(
      context: context,
      builder: (ctx) => _MembersDialog(
        group: group,
        allUsers: _users,
        onChanged: _loadData,
      ),
    );
  }

  // ── TAB IMPORT EXCEL ────────────────────────────────────────────────────────

  // Tab Phòng ban: import từ Excel + danh sách phòng ban.

  Widget _buildDepartmentsTab() {
    final filtered = _departments.where((item) {
      if (_departmentSearch.isEmpty) return true;
      final query = _departmentSearch.toLowerCase();
      return (item['name'] as String? ?? '').toLowerCase().contains(query) ||
          (item['code'] as String? ?? '').toLowerCase().contains(query);
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: _ui('Tim phong ban...'),
                    prefixIcon: const Icon(Icons.search, size: 16),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 8),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8)),
                  ),
                  onChanged: (value) =>
                      setState(() => _departmentSearch = value),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: () => _showDepartmentDialog(),
                icon: const Icon(Icons.add_business_outlined, size: 16),
                label: Text(_ui('Them')),
                style: FilledButton.styleFrom(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  textStyle: const TextStyle(fontSize: 13),
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: filtered.isEmpty
              ? Center(child: Text(_ui('Khong co phong ban nao.')))
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 56),
                  itemBuilder: (_, index) =>
                      _buildDepartmentTile(filtered[index] as Map),
                ),
        ),
      ],
    );
  }

  Widget _buildDepartmentTile(Map department) {
    return ListTile(
      dense: true,
      leading: CircleAvatar(
        radius: 18,
        backgroundColor: Colors.indigo.shade50,
        child: Icon(Icons.account_tree_outlined,
            color: Colors.indigo.shade600, size: 18),
      ),
      title: Text(
        '${department['name'] ?? ''} (${department['code'] ?? ''})',
        style: const TextStyle(fontSize: 13),
      ),
      subtitle: Text(
        '${_pick('Nhân sự', 'Employees')}: ${department['member_count'] ?? 0} | ${department['is_active'] == true ? _pick('Đang dùng', 'Active') : _pick('Vô hiệu', 'Inactive')}',
        style: const TextStyle(fontSize: 12),
      ),
      trailing: PopupMenuButton<String>(
        icon: const Icon(Icons.more_vert, size: 18),
        itemBuilder: (_) => [
          PopupMenuItem(value: 'edit', child: Text(_ui('Chinh sua'))),
          PopupMenuItem(value: 'delete', child: Text(_ui('Xoa'))),
        ],
        onSelected: (action) {
          if (action == 'edit') _showDepartmentDialog(department: department);
          if (action == 'delete') _confirmDeleteDepartment(department);
        },
      ),
    );
  }

  Future<void> _showDepartmentDialog({Map? department}) async {
    final isEdit = department != null;
    final nameCtrl =
        TextEditingController(text: isEdit ? (department['name'] ?? '') : '');
    final codeCtrl =
        TextEditingController(text: isEdit ? (department['code'] ?? '') : '');
    final descCtrl = TextEditingController(
        text: isEdit ? (department['description'] ?? '') : '');
    bool isActive = isEdit ? department['is_active'] == true : true;
    bool saving = false;
    String? error;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(isEdit
              ? _pick('Chỉnh sửa phòng ban', 'Edit department')
              : _pick('Thêm phòng ban', 'Add department')),
          content: SizedBox(
            width: 380,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (error != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(error!,
                        style: TextStyle(
                            color: Colors.red.shade700, fontSize: 13)),
                  ),
                _formField(
                    _pick('Mã phòng ban *', 'Department code *'), codeCtrl),
                const SizedBox(height: 10),
                _formField(
                    _pick('Tên phòng ban *', 'Department name *'), nameCtrl),
                const SizedBox(height: 10),
                TextField(
                  controller: descCtrl,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: _pick('Mô tả', 'Description'),
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: isActive,
                  title: Text(_pick('Đang hoạt động', 'Active')),
                  onChanged: saving
                      ? null
                      : (value) => setLocal(() => isActive = value),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(ctx),
              child: Text(_ui('Huy')),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (codeCtrl.text.trim().isEmpty ||
                          nameCtrl.text.trim().isEmpty) {
                        setLocal(() => error = _pick(
                            'Cần nhập đầy đủ mã và tên phòng ban.',
                            'Department code and name are required.'));
                        return;
                      }
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      try {
                        final payload = {
                          'code': codeCtrl.text.trim(),
                          'name': nameCtrl.text.trim(),
                          'description': descCtrl.text.trim(),
                          'is_active': isActive,
                        };
                        if (isEdit) {
                          await ApiClient().dio.patch(
                              'admin/departments/${department['id']}/',
                              data: payload);
                        } else {
                          await ApiClient()
                              .dio
                              .post('admin/departments/', data: payload);
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        await _loadData();
                      } on DioException catch (e) {
                        final payload = e.response?.data;
                        setLocal(() {
                          error = payload is Map && payload['detail'] is String
                              ? payload['detail'] as String
                              : 'Khong luu duoc phong ban.';
                          saving = false;
                        });
                      } catch (e) {
                        setLocal(() {
                          error = e.toString();
                          saving = false;
                        });
                      }
                    },
              child: Text(isEdit ? 'Luu' : 'Tao'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmDeleteDepartment(Map department) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Xóa phòng ban', 'Delete department')),
        content: Text(_pick(
            'Bạn có chắc muốn xóa phòng ban "${department['name']}"?',
            'Are you sure you want to delete department "${department['name']}"?')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_ui('Huy'))),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: Text(_ui('Xoa')),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ApiClient().dio.delete('admin/departments/${department['id']}/');
      await _loadData();
    } on DioException catch (e) {
      if (mounted) {
        final payload = e.response?.data;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              payload is Map && payload['detail'] is String
                  ? payload['detail'] as String
                  : _pick('Lỗi xóa phòng ban.', 'Failed to delete department.'),
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Widget _buildPositionsTab() {
    final filtered = _positions.where((item) {
      if (_positionSearch.isEmpty) return true;
      final query = _positionSearch.toLowerCase();
      return (item['name'] as String? ?? '').toLowerCase().contains(query) ||
          (item['code'] as String? ?? '').toLowerCase().contains(query);
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: _ui('Tim chuc vu...'),
                    prefixIcon: const Icon(Icons.search, size: 16),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 8),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8)),
                  ),
                  onChanged: (value) => setState(() => _positionSearch = value),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: () => _showPositionDialog(),
                icon: const Icon(Icons.work_outline, size: 16),
                label: Text(_ui('Them')),
                style: FilledButton.styleFrom(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  textStyle: const TextStyle(fontSize: 13),
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: filtered.isEmpty
              ? Center(child: Text(_ui('Khong co chuc vu nao.')))
              : ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 56),
                  itemBuilder: (_, index) =>
                      _buildPositionTile(filtered[index] as Map),
                ),
        ),
      ],
    );
  }

  Widget _buildPositionTile(Map position) {
    final code = (position['code'] as String? ?? '').trim();
    return ListTile(
      dense: true,
      leading: CircleAvatar(
        radius: 18,
        backgroundColor: Colors.orange.shade50,
        child:
            Icon(Icons.work_outline, color: Colors.orange.shade700, size: 18),
      ),
      title: Text(
        code.isNotEmpty
            ? '${position['name'] ?? ''} ($code)'
            : '${position['name'] ?? ''}',
        style: const TextStyle(fontSize: 13),
      ),
      subtitle: Text(
        '${_pick('Nhân sự', 'Employees')}: ${position['user_count'] ?? 0} | ${position['is_active'] == true ? _pick('Đang dùng', 'Active') : _pick('Vô hiệu', 'Inactive')}',
        style: const TextStyle(fontSize: 12),
      ),
      trailing: PopupMenuButton<String>(
        icon: const Icon(Icons.more_vert, size: 18),
        itemBuilder: (_) => [
          PopupMenuItem(value: 'edit', child: Text(_ui('Chinh sua'))),
          PopupMenuItem(value: 'delete', child: Text(_ui('Xoa'))),
        ],
        onSelected: (action) {
          if (action == 'edit') _showPositionDialog(position: position);
          if (action == 'delete') _confirmDeletePosition(position);
        },
      ),
    );
  }

  Future<void> _showPositionDialog({Map? position}) async {
    final isEdit = position != null;
    final nameCtrl =
        TextEditingController(text: isEdit ? (position['name'] ?? '') : '');
    final codeCtrl =
        TextEditingController(text: isEdit ? (position['code'] ?? '') : '');
    final descCtrl = TextEditingController(
        text: isEdit ? (position['description'] ?? '') : '');
    bool isActive = isEdit ? position['is_active'] == true : true;
    bool saving = false;
    String? error;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: Text(isEdit
              ? _pick('Chỉnh sửa chức vụ', 'Edit position')
              : _pick('Thêm chức vụ', 'Add position')),
          content: SizedBox(
            width: 380,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (error != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(error!,
                        style: TextStyle(
                            color: Colors.red.shade700, fontSize: 13)),
                  ),
                _formField(_pick('Mã chức vụ', 'Position code'), codeCtrl),
                const SizedBox(height: 10),
                _formField(_pick('Tên chức vụ *', 'Position name *'), nameCtrl),
                const SizedBox(height: 10),
                TextField(
                  controller: descCtrl,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: _pick('Mô tả', 'Description'),
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: isActive,
                  title: Text(_pick('Đang hoạt động', 'Active')),
                  onChanged: saving
                      ? null
                      : (value) => setLocal(() => isActive = value),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(ctx),
              child: Text(_ui('Huy')),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      if (nameCtrl.text.trim().isEmpty) {
                        setLocal(() => error = _pick('Cần nhập tên chức vụ.',
                            'Position name is required.'));
                        return;
                      }
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      try {
                        final payload = {
                          'code': codeCtrl.text.trim(),
                          'name': nameCtrl.text.trim(),
                          'description': descCtrl.text.trim(),
                          'is_active': isActive,
                        };
                        if (isEdit) {
                          await ApiClient().dio.patch(
                              'admin/positions/${position['id']}/',
                              data: payload);
                        } else {
                          await ApiClient()
                              .dio
                              .post('admin/positions/', data: payload);
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        await _loadData();
                      } on DioException catch (e) {
                        final payload = e.response?.data;
                        setLocal(() {
                          error = payload is Map && payload['detail'] is String
                              ? payload['detail'] as String
                              : 'Khong luu duoc chuc vu.';
                          saving = false;
                        });
                      } catch (e) {
                        setLocal(() {
                          error = e.toString();
                          saving = false;
                        });
                      }
                    },
              child: Text(isEdit ? 'Luu' : 'Tao'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmDeletePosition(Map position) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Xóa chức vụ', 'Delete position')),
        content: Text(_pick(
            'Bạn có chắc muốn xóa chức vụ "${position['name']}"?',
            'Are you sure you want to delete position "${position['name']}"?')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_ui('Huy'))),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: Text(_ui('Xoa')),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ApiClient().dio.delete('admin/positions/${position['id']}/');
      await _loadData();
    } on DioException catch (e) {
      if (mounted) {
        final payload = e.response?.data;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              payload is Map && payload['detail'] is String
                  ? payload['detail'] as String
                  : _pick('Lỗi xóa chức vụ.', 'Failed to delete position.'),
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Widget _buildImportTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Icon(Icons.info_outline,
                      size: 16, color: Colors.blue.shade700),
                  const SizedBox(width: 6),
                  Text('Định dạng file Excel',
                      style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.blue.shade700)),
                ]),
                const SizedBox(height: 8),
                Text(
                  '• Mau moi: Sheet1-NhanSu va Sheet2-DanhMuc\n'
                  '• Sheet1-NhanSu: Ten, Tuoi, HoSo, PhongBan, ChucVu, Email, SoDienThoai, DiaChi, MaNhanVien, CCCD\n'
                  '• Sheet2-DanhMuc: Loai, Ma, Ten, MoTa (Loai = department/position)\n'
                  '• He thong van tuong thich file cu Nhom/Nhan_Su de migrate dan.',
                  style: TextStyle(
                      fontSize: 12.5, color: Colors.blue.shade800, height: 1.6),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: _downloadTemplate,
                  icon: const Icon(Icons.download, size: 15),
                  label: const Text('Tải file Excel mẫu'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.blue.shade700,
                    side: BorderSide(color: Colors.blue.shade400),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    textStyle: const TextStyle(fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _importing ? null : _pickExcel,
                icon: const Icon(Icons.attach_file, size: 16),
                label: Text(_excelFile == null
                    ? 'Chọn file Excel (.xlsx)'
                    : _excelFile!.name),
              ),
            ),
            if (_excelFile != null) ...[
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.close, size: 18),
                tooltip: 'Bỏ chọn',
                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                onPressed: () => setState(() {
                  _excelFile = null;
                  _importDone = false;
                  _importResults.clear();
                  _importLog.clear();
                }),
              ),
            ],
          ]),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: (_excelFile == null || _importing) ? null : _doImport,
              icon: _importing
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.cloud_upload_outlined, size: 18),
              label: Text(_importing ? 'Đang import...' : 'Bắt đầu import'),
            ),
          ),
          if (_importDone) ...[
            const SizedBox(height: 16),
            Row(children: [
              Icon(Icons.check_circle_outline,
                  color: Colors.green.shade600, size: 18),
              const SizedBox(width: 6),
              Text(
                'Da xu ly ${_importResults.length} nhan su | tao moi ${_countImportStatuses('created', 'OK')} | cap nhat ${_countImportStatuses('updated')}',
                style: TextStyle(
                    fontWeight: FontWeight.bold, color: Colors.green.shade700),
              ),
            ]),
            const SizedBox(height: 10),
            _buildImportResultTable(),
            if (_importLog.isNotEmpty) ...[
              const SizedBox(height: 12),
              ExpansionTile(
                title: Text('Nhật ký xử lý (${_importLog.length} mục)',
                    style: const TextStyle(fontSize: 13)),
                children: _importLog.map<Widget>((entry) {
                  final s = entry['status'] as String? ?? '';
                  final color = s == 'ok'
                      ? Colors.green.shade700
                      : s == 'warn'
                          ? Colors.orange.shade700
                          : s == 'error'
                              ? Colors.red.shade700
                              : Colors.grey.shade600;
                  return Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          s == 'ok'
                              ? Icons.check_circle_outline
                              : s == 'warn'
                                  ? Icons.warning_amber_outlined
                                  : s == 'error'
                                      ? Icons.error_outline
                                      : Icons.skip_next_outlined,
                          size: 14,
                          color: color,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(entry['msg'] ?? '',
                              style: TextStyle(fontSize: 12, color: color)),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ],
          ],
        ],
      ),
    );
  }

  // Bảng kết quả import phòng ban từ Excel.

  Widget _buildImportResultTable() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columnSpacing: 16,
        headingRowHeight: 36,
        dataRowMinHeight: 32,
        dataRowMaxHeight: 48,
        columns: const [
          DataColumn(label: Text('Username', style: TextStyle(fontSize: 12))),
          DataColumn(label: Text('Email', style: TextStyle(fontSize: 12))),
          DataColumn(label: Text('Trạng thái', style: TextStyle(fontSize: 12))),
        ],
        rows: _importResults.map<DataRow>((r) {
          final statusText = (r['status'] ?? '').toString();
          final ok = statusText == 'OK' ||
              statusText == 'created' ||
              statusText == 'updated';
          return DataRow(cells: [
            DataCell(Text(r['username'] ?? '',
                style: const TextStyle(fontSize: 12))),
            DataCell(
                Text(r['email'] ?? '', style: const TextStyle(fontSize: 12))),
            DataCell(
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: ok ? Colors.green.shade50 : Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                      color: ok ? Colors.green.shade300 : Colors.red.shade300),
                ),
                child: Text(statusText,
                    style: TextStyle(
                        fontSize: 11,
                        color: ok ? Colors.green.shade700 : Colors.red.shade700,
                        fontWeight: FontWeight.w600)),
              ),
            ),
          ]);
        }).toList(),
      ),
    );
  }

  int _countImportStatuses(String primary, [String? secondary]) {
    return _importResults.where((item) {
      final value = (item['status'] ?? '').toString();
      return value == primary || value == secondary;
    }).length;
  }

  // Chọn file Excel danh sách phòng ban/nhân sự.

  Future<void> _pickExcel() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xlsx', 'xls'],
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _excelFile = result.files.first;
        _importDone = false;
        _importResults.clear();
        _importLog.clear();
      });
    }
  }

  // Thực thi import dữ liệu từ Excel đã chọn.

  Future<void> _doImport() async {
    if (_excelFile?.bytes == null) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _importing = true);
    try {
      final formData = FormData.fromMap({
        'excel_file': MultipartFile.fromBytes(
          _excelFile!.bytes!,
          filename: _excelFile!.name,
        ),
      });
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'admin/import-users/',
            data: formData,
            options: Options(contentType: 'multipart/form-data'),
          );
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _importResults = List.from(resp.data['results'] ?? []);
        _importLog = List.from(resp.data['log'] ?? []);
        if (_importLog.isEmpty) {
          _importLog = [
            {
              'status': 'ok',
              'msg': 'Nhóm tạo mới: ${resp.data['created_groups'] ?? 0}',
            },
            {
              'status': 'ok',
              'msg': 'Nhân sự tạo mới: ${resp.data['created_users'] ?? 0}',
            },
            {
              'status': 'ok',
              'msg': 'Nhân sự cập nhật: ${resp.data['updated_users'] ?? 0}',
            },
          ];
        }
        _importDone = true;
      });
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final usersResp = await ApiClient().dio.get('admin/users/');
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _users = usersResp.data as List);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Lỗi import: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _importing = false);
    }
  }

  // Tải file Excel mẫu để nhập liệu.

  Future<void> _downloadTemplate() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            'admin/import-users/template/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob(
        [bytes],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      );
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', 'import_users_template.xlsx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Lỗi tải mẫu: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  // Dựng 1 ô nhập trong form (nhãn + controller).

  Widget _formField(String label, TextEditingController ctrl,
      {TextInputType? keyboardType}) {
    return TextField(
      controller: ctrl,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: _ui(label),
        isDense: true,
        border: const OutlineInputBorder(),
      ),
    );
  }

  // Dựng badge nhãn nhỏ có màu.

  Widget _badge(String label, MaterialColor color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.shade200),
      ),
      child: Text(_ui(label),
          style: TextStyle(
              fontSize: 11,
              color: color.shade700,
              fontWeight: FontWeight.w600)),
    );
  }

  // Hỏi xác nhận rồi xóa nhóm.

  Future<void> _confirmDeleteGroupV2(Map group) async {
    final otherGroups =
        _groups.where((item) => item['id'] != group['id']).cast<Map>().toList();
    final usageSummary = [
      if ((group['member_count'] ?? 0) > 0)
        '${group['member_count']} thanh vien',
      if ((group['document_count'] ?? 0) > 0)
        '${group['document_count']} van ban',
      if ((group['template_count'] ?? 0) > 0) '${group['template_count']} mau',
      if ((group['pending_template_assignment_count'] ?? 0) > 0)
        '${group['pending_template_assignment_count']} phan quyen cho',
    ];
    final needsTransfer = usageSummary.isNotEmpty;
    int? destinationGroupId = needsTransfer && otherGroups.isNotEmpty
        ? otherGroups.first['id'] as int?
        : null;

    final payload = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: const Text('Xóa nhóm'),
          content: SizedBox(
            width: 420,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Bạn có chắc muốn xóa nhóm "${group['name']}"?'),
                if (usageSummary.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Nhóm này đang có: ${usageSummary.join(', ')}.',
                    style:
                        TextStyle(color: Colors.orange.shade800, height: 1.45),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Cần chọn nhóm đích để chuyển toàn bộ dữ liệu liên quan trước khi xóa.',
                    style: TextStyle(
                        color: Colors.grey.shade700,
                        fontSize: 12.5,
                        height: 1.45),
                  ),
                ] else ...[
                  const SizedBox(height: 12),
                  Text(
                    'Nhóm không còn ràng buộc dữ liệu. Xác nhận để xóa vĩnh viễn.',
                    style: TextStyle(
                        color: Colors.grey.shade700,
                        fontSize: 12.5,
                        height: 1.45),
                  ),
                ],
                if (needsTransfer && otherGroups.isEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(
                      'Không có nhóm đích để chuyển dữ liệu. Hãy tạo nhóm khác trước khi xóa nhóm này.',
                      style:
                          TextStyle(color: Colors.red.shade700, fontSize: 12.5),
                    ),
                  ),
                ] else if (needsTransfer) ...[
                  const SizedBox(height: 12),
                  DropdownButtonFormField<int>(
                    initialValue: destinationGroupId,
                    decoration: const InputDecoration(
                      labelText: 'Nhóm đích',
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                    items: otherGroups
                        .map((item) => DropdownMenuItem<int>(
                              value: item['id'] as int,
                              child: Text((item['name'] ?? '').toString()),
                            ))
                        .toList(),
                    onChanged: (value) =>
                        setLocal(() => destinationGroupId = value),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, null),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: needsTransfer && destinationGroupId == null
                  ? null
                  : () => Navigator.pop(ctx, {
                        'confirm': true,
                        'destination_group_id': destinationGroupId,
                      }),
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              child: const Text('Xóa'),
            ),
          ],
        ),
      ),
    );

    if (payload?['confirm'] != true) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.delete(
        'admin/groups/${group['id']}/',
        queryParameters: {
          'confirm': 1,
          if (payload?['destination_group_id'] != null)
            'destination_group_id': payload?['destination_group_id'],
        },
      );
      await _loadData();
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e.response?.data['detail'] ?? 'Loi xoa nhom.'),
          backgroundColor: Colors.red,
        ));
      }
    }
  }
}

// ── Dialog quản lý thành viên nhóm ────────────────────────────────────────────

// Dialog quản lý thành viên nhóm (StatefulWidget).

class _MembersDialog extends StatefulWidget {
  final Map group;
  final List<dynamic> allUsers;
  final VoidCallback onChanged;

  const _MembersDialog({
    required this.group,
    required this.allUsers,
    required this.onChanged,
  });

  @override
  State<_MembersDialog> createState() => _MembersDialogState();
}

// State dialog thành viên: nạp/thêm/xóa thành viên, đổi vai trò.

class _MembersDialogState extends State<_MembersDialog> {
  List<dynamic> _members = [];
  bool _loading = true;
  int? _addUserId;
  String _addRole = 'member';
  late final TextEditingController _memberSearchCtrl;
  late final FocusNode _memberSearchFocus;

  AppStrings get _strings => AppStrings.of(context);
  String _ui(String value) => _strings.ui(value);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  @override
  // Mở dialog: nạp danh sách thành viên nhóm.

  void initState() {
    super.initState();
    _memberSearchCtrl = TextEditingController();
    _memberSearchFocus = FocusNode();
    _loadMembers();
  }

  @override
  // Đóng dialog: dọn controller.

  void dispose() {
    _memberSearchCtrl.dispose();
    _memberSearchFocus.dispose();
    super.dispose();
  }

  // Nạp danh sách thành viên của nhóm.

  Future<void> _loadMembers() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    try {
      final resp =
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          await ApiClient()
              .dio
              .get('admin/groups/${widget.group['id']}/members/');
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _members = resp.data as List;
        _loading = false;
      });
    } catch (_) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _loading = false);
    }
  }

  List<dynamic> get _nonMembers {
    final memberIds = _members.map((m) => m['user_id'] as int).toSet();
    return widget.allUsers
        .where((u) => !memberIds.contains(u['id'] as int))
        .toList();
  }

  // Chuỗi hiển thị tên người dùng (tên + email).

  String _userDisplay(Map u) {
    final name = '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'.trim();
    return name.isEmpty ? (u['username'] as String? ?? '') : name;
  }

  Iterable<Map<String, dynamic>> _searchUsers(String query) {
    final q = query.trim().toLowerCase();
    final users = _nonMembers.cast<Map<String, dynamic>>();
    if (q.isEmpty) return users.take(8);
    return users.where((u) {
      final display = _userDisplay(u).toLowerCase();
      final username = (u['username'] as String? ?? '').toLowerCase();
      final email = (u['email'] as String? ?? '').toLowerCase();
      return display.contains(q) || username.contains(q) || email.contains(q);
    }).take(8);
  }

  List<Map<String, dynamic>> get _searchResults =>
      _searchUsers(_memberSearchCtrl.text).toList();

  // Thêm 1 thành viên vào nhóm.

  Future<void> _addMember() async {
    if (_addUserId == null) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
        'admin/groups/${widget.group['id']}/members/',
        data: {'user_id': _addUserId, 'role': _addRole},
      );
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _addUserId = null;
        _memberSearchCtrl.clear();
      });
      await _loadMembers();
      widget.onChanged();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // Xóa 1 thành viên khỏi nhóm.

  Future<void> _removeMember(int userId) async {
    try {
      await ApiClient()
          .dio
          .delete('admin/groups/${widget.group['id']}/members/$userId/');
      await _loadMembers();
      widget.onChanged();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // Đổi vai trò thành viên (trưởng nhóm / thành viên).

  Future<void> _toggleRole(int userId, String currentRole) async {
    final newRole = currentRole == 'leader' ? 'member' : 'leader';
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.patch(
        'admin/groups/${widget.group['id']}/members/$userId/',
        data: {'role': newRole},
      );
      await _loadMembers();
      widget.onChanged();
    } catch (_) {}
  }

  @override
  // Dựng dialog thành viên: danh sách + thêm + đổi vai trò/xóa.

  Widget build(BuildContext context) {
    final nonMembers = _nonMembers;

    return AlertDialog(
      title: Text('${_pick('Thành viên', 'Members')}: ${widget.group['name']}'),
      content: SizedBox(
        width: 440,
        height: 400,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(children: [
                // Member list
                Expanded(
                  child: _members.isEmpty
                      ? Center(
                          child: Text(
                            _pick('Nhóm chưa có thành viên.',
                                'This group has no members yet.'),
                            style: const TextStyle(color: Colors.grey),
                          ),
                        )
                      : ListView.separated(
                          itemCount: _members.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (_, i) {
                            final m = _members[i];
                            final isLeader = m['role'] == 'leader';
                            return ListTile(
                              dense: true,
                              title: Text(m['full_name'] ?? m['username'],
                                  style: const TextStyle(fontSize: 13)),
                              subtitle: Text('@${m['username']}',
                                  style: const TextStyle(fontSize: 11)),
                              trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    // Role chip — tap to toggle
                                    GestureDetector(
                                      onTap: () =>
                                          _toggleRole(m['user_id'], m['role']),
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: isLeader
                                              ? Colors.purple.shade50
                                              : Colors.grey.shade100,
                                          borderRadius:
                                              BorderRadius.circular(10),
                                          border: Border.all(
                                              color: isLeader
                                                  ? Colors.purple.shade200
                                                  : Colors.grey.shade300),
                                        ),
                                        child: Text(
                                          isLeader
                                              ? _pick(
                                                  'Trưởng nhóm', 'Team lead')
                                              : _pick('Thành viên', 'Member'),
                                          style: TextStyle(
                                            fontSize: 11,
                                            color: isLeader
                                                ? Colors.purple.shade700
                                                : Colors.grey.shade600,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ),
                                    IconButton(
                                      icon: const Icon(
                                          Icons.remove_circle_outline,
                                          size: 18,
                                          color: Colors.red),
                                      onPressed: () =>
                                          _removeMember(m['user_id']),
                                      tooltip: _pick(
                                          'Xóa khỏi nhóm', 'Remove from group'),
                                    ),
                                  ]),
                            );
                          },
                        ),
                ),
                const Divider(),
                // Add member row
                if (nonMembers.isNotEmpty)
                  Column(children: [
                    TextField(
                      controller: _memberSearchCtrl,
                      focusNode: _memberSearchFocus,
                      decoration: InputDecoration(
                        labelText: _pick('Tìm thành viên', 'Find member'),
                        hintText:
                            _pick('Gõ tên người dùng...', 'Type a username...'),
                        prefixIcon: const Icon(Icons.search, size: 18),
                        isDense: true,
                        border: const OutlineInputBorder(),
                      ),
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onChanged: (_) => setState(() => _addUserId = null),
                    ),
                    if (_memberSearchCtrl.text.trim().isNotEmpty &&
                        _addUserId == null) ...[
                      const SizedBox(height: 6),
                      Container(
                        width: double.infinity,
                        constraints: const BoxConstraints(maxHeight: 180),
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey.shade300),
                          borderRadius: BorderRadius.circular(8),
                          color: Colors.white,
                        ),
                        child: _searchResults.isEmpty
                            ? Padding(
                                padding: const EdgeInsets.all(12),
                                child: Text(
                                  _pick('Không có người dùng phù hợp.',
                                      'No matching users found.'),
                                  style: const TextStyle(
                                      fontSize: 12, color: Colors.grey),
                                ),
                              )
                            : ListView.separated(
                                shrinkWrap: true,
                                itemCount: _searchResults.length,
                                separatorBuilder: (_, __) =>
                                    const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final user = _searchResults[index];
                                  final email =
                                      (user['email'] as String? ?? '');
                                  return ListTile(
                                    dense: true,
                                    title: Text(
                                      _userDisplay(user),
                                      style: const TextStyle(fontSize: 13),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    subtitle: Text(
                                      '@${user['username']}${email.isNotEmpty ? ' • $email' : ''}',
                                      style: const TextStyle(fontSize: 11),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    onTap: () {
                                      _memberSearchCtrl.text =
                                          _userDisplay(user);
                                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                      setState(
                                          () => _addUserId = user['id'] as int);
                                    },
                                  );
                                },
                              ),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(
                        child: DropdownButtonFormField<int>(
                          initialValue: _addUserId,
                          isExpanded: true,
                          decoration: InputDecoration(
                            labelText: _pick('Thêm thành viên', 'Add member'),
                            isDense: true,
                            border: const OutlineInputBorder(),
                          ),
                          items: nonMembers
                              .where((u) =>
                                  _addUserId == null || u['id'] == _addUserId)
                              .map<DropdownMenuItem<int>>((u) {
                            final name =
                                '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'
                                    .trim();
                            final display =
                                name.isEmpty ? u['username'] as String : name;
                            return DropdownMenuItem(
                              value: u['id'] as int,
                              child: Text(display,
                                  style: const TextStyle(fontSize: 13),
                                  overflow: TextOverflow.ellipsis),
                            );
                          }).toList(),
                          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                          onChanged: (v) => setState(() => _addUserId = v),
                        ),
                      ),
                      const SizedBox(width: 8),
                      DropdownButton<String>(
                        value: _addRole,
                        isDense: true,
                        items: const [
                          DropdownMenuItem(
                              value: 'member',
                              child:
                                  Text('TV', style: TextStyle(fontSize: 12))),
                          DropdownMenuItem(
                              value: 'leader',
                              child:
                                  Text('TN', style: TextStyle(fontSize: 12))),
                        ],
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onChanged: (v) =>
                            setState(() => _addRole = v ?? 'member'),
                      ),
                      IconButton(
                        icon: const Icon(Icons.add_circle_outline,
                            color: Colors.blue),
                        onPressed: _addUserId == null ? null : _addMember,
                        tooltip: _pick('Thêm vào nhóm', 'Add to group'),
                      ),
                    ]),
                  ])
                else
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      _pick('Tất cả người dùng đã trong nhóm.',
                          'All users are already in the group.'),
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ),
              ]),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(_ui('Đóng')),
        ),
      ],
    );
  }
}
