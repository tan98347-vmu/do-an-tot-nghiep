// === MÀN HÌNH DANH SÁCH MẪU VĂN BẢN ===
// Hiển thị theo nhóm/tab (của tôi / phòng ban / dùng chung / yêu thích / tất cả — templateCollectionProvider).
// - Tìm kiếm/lọc (chủ sở hữu, nhóm, theo tag _searchByTag; admin lọc thêm _loadAdminFilterData). Thẻ _TemplateCard có xem trước PDF ('preview-pdf/') + yêu thích.
// - Mở chi tiết (/templates/<id>), sửa (/edit), tạo mới (/templates/create).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/templates/template_list_screen.dart.
import 'dart:async';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui;
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/template_delete_helper.dart';
import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/templates_provider.dart';
import '../../models/template.dart';
import '../../models/user.dart';
import '../../widgets/common/record_code_label.dart';
import '../../widgets/common/view_mode_toggle.dart';
import '../../widgets/pdf/web_pdf_frame.dart';

// ─── Simple model cho admin filter lists ────────────────────────────────────
// Mục đơn giản (id + nhãn) cho dropdown lọc.

class _SimpleItem {
  final int id;
  final String label;
  const _SimpleItem(this.id, this.label);
}

final Set<String> _registeredTemplateListPreviewViews = <String>{};

// Widget màn DANH SÁCH MẪU VĂN BẢN; nhận group (nhóm/tab đang xem).

class TemplateListScreen extends ConsumerStatefulWidget {
  final String group;
  const TemplateListScreen({super.key, required this.group});

  @override
  ConsumerState<TemplateListScreen> createState() => _TemplateListScreenState();
}

// State màn danh sách mẫu: bộ lọc, tìm kiếm, chọn nhiều, dữ liệu lọc admin.

class _TemplateListScreenState extends ConsumerState<TemplateListScreen> {
  final _searchCtrl = TextEditingController();
  final _ownerCtrl = TextEditingController();
  Timer? _debounce;
  String _search = '';
  String _ownerQuery = '';
  String _visFilter = '';
  String _statusFilter = '';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  DateTime? _effectiveFrom;
  DateTime? _effectiveTo;
  DateTime? _endDateFrom;
  DateTime? _endDateTo;
  bool _showFilters = false;
  bool _showFilterPanel = false;
  String _viewMode = 'cards';
  final Set<int> _selectedTemplateIds = <int>{};
  bool _bulkDeleting = false;

  // Admin filters
  String _adminOwnerIdFilter = '';
  String _adminGroupIdFilter = '';
  List<_SimpleItem> _adminUsers = [];
  List<_SimpleItem> _adminGroups = [];
  bool _adminFiltersLoaded = false;

  AppStrings get _strings => AppStrings.of(context);
  String _tr(String vi, String en) => _strings.pick(vi, en);

  String _searchFieldLabelText() => switch (widget.group) {
        'system' => _tr('Tên / mã hệ thống / tag mẫu dùng chung',
            'Shared template title / system code / tag'),
        'team' => _tr('Tên / mã hệ thống / tag mẫu phòng ban',
            'Department template title / system code / tag'),
        'private' => _tr('Tên / mã hệ thống / tag mẫu của tôi',
            'My template title / system code / tag'),
        'favorite' => _tr('Tên / mã hệ thống / tag mẫu yêu thích',
            'Favorite template title / system code / tag'),
        'admin' => _tr('Tên / mã hệ thống / tag mẫu trong hệ thống',
            'System template title / system code / tag'),
        _ => _tr('Tên / mã hệ thống / tag mẫu',
            'Template title / system code / tag'),
      };

  String _ownerFieldLabelText() =>
      _isAdminView ? _tr('Chủ sở hữu', 'Owner') : _tr('Người tạo', 'Creator');

  String _filterSummaryTextLocalized() => switch (widget.group) {
        'system' => _tr(
            'Tab này đã tách sẵn mẫu dùng chung, bộ lọc ưu tiên tên, mã, trạng thái và người tạo.',
            'This tab focuses on shared templates, with filters for title, code, status, and creator.'),
        'team' => _tr(
            'Tab này đã tách sẵn mẫu phòng ban, bộ lọc ưu tiên tên, mã, trạng thái và người tạo.',
            'This tab focuses on department templates, with filters for title, code, status, and creator.'),
        'private' => _tr(
            'Tab này là không gian mẫu của bạn, bộ lọc ưu tiên tên, mã, trạng thái và mức chia sẻ.',
            'This is your personal template space, with filters for title, code, status, and sharing level.'),
        'favorite' => _tr(
            'Tab này là danh sách yêu thích, bộ lọc ưu tiên tên, mã, trạng thái, người tạo và mức chia sẻ.',
            'This is your favorites list, with filters for title, code, status, creator, and sharing level.'),
        'admin' => _tr(
            'Tab này dành cho quản trị, bộ lọc ưu tiên tên, mã, chủ sở hữu, phòng ban và trạng thái.',
            'This admin tab focuses on title, code, owner, department, and status filters.'),
        _ => _tr('Dùng bộ lọc theo thuộc tính để khoanh đúng mẫu cần tìm.',
            'Use the attribute filters to narrow down the right templates.'),
      };

  String _groupTitleText() => switch (widget.group) {
        'system' => _tr('Mẫu dùng chung', 'Shared templates'),
        'team' => _tr('Mẫu phòng ban của tôi', 'My department templates'),
        'private' => _tr('Mẫu của tôi', 'My private templates'),
        'favorite' => _tr('Mẫu yêu thích', 'Favorite templates'),
        'peer' =>
          _tr('Mẫu chia sẻ cho đồng nghiệp', 'Templates shared with me'),
        'admin' => _tr('Tất cả mẫu văn bản (Admin)', 'All templates (Admin)'),
        _ => _tr('Quản lý mẫu văn bản', 'Template management'),
      };

  String _groupSubtitleText() => switch (widget.group) {
        'system' => _tr('Mẫu dùng chung cho toàn bộ nhân viên trong hệ thống',
            'Templates shared across the organization'),
        'team' => _tr('Các mẫu dùng chung trong phòng ban hoặc nhóm của bạn',
            'Templates shared within your department or group'),
        'private' => _tr(
            'Tất cả mẫu bạn đã tạo, kể cả bản nháp hoặc đang chờ phê duyệt',
            'All templates you created, including drafts and pending approvals'),
        'favorite' => _tr('Các mẫu bạn đã đánh dấu yêu thích',
            'Templates you marked as favorite'),
        'peer' => _tr('Mẫu được đồng nghiệp chia sẻ riêng cho bạn',
            'Templates peers shared directly with you'),
        'admin' => _tr('Xem và quản lý toàn bộ mẫu văn bản của người dùng',
            'Browse and manage every template in the system'),
        _ => _tr('Tất cả mẫu văn bản bạn có quyền truy cập',
            'All templates you can access'),
      };

  @override
  // Mở màn: nạp danh sách mẫu của nhóm + dữ liệu lọc (admin).

  void initState() {
    super.initState();
    // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

    final user = ref.read(currentUserProvider);
    if (user?.isSuperuser == true) _loadAdminFilterData();
  }

  // Nạp dữ liệu cho bộ lọc nâng cao của admin (nhóm/người dùng).

  Future<void> _loadAdminFilterData() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final usersResp = await ApiClient().dio.get('admin/users/');
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final groupsResp = await ApiClient().dio.get('admin/groups/');
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _adminUsers = (usersResp.data as List).map<_SimpleItem>((u) {
          final name =
              '${u['first_name'] ?? ''} ${u['last_name'] ?? ''}'.trim();
          return _SimpleItem(
              u['id'], name.isEmpty ? (u['username'] ?? '').toString() : name);
        }).toList();
        _adminGroups = (groupsResp.data as List).map<_SimpleItem>((g) {
          return _SimpleItem(g['id'], g['name'] ?? '');
        }).toList();
        _adminFiltersLoaded = true;
      });
    } catch (_) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _adminFiltersLoaded = true);
    }
  }

  @override
  // Rời màn: dọn controller tìm kiếm.

  void dispose() {
    _searchCtrl.dispose();
    _ownerCtrl.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  // Lọc mẫu theo 1 tag khi bấm vào tag.

  void _searchByTag(String tag) {
    final query = '#$tag';
    _searchCtrl.text = query;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _search = query.toLowerCase());
  }

  // Lọc danh sách theo từ khóa (debounce).

  void _onSearchChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _search = v.toLowerCase().trim());
    });
  }

  void _onOwnerChanged(String v) {
    setState(() => _ownerQuery = v.toLowerCase().trim());
  }

  String get _serverSearchQuery {
    final value = _search.trim();
    if (value.startsWith('#')) {
      return value.substring(1).trim();
    }
    return value;
  }

  // Xóa toàn bộ bộ lọc.

  void _resetFilters() {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _searchCtrl.clear();
      _ownerCtrl.clear();
      _search = '';
      _ownerQuery = '';
      _visFilter = '';
      _statusFilter = '';
      _dateFrom = null;
      _dateTo = null;
      _effectiveFrom = null;
      _effectiveTo = null;
      _endDateFrom = null;
      _endDateTo = null;
      _adminOwnerIdFilter = '';
      _adminGroupIdFilter = '';
    });
  }

  // Đang có bộ lọc nào bật không.

  bool _hasActiveFilter() =>
      _search.isNotEmpty ||
      _ownerQuery.isNotEmpty ||
      _visFilter.isNotEmpty ||
      _statusFilter.isNotEmpty ||
      _dateFrom != null ||
      _dateTo != null ||
      _effectiveFrom != null ||
      _effectiveTo != null ||
      _endDateFrom != null ||
      _endDateTo != null ||
      _adminOwnerIdFilter.isNotEmpty ||
      _adminGroupIdFilter.isNotEmpty;

  int get _activeFilterCount {
    var count = 0;
    if (_search.isNotEmpty) count++;
    if (_ownerQuery.isNotEmpty) count++;
    if (_visFilter.isNotEmpty) count++;
    if (_statusFilter.isNotEmpty) count++;
    if (_dateFrom != null || _dateTo != null) count++;
    if (_effectiveFrom != null || _effectiveTo != null) count++;
    if (_endDateFrom != null || _endDateTo != null) count++;
    if (_adminOwnerIdFilter.isNotEmpty) count++;
    if (_adminGroupIdFilter.isNotEmpty) count++;
    return count;
  }

  // Kiểm 1 ngày có nằm trong khoảng lọc không.

  bool _matchDate(String? dateStr, DateTime? from, DateTime? to) {
    if (from == null && to == null) return true;
    if (dateStr == null || dateStr.isEmpty) return false;
    try {
      final d = DateTime.parse(dateStr.substring(0, 10));
      if (from != null && d.isBefore(from)) return false;
      if (to != null && d.isAfter(to)) return false;
      return true;
    } catch (_) {
      return true;
    }
  }

  List<DocumentTemplate> _filter(List<DocumentTemplate> all) {
    return all.where((t) {
      if (_visFilter.isNotEmpty && t.visibility != _visFilter) return false;
      if (_statusFilter.isNotEmpty && t.status != _statusFilter) return false;
      if (_ownerQuery.isNotEmpty &&
          !t.ownerName.toLowerCase().contains(_ownerQuery)) {
        return false;
      }
      if (!_matchDate(t.createdAt, _dateFrom, _dateTo)) return false;
      if (!_matchDate(t.effectiveDate, _effectiveFrom, _effectiveTo))
        return false;
      if (!_matchDate(t.endDate, _endDateFrom, _endDateTo)) return false;
      return true;
    }).toList();
  }

  bool get _isAdminView => widget.group == 'admin';
  bool get _showVisibilityFilter =>
      _isAdminView || widget.group == 'private' || widget.group == 'favorite';
  bool get _showOwnerFilter => widget.group != 'private';

  String get _filterSummaryText => switch (widget.group) {
        'system' =>
          'Tab này đã tách sẵn mẫu dùng chung, bộ lọc ưu tiên tên mã, trạng thái và người tạo.',
        'team' =>
          'Tab này đã tách sẵn mẫu phòng ban, bộ lọc ưu tiên tên mã, trạng thái và người tạo.',
        'private' =>
          'Tab này đã là không gian mẫu của bạn, bộ lọc ưu tiên tên mã, trạng thái và mức chia sẻ.',
        'favorite' =>
          'Tab này đã là danh sách yêu thích, bộ lọc ưu tiên tên mã, trạng thái, người tạo và mức chia sẻ.',
        'admin' =>
          'Tab này dành cho quản trị, bộ lọc ưu tiên tên mã, chủ sở hữu, phòng ban và trạng thái.',
        _ => 'Dùng bộ lọc theo thuộc tính để khoanh đúng mẫu cần tìm.',
      };

  // Kiểm user có quyền xóa mẫu này không.

  bool _canDeleteTemplate(DocumentTemplate t, AppUser? user) {
    return t.canDelete;
  }

  TemplateCollectionParams get _collectionParams => TemplateCollectionParams(
        group: widget.group,
        q: _serverSearchQuery,
        admin: _isAdminView,
        ownerId: _adminOwnerIdFilter,
        groupId: _adminGroupIdFilter,
      );

  // Làm mới danh sách mẫu từ server.

  void _refreshTemplates() {
    ref.invalidate(templateCollectionProvider(_collectionParams));
  }

  // Chọn/bỏ chọn 1 mẫu (chế độ chọn nhiều).

  void _toggleTemplateSelection(int id, bool selected) {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      if (selected) {
        _selectedTemplateIds.add(id);
      } else {
        _selectedTemplateIds.remove(id);
      }
    });
  }

  // Chọn/bỏ chọn tất cả mẫu đang lọc.

  void _toggleSelectAllTemplates(
      List<DocumentTemplate> filtered, AppUser? user) {
    final deletableIds = filtered
        .where((t) => _canDeleteTemplate(t, user))
        .map((t) => t.id)
        .toSet();
    if (deletableIds.isEmpty) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      final alreadyAllSelected =
          deletableIds.every(_selectedTemplateIds.contains);
      if (alreadyAllSelected) {
        _selectedTemplateIds.removeAll(deletableIds);
      } else {
        _selectedTemplateIds.addAll(deletableIds);
      }
    });
  }

  // Nút Xóa nhiều: xóa hàng loạt mẫu đã chọn (có xác nhận).

  Future<void> _bulkDeleteTemplates(BuildContext context) async {
    if (_selectedTemplateIds.isEmpty || _bulkDeleting) return;

    final count = _selectedTemplateIds.length;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xóa hàng loạt'),
        content: Text('Bạn có chắc muốn xóa $count mẫu văn bản đã chọn?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );

    if (ok != true || !mounted) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _bulkDeleting = true);
    var successCount = 0;
    var failedCount = 0;
    final ids = _selectedTemplateIds.toList();

    for (final id in ids) {
      try {
        // Xoa hang loat: nguoi dung da chu dong chon nhieu mau + xac nhan, nen
        // dung force=true de mau dang duoc su dung cung duoc xoa (soft-delete,
        // van ban da sinh khong bi anh huong).
        await ApiClient().dio.delete(
          'templates/$id/',
          queryParameters: {'force': 'true'},
        );
        successCount++;
      } catch (_) {
        failedCount++;
      }
    }

    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _bulkDeleting = false;
      _selectedTemplateIds.clear();
    });
    _refreshTemplates();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          failedCount == 0
              ? 'Đã xóa $successCount mẫu văn bản.'
              : 'Đã xóa $successCount mẫu, lỗi $failedCount mẫu.',
        ),
        backgroundColor: failedCount == 0 ? Colors.green : Colors.orange,
      ),
    );
  }

  @override
  // Dựng màn: tab nhóm + tìm/lọc + lưới mẫu (mỗi mẫu là _TemplateCard) + thao tác chọn nhiều.

  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final currentUser = ref.watch(currentUserProvider);
    final isSuperuser = currentUser?.isSuperuser ?? false;
    final isMobile = MediaQuery.sizeOf(context).width < 760;
    final filterFieldWidth =
        isMobile ? MediaQuery.sizeOf(context).width - 56 : 240.0;
    final compactFieldWidth =
        isMobile ? MediaQuery.sizeOf(context).width - 56 : 190.0;
    final strings = AppStrings.of(context);
    final groupTitle = _groupTitleText();
    final groupSubtitle = _groupSubtitleText();

    // Chọn provider phù hợp
    final asyncTemplates =
        ref.watch(templateCollectionProvider(_collectionParams));

    return Padding(
      padding: EdgeInsets.all(isMobile ? 12 : 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          isMobile
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      groupTitle,
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      groupSubtitle,
                      style:
                          TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                      onPressed: () => context.go('/templates/create'),
                      icon: const Icon(Icons.add, size: 18),
                      label: Text(
                          strings.pick('Tạo mẫu văn bản', 'Create template')),
                    ),
                  ],
                )
              : Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(groupTitle,
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(fontWeight: FontWeight.bold)),
                          Text(groupSubtitle,
                              style: TextStyle(
                                  color: Colors.grey.shade600, fontSize: 13)),
                        ],
                      ),
                    ),
                    FilledButton.icon(
                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                      onPressed: () => context.go('/templates/create'),
                      icon: const Icon(Icons.add, size: 18),
                      label: Text(
                          strings.pick('Tạo mẫu văn bản', 'Create template')),
                    ),
                  ],
                ),

          const SizedBox(height: 16),

          if (!_showFilterPanel) ...[
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => setState(() => _showFilterPanel = true),
                icon: const Icon(Icons.tune, size: 18),
                label: Text(
                  _hasActiveFilter()
                      ? 'Hiện bộ lọc ($_activeFilterCount)'
                      : 'Hiện bộ lọc',
                ),
              ),
            ),
            const SizedBox(height: 12),
          ] else ...[
            Card(
              margin: EdgeInsets.zero,
              color: Colors.white,
              child: Padding(
                padding: EdgeInsets.all(isMobile ? 12 : 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Icon(Icons.tune_rounded,
                            size: 18, color: Colors.blueGrey),
                        Text(
                          'Bộ lọc thông minh',
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.blueGrey.shade800,
                                  ),
                        ),
                        if (_hasActiveFilter())
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(color: Colors.blue.shade100),
                            ),
                            child: Text(
                              strings.pick(
                                '$_activeFilterCount bộ lọc đang bật',
                                '$_activeFilterCount active filters',
                              ),
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: Colors.blue.shade700,
                              ),
                            ),
                          ),
                        OutlinedButton.icon(
                          onPressed: () => setState(() {
                            _showFilterPanel = false;
                            _showFilters = false;
                          }),
                          icon: const Icon(Icons.visibility_off_outlined,
                              size: 16),
                          label:
                              Text(strings.pick('Ẩn bộ lọc', 'Hide filters')),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _filterSummaryTextLocalized(),
                      style:
                          TextStyle(fontSize: 12, color: Colors.grey.shade700),
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: filterFieldWidth,
                          child: TextField(
                            controller: _searchCtrl,
                            decoration: InputDecoration(
                              labelText: _searchFieldLabelText(),
                              hintText: strings.pick(
                                  'Lọc theo tên, mã hoặc tag',
                                  'Filter by title, code or tag'),
                              prefixIcon: const Icon(Icons.search),
                              suffixIcon: _search.isNotEmpty
                                  ? IconButton(
                                      icon: const Icon(Icons.clear, size: 18),
                                      onPressed: () {
                                        _searchCtrl.clear();
                                        setState(() => _search = '');
                                      },
                                    )
                                  : null,
                              border: const OutlineInputBorder(),
                              isDense: true,
                            ),
                            onChanged: _onSearchChanged,
                          ),
                        ),
                        SizedBox(
                          width: compactFieldWidth,
                          child: DropdownButtonFormField<String>(
                            value: _statusFilter.isEmpty ? null : _statusFilter,
                            decoration: InputDecoration(
                              labelText: strings.pick('Trạng thái', 'Status'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                              prefixIcon:
                                  const Icon(Icons.fact_check, size: 16),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.pick('Tất cả', 'All'))),
                              DropdownMenuItem(
                                  value: 'approved',
                                  child: Text(
                                      strings.pick('Đã duyệt', 'Approved'))),
                              DropdownMenuItem(
                                  value: 'pending',
                                  child: Text(
                                      strings.pick('Chờ duyệt', 'Pending'))),
                              DropdownMenuItem(
                                  value: 'rejected',
                                  child: Text(
                                      strings.pick('Bị từ chối', 'Rejected'))),
                              DropdownMenuItem(
                                  value: 'draft',
                                  child: Text(strings.ui('Bản nháp'))),
                            ],
                            onChanged: (v) =>
                                setState(() => _statusFilter = v ?? ''),
                          ),
                        ),
                        if (_showVisibilityFilter)
                          SizedBox(
                            width: compactFieldWidth,
                            child: DropdownButtonFormField<String>(
                              value: _visFilter.isEmpty ? null : _visFilter,
                              decoration: InputDecoration(
                                labelText: strings.ui('Mức chia sẻ'),
                                isDense: true,
                                border: const OutlineInputBorder(),
                                prefixIcon:
                                    const Icon(Icons.visibility, size: 16),
                              ),
                              items: [
                                DropdownMenuItem(
                                    value: null,
                                    child: Text(strings.pick('Tất cả', 'All'))),
                                DropdownMenuItem(
                                    value: 'public',
                                    child: Text(strings.ui('Công khai'))),
                                DropdownMenuItem(
                                    value: 'group',
                                    child: Text(strings.ui('Phòng ban'))),
                                DropdownMenuItem(
                                    value: 'private',
                                    child: Text(strings.ui('Riêng tư'))),
                              ],
                              onChanged: (v) =>
                                  setState(() => _visFilter = v ?? ''),
                            ),
                          ),
                        if (_showOwnerFilter)
                          SizedBox(
                            width: filterFieldWidth,
                            child: TextField(
                              controller: _ownerCtrl,
                              decoration: InputDecoration(
                                labelText: _ownerFieldLabelText(),
                                hintText: strings.pick(
                                    'Gõ tên người tạo để lọc nhanh',
                                    'Type owner name to filter'),
                                prefixIcon:
                                    const Icon(Icons.person_search_outlined),
                                suffixIcon: _ownerQuery.isNotEmpty
                                    ? IconButton(
                                        icon: const Icon(Icons.clear, size: 18),
                                        onPressed: () {
                                          _ownerCtrl.clear();
                                          setState(() => _ownerQuery = '');
                                        },
                                      )
                                    : null,
                                border: const OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: _onOwnerChanged,
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          onPressed: () =>
                              setState(() => _showFilters = !_showFilters),
                          icon: Icon(
                              _showFilters
                                  ? Icons.expand_less
                                  : Icons.expand_more,
                              size: 18),
                          label: Text(_showFilters
                              ? strings.pick(
                                  'Ẩn bộ lọc thêm', 'Hide more filters')
                              : strings.pick('Bộ lọc thêm', 'More filters')),
                        ),
                        if (_hasActiveFilter())
                          TextButton.icon(
                            onPressed: _resetFilters,
                            icon: const Icon(Icons.refresh, size: 16),
                            label: Text(strings.ui('Đặt lại')),
                            style: TextButton.styleFrom(
                                foregroundColor: Colors.red),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Visibility(
            visible: false,
            maintainState: true,
            child:
                // Search bar
                Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: strings.templateSearchHint(widget.group),
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _search.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear, size: 18),
                              onPressed: () {
                                _searchCtrl.clear();
                                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                setState(() => _search = '');
                              })
                          : null,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10)),
                      filled: true,
                      fillColor: Colors.white,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          vertical: 12, horizontal: 14),
                    ),
                    onChanged: _onSearchChanged,
                  ),
                ),
                const SizedBox(width: 8),
                Badge(
                  isLabelVisible: _hasActiveFilter(),
                  label: Text('$_activeFilterCount'),
                  child: OutlinedButton(
                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                    onPressed: () =>
                        setState(() => _showFilters = !_showFilters),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(44, 44),
                      padding: EdgeInsets.zero,
                      side: _hasActiveFilter()
                          ? const BorderSide(color: Colors.blue, width: 1.5)
                          : null,
                    ),
                    child:
                        Icon(_showFilters ? Icons.tune : Icons.tune, size: 18),
                  ),
                ),
                if (_hasActiveFilter()) ...[
                  const SizedBox(width: 6),
                  isMobile
                      ? IconButton(
                          onPressed: _resetFilters,
                          tooltip: 'Xóa bộ lọc',
                          icon: const Icon(Icons.refresh,
                              size: 18, color: Colors.red),
                        )
                      : TextButton.icon(
                          onPressed: _resetFilters,
                          icon: const Icon(Icons.refresh, size: 16),
                          label:
                              Text(strings.pick('Xóa bộ lọc', 'Clear filters')),
                          style:
                              TextButton.styleFrom(foregroundColor: Colors.red),
                        ),
                ],
              ],
            ),

            // Panel bộ lọc nâng cao
          ),
          if (_showFilters) ...[
            const SizedBox(height: 10),
            Card(
              margin: EdgeInsets.zero,
              color: Colors.grey.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Icon(Icons.tune,
                            size: 16, color: Colors.blueGrey),
                        const SizedBox(width: 6),
                        Text(
                            strings.pick('Bộ lọc nâng cao', 'Advanced filters'),
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.blueGrey.shade700)),
                        if (isSuperuser) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.purple.shade50,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: Colors.purple.shade200),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.admin_panel_settings,
                                    size: 12, color: Colors.purple.shade700),
                                const SizedBox(width: 4),
                                Text('Admin',
                                    style: TextStyle(
                                        fontSize: 11,
                                        color: Colors.purple.shade700,
                                        fontWeight: FontWeight.w600)),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: 200,
                          child: DropdownButtonFormField<String>(
                            value: _visFilter.isEmpty ? null : _visFilter,
                            decoration: const InputDecoration(
                              labelText: 'Mức chia sẻ',
                              isDense: true,
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.visibility, size: 16),
                            ),
                            items: const [
                              DropdownMenuItem(
                                  value: null, child: Text('Tất cả')),
                              DropdownMenuItem(
                                value: 'public',
                                child: Row(children: [
                                  Icon(Icons.public,
                                      size: 14, color: Colors.green),
                                  SizedBox(width: 6),
                                  Text('Thông thường (Công khai)'),
                                ]),
                              ),
                              DropdownMenuItem(
                                value: 'group',
                                child: Row(children: [
                                  Icon(Icons.group,
                                      size: 14, color: Colors.blue),
                                  SizedBox(width: 6),
                                  Text('Phòng ban'),
                                ]),
                              ),
                              DropdownMenuItem(
                                value: 'private',
                                child: Row(children: [
                                  Icon(Icons.lock,
                                      size: 14, color: Colors.grey),
                                  SizedBox(width: 6),
                                  Text('Riêng tư'),
                                ]),
                              ),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _visFilter = v ?? ''),
                          ),
                        ),
                        SizedBox(
                          width: 200,
                          child: DropdownButtonFormField<String>(
                            value: _statusFilter.isEmpty ? null : _statusFilter,
                            decoration: const InputDecoration(
                              labelText: 'Trạng thái duyệt',
                              isDense: true,
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.fact_check, size: 16),
                            ),
                            items: const [
                              DropdownMenuItem(
                                  value: null, child: Text('Tất cả')),
                              DropdownMenuItem(
                                  value: 'approved',
                                  child: Row(children: [
                                    Icon(Icons.check_circle,
                                        size: 14, color: Colors.green),
                                    SizedBox(width: 6),
                                    Text('Đã duyệt')
                                  ])),
                              DropdownMenuItem(
                                  value: 'pending',
                                  child: Row(children: [
                                    Icon(Icons.pending,
                                        size: 14, color: Colors.orange),
                                    SizedBox(width: 6),
                                    Text('Chờ duyệt')
                                  ])),
                              DropdownMenuItem(
                                  value: 'rejected',
                                  child: Row(children: [
                                    Icon(Icons.cancel,
                                        size: 14, color: Colors.red),
                                    SizedBox(width: 6),
                                    Text('Bị từ chối')
                                  ])),
                              DropdownMenuItem(
                                  value: 'draft',
                                  child: Row(children: [
                                    Icon(Icons.edit,
                                        size: 14, color: Colors.grey),
                                    SizedBox(width: 6),
                                    Text('Bản nháp')
                                  ])),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _statusFilter = v ?? ''),
                          ),
                        ),
                        // Admin: filter by owner
                        if (isSuperuser && _adminFiltersLoaded) ...[
                          SizedBox(
                            width: 220,
                            child: DropdownButtonFormField<String>(
                              value: _adminOwnerIdFilter.isEmpty
                                  ? null
                                  : _adminOwnerIdFilter,
                              decoration: const InputDecoration(
                                labelText: 'Lọc theo người dùng',
                                isDense: true,
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.person, size: 16),
                              ),
                              items: [
                                DropdownMenuItem(
                                    value: null,
                                    child: Text(strings.pick(
                                        'Tất cả người dùng', 'All users'))),
                                ..._adminUsers.map((u) => DropdownMenuItem(
                                      value: u.id.toString(),
                                      child: Text(u.label,
                                          overflow: TextOverflow.ellipsis),
                                    )),
                              ],
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              onChanged: (v) =>
                                  setState(() => _adminOwnerIdFilter = v ?? ''),
                            ),
                          ),
                          SizedBox(
                            width: 220,
                            child: DropdownButtonFormField<String>(
                              value: _adminGroupIdFilter.isEmpty
                                  ? null
                                  : _adminGroupIdFilter,
                              decoration: const InputDecoration(
                                labelText: 'Lọc theo phòng ban',
                                isDense: true,
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.group_work, size: 16),
                              ),
                              items: [
                                DropdownMenuItem(
                                    value: null,
                                    child: Text(strings.pick('Tất cả phòng ban',
                                        'All departments'))),
                                ..._adminGroups.map((g) => DropdownMenuItem(
                                      value: g.id.toString(),
                                      child: Text(g.label,
                                          overflow: TextOverflow.ellipsis),
                                    )),
                              ],
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              onChanged: (v) =>
                                  setState(() => _adminGroupIdFilter = v ?? ''),
                            ),
                          ),
                        ],
                      ],
                    ),
                    if (!_isAdminView) ...[
                      const SizedBox(height: 14),
                      const Divider(height: 1),
                      const SizedBox(height: 14),
                      _DateRangeRow(
                        label: 'Ngày tạo',
                        icon: Icons.calendar_today,
                        from: _dateFrom, to: _dateTo,
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onFromPick: (d) => setState(() => _dateFrom = d),
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onToPick: (d) => setState(() => _dateTo = d),
                      ),
                      const SizedBox(height: 10),
                      _DateRangeRow(
                        label: 'Hiệu lực từ ngày',
                        icon: Icons.event_available,
                        from: _effectiveFrom, to: _effectiveTo,
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onFromPick: (d) => setState(() => _effectiveFrom = d),
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onToPick: (d) => setState(() => _effectiveTo = d),
                      ),
                      const SizedBox(height: 10),
                      _DateRangeRow(
                        label: 'Hết hiệu lực',
                        icon: Icons.event_busy,
                        from: _endDateFrom, to: _endDateTo,
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onFromPick: (d) => setState(() => _endDateFrom = d),
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onToPick: (d) => setState(() => _endDateTo = d),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 12),

          if (_showFilterPanel) ...[
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _QuickChip(
                    label: 'Tất cả',
                    active: _visFilter.isEmpty && _statusFilter.isEmpty,
                    onTap: () => setState(() {
                      _visFilter = '';
                      _statusFilter = '';
                    }),
                  ),
                  if (_showVisibilityFilter) ...[
                    const SizedBox(width: 6),
                    _QuickChip(
                      label: 'Công khai',
                      icon: Icons.public,
                      color: Colors.green,
                      active: _visFilter == 'public',
                      onTap: () => setState(
                        () =>
                            _visFilter = _visFilter == 'public' ? '' : 'public',
                      ),
                    ),
                    const SizedBox(width: 6),
                    _QuickChip(
                      label: 'Phòng ban',
                      icon: Icons.group,
                      color: Colors.blue,
                      active: _visFilter == 'group',
                      onTap: () => setState(
                        () => _visFilter = _visFilter == 'group' ? '' : 'group',
                      ),
                    ),
                    const SizedBox(width: 6),
                    _QuickChip(
                      label: 'Riêng tư',
                      icon: Icons.lock,
                      color: Colors.grey,
                      active: _visFilter == 'private',
                      onTap: () => setState(
                        () => _visFilter =
                            _visFilter == 'private' ? '' : 'private',
                      ),
                    ),
                  ],
                  const SizedBox(width: 6),
                  _QuickChip(
                    label: 'Đã duyệt',
                    icon: Icons.check_circle,
                    color: Colors.teal,
                    active: _statusFilter == 'approved',
                    onTap: () => setState(
                      () => _statusFilter =
                          _statusFilter == 'approved' ? '' : 'approved',
                    ),
                  ),
                  const SizedBox(width: 6),
                  _QuickChip(
                    label: 'Chờ duyệt',
                    icon: Icons.pending,
                    color: Colors.orange,
                    active: _statusFilter == 'pending',
                    onTap: () => setState(
                      () => _statusFilter =
                          _statusFilter == 'pending' ? '' : 'pending',
                    ),
                  ),
                  const SizedBox(width: 6),
                  _QuickChip(
                    label: 'Bản nháp',
                    icon: Icons.edit,
                    color: Colors.grey,
                    active: _statusFilter == 'draft',
                    onTap: () => setState(
                      () => _statusFilter =
                          _statusFilter == 'draft' ? '' : 'draft',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Quick filter chips
          Visibility(
            visible: false,
            maintainState: true,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _QuickChip(
                    label: 'Tất cả',
                    active: _visFilter.isEmpty && _statusFilter.isEmpty,
                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                    onTap: () => setState(() {
                      _visFilter = '';
                      _statusFilter = '';
                    }),
                  ),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Công khai',
                      icon: Icons.public,
                      color: Colors.green,
                      active: _visFilter == 'public',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() =>
                          _visFilter = _visFilter == 'public' ? '' : 'public')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Phòng ban',
                      icon: Icons.group,
                      color: Colors.blue,
                      active: _visFilter == 'group',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() =>
                          _visFilter = _visFilter == 'group' ? '' : 'group')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Riêng tư',
                      icon: Icons.lock,
                      color: Colors.grey,
                      active: _visFilter == 'private',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _visFilter =
                          _visFilter == 'private' ? '' : 'private')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Đã duyệt',
                      icon: Icons.check_circle,
                      color: Colors.teal,
                      active: _statusFilter == 'approved',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _statusFilter =
                          _statusFilter == 'approved' ? '' : 'approved')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Chờ duyệt',
                      icon: Icons.pending,
                      color: Colors.orange,
                      active: _statusFilter == 'pending',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _statusFilter =
                          _statusFilter == 'pending' ? '' : 'pending')),
                  if (!_isAdminView) ...[
                    const SizedBox(width: 6),
                    _QuickChip(
                        label: 'Yêu thích',
                        icon: Icons.star,
                        color: Colors.amber,
                        active: _statusFilter == '__favorite__',
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onTap: () => setState(() => _statusFilter =
                            _statusFilter == '__favorite__'
                                ? ''
                                : '__favorite__')),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          // Results
          Expanded(
            child: asyncTemplates.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Lỗi: $e')),
              data: (templates) {
                List<DocumentTemplate> filtered = _filter(templates);
                if (_statusFilter == '__favorite__') {
                  filtered = filtered.where((t) => t.isFavorite).toList();
                }
                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.search_off,
                            size: 64, color: Colors.grey.shade300),
                        const SizedBox(height: 12),
                        Text(
                            strings.pick('Không tìm thấy mẫu nào.',
                                'No templates found.'),
                            style: TextStyle(
                                color: Colors.grey.shade500, fontSize: 15)),
                        if (_hasActiveFilter()) ...[
                          const SizedBox(height: 8),
                          TextButton(
                            onPressed: _resetFilters,
                            child: Text(strings.pick(
                              'Xóa bộ lọc để xem tất cả',
                              'Clear filters to view all',
                            )),
                          ),
                        ],
                      ],
                    ),
                  );
                }
                final deletableTemplates = filtered
                    .where((t) => _canDeleteTemplate(t, currentUser))
                    .toList();
                final allVisibleSelected = deletableTemplates.isNotEmpty &&
                    deletableTemplates
                        .every((t) => _selectedTemplateIds.contains(t.id));
                final effectiveViewMode = isMobile ? 'compact_list' : _viewMode;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: [
                                Text(
                                  strings.pick(
                                    'Tìm thấy ${filtered.length} mẫu',
                                    'Found ${filtered.length} templates',
                                  ),
                                  style: TextStyle(
                                    color: Colors.grey.shade600,
                                    fontSize: 13,
                                  ),
                                ),
                                if (_search.isNotEmpty) ...[
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.yellow.shade100,
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: Colors.yellow.shade300,
                                      ),
                                    ),
                                    child: Text(
                                      strings.pick(
                                        'Khớp: "$_search"',
                                        'Match: "$_search"',
                                      ),
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Colors.orange.shade800,
                                      ),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                        // Desktop: gom tat ca cong cu (chon tat ca, da chon, bo
                        // chon, toggle the/danh sach, xoa hang loat) vao CUNG 1 dong.
                        if (!isMobile) ...[
                          const SizedBox(width: 8),
                          OutlinedButton.icon(
                            onPressed: deletableTemplates.isEmpty
                                ? null
                                : () => _toggleSelectAllTemplates(
                                    filtered, currentUser),
                            icon: Icon(
                              allVisibleSelected
                                  ? Icons.check_box_rounded
                                  : Icons.check_box_outline_blank_rounded,
                              size: 18,
                            ),
                            label: Text(allVisibleSelected
                                ? strings.pick(
                                    'Bỏ chọn tất cả', 'Clear selection')
                                : strings.pick('Chọn tất cả', 'Select all')),
                          ),
                          if (_selectedTemplateIds.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            Text(
                              strings.pick(
                                'Đã chọn ${_selectedTemplateIds.length}',
                                'Selected ${_selectedTemplateIds.length}',
                              ),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: Colors.blueGrey.shade700,
                              ),
                            ),
                            TextButton(
                              onPressed: () =>
                                  setState(() => _selectedTemplateIds.clear()),
                              child: Text(strings.pick('Bỏ chọn', 'Clear')),
                            ),
                          ],
                          const SizedBox(width: 8),
                          ViewModeToggle(
                            value: _viewMode,
                            onChanged: (value) =>
                                setState(() => _viewMode = value),
                            cardLabel: strings.pick('Dạng thẻ', 'Card view'),
                            listLabel:
                                strings.pick('Dạng danh sách', 'List view'),
                          ),
                          if (_selectedTemplateIds.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            FilledButton.icon(
                              onPressed: _bulkDeleting
                                  ? null
                                  : () => _bulkDeleteTemplates(context),
                              style: FilledButton.styleFrom(
                                backgroundColor: Colors.red.shade600,
                              ),
                              icon: _bulkDeleting
                                  ? const SizedBox(
                                      width: 14,
                                      height: 14,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white,
                                      ),
                                    )
                                  : const Icon(Icons.delete_sweep_outlined,
                                      size: 18),
                              label: Text(_bulkDeleting
                                  ? strings.pick('Đang xóa...', 'Deleting...')
                                  : strings.pick(
                                      'Xóa hàng loạt', 'Delete selected')),
                            ),
                          ],
                        ],
                      ],
                    ),
                    const SizedBox(height: 10),
                    // Mobile: giu thanh chon/xoa rieng (hien khi da chon item).
                    if (isMobile && _selectedTemplateIds.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.grey.shade200),
                        ),
                        child: isMobile
                            ? Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  OutlinedButton.icon(
                                    onPressed: deletableTemplates.isEmpty
                                        ? null
                                        : () => _toggleSelectAllTemplates(
                                            filtered, currentUser),
                                    icon: Icon(
                                      allVisibleSelected
                                          ? Icons.check_box_rounded
                                          : Icons
                                              .check_box_outline_blank_rounded,
                                      size: 18,
                                    ),
                                    label: Text(
                                      allVisibleSelected
                                          ? strings.pick('Bỏ chọn tất cả',
                                              'Clear selection')
                                          : strings.pick(
                                              'Chọn tất cả', 'Select all'),
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    _selectedTemplateIds.isEmpty
                                        ? strings.pick('Chưa chọn mẫu nào',
                                            'No templates selected')
                                        : strings.pick(
                                            'Đã chọn ${_selectedTemplateIds.length} mẫu',
                                            'Selected ${_selectedTemplateIds.length} templates'),
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.blueGrey.shade700,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: [
                                      if (_selectedTemplateIds.isNotEmpty)
                                        TextButton(
                                          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                          onPressed: () => setState(() =>
                                              _selectedTemplateIds.clear()),
                                          child: Text(
                                              strings.pick('Bỏ chọn', 'Clear')),
                                        ),
                                      FilledButton.icon(
                                        onPressed: _selectedTemplateIds
                                                    .isEmpty ||
                                                _bulkDeleting
                                            ? null
                                            : () =>
                                                _bulkDeleteTemplates(context),
                                        style: FilledButton.styleFrom(
                                          backgroundColor: Colors.red.shade600,
                                        ),
                                        icon: _bulkDeleting
                                            ? const SizedBox(
                                                width: 14,
                                                height: 14,
                                                child:
                                                    CircularProgressIndicator(
                                                  strokeWidth: 2,
                                                  color: Colors.white,
                                                ),
                                              )
                                            : const Icon(
                                                Icons.delete_sweep_outlined,
                                                size: 18),
                                        label: Text(_bulkDeleting
                                            ? strings.pick(
                                                'Đang xóa...', 'Deleting...')
                                            : strings.pick('Xóa hàng loạt',
                                                'Delete selected')),
                                      ),
                                    ],
                                  ),
                                ],
                              )
                            : Row(
                                children: [
                                  OutlinedButton.icon(
                                    onPressed: deletableTemplates.isEmpty
                                        ? null
                                        : () => _toggleSelectAllTemplates(
                                            filtered, currentUser),
                                    icon: Icon(
                                      allVisibleSelected
                                          ? Icons.check_box_rounded
                                          : Icons
                                              .check_box_outline_blank_rounded,
                                      size: 18,
                                    ),
                                    label: Text(allVisibleSelected
                                        ? strings.pick(
                                            'Bỏ chọn tất cả', 'Clear selection')
                                        : strings.pick(
                                            'Chọn tất cả', 'Select all')),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      _selectedTemplateIds.isEmpty
                                          ? strings.pick('Chưa chọn mẫu nào',
                                              'No templates selected')
                                          : strings.pick(
                                              'Đã chọn ${_selectedTemplateIds.length} mẫu',
                                              'Selected ${_selectedTemplateIds.length} templates'),
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.blueGrey.shade700,
                                      ),
                                    ),
                                  ),
                                  if (_selectedTemplateIds.isNotEmpty)
                                    TextButton(
                                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                      onPressed: () => setState(
                                          () => _selectedTemplateIds.clear()),
                                      child: Text(
                                          strings.pick('Bỏ chọn', 'Clear')),
                                    ),
                                  const SizedBox(width: 8),
                                  FilledButton.icon(
                                    onPressed: _selectedTemplateIds.isEmpty ||
                                            _bulkDeleting
                                        ? null
                                        : () => _bulkDeleteTemplates(context),
                                    style: FilledButton.styleFrom(
                                      backgroundColor: Colors.red.shade600,
                                    ),
                                    icon: _bulkDeleting
                                        ? const SizedBox(
                                            width: 14,
                                            height: 14,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white,
                                            ),
                                          )
                                        : const Icon(
                                            Icons.delete_sweep_outlined,
                                            size: 18),
                                    label: Text(_bulkDeleting
                                        ? strings.pick(
                                            'Đang xóa...', 'Deleting...')
                                        : strings.pick('Xóa hàng loạt',
                                            'Delete selected')),
                                  ),
                                ],
                              ),
                      ),
                    const SizedBox(height: 10),
                    Expanded(
                      child: effectiveViewMode == 'cards'
                          ? GridView.builder(
                              gridDelegate:
                                  const SliverGridDelegateWithMaxCrossAxisExtent(
                                maxCrossAxisExtent: 340,
                                childAspectRatio: 1.25,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: filtered.length,
                              itemBuilder: (_, i) => _TemplateCard(
                                template: filtered[i],
                                searchQuery: _search,
                                currentUser: currentUser,
                                selected: _selectedTemplateIds
                                    .contains(filtered[i].id),
                                selectionEnabled: _canDeleteTemplate(
                                    filtered[i], currentUser),
                                onSelectedChanged: (selected) =>
                                    _toggleTemplateSelection(
                                        filtered[i].id, selected ?? false),
                                onRefresh: _refreshTemplates,
                              ),
                            )
                          : ListView.separated(
                              itemCount: filtered.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (_, i) => _TemplateCard(
                                template: filtered[i],
                                searchQuery: _search,
                                currentUser: currentUser,
                                compact: true,
                                selected: _selectedTemplateIds
                                    .contains(filtered[i].id),
                                selectionEnabled: _canDeleteTemplate(
                                    filtered[i], currentUser),
                                onSelectedChanged: (selected) =>
                                    _toggleTemplateSelection(
                                        filtered[i].id, selected ?? false),
                                onRefresh: _refreshTemplates,
                              ),
                            ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  String get _groupTitle => switch (widget.group) {
        'system' => 'Mẫu dùng chung',
        'team' => 'Mẫu phòng ban của tôi',
        'private' => 'Mẫu của tôi',
        'favorite' => 'Mẫu yêu thích',
        'admin' => 'Tất cả mẫu văn bản (Admin)',
        _ => 'Quản lý mẫu văn bản',
      };

  String get _groupSubtitle => switch (widget.group) {
        'system' => 'Mẫu dùng chung cho tất cả nhân viên',
        'team' => 'Mẫu dùng chung trong phòng ban của bạn',
        'private' =>
          'Tat ca mau do ban tao ra, ke ca mau dang cho duyet hoac cho phe duyet lai',
        'favorite' => 'Các mẫu bạn đã đánh dấu yêu thích',
        'admin' => 'Xem và quản lý tất cả mẫu văn bản của mọi người dùng',
        _ => 'Tất cả mẫu văn bản bạn có quyền truy cập',
      };
}

// ─── Card ──────────────────────────────────────────────────────────────────

// Thẻ 1 mẫu trong lưới (ConsumerStatefulWidget).

class _TemplateCard extends ConsumerStatefulWidget {
  final DocumentTemplate template;
  final String searchQuery;
  final AppUser? currentUser;
  final VoidCallback onRefresh;
  final bool compact;
  final bool selected;
  final bool selectionEnabled;
  final ValueChanged<bool?> onSelectedChanged;

  const _TemplateCard({
    required this.template,
    required this.searchQuery,
    required this.currentUser,
    required this.onRefresh,
    this.compact = false,
    required this.selected,
    required this.selectionEnabled,
    required this.onSelectedChanged,
  });

  @override
  ConsumerState<_TemplateCard> createState() => _TemplateCardState();
}

// State thẻ mẫu: xem trước PDF/HTML + thao tác yêu thích/xóa.

class _TemplateCardState extends ConsumerState<_TemplateCard> {
  bool _favLoading = false;
  bool _localFav = false;
  bool _initialized = false;

  @override
  // Khi mẫu của thẻ đổi -> cập nhật trạng thái.

  void didUpdateWidget(_TemplateCard old) {
    super.didUpdateWidget(old);
    if (!_initialized ||
        old.template.isFavorite != widget.template.isFavorite) {
      _localFav = widget.template.isFavorite;
      _initialized = true;
    }
  }

  @override
  // Khởi tạo thẻ: chuẩn bị xem trước + cờ đã đọc duyệt.

  void initState() {
    super.initState();
    _localFav = widget.template.isFavorite;
    _initialized = true;
  }

  // Kiểm quyền xóa mẫu (trong thẻ).

  bool _canDelete(DocumentTemplate t, AppUser? user) {
    return t.canDelete;
  }

  // Kiểm quyền sửa mẫu (trong thẻ).

  bool _canEdit(DocumentTemplate t, AppUser? user) {
    return t.canEdit;
  }

  // Key lưu cục bộ đánh dấu đã đọc kết quả duyệt mẫu.

  String _reviewStorageKey(int templateId) =>
      'template_review_seen:$templateId';

  String? _reviewToken(DocumentTemplate t) {
    final action = t.lastReviewAction;
    final at = t.lastReviewAt;
    if (action == null || at == null || at.isEmpty) return null;
    if (action != 'approve' && action != 'reject') return null;
    return '$action@$at';
  }

  // Mẫu có thông báo duyệt chưa đọc không (chấm đỏ).

  bool _hasUnreadReview(DocumentTemplate t, AppUser? user) {
    if (user == null || user.id != t.ownerId) return false;
    final token = _reviewToken(t);
    if (token == null) return false;
    return html.window.localStorage[_reviewStorageKey(t.id)] != token;
  }

  String? _ownerReviewSummary(DocumentTemplate t, AppUser? user) {
    if (user == null || user.id != t.ownerId) return null;
    final actor = t.lastReviewActorName?.trim();
    final rawAt = t.lastReviewAt?.trim();
    final at =
        rawAt != null && rawAt.length >= 10 ? rawAt.substring(0, 10) : rawAt;
    switch (t.lastReviewAction) {
      case 'approve':
        return 'Đã duyệt bởi ${actor?.isNotEmpty == true ? actor : 'hệ thống'}${at != null && at.isNotEmpty ? ' ngày $at' : ''}.';
      case 'reject':
        return 'Đã từ chối bởi ${actor?.isNotEmpty == true ? actor : 'hệ thống'}${at != null && at.isNotEmpty ? ' ngày $at' : ''}.';
      default:
        return null;
    }
  }

  // Bật/tắt yêu thích mẫu (trong thẻ).

  Future<void> _toggleFavorite() async {
    if (_favLoading) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _favLoading = true;
      _localFav = !_localFav;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('templates/${widget.template.id}/favorite/');
      widget.onRefresh();
    } catch (_) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _localFav = !_localFav); // revert
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _favLoading = false);
    }
  }

  // Xóa mẫu (trong thẻ) -> thùng rác.

  Future<void> _delete(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xóa'),
        content: Text(
            'Bạn có chắc muốn xóa mẫu "${widget.template.title}"?\nHành động này không thể hoàn tác.'),
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
    if (ok != true || !mounted) return;
    try {
      // Helper xu ly thong nhat truong hop mau dang duoc su dung (409 -> xac nhan).
      final outcome =
          await deleteTemplateWithUsageGuard(context, widget.template.id);
      if (outcome == TemplateDeleteOutcome.deleted) {
        widget.onRefresh();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text('Đã xóa mẫu văn bản.'),
                backgroundColor: Colors.green),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi xóa: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // Dựng khung xem trước HTML nhỏ trong thẻ mẫu.

  Widget _buildHtmlPreviewFrame(String viewKey, String htmlContent) {
    if (_registeredTemplateListPreviewViews.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        return html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..srcdoc = htmlContent;
      });
    }
    return HtmlElementView(viewType: viewKey);
  }

  // Mở xem trước mẫu (PDF/HTML) từ thẻ.

  Future<void> _previewTemplate(BuildContext context) async {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => const Dialog(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              ),
              SizedBox(width: 16),
              Text('Dang tai xem truoc...'),
            ],
          ),
        ),
      ),
    );

    String? pdfUrl;
    String? htmlContent;
    String? notice;
    Object? previewError;
    try {
      try {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final pdfResp = await ApiClient().dio.get(
              'templates/${widget.template.id}/preview-pdf/',
              queryParameters: {
                'rev': widget.template.updatedAt,
                'ts': DateTime.now().millisecondsSinceEpoch.toString(),
              },
              options: Options(responseType: ResponseType.bytes),
            );
        final bytes = List<int>.from(pdfResp.data as List);
        final pdfBytes = Uint8List.fromList(bytes);
        final blob = html.Blob([pdfBytes], 'application/pdf');
        pdfUrl = html.Url.createObjectUrlFromBlob(blob);
        debugPrint(
          '[template_list_preview] pdf_ready | template_id=${widget.template.id} | bytes=${pdfBytes.length} | status=${pdfResp.statusCode} | content_type=${pdfResp.headers.value('content-type')} | blob_url=$pdfUrl',
        );
      } on DioException catch (error) {
        debugPrint(
            '[template_list_preview] pdf_failed | template_id=${widget.template.id} | error=$error');
        final data = error.response?.data;
        if (data is Map && data['detail'] != null) {
          notice = '${data['detail']} Dang chuyen sang xem HTML.';
        } else {
          notice = 'Khong tao duoc preview PDF. Dang chuyen sang xem HTML.';
        }
      }

      if (pdfUrl == null) {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final htmlResp = await ApiClient().dio.get(
          'templates/${widget.template.id}/content-html/',
          queryParameters: {
            'rev': widget.template.updatedAt,
            'ts': DateTime.now().millisecondsSinceEpoch.toString(),
          },
        );
        htmlContent = htmlResp.data['html'] as String? ?? '';
        debugPrint(
          '[template_list_preview] html_fallback | template_id=${widget.template.id} | html_chars=${htmlContent.length}',
        );
      }
    } catch (error) {
      debugPrint(
          '[template_list_preview] load_failed | template_id=${widget.template.id} | error=$error');
      previewError = error;
    } finally {
      if (context.mounted) {
        Navigator.of(context, rootNavigator: true).pop();
      }
    }

    if (!context.mounted) {
      if (pdfUrl != null) html.Url.revokeObjectUrl(pdfUrl);
      return;
    }
    if (previewError != null ||
        (pdfUrl == null && (htmlContent == null || htmlContent!.isEmpty))) {
      if (pdfUrl != null) {
        html.Url.revokeObjectUrl(pdfUrl);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              'Không tải được preview mẫu: ${previewError ?? 'không có dữ liệu'}'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final viewKey =
        'template-list-preview-${widget.template.id}-${DateTime.now().millisecondsSinceEpoch}';
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: const EdgeInsets.all(18),
        child: SizedBox(
          width: 1100,
          height: MediaQuery.of(ctx).size.height * 0.88,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 10, 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Xem truoc: ${widget.template.title}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 17, fontWeight: FontWeight.w700),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              if (pdfUrl != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: OutlinedButton.icon(
                      onPressed: () => html.window.open(pdfUrl!, '_blank'),
                      icon: const Icon(Icons.picture_as_pdf_outlined, size: 16),
                      label: const Text('Mo PDF'),
                    ),
                  ),
                ),
              if (notice != null && notice!.isNotEmpty)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF7ED),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFFED7AA)),
                  ),
                  child: Text(
                    notice!,
                    style: const TextStyle(
                        color: Color(0xFF9A3412), fontSize: 12.5),
                  ),
                ),
              const Divider(height: 1),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: pdfUrl != null
                      ? WebPdfFrame(
                          viewKey: viewKey,
                          pdfUrl: pdfUrl!,
                        )
                      : _buildHtmlPreviewFrame(
                          viewKey, htmlContent ?? '<p>Khong co noi dung.</p>'),
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (pdfUrl != null) {
      html.Url.revokeObjectUrl(pdfUrl);
    }
  }

  @override
  // Dựng thẻ mẫu: tiêu đề, badge trạng thái/phạm vi, xem trước, nút yêu thích/sửa/xóa; bấm mở chi tiết.

  Widget build(BuildContext context) {
    final t = widget.template;
    final user = widget.currentUser;
    final canDelete = _canDelete(t, user);
    final canEdit = _canEdit(t, user);
    final reviewSummary = _ownerReviewSummary(t, user);
    final hasUnreadReview = _hasUnreadReview(t, user);
    final isPhone = MediaQuery.sizeOf(context).width < 760;
    final useCompactLayout = widget.compact || isPhone;
    // Ô checkbox chọn mẫu (chế độ chọn nhiều) trong thẻ.

    Widget selectionBox() => Checkbox(
          value: widget.selected,
          onChanged: widget.selectionEnabled ? widget.onSelectedChanged : null,
          visualDensity: VisualDensity.compact,
        );
    // Hàng nút thao tác nhanh trong thẻ mẫu.

    Widget actionRow() => Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            GestureDetector(
              onTap: () => _previewTemplate(context),
              child: Icon(Icons.preview_outlined,
                  size: 16, color: Colors.teal.shade500),
            ),
            const SizedBox(width: 4),
            GestureDetector(
              onTap: _toggleFavorite,
              child: _favLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 1.5),
                    )
                  : Icon(
                      _localFav
                          ? Icons.star_rounded
                          : Icons.star_outline_rounded,
                      color: _localFav ? Colors.amber : Colors.grey.shade400,
                      size: 16,
                    ),
            ),
            if (canEdit) ...[
              const SizedBox(width: 4),
              GestureDetector(
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onTap: () => context.go('/templates/${t.id}/edit'),
                child: Icon(Icons.edit_outlined,
                    size: 15, color: Colors.blue.shade400),
              ),
            ],
            if (canDelete) ...[
              const SizedBox(width: 4),
              GestureDetector(
                onTap: () => _delete(context),
                child: Icon(Icons.delete_outline,
                    size: 15, color: Colors.red.shade400),
              ),
            ],
          ],
        );

    Widget compactActionMenu() => PopupMenuButton<String>(
          tooltip: 'Thao tác',
          onSelected: (value) {
            switch (value) {
              case 'preview':
                _previewTemplate(context);
                break;
              case 'favorite':
                _toggleFavorite();
                break;
              case 'edit':
                context.go('/templates/${t.id}/edit');
                break;
              case 'delete':
                _delete(context);
                break;
            }
          },
          itemBuilder: (_) => [
            const PopupMenuItem(
              value: 'preview',
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.preview_outlined),
                title: Text('Xem trước'),
              ),
            ),
            PopupMenuItem(
              value: 'favorite',
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  _localFav ? Icons.star_rounded : Icons.star_outline_rounded,
                  color: _localFav ? Colors.amber : null,
                ),
                title: Text(_localFav ? 'Bỏ yêu thích' : 'Đánh dấu yêu thích'),
              ),
            ),
            if (canEdit)
              const PopupMenuItem(
                value: 'edit',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.edit_outlined),
                  title: Text('Chỉnh sửa'),
                ),
              ),
            if (canDelete)
              const PopupMenuItem(
                value: 'delete',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.delete_outline, color: Colors.redAccent),
                  title: Text('Xóa mẫu'),
                ),
              ),
          ],
          child: Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: const Icon(Icons.more_horiz),
          ),
        );
    // Hiển thị danh sách tag của mẫu (giới hạn số lượng).

    Widget tagsWrap(int limit) => Wrap(
          spacing: 4,
          runSpacing: 4,
          children: t.tags
              .take(limit)
              .map((tag) => GestureDetector(
                    onTap: () {
                      final listState = context
                          .findAncestorStateOfType<_TemplateListScreenState>();
                      listState?._searchByTag(tag);
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: Colors.indigo.shade100),
                      ),
                      child: Text('#$tag',
                          style: TextStyle(
                              fontSize: 10, color: Colors.indigo.shade700)),
                    ),
                  ))
              .toList(),
        );

    if (useCompactLayout) {
      return Card(
        clipBehavior: Clip.antiAlias,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color:
                widget.selected ? Colors.blue.shade200 : Colors.grey.shade200,
          ),
        ),
        child: InkWell(
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onTap: () => context.go('/templates/${t.id}'),
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isPhone ? 12 : 10,
              vertical: isPhone ? 12 : 10,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    selectionBox(),
                    const SizedBox(width: 4),
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.file_copy_outlined,
                        size: 18,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: _HighlightText(
                                  text: t.title,
                                  query: widget.searchQuery,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                  ),
                                  maxLines: 2,
                                ),
                              ),
                              if (hasUnreadReview) ...[
                                const SizedBox(width: 6),
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: const BoxDecoration(
                                    color: Colors.redAccent,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 5),
                          RecordCodeLabel(code: t.recordCode),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _StatusChip(status: t.status),
                              _VisibilityChip(visibility: t.visibility),
                              if (t.variableCount > 0)
                                Text(
                                  '${t.variableCount} biến',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.grey.shade600,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    compactActionMenu(),
                  ],
                ),
                if (t.description.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _HighlightText(
                    text: t.description,
                    query: widget.searchQuery,
                    style: TextStyle(
                      color: Colors.grey.shade700,
                      fontSize: 12.5,
                    ),
                    maxLines: isPhone ? 3 : 2,
                  ),
                ],
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    Text(
                      t.ownerName,
                      style: TextStyle(
                          fontSize: 11.5, color: Colors.grey.shade500),
                    ),
                    if (t.effectiveDate != null && t.effectiveDate!.isNotEmpty)
                      Text(
                        t.effectiveDate!.length >= 10
                            ? t.effectiveDate!.substring(0, 10)
                            : t.effectiveDate!,
                        style: TextStyle(
                            fontSize: 11.5, color: Colors.grey.shade500),
                      ),
                  ],
                ),
                if (reviewSummary != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    reviewSummary,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: t.lastReviewAction == 'reject'
                          ? Colors.red.shade400
                          : Colors.green.shade600,
                    ),
                  ),
                ],
                if (t.tags.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  tagsWrap(isPhone ? 3 : 4),
                ],
              ],
            ),
          ),
        ),
      );
    }

    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        onTap: () => context.go('/templates/${t.id}'),
        hoverColor: Colors.blue.withOpacity(0.04),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon + Title + Status
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  selectionBox(),
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: const Icon(Icons.file_copy_outlined,
                        size: 15, color: Colors.blue),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Row(
                      children: [
                        Expanded(
                          child: _HighlightText(
                            text: t.title,
                            query: widget.searchQuery,
                            style: const TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 13),
                            maxLines: 2,
                          ),
                        ),
                        if (hasUnreadReview) ...[
                          const SizedBox(width: 6),
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Colors.redAccent,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: 4),
                  _StatusChip(status: t.status),
                ],
              ),
              const SizedBox(height: 5),
              RecordCodeLabel(code: t.recordCode, compact: true),
              // Description
              if (t.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                _HighlightText(
                  text: t.description,
                  query: widget.searchQuery,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 11.5),
                  maxLines: 2,
                ),
              ],
              // Category
              if (t.categoryName != null) ...[
                const SizedBox(height: 4),
                Row(children: [
                  Icon(Icons.label_outline,
                      size: 11, color: Colors.grey.shade400),
                  const SizedBox(width: 3),
                  Flexible(
                    child: _HighlightText(
                      text: t.categoryName!,
                      query: widget.searchQuery,
                      style:
                          TextStyle(fontSize: 11, color: Colors.grey.shade500),
                    ),
                  ),
                ]),
              ],
              const Spacer(),
              // Dates
              if (t.effectiveDate != null || t.endDate != null) ...[
                Row(children: [
                  if (t.effectiveDate != null) ...[
                    Icon(Icons.calendar_today,
                        size: 10, color: Colors.grey.shade400),
                    const SizedBox(width: 2),
                    Flexible(
                      child: Text(
                        t.effectiveDate!.length >= 10
                            ? t.effectiveDate!.substring(0, 10)
                            : t.effectiveDate!,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            fontSize: 10, color: Colors.grey.shade500),
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (t.endDate != null) ...[
                    Icon(Icons.event_busy,
                        size: 10, color: Colors.red.shade300),
                    const SizedBox(width: 2),
                    Flexible(
                      child: Text(
                        t.endDate!.length >= 10
                            ? t.endDate!.substring(0, 10)
                            : t.endDate!,
                        overflow: TextOverflow.ellipsis,
                        style:
                            TextStyle(fontSize: 10, color: Colors.red.shade300),
                      ),
                    ),
                  ],
                ]),
                const SizedBox(height: 4),
              ],
              // Tags row
              if (t.tags.isNotEmpty) ...[
                tagsWrap(3),
                const SizedBox(height: 4),
              ],
              // Footer: left=visibility+varcount, right=actions
              Row(
                children: [
                  // Left side absorbs available space
                  Expanded(
                    child: Row(
                      children: [
                        _VisibilityChip(visibility: t.visibility),
                        if (t.variableCount > 0) ...[
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              '${t.variableCount} biến',
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                  fontSize: 10.5, color: Colors.grey.shade500),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  actionRow(),
                ],
              ),
              // Owner name on separate line
              Text(
                t.ownerName,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 10, color: Colors.grey.shade400),
              ),
              if (reviewSummary != null)
                Text(
                  reviewSummary,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 10,
                    color: t.lastReviewAction == 'reject'
                        ? Colors.red.shade400
                        : Colors.green.shade500,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Chips ─────────────────────────────────────────────────────────────────

// Widget chip trạng thái duyệt của mẫu.

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  // Dựng chip trạng thái.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, color) = switch (status) {
      'approved' => (strings.ui('Đã duyệt'), Colors.green),
      'pending_leader' => (
          strings.pick('Chờ trưởng nhóm', 'Waiting for team lead'),
          Colors.amber
        ),
      'pending' => (strings.ui('Chờ duyệt'), Colors.orange),
      'rejected' => (strings.ui('Bị từ chối'), Colors.red),
      _ => (strings.ui('Bản nháp'), Colors.grey),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 10, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

// Widget chip phạm vi hiển thị của mẫu.

class _VisibilityChip extends StatelessWidget {
  final String visibility;
  const _VisibilityChip({required this.visibility});

  @override
  // Dựng chip phạm vi.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, icon, color) = switch (visibility) {
      'public' => (strings.ui('Công khai'), Icons.public, Colors.green),
      'group' => (strings.ui('Phòng ban'), Icons.group, Colors.blue),
      _ => (strings.ui('Riêng tư'), Icons.lock, Colors.grey),
    };
    return Row(children: [
      Icon(icon, size: 12, color: color),
      const SizedBox(width: 3),
      Text(label, style: TextStyle(fontSize: 11, color: color)),
    ]);
  }
}

// Widget chip lọc nhanh.

class _QuickChip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;
  final Color? color;
  final IconData? icon;
  const _QuickChip(
      {required this.label,
      required this.active,
      required this.onTap,
      this.color,
      this.icon});

  @override
  // Dựng chip lọc nhanh.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final c = color ?? Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: active ? c : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: active ? c : Colors.grey.shade300),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 13, color: active ? Colors.white : c),
              const SizedBox(width: 4),
            ],
            Text(strings.ui(label),
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  color: active ? Colors.white : Colors.grey.shade700,
                )),
          ],
        ),
      ),
    );
  }
}

// ─── Date Range Row ─────────────────────────────────────────────────────────

// Widget chọn khoảng ngày (từ - đến) trong bộ lọc.

class _DateRangeRow extends StatelessWidget {
  final String label;
  final IconData icon;
  final DateTime? from;
  final DateTime? to;
  final void Function(DateTime?) onFromPick;
  final void Function(DateTime?) onToPick;

  const _DateRangeRow({
    required this.label,
    required this.icon,
    required this.from,
    required this.to,
    required this.onFromPick,
    required this.onToPick,
  });

  // Định dạng ngày 'từ'.

  String _fmt(DateTime? d) => d == null
      ? 'Từ ngày'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  // Định dạng ngày 'đến'.

  String _fmtTo(DateTime? d) => d == null
      ? 'Đến ngày'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  // Mở lịch chọn 1 mốc ngày cho bộ lọc.

  Future<void> _pick(BuildContext context, DateTime? current,
      void Function(DateTime?) cb) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    cb(picked);
  }

  @override
  // Dựng hàng chọn khoảng ngày.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Row(
      children: [
        Icon(icon, size: 15, color: Colors.blueGrey.shade400),
        const SizedBox(width: 6),
        SizedBox(
          width: 120,
          child: Text(strings.ui(label),
              style:
                  const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500)),
        ),
        Expanded(
          child: OutlinedButton(
            onPressed: () => _pick(context, from, onFromPick),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              side: BorderSide(
                  color: from != null ? Colors.blue : Colors.grey.shade300),
            ),
            child: Text(strings.ui(_fmt(from)),
                style: TextStyle(
                    fontSize: 12,
                    color: from != null
                        ? Colors.blue.shade700
                        : Colors.grey.shade500)),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Text('→',
              style: TextStyle(color: Colors.grey.shade400, fontSize: 14)),
        ),
        Expanded(
          child: OutlinedButton(
            onPressed: () => _pick(context, to, onToPick),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              side: BorderSide(
                  color: to != null ? Colors.blue : Colors.grey.shade300),
            ),
            child: Text(strings.ui(_fmtTo(to)),
                style: TextStyle(
                    fontSize: 12,
                    color: to != null
                        ? Colors.blue.shade700
                        : Colors.grey.shade500)),
          ),
        ),
        if (from != null || to != null)
          IconButton(
            icon: Icon(Icons.clear, size: 16, color: Colors.grey.shade500),
            tooltip: strings.ui('Xóa khoảng ngày này'),
            onPressed: () {
              onFromPick(null);
              onToPick(null);
            },
          )
        else
          const SizedBox(width: 36),
      ],
    );
  }
}

// ─── Highlight Text ─────────────────────────────────────────────────────────

// Widget tô sáng phần text khớp từ khóa tìm kiếm.

class _HighlightText extends StatelessWidget {
  final String text;
  final String query;
  final TextStyle style;
  final int maxLines;

  const _HighlightText({
    required this.text,
    required this.query,
    required this.style,
    this.maxLines = 1,
  });

  @override
  // Dựng text có tô sáng đoạn khớp tìm kiếm.

  Widget build(BuildContext context) {
    if (query.isEmpty) {
      return Text(text,
          style: style, maxLines: maxLines, overflow: TextOverflow.ellipsis);
    }
    final lower = text.toLowerCase();
    final spans = <TextSpan>[];
    int start = 0;
    while (start < text.length) {
      final idx = lower.indexOf(query, start);
      if (idx < 0) {
        spans.add(TextSpan(text: text.substring(start), style: style));
        break;
      }
      if (idx > start) {
        spans.add(TextSpan(text: text.substring(start, idx), style: style));
      }
      spans.add(TextSpan(
        text: text.substring(idx, idx + query.length),
        style: style.copyWith(
          backgroundColor: Colors.yellow.shade200,
          color: Colors.black87,
          fontWeight: FontWeight.bold,
        ),
      ));
      start = idx + query.length;
    }
    return Text.rich(
      TextSpan(children: spans),
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
    );
  }
}
