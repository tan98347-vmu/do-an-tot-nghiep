// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../models/signing.dart';
import '../../providers/signing_summary_provider.dart';

// Mục đích: Widget `SigningDelegationScreen` triển khai phần việc `Signing Delegation Screen` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningDelegationScreen extends ConsumerStatefulWidget {
  const SigningDelegationScreen({super.key});

  @override
  ConsumerState<SigningDelegationScreen> createState() => _SigningDelegationScreenState();
}

// Mục đích: Widget `_SigningDelegationScreenState` triển khai phần việc `Signing Delegation Screen State` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _SigningDelegationScreenState extends ConsumerState<SigningDelegationScreen> {
  bool _loading = true;
  String? _error;
  SigningSummary _summary = const SigningSummary.zero();
  List<DepartmentDelegationItem> _delegations = const [];
  List<SigningCandidate> _hrCandidates = const [];
  List<SigningCandidate> _accountingCandidates = const [];
  int? _selectedHrUserId;
  int? _selectedAccountingUserId;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _load();
  }

  // Mục đích: Phương thức `_load` triển khai phần việc `load` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _load() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final baseResponses = await Future.wait([
        ApiClient().dio.get('signing/summary/'),
        ApiClient().dio.get('signing/delegations/'),
      ]);
      final summary = SigningSummary.fromJson(
        Map<String, dynamic>.from(baseResponses[0].data as Map),
      );
      final delegations = (baseResponses[1].data as List)
          .map((item) => DepartmentDelegationItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      List<SigningCandidate> hrCandidates = const [];
      List<SigningCandidate> accountingCandidates = const [];
      if (summary.canManageHrDelegations) {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final hrResp = await ApiClient().dio.get('signing/candidates/?permission_type=approve_signing_proposal');
        hrCandidates = (hrResp.data as List)
            .map((item) => SigningCandidate.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList();
      }
      if (summary.canManageAccountingDelegations) {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final accountingResp = await ApiClient().dio.get('signing/candidates/?permission_type=view_signed_pdf');
        accountingCandidates = (accountingResp.data as List)
            .map((item) => SigningCandidate.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList();
      }
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _summary = summary;
        _delegations = delegations;
        _hrCandidates = hrCandidates;
        _accountingCandidates = accountingCandidates;
        _loading = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ?? error.message;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  // Mục đích: Phương thức `_addDelegation` triển khai phần việc `add Delegation` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _addDelegation(String permissionType, int? userId) async {
    if (userId == null) return;
    // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

    await ApiClient().dio.post(
      'signing/delegations/',
      data: {
        'delegate_user_id': userId,
        'permission_type': permissionType,
      },
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Đã cập nhật ủy quyền ký số.')),
    );
    ref.invalidate(signingSummaryProvider);
    await _load();
  }

  // Mục đích: Phương thức `_deleteDelegation` triển khai phần việc `delete Delegation` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _deleteDelegation(int id) async {
    // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

    await ApiClient().dio.delete('signing/delegations/$id/');
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Đã xóa ủy quyền.')),
    );
    ref.invalidate(signingSummaryProvider);
    await _load();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final summary = _summary;
    final hrDelegations = _delegations.where((item) => item.permissionType == 'approve_signing_proposal').toList();
    final accountingDelegations = _delegations.where((item) => item.permissionType == 'view_signed_pdf').toList();

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(title: const Text('Ủy quyền ký số')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text('Lỗi: $_error'),
                ))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (_summary.canManageHrDelegations) ...[
                      _DelegationSection(
                        title: 'Ủy quyền duyệt đề xuất ký',
                        subtitle: _summary.hrDepartmentName == null
                            ? 'Chưa xác định phòng Nhân sự.'
                            : 'Phòng Nhân sự: ${summary.hrDepartmentName}',
                        items: hrDelegations,
                        candidates: _hrCandidates,
                        selectedUserId: _selectedHrUserId,
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onSelected: (value) => setState(() => _selectedHrUserId = value),
                        onAdd: () => _addDelegation('approve_signing_proposal', _selectedHrUserId),
                        onDelete: _deleteDelegation,
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (_summary.canManageAccountingDelegations) ...[
                      _DelegationSection(
                        title: 'Ủy quyền xem PDF đã ký',
                        subtitle: summary.accountingDepartmentName == null
                            ? 'Chưa xác định phòng Kế toán.'
                            : 'Phòng Kế toán: ${summary.accountingDepartmentName}',
                        items: accountingDelegations,
                        candidates: _accountingCandidates,
                        selectedUserId: _selectedAccountingUserId,
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        onSelected: (value) => setState(() => _selectedAccountingUserId = value),
                        onAdd: () => _addDelegation('view_signed_pdf', _selectedAccountingUserId),
                        onDelete: _deleteDelegation,
                      ),
                    ],
                    if (!_summary.canManageHrDelegations && !_summary.canManageAccountingDelegations)
                      const Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('Bạn không có quyền quản lý ủy quyền ký số.'),
                        ),
                      ),
                  ],
                ),
    );
  }
}

// Mục đích: Lớp `_DelegationSection` triển khai phần việc `Delegation Section` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DelegationSection extends StatelessWidget {
  final String title;
  final String subtitle;
  final List<DepartmentDelegationItem> items;
  final List<SigningCandidate> candidates;
  final int? selectedUserId;
  final ValueChanged<int?> onSelected;
  final VoidCallback onAdd;
  final Future<void> Function(int id) onDelete;

  const _DelegationSection({
    required this.title,
    required this.subtitle,
    required this.items,
    required this.candidates,
    required this.selectedUserId,
    required this.onSelected,
    required this.onAdd,
    required this.onDelete,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/signing/signing_delegation_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text(subtitle, style: const TextStyle(color: Color(0xFF475569))),
            const SizedBox(height: 12),
            DropdownButtonFormField<int>(
              value: selectedUserId,
              decoration: const InputDecoration(
                labelText: 'Chọn người được ủy quyền',
                border: OutlineInputBorder(),
              ),
              items: candidates.map((candidate) {
                return DropdownMenuItem<int>(
                  value: candidate.id,
                  child: Text(candidate.label),
                );
              }).toList(),
              onChanged: onSelected,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Thêm ủy quyền'),
            ),
            const SizedBox(height: 12),
            if (items.isEmpty)
              const Text('Chưa có ủy quyền nào.')
            else
              ...items.map((item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(item.delegateUserName),
                    subtitle: Text(item.departmentName),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () => onDelete(item.id),
                    ),
                  )),
          ],
        ),
      ),
    );
  }
}
