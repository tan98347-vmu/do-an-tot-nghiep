// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/documents_provider.dart';
import '../../models/document.dart';
import '../../models/user.dart';
import '../../widgets/common/view_mode_toggle.dart';

// Mục đích: Lớp `_SimpleItem` triển khai phần việc `Simple Item` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _SimpleItem {
  final int id;
  final String label;
  const _SimpleItem(this.id, this.label);
}

// Mục đích: Widget `DocumentListScreen` triển khai phần việc `Document List Screen` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DocumentListScreen extends ConsumerStatefulWidget {
  final String group;
  const DocumentListScreen({super.key, required this.group});

  @override
  ConsumerState<DocumentListScreen> createState() => _DocumentListScreenState();
}

// Mục đích: Widget `_DocumentListScreenState` triển khai phần việc `Document List Screen State` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DocumentListScreenState extends ConsumerState<DocumentListScreen> {
  final _searchCtrl = TextEditingController();
  final _ownerCtrl = TextEditingController();
  Timer? _debounce;
  String _search = '';
  String _ownerQuery = '';
  String _visFilter = '';
  String _statusFilter = '';
  String _sourceFilter = '';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  DateTime? _updatedFrom;
  DateTime? _updatedTo;
  bool _showFilters = false;
  bool _showFilterPanel = false;
  String _viewMode = 'cards';
  final Set<int> _selectedDocIds = <int>{};
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
        'private' => _tr('Tên / số hiệu / mẫu nguồn của tôi',
            'My document title / number / source template'),
        'group' => _tr('Tên / số hiệu văn bản trong nhóm',
            'Group document title / number'),
        'public' => _tr('Tên / số hiệu văn bản công khai',
            'Public document title / number'),
        'favorite' => _tr('Tên / số hiệu văn bản yêu thích',
            'Favorite document title / number'),
        'archived' => _tr('Tên / số hiệu văn bản lưu trữ',
            'Archived document title / number'),
        'admin' => _tr('Tên / số hiệu văn bản trong hệ thống',
            'System document title / number'),
        _ => _tr('Tên / số hiệu văn bản', 'Document title / number'),
      };

  String _ownerFieldLabelText() =>
      _isAdminView ? _tr('Chủ sở hữu', 'Owner') : _tr('Người tạo', 'Creator');

  String _filterSummaryTextLocalized() => switch (widget.group) {
        'private' => _tr(
            'Tab này là không gian văn bản của bạn, bộ lọc ưu tiên tên, mã, trạng thái, nguồn gốc và mức chia sẻ.',
            'This is your personal document space, with filters for title, number, status, origin, and sharing level.'),
        'group' => _tr(
            'Tab này đã tách sẵn văn bản trong nhóm, bộ lọc ưu tiên tên, mã, người tạo, trạng thái và nguồn gốc.',
            'This tab focuses on group documents, with filters for title, number, creator, status, and origin.'),
        'public' => _tr(
            'Tab này đã tách sẵn văn bản công khai, bộ lọc ưu tiên tên, mã, người tạo, trạng thái và nguồn gốc.',
            'This tab focuses on public documents, with filters for title, number, creator, status, and origin.'),
        'favorite' => _tr(
            'Tab này là danh sách yêu thích, bộ lọc ưu tiên tên, mã, người tạo, trạng thái, nguồn gốc và mức chia sẻ.',
            'This is your favorites list, with filters for title, number, creator, status, origin, and sharing level.'),
        'archived' => _tr(
            'Tab này là kho lưu trữ, bộ lọc ưu tiên tên, mã, người tạo, trạng thái và mức chia sẻ.',
            'This is your archive, with filters for title, number, creator, status, and sharing level.'),
        'admin' => _tr(
            'Tab này dành cho quản trị, bộ lọc ưu tiên tên, mã, chủ sở hữu, phòng ban, trạng thái và nguồn gốc.',
            'This admin tab focuses on title, number, owner, department, status, and origin filters.'),
        _ => _tr('Dùng bộ lọc theo thuộc tính để khoanh đúng văn bản cần tìm.',
            'Use the attribute filters to narrow down the right documents.'),
      };

  String _groupTitleText() => switch (widget.group) {
        'private' => _tr('Văn bản của tôi', 'My documents'),
        'group' => _tr('Đã chia sẻ trong nhóm', 'Shared in my groups'),
        'public' => _tr('Đã chia sẻ công khai', 'Publicly shared documents'),
        'favorite' => _tr('Văn bản yêu thích', 'Favorite documents'),
        'peer' => _tr('Văn bản chia sẻ cho đồng nghiệp', 'Documents shared with me'),
        'archived' => _tr('Đã lưu trữ', 'Archived documents'),
        'admin' => _tr('Tất cả văn bản (Admin)', 'All documents (Admin)'),
        _ => _tr('Quản lý văn bản', 'Document management'),
      };

  String _groupSubtitleText() => switch (widget.group) {
        'private' => _tr(
            'Theo dõi các văn bản riêng của bạn và tải lên tài liệu Word mới',
            'Track your private documents and upload new Word files'),
        'group' => _tr(
            'Những văn bản đang được chia sẻ trong các nhóm bạn tham gia',
            'Documents shared inside the groups you belong to'),
        'public' => _tr('Các văn bản được chia sẻ công khai trong hệ thống',
            'Documents publicly shared across the system'),
        'favorite' => _tr('Danh sách văn bản bạn đã đánh dấu yêu thích',
            'Documents you bookmarked as favorites'),
        'peer' => _tr(
            'Văn bản được đồng nghiệp chia sẻ riêng cho bạn',
            'Documents peers shared directly with you'),
        'archived' =>
          _tr('Các văn bản bạn đã lưu trữ', 'Documents you archived'),
        'admin' => _tr('Xem và quản lý toàn bộ văn bản của người dùng',
            'Browse and manage every document in the system'),
        _ =>
          _tr('Các văn bản bạn có quyền truy cập', 'Documents you can access'),
      };

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

    final user = ref.read(currentUserProvider);
    if (user?.isSuperuser == true) _loadAdminFilterData();
  }

  // Mục đích: Phương thức `_loadAdminFilterData` triển khai phần việc `load Admin Filter Data` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _searchCtrl.dispose();
    _ownerCtrl.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  // Mục đích: Phương thức `_onSearchChanged` triển khai phần việc `on Search Changed` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  String get _serverSearchQuery => _search.trim();

  // Mục đích: Phương thức `_showUploadDocxDialog` triển khai phần việc `show Upload Docx Dialog` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _showUploadDocxDialog() async {
    final titleCtrl = TextEditingController();
    PlatformFile? pickedFile;
    bool uploading = false;
    String? uploadError;

    final uploaded = await showDialog<bool>(
      context: context,
      barrierDismissible: !uploading,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx2, setS) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.upload_file, color: Colors.teal),
              SizedBox(width: 8),
              Text('Upload văn bản Word'),
            ],
          ),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'File Word sẽ được lưu vào "Văn bản của tôi" (riêng tư).',
                  style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                ),
                const SizedBox(height: 16),
                // Chọn file
                OutlinedButton.icon(
                  onPressed: uploading
                      ? null
                      : () async {
                          final result = await FilePicker.platform.pickFiles(
                            type: FileType.custom,
                            allowedExtensions: ['docx'],
                            withData: true,
                          );
                          if (result != null && result.files.isNotEmpty) {
                            setS(() {
                              pickedFile = result.files.first;
                              uploadError = null;
                            });
                          }
                        },
                  icon: const Icon(Icons.folder_open_outlined),
                  label: Text(pickedFile == null
                      ? 'Chọn file .docx'
                      : pickedFile!.name),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(
                      color: pickedFile != null
                          ? Colors.teal
                          : Colors.grey.shade400,
                      width: pickedFile != null ? 1.5 : 1,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                // Tiêu đề
                TextField(
                  controller: titleCtrl,
                  enabled: !uploading,
                  decoration: const InputDecoration(
                    labelText: 'Tiêu đề văn bản *',
                    hintText: 'Để trống sẽ lấy tên file',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                // Lỗi
                if (uploadError != null) ...[
                  const SizedBox(height: 10),
                  Text(uploadError!,
                      style:
                          const TextStyle(color: Colors.red, fontSize: 12.5)),
                ],
                if (uploading) ...[
                  const SizedBox(height: 14),
                  const Row(
                    children: [
                      SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2)),
                      SizedBox(width: 10),
                      Text('Đang upload...', style: TextStyle(fontSize: 13)),
                    ],
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: uploading ? null : () => Navigator.pop(ctx),
              child: const Text('Hủy'),
            ),
            FilledButton.icon(
              onPressed: (uploading || pickedFile == null)
                  ? null
                  : () async {
                      if (pickedFile!.bytes == null) {
                        setS(() => uploadError = 'Không đọc được file.');
                        return;
                      }
                      final title = titleCtrl.text.trim().isNotEmpty
                          ? titleCtrl.text.trim()
                          : pickedFile!.name.replaceAll(
                              RegExp(r'\.docx$', caseSensitive: false), '');
                      setS(() {
                        uploading = true;
                        uploadError = null;
                      });
                      try {
                        final formData = FormData.fromMap({
                          'title': title,
                          'docx_file': MultipartFile.fromBytes(
                              pickedFile!.bytes!,
                              filename: pickedFile!.name),
                          'visibility': 'private',
                        });
                        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

                        await ApiClient()
                            .dio
                            .post('documents/upload/', data: formData);
                        if (ctx.mounted) Navigator.pop(ctx, true);
                      } catch (e) {
                        setS(() {
                          uploading = false;
                          uploadError = 'Lỗi upload: $e';
                        });
                      }
                    },
              icon: const Icon(Icons.cloud_upload_outlined, size: 16),
              label: const Text('Upload'),
              style: FilledButton.styleFrom(backgroundColor: Colors.teal),
            ),
          ],
        ),
      ),
    );

    titleCtrl.dispose();
    if (mounted && uploaded == true) {
      refreshDocumentCollections(ref);
    }
  }

  // Mục đích: Phương thức `_resetFilters` triển khai phần việc `reset Filters` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _resetFilters() {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _searchCtrl.clear();
      _ownerCtrl.clear();
      _search = '';
      _ownerQuery = '';
      _visFilter = '';
      _statusFilter = '';
      _sourceFilter = '';
      _dateFrom = null;
      _dateTo = null;
      _updatedFrom = null;
      _updatedTo = null;
      _adminOwnerIdFilter = '';
      _adminGroupIdFilter = '';
    });
  }

  // Mục đích: Phương thức `_hasActiveFilter` triển khai phần việc `has Active Filter` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _hasActiveFilter() =>
      _search.isNotEmpty ||
      _ownerQuery.isNotEmpty ||
      _visFilter.isNotEmpty ||
      _statusFilter.isNotEmpty ||
      _sourceFilter.isNotEmpty ||
      _dateFrom != null ||
      _dateTo != null ||
      _updatedFrom != null ||
      _updatedTo != null ||
      _adminOwnerIdFilter.isNotEmpty ||
      _adminGroupIdFilter.isNotEmpty;

  int get _activeFilterCount {
    var count = 0;
    if (_search.isNotEmpty) count++;
    if (_ownerQuery.isNotEmpty) count++;
    if (_visFilter.isNotEmpty) count++;
    if (_statusFilter.isNotEmpty) count++;
    if (_sourceFilter.isNotEmpty) count++;
    if (_dateFrom != null || _dateTo != null) count++;
    if (_updatedFrom != null || _updatedTo != null) count++;
    if (_adminOwnerIdFilter.isNotEmpty) count++;
    if (_adminGroupIdFilter.isNotEmpty) count++;
    return count;
  }

  // Mục đích: Phương thức `_matchDate` triển khai phần việc `match Date` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  List<Document> _filter(List<Document> all) {
    return all.where((d) {
      if (_visFilter.isNotEmpty && d.visibility != _visFilter) return false;
      if (_statusFilter.isNotEmpty && d.status != _statusFilter) return false;
      if (_sourceFilter.isNotEmpty && d.sourceType != _sourceFilter)
        return false;
      if (_ownerQuery.isNotEmpty &&
          !d.ownerName.toLowerCase().contains(_ownerQuery)) {
        return false;
      }
      if (!_matchDate(d.createdAt, _dateFrom, _dateTo)) return false;
      if (!_matchDate(d.updatedAt, _updatedFrom, _updatedTo)) return false;
      return true;
    }).toList();
  }

  bool get _isAdminView => widget.group == 'admin';
  bool get _showVisibilityFilter =>
      _isAdminView ||
      widget.group == 'private' ||
      widget.group == 'favorite' ||
      widget.group == 'archived';
  bool get _showOwnerFilter => widget.group != 'private';

  String get _searchFieldLabel => switch (widget.group) {
        'private' => 'Tên / số hiệu / mẫu nguồn của tôi',
        'group' => 'Tên / số hiệu văn bản trong nhóm',
        'public' => 'Tên / số hiệu văn bản công khai',
        'favorite' => 'Tên / số hiệu văn bản yêu thích',
        'archived' => 'Tên / số hiệu văn bản lưu trữ',
        'admin' => 'Tên / số hiệu văn bản trong hệ thống',
        _ => 'Tên / số hiệu văn bản',
      };

  String get _ownerFieldLabel =>
      _isAdminView ? 'Chủ sở hữu' : 'Người tạo';

  String get _filterSummaryText => switch (widget.group) {
        'private' =>
          'Tab này đã là không gian văn bản của bạn, bộ lọc ưu tiên tên mã, trạng thái, nguồn gốc và mức chia sẻ.',
        'group' =>
          'Tab này đã tách sẵn văn bản trong nhóm, bộ lọc ưu tiên tên mã, người tạo, trạng thái và nguồn gốc.',
        'public' =>
          'Tab này đã tách sẵn văn bản công khai, bộ lọc ưu tiên tên mã, người tạo, trạng thái và nguồn gốc.',
        'favorite' =>
          'Tab này đã là danh sách yêu thích, bộ lọc ưu tiên tên mã, người tạo, trạng thái, nguồn gốc và mức chia sẻ.',
        'archived' =>
          'Tab này đã là kho lưu trữ, bộ lọc ưu tiên tên mã, người tạo, trạng thái và mức chia sẻ.',
        'admin' =>
          'Tab này dành cho quản trị, bộ lọc ưu tiên tên mã, chủ sở hữu, phòng ban, trạng thái và nguồn gốc.',
        _ =>
          'Dùng bộ lọc theo thuộc tính để khoanh đúng văn bản cần tìm.',
      };

  // Mục đích: Phương thức `_canDeleteDocument` triển khai phần việc `can Delete Document` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _canDeleteDocument(Document d, AppUser? user) {
    return d.canDelete;
  }

  DocumentCollectionParams get _collectionParams => DocumentCollectionParams(
        group: widget.group,
        q: _serverSearchQuery,
        admin: _isAdminView,
        ownerId: _adminOwnerIdFilter,
        groupId: _adminGroupIdFilter,
      );

  // Mục đích: Phương thức `_refreshDocuments` triển khai phần việc `refresh Documents` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _refreshDocuments() {
    ref.invalidate(documentCollectionProvider(_collectionParams));
  }

  // Mục đích: Phương thức `_toggleDocumentSelection` triển khai phần việc `toggle Document Selection` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _toggleDocumentSelection(int id, bool selected) {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      if (selected) {
        _selectedDocIds.add(id);
      } else {
        _selectedDocIds.remove(id);
      }
    });
  }

  // Mục đích: Phương thức `_toggleSelectAllDocuments` triển khai phần việc `toggle Select All Documents` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _toggleSelectAllDocuments(List<Document> filtered, AppUser? user) {
    final deletableIds = filtered
        .where((d) => _canDeleteDocument(d, user))
        .map((d) => d.id)
        .toSet();
    if (deletableIds.isEmpty) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      final alreadyAllSelected = deletableIds.every(_selectedDocIds.contains);
      if (alreadyAllSelected) {
        _selectedDocIds.removeAll(deletableIds);
      } else {
        _selectedDocIds.addAll(deletableIds);
      }
    });
  }

  // Mục đích: Phương thức `_bulkDeleteDocuments` triển khai phần việc `bulk Delete Documents` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _bulkDeleteDocuments(BuildContext context) async {
    if (_selectedDocIds.isEmpty || _bulkDeleting) return;

    final count = _selectedDocIds.length;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xóa hàng loạt'),
        content: Text('Bạn có chắc muốn xóa $count văn bản đã chọn?'),
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
    final ids = _selectedDocIds.toList();

    for (final id in ids) {
      try {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        await ApiClient().dio.delete('documents/$id/');
        successCount++;
      } catch (_) {
        failedCount++;
      }
    }

    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _bulkDeleting = false;
      _selectedDocIds.clear();
    });
    refreshDocumentCollections(ref);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          failedCount == 0
              ? 'Đã xóa $successCount văn bản.'
              : 'Đã xóa $successCount văn bản, lỗi $failedCount văn bản.',
        ),
        backgroundColor: failedCount == 0 ? Colors.green : Colors.orange,
      ),
    );
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final currentUser = ref.watch(currentUserProvider);
    final isSuperuser = currentUser?.isSuperuser ?? false;
    final strings = AppStrings.of(context);
    final groupTitle = _groupTitleText();
    final groupSubtitle = _groupSubtitleText();
    final isMobile = MediaQuery.sizeOf(context).width < 760;
    final filterFieldWidth =
        isMobile ? MediaQuery.sizeOf(context).width - 56 : 240.0;
    final compactFieldWidth =
        isMobile ? MediaQuery.sizeOf(context).width - 56 : 190.0;
    final effectiveViewMode = isMobile ? 'compact_list' : _viewMode;

    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final asyncDocs = ref.watch(documentCollectionProvider(_collectionParams));

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
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
              // Nút Upload Word — chỉ hiện trong tab "Văn bản của tôi"
              if (widget.group == 'private')
                FilledButton.icon(
                  onPressed: _showUploadDocxDialog,
                  icon: const Icon(Icons.upload_file, size: 16),
                  label: Text(strings.pick('Tải lên Word', 'Upload Word')),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.teal,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10),
                  ),
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
                        const Icon(Icons.manage_search_rounded,
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
                                'Lọc theo tên, số hiệu hoặc mẫu nguồn',
                                'Filter by title, number or source template',
                              ),
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
                              labelText: strings.ui('Trạng thái'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                              prefixIcon:
                                  const Icon(Icons.fact_check, size: 16),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'final',
                                  child: Text(strings.ui('Chính thức'))),
                              DropdownMenuItem(
                                  value: 'draft',
                                  child: Text(strings.ui('Bản nháp'))),
                              DropdownMenuItem(
                                  value: 'archived',
                                  child: Text(strings.ui('Lưu trữ'))),
                            ],
                            onChanged: (v) =>
                                setState(() => _statusFilter = v ?? ''),
                          ),
                        ),
                        SizedBox(
                          width: compactFieldWidth,
                          child: DropdownButtonFormField<String>(
                            value: _sourceFilter.isEmpty ? null : _sourceFilter,
                            decoration: InputDecoration(
                              labelText: strings.ui('Nguồn gốc'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                              prefixIcon: const Icon(Icons.source, size: 16),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'generated',
                                  child: Text(strings.ui('Sinh bởi AI'))),
                              DropdownMenuItem(
                                  value: 'uploaded',
                                  child: Text(
                                      strings.ui('Tải lên thủ công'))),
                            ],
                            onChanged: (v) =>
                                setState(() => _sourceFilter = v ?? ''),
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
                                    child: Text(strings.ui('Tất cả'))),
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
                                  'Type owner name to filter',
                                ),
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

          // Search bar
          Visibility(
            visible: false,
            maintainState: true,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: strings.documentSearchHint(widget.group),
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
                  TextButton.icon(
                    onPressed: _resetFilters,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: Text(strings.pick('Xóa bộ lọc', 'Clear filters')),
                    style: TextButton.styleFrom(foregroundColor: Colors.red),
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
                    Row(
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
                        // Mức chia sẻ
                        SizedBox(
                          width: 200,
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
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'public',
                                  child: Row(children: [
                                    const Icon(Icons.public,
                                        size: 14, color: Colors.green),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Công khai'))
                                  ])),
                              DropdownMenuItem(
                                  value: 'group',
                                  child: Row(children: [
                                    const Icon(Icons.group,
                                        size: 14, color: Colors.blue),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Phòng ban'))
                                  ])),
                              DropdownMenuItem(
                                  value: 'private',
                                  child: Row(children: [
                                    const Icon(Icons.lock,
                                        size: 14, color: Colors.grey),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Riêng tư'))
                                  ])),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _visFilter = v ?? ''),
                          ),
                        ),
                        // Trạng thái
                        SizedBox(
                          width: 200,
                          child: DropdownButtonFormField<String>(
                            value: _statusFilter.isEmpty ? null : _statusFilter,
                            decoration: InputDecoration(
                              labelText: strings.ui('Trạng thái'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                              prefixIcon:
                                  const Icon(Icons.fact_check, size: 16),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'final',
                                  child: Row(children: [
                                    const Icon(Icons.verified,
                                        size: 14, color: Colors.green),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Chính thức'))
                                  ])),
                              DropdownMenuItem(
                                  value: 'draft',
                                  child: Row(children: [
                                    const Icon(Icons.edit,
                                        size: 14, color: Colors.orange),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Bản nháp'))
                                  ])),
                              DropdownMenuItem(
                                  value: 'archived',
                                  child: Row(children: [
                                    const Icon(Icons.archive,
                                        size: 14, color: Colors.grey),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Lưu trữ'))
                                  ])),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _statusFilter = v ?? ''),
                          ),
                        ),
                        // Loại nguồn
                        SizedBox(
                          width: 200,
                          child: DropdownButtonFormField<String>(
                            value: _sourceFilter.isEmpty ? null : _sourceFilter,
                            decoration: InputDecoration(
                              labelText: strings.ui('Nguồn gốc'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                              prefixIcon: const Icon(Icons.source, size: 16),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'generated',
                                  child: Row(children: [
                                    const Icon(Icons.auto_awesome,
                                        size: 14, color: Colors.purple),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Sinh bởi AI'))
                                  ])),
                              DropdownMenuItem(
                                  value: 'uploaded',
                                  child: Row(children: [
                                    const Icon(Icons.upload_file,
                                        size: 14, color: Colors.teal),
                                    const SizedBox(width: 6),
                                    Text(strings.ui('Upload thủ công'))
                                  ])),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _sourceFilter = v ?? ''),
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
                    _DateRangeRow(
                      label: 'Cập nhật',
                      icon: Icons.update,
                      from: _updatedFrom, to: _updatedTo,
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onFromPick: (d) => setState(() => _updatedFrom = d),
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onToPick: (d) => setState(() => _updatedTo = d),
                    ),
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
                    active: _visFilter.isEmpty &&
                        _statusFilter.isEmpty &&
                        _sourceFilter.isEmpty,
                    onTap: () => setState(() {
                      _visFilter = '';
                      _statusFilter = '';
                      _sourceFilter = '';
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
                  if (widget.group != 'archived') ...[
                    const SizedBox(width: 6),
                    _QuickChip(
                      label: 'Chính thức',
                      icon: Icons.verified,
                      color: Colors.green,
                      active: _statusFilter == 'final',
                      onTap: () => setState(
                        () => _statusFilter =
                            _statusFilter == 'final' ? '' : 'final',
                      ),
                    ),
                    const SizedBox(width: 6),
                    _QuickChip(
                      label: 'Bản nháp',
                      icon: Icons.edit,
                      color: Colors.orange,
                      active: _statusFilter == 'draft',
                      onTap: () => setState(
                        () => _statusFilter =
                            _statusFilter == 'draft' ? '' : 'draft',
                      ),
                    ),
                  ],
                  const SizedBox(width: 6),
                  _QuickChip(
                    label: 'Sinh bởi AI',
                    icon: Icons.auto_awesome,
                    color: Colors.purple,
                    active: _sourceFilter == 'generated',
                    onTap: () => setState(
                      () => _sourceFilter =
                          _sourceFilter == 'generated' ? '' : 'generated',
                    ),
                  ),
                  const SizedBox(width: 6),
                  _QuickChip(
                    label: 'Tải lên Word',
                    icon: Icons.upload_file,
                    color: Colors.teal,
                    active: _sourceFilter == 'uploaded',
                    onTap: () => setState(
                      () => _sourceFilter =
                          _sourceFilter == 'uploaded' ? '' : 'uploaded',
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
                    active: _visFilter.isEmpty &&
                        _statusFilter.isEmpty &&
                        _sourceFilter.isEmpty,
                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                    onTap: () => setState(() {
                      _visFilter = '';
                      _statusFilter = '';
                      _sourceFilter = '';
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
                      label: 'Chính thức',
                      icon: Icons.verified,
                      color: Colors.green,
                      active: _statusFilter == 'final',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _statusFilter =
                          _statusFilter == 'final' ? '' : 'final')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Bản nháp',
                      icon: Icons.edit,
                      color: Colors.orange,
                      active: _statusFilter == 'draft',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _statusFilter =
                          _statusFilter == 'draft' ? '' : 'draft')),
                  const SizedBox(width: 6),
                  _QuickChip(
                      label: 'Sinh bởi AI',
                      icon: Icons.auto_awesome,
                      color: Colors.purple,
                      active: _sourceFilter == 'generated',
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _sourceFilter =
                          _sourceFilter == 'generated' ? '' : 'generated')),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          // Results
          Expanded(
            child: asyncDocs.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Text('${strings.pick('Lỗi', 'Error')}: $e'),
              ),
              data: (docs) {
                final filtered = _filter(docs);
                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.search_off,
                            size: 64, color: Colors.grey.shade300),
                        const SizedBox(height: 12),
                        Text(
                            strings.pick('Không tìm thấy văn bản nào.',
                                'No documents found.'),
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
                final deletableDocs = filtered
                    .where((d) => _canDeleteDocument(d, currentUser))
                    .toList();
                final allVisibleSelected = deletableDocs.isNotEmpty &&
                    deletableDocs.every((d) => _selectedDocIds.contains(d.id));
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
                                    'Tìm thấy ${filtered.length} văn bản',
                                    'Found ${filtered.length} documents',
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
                            onPressed: deletableDocs.isEmpty
                                ? null
                                : () => _toggleSelectAllDocuments(
                                    filtered, currentUser),
                            icon: Icon(
                              allVisibleSelected
                                  ? Icons.check_box_rounded
                                  : Icons.check_box_outline_blank_rounded,
                              size: 18,
                            ),
                            label: Text(allVisibleSelected
                                ? strings.pick('Bỏ chọn tất cả', 'Clear selection')
                                : strings.pick('Chọn tất cả', 'Select all')),
                          ),
                          if (_selectedDocIds.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            Text(
                              strings.pick(
                                'Đã chọn ${_selectedDocIds.length}',
                                'Selected ${_selectedDocIds.length}',
                              ),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: Colors.blueGrey.shade700,
                              ),
                            ),
                            TextButton(
                              onPressed: () =>
                                  setState(() => _selectedDocIds.clear()),
                              child: Text(strings.pick('Bỏ chọn', 'Clear')),
                            ),
                          ],
                          const SizedBox(width: 8),
                          ViewModeToggle(
                            value: _viewMode,
                            onChanged: (value) => setState(() => _viewMode = value),
                            cardLabel: strings.ui('Dạng thẻ'),
                            listLabel: strings.ui('Dạng danh sách'),
                          ),
                          if (_selectedDocIds.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            FilledButton.icon(
                              onPressed: _bulkDeleting
                                  ? null
                                  : () => _bulkDeleteDocuments(context),
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
                    if (isMobile && _selectedDocIds.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.grey.shade200),
                        ),
                        child: Row(
                          children: [
                            OutlinedButton.icon(
                              onPressed: deletableDocs.isEmpty
                                  ? null
                                  : () => _toggleSelectAllDocuments(
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
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _selectedDocIds.isEmpty
                                    ? strings.pick('Chưa chọn văn bản nào',
                                        'No documents selected')
                                    : strings.pick(
                                        'Đã chọn ${_selectedDocIds.length} văn bản',
                                        'Selected ${_selectedDocIds.length} documents',
                                      ),
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.blueGrey.shade700,
                                ),
                              ),
                            ),
                            if (_selectedDocIds.isNotEmpty)
                              TextButton(
                                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                onPressed: () =>
                                    setState(() => _selectedDocIds.clear()),
                                child: Text(strings.pick('Bỏ chọn', 'Clear')),
                              ),
                            const SizedBox(width: 8),
                            FilledButton.icon(
                              onPressed:
                                  _selectedDocIds.isEmpty || _bulkDeleting
                                      ? null
                                      : () => _bulkDeleteDocuments(context),
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
                        ),
                      ),
                    const SizedBox(height: 10),
                    Expanded(
                      child: effectiveViewMode == 'cards'
                          ? GridView.builder(
                              gridDelegate:
                                  const SliverGridDelegateWithMaxCrossAxisExtent(
                                maxCrossAxisExtent: 340,
                                childAspectRatio: 1.4,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: filtered.length,
                              itemBuilder: (_, i) => _DocCard(
                                doc: filtered[i],
                                searchQuery: _search,
                                currentUser: currentUser,
                                selected:
                                    _selectedDocIds.contains(filtered[i].id),
                                selectionEnabled: _canDeleteDocument(
                                    filtered[i], currentUser),
                                onSelectedChanged: (selected) =>
                                    _toggleDocumentSelection(
                                        filtered[i].id, selected ?? false),
                                onRefresh: _refreshDocuments,
                              ),
                            )
                          : ListView.separated(
                              itemCount: filtered.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (_, i) => _DocCard(
                                doc: filtered[i],
                                searchQuery: _search,
                                currentUser: currentUser,
                                compact: true,
                                selected:
                                    _selectedDocIds.contains(filtered[i].id),
                                selectionEnabled: _canDeleteDocument(
                                    filtered[i], currentUser),
                                onSelectedChanged: (selected) =>
                                    _toggleDocumentSelection(
                                        filtered[i].id, selected ?? false),
                                onRefresh: _refreshDocuments,
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

  String get _resolvedGroupTitle => switch (widget.group) {
        'private' => 'Van ban cua toi',
        'group' => 'Van ban chia se trong nhom',
        'public' => 'Van ban chia se cong khai',
        'favorite' => 'Van ban yeu thich',
        'archived' => 'Van ban da luu tru',
        'admin' => 'Tat ca van ban (Admin)',
        _ => 'Tat ca van ban',
      };

  String get _resolvedGroupSubtitle => switch (widget.group) {
        'private' =>
          'Tat ca van ban do ban tao ra, bat ke dang de rieng tu, phong ban hay cong khai',
        'group' => 'Van ban dang chia se voi nhung nguoi trong cung nhom',
        'public' =>
          'Van ban da duoc phe duyet va chia se voi toan bo nguoi dung',
        'favorite' => 'Cac van ban ban da danh dau yeu thich',
        'archived' => 'Van ban da duoc chuyen vao luu tru',
        'admin' => 'Xem va quan ly tat ca van ban cua moi nguoi dung',
        _ => 'Tat ca van ban ban co quyen truy cap',
      };

  String get _groupTitle => switch (widget.group) {
        'private' => 'Văn bản đã được tạo bởi người dùng',
        'group' => 'Văn bản đã được chia sẻ trong nhóm',
        'public' =>
          'Văn bản đã được chia sẻ với tất cả mọi người',
        'favorite' => 'Văn bản yêu thích',
        'archived' => 'Văn bản đã lưu trữ',
        'admin' => 'Tất cả văn bản (Admin)',
        _ => 'Tất cả văn bản',
      };

  String get _groupSubtitle => switch (widget.group) {
        'private' => 'Những văn bản riêng do bạn tạo ra',
        'group' =>
          'Văn bản đã được chia sẻ với những người trong cùng nhóm',
        'public' =>
          'Văn bản đã được phê duyệt và chia sẻ với toàn bộ người dùng',
        'favorite' => 'Các văn bản bạn đã đánh dấu yêu thích',
        'archived' => 'Văn bản đã được chuyển vào lưu trữ',
        'admin' =>
          'Xem và quản lý tất cả văn bản của mọi người dùng',
        _ => 'Tất cả văn bản bạn có quyền truy cập',
      };
}

// ─── Card ──────────────────────────────────────────────────────────────────

// Mục đích: Lớp `_DocCard` triển khai phần việc `Doc Card` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DocCard extends ConsumerWidget {
  final Document doc;
  final String searchQuery;
  final AppUser? currentUser;
  final VoidCallback onRefresh;
  final bool compact;
  final bool selected;
  final bool selectionEnabled;
  final ValueChanged<bool?> onSelectedChanged;

  const _DocCard({
    required this.doc,
    required this.searchQuery,
    required this.currentUser,
    required this.onRefresh,
    this.compact = false,
    required this.selected,
    required this.selectionEnabled,
    required this.onSelectedChanged,
  });

  // Mục đích: Phương thức `_canDelete` triển khai phần việc `can Delete` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _canDelete(Document d, AppUser? user) {
    return d.canDelete;
  }

  // Mục đích: Phương thức `_refreshCollections` triển khai phần việc `refresh Collections` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _refreshCollections(WidgetRef ref) {
    refreshDocumentCollections(ref);
  }

  // Mục đích: Phương thức `_delete` triển khai phần việc `delete` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xóa'),
        content: Text(
            'Bạn có chắc muốn xóa văn bản "${doc.title}"?\nHành động này không thể hoàn tác.'),
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
    if (ok != true || !context.mounted) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.delete('documents/${doc.id}/');
      _refreshCollections(ref);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Đã xóa văn bản.'),
              backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Lỗi xóa: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  // Mục đích: Phương thức `_archive` triển khai phần việc `archive` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _archive(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Lưu trữ văn bản'),
        content: Text('Bạn có chắc muốn lưu trữ văn bản "${doc.title}"?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Hủy')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.orange),
            child: const Text('Lưu trữ'),
          ),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${doc.id}/archive/');
      _refreshCollections(ref);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Đã lưu trữ văn bản.'),
              backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Lỗi lưu trữ: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
  }

  // Mục đích: Phương thức `_toggleFavorite` triển khai phần việc `toggle Favorite` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _toggleFavorite(BuildContext context, WidgetRef ref) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${doc.id}/favorite/');
      _refreshCollections(ref);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Lỗi yêu thích: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    final canDelete = _canDelete(doc, currentUser);
    final isPhone = MediaQuery.sizeOf(context).width < 760;
    final useCompactLayout = compact || isPhone;
    // Mục đích: Phương thức `selectionBox` triển khai phần việc `selection Box` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget selectionBox() => Checkbox(
          value: selected,
          onChanged: selectionEnabled ? onSelectedChanged : null,
          visualDensity: VisualDensity.compact,
        );
    // Mục đích: Phương thức `actionRow` triển khai phần việc `action Row` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget actionRow() => Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            GestureDetector(
              onTap: () => _toggleFavorite(context, ref),
              child: Icon(
                doc.isFavorite
                    ? Icons.star_rounded
                    : Icons.star_outline_rounded,
                size: 16,
                color: doc.isFavorite
                    ? Colors.amber.shade600
                    : Colors.grey.shade400,
              ),
            ),
            const SizedBox(width: 4),
            if (currentUser?.id == doc.ownerId &&
                doc.visibility == 'private' &&
                !doc.isArchived) ...[
              GestureDetector(
                onTap: () => _archive(context, ref),
                child: Icon(Icons.archive_outlined,
                    size: 16, color: Colors.orange.shade400),
              ),
              const SizedBox(width: 4),
            ],
            if (canDelete)
              GestureDetector(
                onTap: () => _delete(context, ref),
                child: Icon(Icons.delete_outline,
                    size: 16, color: Colors.red.shade400),
              ),
          ],
        );

    Widget compactActionMenu() => PopupMenuButton<String>(
          tooltip: 'Thao tác',
          onSelected: (value) {
            switch (value) {
              case 'favorite':
                _toggleFavorite(context, ref);
                break;
              case 'archive':
                _archive(context, ref);
                break;
              case 'delete':
                _delete(context, ref);
                break;
            }
          },
          itemBuilder: (_) => [
            PopupMenuItem(
              value: 'favorite',
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  doc.isFavorite
                      ? Icons.star_rounded
                      : Icons.star_outline_rounded,
                  color: doc.isFavorite ? Colors.amber.shade600 : null,
                ),
                title: Text(doc.isFavorite
                    ? 'Bỏ yêu thích'
                    : 'Đánh dấu yêu thích'),
              ),
            ),
            if (currentUser?.id == doc.ownerId &&
                doc.visibility == 'private' &&
                !doc.isArchived)
              const PopupMenuItem(
                value: 'archive',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.archive_outlined),
                  title: Text('Lưu trữ'),
                ),
              ),
            if (canDelete)
              const PopupMenuItem(
                value: 'delete',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.delete_outline, color: Colors.redAccent),
                  title: Text('Xóa văn bản'),
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

    if (useCompactLayout) {
      return Card(
        clipBehavior: Clip.antiAlias,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: selected ? Colors.blue.shade200 : Colors.grey.shade200,
          ),
        ),
        child: InkWell(
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onTap: () => context.go('/documents/${doc.id}'),
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
                        color: _sourceColor(doc.sourceType).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        _sourceIcon(doc.sourceType),
                        size: 18,
                        color: _sourceColor(doc.sourceType),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _HighlightText(
                            text: doc.title,
                            query: searchQuery,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                            maxLines: 2,
                          ),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _StatusChip(status: doc.status),
                              _VisChip(visibility: doc.visibility),
                              _SigningChip(status: doc.signingStatus),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    compactActionMenu(),
                  ],
                ),
                if (doc.docNumber != null && doc.docNumber!.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _HighlightText(
                    text: '#${doc.docNumber!}',
                    query: searchQuery,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
                if (doc.templateTitle != null &&
                    doc.templateTitle!.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  _HighlightText(
                    text: 'Mẫu: ${doc.templateTitle!}',
                    query: searchQuery,
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
                    maxLines: 2,
                  ),
                ],
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    Text(
                      doc.ownerName,
                      style: TextStyle(
                          fontSize: 11.5, color: Colors.grey.shade500),
                    ),
                    Text(
                      doc.updatedAt.length >= 10
                          ? doc.updatedAt.substring(0, 10)
                          : doc.updatedAt,
                      style: TextStyle(
                          fontSize: 11.5, color: Colors.grey.shade500),
                    ),
                  ],
                ),
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

        onTap: () => context.go('/documents/${doc.id}'),
        hoverColor: Colors.blue.withOpacity(0.04),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon + Title
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  selectionBox(),
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: _sourceColor(doc.sourceType).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: Icon(_sourceIcon(doc.sourceType),
                        size: 15, color: _sourceColor(doc.sourceType)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _HighlightText(
                      text: doc.title,
                      query: searchQuery,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 13),
                      maxLines: 2,
                    ),
                  ),
                ],
              ),
              // Doc number
              if (doc.docNumber != null && doc.docNumber!.isNotEmpty) ...[
                const SizedBox(height: 4),
                _HighlightText(
                  text: '#${doc.docNumber!}',
                  query: searchQuery,
                  style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      fontSize: 11,
                      fontWeight: FontWeight.w500),
                ),
              ],
              // Template name
              if (doc.templateTitle != null) ...[
                const SizedBox(height: 3),
                _HighlightText(
                  text: 'Mẫu: ${doc.templateTitle!}',
                  query: searchQuery,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 11),
                ),
              ],
              // Notes
              if (doc.notes != null && doc.notes!.isNotEmpty) ...[
                const SizedBox(height: 3),
                _HighlightText(
                  text: doc.notes!,
                  query: searchQuery,
                  style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                  maxLines: 2,
                ),
              ],
              const Spacer(),
              // Footer
              Row(
                children: [
                  _StatusChip(status: doc.status),
                  const SizedBox(width: 5),
                  _SigningChip(status: doc.signingStatus),
                  const SizedBox(width: 5),
                  _VisChip(visibility: doc.visibility),
                  const Spacer(),
                  // Owner name (for admin view)
                  if (currentUser?.isSuperuser == true)
                    Flexible(
                      child: Text(
                        doc.ownerName,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            fontSize: 10, color: Colors.grey.shade400),
                      ),
                    ),
                  actionRow(),
                  const SizedBox(width: 4),
                  Text(
                    doc.updatedAt.length >= 10
                        ? doc.updatedAt.substring(0, 10)
                        : doc.updatedAt,
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 10),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _sourceIcon(String? src) => switch (src) {
        'generated' => Icons.auto_awesome,
        'uploaded' => Icons.upload_file,
        _ => Icons.description_outlined,
      };

  Color _sourceColor(String? src) => switch (src) {
        'generated' => Colors.purple,
        'uploaded' => Colors.teal,
        _ => Colors.blueGrey,
      };
}

// ─── Chips ─────────────────────────────────────────────────────────────────

// Mục đích: Lớp `_StatusChip` triển khai phần việc `Status Chip` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});
  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, color) = switch (status) {
      'final' => (strings.ui('Chính thức'), Colors.green),
      'archived' => (strings.ui('Lưu trữ'), Colors.grey),
      _ => (strings.ui('Bản nháp'), Colors.orange),
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

// Mục đích: Lớp `_VisChip` triển khai phần việc `Vis Chip` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _VisChip extends StatelessWidget {
  final String visibility;
  const _VisChip({required this.visibility});
  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final (icon, color) = switch (visibility) {
      'public' => (Icons.public, Colors.green),
      'group' => (Icons.group, Colors.blue),
      _ => (Icons.lock, Colors.grey),
    };
    return Icon(icon, size: 13, color: color.withOpacity(0.7));
  }
}

// Mục đích: Lớp `_SigningChip` triển khai phần việc `Signing Chip` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _SigningChip extends StatelessWidget {
  final String status;

  const _SigningChip({required this.status});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isSigned = status == 'signed';
    final color = isSigned ? const Color(0xFF166534) : const Color(0xFFD97706);
    final label = isSigned ? strings.ui('Đã ký') : strings.ui('Chưa ký');
    final icon = isSigned ? Icons.verified_outlined : Icons.gpp_maybe_outlined;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
                fontSize: 10, color: color, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_QuickChip` triển khai phần việc `Quick Chip` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

// Mục đích: Lớp `_DateRangeRow` triển khai phần việc `Date Range Row` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // Mục đích: Phương thức `_fmt` triển khai phần việc `fmt` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _fmt(DateTime? d) => d == null
      ? 'Từ ngày'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  // Mục đích: Phương thức `_fmtTo` triển khai phần việc `fmt To` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _fmtTo(DateTime? d) => d == null
      ? 'Đến ngày'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  // Mục đích: Phương thức `_pick` triển khai phần việc `pick` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _pick(
      BuildContext context, DateTime? cur, void Function(DateTime?) cb) async {
    final p = await showDatePicker(
      context: context,
      initialDate: cur ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    cb(p);
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Row(
      children: [
        Icon(icon, size: 15, color: Colors.blueGrey.shade400),
        const SizedBox(width: 6),
        SizedBox(
            width: 100,
            child: Text(strings.ui(label),
                style: const TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w500))),
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
            tooltip: strings.ui('Xóa khoảng ngày này'),
            icon: Icon(Icons.clear, size: 16, color: Colors.grey.shade500),
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

// Mục đích: Lớp `_HighlightText` triển khai phần việc `Highlight Text` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/document_list_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
      if (idx > start)
        spans.add(TextSpan(text: text.substring(start, idx), style: style));
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
    return Text.rich(TextSpan(children: spans),
        maxLines: maxLines, overflow: TextOverflow.ellipsis);
  }
}
