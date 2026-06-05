import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/browser_confirm.dart';
import '../../l10n/app_strings.dart';
import '../../models/template_manual_edit_session.dart';
import '../../providers/template_manual_edit_provider.dart';
import '../../providers/templates_provider.dart';
import '../../widgets/documents/manual_edit_iframe.dart';

class TemplateManualEditScreen extends ConsumerStatefulWidget {
  const TemplateManualEditScreen({
    super.key,
    required this.templateId,
    this.returnTo = 'detail',
  });

  final int templateId;
  final String returnTo;

  @override
  ConsumerState<TemplateManualEditScreen> createState() =>
      _TemplateManualEditScreenState();
}

class _TemplateManualEditScreenState
    extends ConsumerState<TemplateManualEditScreen> {
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _editorSavePollInterval = Duration(milliseconds: 400);
  static const Duration _editorSaveSyncTimeout = Duration(seconds: 12);
  static const double _compactLayoutBreakpoint = 1100;
  static const double _compactHeightBreakpoint = 760;

  final TextEditingController _changeNoteCtrl = TextEditingController();

  TemplateManualEditSession? _session;
  Timer? _heartbeatTimer;
  bool _loading = true;
  bool _finishLoading = false;
  bool _cancelLoading = false;
  bool? _controlsCollapsedOverride;
  String? _error;

  AppStrings get _strings => AppStrings.of(context);

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _changeNoteCtrl.dispose();
    super.dispose();
  }

  String get _returnPath {
    if (widget.returnTo == 'edit') {
      return '/templates/${widget.templateId}/edit';
    }
    return '/templates/${widget.templateId}';
  }

  String get _returnLabel {
    if (widget.returnTo == 'edit') {
      return _strings.pick(
        'Quay lại chỉnh sửa mẫu',
        'Back to template editing',
      );
    }
    return _strings.pick(
      'Quay lại chi tiết mẫu',
      'Back to template details',
    );
  }

  void _refreshTemplateCollections() {
    ref.invalidate(templateDetailProvider(widget.templateId));
    ref.invalidate(templateVersionsProvider(widget.templateId));
    ref.invalidate(templateVersionsAllProvider(widget.templateId));
    ref.invalidate(templatesProvider(''));
    ref.invalidate(templatesProvider('private'));
    ref.invalidate(templatesProvider('team'));
    ref.invalidate(templatesProvider('system'));
    ref.invalidate(templatesProvider('favorite'));
  }

  void _restartHeartbeat(TemplateManualEditSession session) {
    _heartbeatTimer?.cancel();
    if (!session.isActive) return;
    _heartbeatTimer =
        Timer.periodic(_heartbeatInterval, (_) => _heartbeatSession());
  }

  Future<void> _heartbeatSession() async {
    final session = _session;
    if (!mounted || session == null || !session.isActive) return;
    try {
      final refreshed = await ref
          .read(templateManualEditApiProvider)
          .heartbeatSession(session.id);
      if (!mounted) return;
      setState(() => _session = refreshed);
      _restartHeartbeat(refreshed);
    } catch (error) {
      if (!mounted) return;
      _heartbeatTimer?.cancel();
      setState(() {
        _loading = false;
        _error = describeTemplateManualEditError(error);
      });
    }
  }

  Future<void> _loadSession() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final session =
          await ref.read(templateManualEditApiProvider).ensureSession(
                widget.templateId,
              );
      if (!mounted) return;
      setState(() {
        _session = session;
        _loading = false;
      });
      _restartHeartbeat(session);
    } catch (error) {
      if (!mounted) return;
      _heartbeatTimer?.cancel();
      setState(() {
        _loading = false;
        _error = describeTemplateManualEditError(error);
      });
    }
  }

  String _editorViewKey(TemplateManualEditSession session) {
    return 'template-manual-edit-session-${session.id}';
  }

  bool _canRenderEditor(TemplateManualEditSession session) {
    return kIsWeb &&
        session.providerReady &&
        (session.editorUrl ?? '').isNotEmpty;
  }

  DateTime? _parseIsoTimestamp(String? raw) {
    final value = raw?.trim() ?? '';
    if (value.isEmpty) return null;
    return DateTime.tryParse(value)?.toUtc();
  }

  bool _workingCopySyncAdvanced(String? before, String? after) {
    final beforeTs = _parseIsoTimestamp(before);
    final afterTs = _parseIsoTimestamp(after);
    if (afterTs == null) return false;
    if (beforeTs == null) return true;
    return afterTs.isAfter(beforeTs);
  }

  Future<TemplateManualEditSession> _waitForWorkingCopySync(
    int sessionId, {
    required String? previousSyncAt,
  }) async {
    final deadline = DateTime.now().add(_editorSaveSyncTimeout);
    TemplateManualEditSession? latest;
    while (DateTime.now().isBefore(deadline)) {
      final refreshed =
          await ref.read(templateManualEditApiProvider).getSession(sessionId);
      latest = refreshed;
      if (mounted) setState(() => _session = refreshed);
      if (_workingCopySyncAdvanced(
        previousSyncAt,
        refreshed.workingCopyUpdatedAt,
      )) {
        return refreshed;
      }
      await Future<void>.delayed(_editorSavePollInterval);
    }
    throw StateError(
      latest == null
          ? _strings.pick(
              'Trình sửa web chưa đồng bộ nội dung mới vào server. Vui lòng thử lại.',
              'The web editor has not synced the latest content to the server yet. Please try again.',
            )
          : _strings.pick(
              'Trình sửa web chưa đồng bộ nội dung mới vào server. Vui lòng đợi thêm vài giây rồi bấm lưu lại.',
              'The web editor has not synced the latest content to the server yet. Please wait a few more seconds and save again.',
            ),
    );
  }

  Future<TemplateManualEditSession> _flushEditorChanges(
    TemplateManualEditSession session,
  ) async {
    if (!_canRenderEditor(session)) return session;
    final previousSyncAt = session.workingCopyUpdatedAt;
    await requestManualEditIFrameSave(viewKey: _editorViewKey(session));
    return _waitForWorkingCopySync(
      session.id,
      previousSyncAt: previousSyncAt,
    );
  }

  Future<void> _finishSession() async {
    final session = _session;
    if (session == null || _finishLoading) return;
    setState(() => _finishLoading = true);
    try {
      final refreshed = await _flushEditorChanges(session);
      await ref.read(templateManualEditApiProvider).finishSession(
            refreshed.id,
            changeNote: _changeNoteCtrl.text.trim(),
          );
      _heartbeatTimer?.cancel();
      if (!mounted) return;
      _refreshTemplateCollections();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _strings.pick(
              'Đã lưu mẫu thành phiên bản mới.',
              'Template saved as a new version.',
            ),
          ),
          backgroundColor: Colors.green,
        ),
      );
      context.go(_returnPath);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(describeTemplateManualEditError(error)),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _finishLoading = false);
    }
  }

  Future<void> _cancelSession() async {
    final session = _session;
    if (session == null || _cancelLoading) return;
    final confirmed = await showPlatformConfirmDialog(
      context: context,
      title: _strings.pick('Hủy phiên chỉnh sửa', 'Cancel editing session'),
      message: _strings.pick(
        'Phiên chỉnh sửa thủ công của mẫu sẽ bị hủy và không tạo phiên bản mới. Tiếp tục?',
        'The manual editing session will be cancelled and no new template version will be created. Continue?',
      ),
      cancelLabel: _strings.pick('Đóng', 'Close'),
      confirmLabel: _strings.pick('Hủy phiên', 'Cancel session'),
    );
    if (!confirmed) return;

    setState(() => _cancelLoading = true);
    try {
      await ref.read(templateManualEditApiProvider).cancelSession(session.id);
      _heartbeatTimer?.cancel();
      if (!mounted) return;
      _refreshTemplateCollections();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _strings.pick(
              'Đã hủy phiên chỉnh sửa thủ công của mẫu.',
              'The manual template editing session was cancelled.',
            ),
          ),
          backgroundColor: Colors.orange,
        ),
      );
      context.go(_returnPath);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(describeTemplateManualEditError(error)),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _cancelLoading = false);
    }
  }

  bool _isCompactViewportSize(Size size) {
    return size.width < _compactLayoutBreakpoint ||
        size.height < _compactHeightBreakpoint;
  }

  bool _controlsCollapsed(BoxConstraints constraints) {
    final compact = _isCompactViewportSize(
      Size(constraints.maxWidth, constraints.maxHeight),
    );
    return _controlsCollapsedOverride ?? compact;
  }

  Widget _buildSessionSidePanel(
    BuildContext context,
    TemplateManualEditSession session, {
    required bool stacked,
  }) {
    return Container(
      width: stacked ? double.infinity : 320,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          left: stacked
              ? BorderSide.none
              : BorderSide(color: Colors.grey.shade200),
          top: stacked
              ? BorderSide(color: Colors.grey.shade200)
              : BorderSide.none,
        ),
      ),
      child: ListView(
        children: [
          Text(
            _strings.pick('Trạng thái phiên', 'Session status'),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 10),
          Text('${_strings.pick('Provider', 'Provider')}: ${session.provider}'),
          const SizedBox(height: 6),
          Text('${_strings.pick('Trạng thái', 'Status')}: ${session.status}'),
          const SizedBox(height: 6),
          Text(
            '${_strings.pick('Phiên bản gốc', 'Base version')}: v${session.baseVersionLabel}',
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _changeNoteCtrl,
            minLines: 2,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: _strings.pick(
                'Ghi chú phiên bản mới',
                'New version note',
              ),
              hintText: _strings.pick(
                'Ví dụ: Chỉnh sửa nội dung mẫu trên web editor',
                'Example: Edited template content in the web editor',
              ),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed:
                _finishLoading || !session.isActive ? null : _finishSession,
            icon: _finishLoading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: Text(_strings.pick('Lưu & hoàn tất', 'Save & finish')),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed:
                _cancelLoading || !session.isActive ? null : _cancelSession,
            icon: _cancelLoading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.close),
            label: Text(_strings.pick('Hủy phiên', 'Cancel session')),
          ),
          const SizedBox(height: 10),
          TextButton(
            onPressed: () => context.go(_returnPath),
            child: Text(_returnLabel),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 40),
                  const SizedBox(height: 12),
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _loadSession,
                    child: Text(_strings.pick('Thử lại', 'Retry')),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final session = _session;
    if (session == null) {
      return Center(
        child: Text(
          _strings.pick(
            'Không tìm thấy phiên chỉnh sửa mẫu.',
            'Template editing session not found.',
          ),
        ),
      );
    }

    if (!session.isActive) {
      final closedMessage = switch (session.status) {
        'expired' => _strings.pick(
            'Phiên chỉnh sửa đã hết hạn. Bấm thử lại để mở phiên mới.',
            'The editing session expired. Retry to open a new session.',
          ),
        'cancelled' => _strings.pick(
            'Phiên chỉnh sửa đã bị hủy.',
            'The editing session was cancelled.',
          ),
        'finished' => _strings.pick(
            'Phiên chỉnh sửa đã được lưu thành phiên bản mới.',
            'The editing session was saved as a new version.',
          ),
        'failed' => _strings.pick(
            'Phiên chỉnh sửa đã lỗi. Bấm thử lại để mở phiên mới.',
            'The editing session failed. Retry to open a new session.',
          ),
        _ => _strings.pick(
            'Phiên chỉnh sửa không còn hoạt động.',
            'The editing session is no longer active.',
          ),
      };
      return Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.history_toggle_off,
                    size: 40,
                    color: Colors.orange,
                  ),
                  const SizedBox(height: 12),
                  Text(closedMessage, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _loadSession,
                    child: Text(_strings.pick('Thử lại', 'Retry')),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => context.go(_returnPath),
                    child: Text(_returnLabel),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final canRenderEditor = _canRenderEditor(session);

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < _compactLayoutBreakpoint;
        final controlsCollapsed = _controlsCollapsed(constraints);
        final sidePanel = _buildSessionSidePanel(
          context,
          session,
          stacked: stacked,
        );

        final editor = canRenderEditor
            ? ManualEditIFrame(
                viewKey: _editorViewKey(session),
                src: session.editorUrl!,
              )
            : Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 540),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.link_off,
                            color: Colors.orange,
                            size: 40,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            !kIsWeb
                                ? _strings.pick(
                                    'Trình sửa thủ công của mẫu chỉ được hỗ trợ trên Flutter Web.',
                                    'Manual template editing is only supported on Flutter Web.',
                                  )
                                : (session.providerStatusDetail
                                            ?.trim()
                                            .isNotEmpty ??
                                        false)
                                    ? session.providerStatusDetail!.trim()
                                    : _strings.pick(
                                        'Provider Collabora/CODE chưa được cấu hình đầy đủ. Editor URL chưa sẵn sàng.',
                                        'The Collabora/CODE provider is not fully configured. The editor URL is not ready.',
                                      ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );

        if (controlsCollapsed) return editor;

        if (stacked) {
          return Column(
            children: [
              Expanded(child: editor),
              SizedBox(height: 320, child: sidePanel),
            ],
          );
        }
        return Row(
          children: [
            Expanded(child: editor),
            sidePanel,
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = _session?.templateTitle ??
        _strings.pick('Chỉnh sửa mẫu văn bản', 'Edit template');
    final isCompactViewport =
        _isCompactViewportSize(MediaQuery.sizeOf(context));
    final showControlsToggle = _session?.isActive == true &&
        (_controlsCollapsedOverride != null || isCompactViewport);
    final controlsCollapsed = _controlsCollapsedOverride ?? isCompactViewport;

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          if (showControlsToggle)
            IconButton(
              tooltip: controlsCollapsed
                  ? _strings.pick(
                      'Hiện bảng thao tác phiên',
                      'Show session controls',
                    )
                  : _strings.pick(
                      'Ẩn bảng thao tác phiên',
                      'Hide session controls',
                    ),
              onPressed: () => setState(
                () => _controlsCollapsedOverride = !controlsCollapsed,
              ),
              icon: Icon(
                controlsCollapsed ? Icons.tune : Icons.tune_outlined,
              ),
            ),
          if (_session?.isActive == true)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  _strings.pick('Phiên đang mở', 'Session active'),
                  style: TextStyle(color: Colors.green.shade800),
                ),
              ),
            ),
        ],
      ),
      body: _buildBody(),
    );
  }
}
