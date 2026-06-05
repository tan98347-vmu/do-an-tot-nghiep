// UnifiedShareSheet - component UI thong nhat cho chia se 3 loai resource
// (Template / Document / Prompt) theo kien truc moi:
//   - 4 pham vi (scope): private, group, colleagues, everyone
//   - 3 quyen (radio): view, edit, delete (ladder)
//   - Multi-scope: 1 resource co the co nhieu grant cho cac scope khac nhau

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/share_grant.dart';
import '../../providers/sharing_provider.dart';
import 'grant_status_badge.dart';
import 'group_picker_dialog.dart';
import 'peer_user_search_dialog.dart';

enum SharePresentation { dialog, bottomSheet, inlinePanel }

class UnifiedShareSheet extends ConsumerStatefulWidget {
  final String entityType; // 'templates' | 'documents' | 'prompts'
  final int entityId;
  final String entityTitle;
  final SharePresentation presentation;
  final bool readOnly;
  final Future<void> Function()? onChanged;

  const UnifiedShareSheet({
    super.key,
    required this.entityType,
    required this.entityId,
    required this.entityTitle,
    this.presentation = SharePresentation.dialog,
    this.readOnly = false,
    this.onChanged,
  });

  /// Helper: mo dialog tu mot context bat ki.
  static Future<void> showDialogPresentation(
    BuildContext context, {
    required String entityType,
    required int entityId,
    required String entityTitle,
  }) {
    return showDialog(
      context: context,
      builder: (_) => Dialog(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600, maxHeight: 720),
          child: UnifiedShareSheet(
            entityType: entityType,
            entityId: entityId,
            entityTitle: entityTitle,
            presentation: SharePresentation.dialog,
          ),
        ),
      ),
    );
  }

  /// Helper: mo bottom sheet
  static Future<void> showBottomSheetPresentation(
    BuildContext context, {
    required String entityType,
    required int entityId,
    required String entityTitle,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.85,
        builder: (ctx, scroll) => UnifiedShareSheet(
          entityType: entityType,
          entityId: entityId,
          entityTitle: entityTitle,
          presentation: SharePresentation.bottomSheet,
        ),
      ),
    );
  }

  @override
  ConsumerState<UnifiedShareSheet> createState() => _UnifiedShareSheetState();
}

class _UnifiedShareSheetState extends ConsumerState<UnifiedShareSheet> {
  ShareScope _newScope = ShareScope.group;
  SharePermission _newPermission = SharePermission.view;
  GroupBrief? _newGroup;
  final List<int> _newUserIds = [];
  bool _busy = false;
  String? _localError;

  // Cap nhat truc tiep: dinh ky lam moi danh sach grant khi con grant cho duyet,
  // de owner thay ngay ket qua duyet ma khong can thoat ra/vao lai.
  Timer? _refreshTimer;
  bool _hasPending = false;

  SharingKey get _key => SharingKey(widget.entityType, widget.entityId);
  SharingActions get _actions => SharingActions(ref, _key);

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted || _busy) return;
      if (_hasPending) ref.invalidate(sharingGrantsProvider(_key));
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _notifyChanged() async {
    final callback = widget.onChanged;
    if (callback == null) return;
    await callback();
  }

  Future<void> _withBusy(Future<void> Function() task) async {
    setState(() {
      _busy = true;
      _localError = null;
    });
    try {
      await task();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickGroup() async {
    final g = await GroupPickerDialog.show(context);
    if (g != null) setState(() => _newGroup = g);
  }

  Future<void> _pickUsers() async {
    final ids = await PeerUserSearchDialog.show(
      context,
      alreadyInAudience: _newUserIds.toSet(),
    );
    if (ids != null) {
      setState(() => _newUserIds
        ..clear()
        ..addAll(ids));
    }
  }

  Future<void> _submitNew() async {
    await _withBusy(() async {
      final results = <CreateGrantResult>[];
      if (_newScope == ShareScope.colleagues) {
        if (_newUserIds.isEmpty) return;
        for (final uid in _newUserIds) {
          final r = await _actions.createGrant(
            scope: _newScope,
            permission: _newPermission,
            targetUserId: uid,
          );
          results.add(r);
          if (!r.ok) break;
        }
      } else if (_newScope == ShareScope.group) {
        if (_newGroup == null) return;
        results.add(await _actions.createGrant(
          scope: _newScope,
          permission: _newPermission,
          targetGroupId: _newGroup!.id,
        ));
      } else {
        results.add(await _actions.createGrant(
          scope: _newScope,
          permission: _newPermission,
        ));
      }

      final firstError = results.firstWhere((r) => !r.ok,
          orElse: () => const CreateGrantResult());
      if (firstError.error != null) {
        setState(() => _localError = firstError.error);
        _showSnack(firstError.error!, isError: true);
      } else {
        setState(() {
          _newGroup = null;
          _newUserIds.clear();
          _newPermission = SharePermission.view;
        });
        _showSnack(_submitMessage(results), isError: false);
        await _notifyChanged();
      }
    });
  }

  /// Soan thong bao than thien dua tren trang thai duyet thuc te cua grant vua tao.
  String _submitMessage(List<CreateGrantResult> results) {
    final statuses = results
        .map((r) => r.grant?.approvalStatus)
        .whereType<ShareApprovalStatus>()
        .toList();
    if (statuses.any((s) => s == ShareApprovalStatus.pendingAdmin)) {
      return 'Đã gửi yêu cầu chia sẻ — chờ Quản trị viên duyệt.';
    }
    if (statuses.any((s) => s == ShareApprovalStatus.pendingLeader)) {
      return 'Đã gửi yêu cầu chia sẻ — chờ Trưởng nhóm duyệt.';
    }
    if (statuses.any((s) => s == ShareApprovalStatus.active)) {
      return 'Đã chia sẻ thành công.';
    }
    return 'Đã lưu chia sẻ.';
  }

  void _showSnack(String message, {required bool isError}) {
    if (!mounted) return;
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.showSnackBar(SnackBar(
      content: Row(
        children: [
          Icon(isError ? Icons.error_outline : Icons.check_circle_outline,
              color: Colors.white, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(message)),
        ],
      ),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
      behavior: SnackBarBehavior.floating,
    ));
  }

  @override
  Widget build(BuildContext context) {
    final asyncGrants = ref.watch(sharingGrantsProvider(_key));
    final isDialog = widget.presentation == SharePresentation.dialog;
    final isInline = widget.presentation == SharePresentation.inlinePanel;

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!isInline) _buildHeader(context),
        asyncGrants.when(
          loading: () => const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (e, _) => Padding(
            padding: const EdgeInsets.all(16),
            child: Text('Lỗi: $e', style: const TextStyle(color: Colors.red)),
          ),
          data: (grants) {
            // Bat/tat auto-refresh tuy theo con grant cho duyet hay khong.
            _hasPending = grants.any((g) => g.isPending);
            return Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_localError != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(_localError!,
                            style: const TextStyle(color: Colors.red)),
                      ),
                    _buildExistingGrantsSection(grants),
                    const SizedBox(height: 16),
                    if (!widget.readOnly) _buildNewGrantSection(),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );

    if (isDialog) {
      return Material(child: content);
    }
    return content;
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          const Icon(Icons.share, size: 22),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Chia sẻ: ${widget.entityTitle}',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
        ],
      ),
    );
  }

  Widget _buildExistingGrantsSection(List<ShareGrant> grants) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: const [
            Text('Các chia sẻ hiện tại',
                style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        if (grants.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text('Chưa có chia sẻ nào.',
                style: TextStyle(color: Colors.grey)),
          )
        else
          ...grants.map((g) => _buildGrantRow(g)),
      ],
    );
  }

  Widget _buildGrantRow(ShareGrant grant) {
    final target = switch (grant.scope) {
      ShareScope.group =>
        grant.targetGroup?.name ?? '(nhóm #${grant.targetGroupId})',
      ShareScope.colleagues =>
        grant.targetUser?.displayName ?? '(user #${grant.targetUserId})',
      ShareScope.everyone => 'Toàn bộ công ty',
      ShareScope.private => '(riêng tư)',
    };
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _scopeIcon(grant.scope),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${shareScopeLabel(grant.scope)} - $target',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              GrantStatusBadge(status: grant.approvalStatus),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<SharePermission>(
                  value: grant.permissionLevel,
                  isDense: true,
                  decoration: const InputDecoration(
                    isDense: true,
                    border: OutlineInputBorder(),
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  ),
                  items: SharePermission.values
                      .map((p) => DropdownMenuItem(
                            value: p,
                            child: Text(sharePermissionLabel(p),
                                style: const TextStyle(fontSize: 12)),
                          ))
                      .toList(),
                  onChanged: (widget.readOnly || _busy)
                      ? null
                      : (v) {
                          if (v != null) {
                            _withBusy(() async {
                              final err =
                                  await _actions.updatePermission(grant.id, v);
                              if (err != null && mounted) {
                                setState(() => _localError = err);
                              } else {
                                await _notifyChanged();
                              }
                            });
                          }
                        },
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.delete_outline,
                    color: Colors.red, size: 20),
                tooltip: 'Thu hồi',
                onPressed: (widget.readOnly || _busy)
                    ? null
                    : () async {
                        await _withBusy(() async {
                          final err = await _actions.revokeGrant(grant.id);
                          if (err != null && mounted) {
                            setState(() => _localError = err);
                          } else {
                            await _notifyChanged();
                          }
                        });
                      },
              ),
            ],
          ),
          _buildGrantStatusDetail(grant),
        ],
      ),
    );
  }

  /// Dong chi tiet trang thai duyet: ghi ro AI duyet voi QUYEN gi, hoac ai se duyet.
  Widget _buildGrantStatusDetail(ShareGrant grant) {
    final perm = sharePermissionLabel(grant.permissionLevel);
    Widget line(IconData icon, Color color, String text) => Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Expanded(
                child: Text(text,
                    style: TextStyle(fontSize: 11.5, color: color)),
              ),
            ],
          ),
        );

    switch (grant.approvalStatus) {
      case ShareApprovalStatus.active:
        final by = grant.approvedBy?.displayName;
        final when = _fmtDate(grant.approvedAt);
        final parts = <String>['Đã được duyệt — quyền "$perm"'];
        if (by != null && by.isNotEmpty) parts.add('bởi $by');
        if (when.isNotEmpty) parts.add(when);
        return line(Icons.verified_outlined, Colors.green.shade700,
            parts.join(' • '));
      case ShareApprovalStatus.pendingAdmin:
        return line(Icons.hourglass_top, Colors.deepOrange.shade700,
            'Chờ Quản trị viên duyệt (quyền "$perm")');
      case ShareApprovalStatus.pendingLeader:
        final who = grant.scope == ShareScope.group
            ? 'trưởng nhóm "${grant.targetGroup?.name ?? ''}"'
            : 'trưởng nhóm chung';
        return line(Icons.hourglass_top, Colors.orange.shade800,
            'Chờ $who duyệt (quyền "$perm")');
      case ShareApprovalStatus.rejected:
        final by = grant.approvedBy?.displayName ?? '';
        final note = grant.approverNote.isNotEmpty
            ? ' — ${grant.approverNote}'
            : '';
        return line(Icons.cancel_outlined, Colors.red.shade700,
            'Bị từ chối${by.isNotEmpty ? ' bởi $by' : ''}$note');
      case ShareApprovalStatus.draft:
        return line(Icons.edit_note, Colors.grey.shade600, 'Nháp — chưa gửi duyệt');
    }
  }

  /// Rut gon ISO datetime -> "dd/MM/yyyy HH:mm" (an toan voi null/sai dinh dang).
  String _fmtDate(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    final dt = DateTime.tryParse(iso);
    if (dt == null) return '';
    final l = dt.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(l.day)}/${two(l.month)}/${l.year} ${two(l.hour)}:${two(l.minute)}';
  }

  Widget _scopeIcon(ShareScope scope) {
    final icon = switch (scope) {
      ShareScope.private => Icons.lock_outline,
      ShareScope.group => Icons.group_outlined,
      ShareScope.colleagues => Icons.person_add_alt_outlined,
      ShareScope.everyone => Icons.public,
    };
    return Icon(icon, size: 18, color: Colors.blueGrey);
  }

  Widget _buildNewGrantSection() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.blue.shade200),
        borderRadius: BorderRadius.circular(8),
        color: Colors.blue.withOpacity(0.04),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Thêm chia sẻ mới',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            children: ShareScope.values.map((s) {
              final selected = s == _newScope;
              return ChoiceChip(
                label: Text(shareScopeLabel(s)),
                selected: selected,
                onSelected: (_) => setState(() {
                  _newScope = s;
                  _newGroup = null;
                  _newUserIds.clear();
                }),
              );
            }).toList(),
          ),
          const SizedBox(height: 4),
          Text(shareScopeDescription(_newScope),
              style: const TextStyle(fontSize: 11, color: Colors.grey)),
          const SizedBox(height: 10),
          if (_newScope == ShareScope.group)
            Row(children: [
              Expanded(
                child: Text(_newGroup?.name ?? 'Chưa chọn nhóm'),
              ),
              TextButton.icon(
                icon: const Icon(Icons.group),
                label: const Text('Chọn nhóm'),
                onPressed: _pickGroup,
              ),
            ])
          else if (_newScope == ShareScope.colleagues)
            Row(children: [
              Expanded(
                child: Text('${_newUserIds.length} người đã chọn'),
              ),
              TextButton.icon(
                icon: const Icon(Icons.person_add),
                label: const Text('Chọn người'),
                onPressed: _pickUsers,
              ),
            ]),
          const SizedBox(height: 10),
          const Text('Quyền hạn:',
              style: TextStyle(fontWeight: FontWeight.w600)),
          ...SharePermission.values.map((p) {
            return RadioListTile<SharePermission>(
              value: p,
              groupValue: _newPermission,
              onChanged: (v) {
                if (v != null) setState(() => _newPermission = v);
              },
              title: Text(sharePermissionLabel(p),
                  style: const TextStyle(fontSize: 13)),
              dense: true,
              contentPadding: EdgeInsets.zero,
              visualDensity: VisualDensity.compact,
            );
          }),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: ElevatedButton.icon(
              icon: _busy
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.add),
              label: const Text('Thêm chia sẻ'),
              onPressed: (_canSubmit() && !_busy) ? _submitNew : null,
            ),
          ),
        ],
      ),
    );
  }

  bool _canSubmit() {
    if (_newScope == ShareScope.group) return _newGroup != null;
    if (_newScope == ShareScope.colleagues) return _newUserIds.isNotEmpty;
    return true;
  }
}
