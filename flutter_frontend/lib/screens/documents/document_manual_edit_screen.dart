import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/beforeunload_guard.dart';
import '../../core/browser_confirm.dart';
import '../../models/document_manual_edit_session.dart';
import '../../providers/document_manual_edit_provider.dart';
import '../../providers/documents_provider.dart';
import '../../widgets/documents/manual_edit_iframe.dart';

class DocumentManualEditScreen extends ConsumerStatefulWidget {
  final int documentId;

  const DocumentManualEditScreen({
    super.key,
    required this.documentId,
  });

  @override
  ConsumerState<DocumentManualEditScreen> createState() =>
      _DocumentManualEditScreenState();
}

class _DocumentManualEditScreenState
    extends ConsumerState<DocumentManualEditScreen> {
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _editorSavePollInterval = Duration(milliseconds: 400);
  static const Duration _editorSaveSyncTimeout = Duration(seconds: 12);
  static const double _compactLayoutBreakpoint = 1100;
  static const double _compactHeightBreakpoint = 760;

  final TextEditingController _changeNoteCtrl = TextEditingController();
  DocumentManualEditSession? _session;
  Timer? _heartbeatTimer;
  bool _loading = true;
  bool _finishLoading = false;
  bool _cancelLoading = false;
  bool? _controlsCollapsedOverride;
  String? _error;
  // Cho phep roi man hinh ma khong canh bao (sau khi luu/huy thanh cong).
  bool _leaving = false;

  bool get _hasUnsavedRisk => !_leaving && _session?.isActive == true;

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    setBeforeUnloadGuard(false);
    _changeNoteCtrl.dispose();
    super.dispose();
  }

  void _restartHeartbeat(DocumentManualEditSession session) {
    _heartbeatTimer?.cancel();
    if (!session.isActive) {
      return;
    }
    _heartbeatTimer =
        Timer.periodic(_heartbeatInterval, (_) => _heartbeatSession());
  }

  Future<void> _heartbeatSession() async {
    final session = _session;
    if (!mounted || session == null || !session.isActive) {
      return;
    }
    try {
      final refreshed = await ref
          .read(documentManualEditApiProvider)
          .heartbeatSession(session.id);
      if (!mounted) {
        return;
      }
      setState(() => _session = refreshed);
      setBeforeUnloadGuard(refreshed.isActive);
      _restartHeartbeat(refreshed);
    } catch (error) {
      if (!mounted) {
        return;
      }
      _heartbeatTimer?.cancel();
      setState(() {
        _loading = false;
        _error = describeManualEditError(error);
      });
    }
  }

  Future<void> _loadSession() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final session = await ref
          .read(documentManualEditApiProvider)
          .ensureSession(widget.documentId);
      if (!mounted) return;
      setState(() {
        _session = session;
        _loading = false;
      });
      setBeforeUnloadGuard(session.isActive);
      _restartHeartbeat(session);
    } catch (error) {
      if (!mounted) return;
      _heartbeatTimer?.cancel();
      setState(() {
        _loading = false;
        _error = describeManualEditError(error);
      });
    }
  }

  String _editorViewKey(DocumentManualEditSession session) {
    return 'manual-edit-session-${session.id}';
  }

  bool _canRenderEditor(DocumentManualEditSession session) {
    return kIsWeb &&
        session.providerReady &&
        (session.editorUrl ?? '').isNotEmpty;
  }

  DateTime? _parseIsoTimestamp(String? raw) {
    final value = raw?.trim() ?? '';
    if (value.isEmpty) {
      return null;
    }
    return DateTime.tryParse(value)?.toUtc();
  }

  bool _workingCopySyncAdvanced(
    String? before,
    String? after,
  ) {
    final beforeTs = _parseIsoTimestamp(before);
    final afterTs = _parseIsoTimestamp(after);
    if (afterTs == null) {
      return false;
    }
    if (beforeTs == null) {
      return true;
    }
    return afterTs.isAfter(beforeTs);
  }

  Future<DocumentManualEditSession> _waitForWorkingCopySync(
    int sessionId, {
    required String? previousSyncAt,
  }) async {
    final deadline = DateTime.now().add(_editorSaveSyncTimeout);
    DocumentManualEditSession? latest;
    while (DateTime.now().isBefore(deadline)) {
      final refreshed =
          await ref.read(documentManualEditApiProvider).getSession(sessionId);
      latest = refreshed;
      if (mounted) {
        setState(() => _session = refreshed);
      }
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
          ? 'Trinh sua web chua dong bo noi dung moi vao server. Vui long thu lai.'
          : 'Trinh sua web chua dong bo noi dung moi vao server. Vui long doi them vai giay roi bam luu lai.',
    );
  }

  Future<DocumentManualEditSession> _flushEditorChanges(
      DocumentManualEditSession session) async {
    if (!_canRenderEditor(session)) {
      return session;
    }
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
      final refreshedSession = await _flushEditorChanges(session);
      await ref.read(documentManualEditApiProvider).finishSession(
            refreshedSession.id,
            changeNote: _changeNoteCtrl.text.trim(),
          );
      _heartbeatTimer?.cancel();
      _leaving = true;
      setBeforeUnloadGuard(false);
      if (!mounted) return;
      refreshDocumentCollections(ref);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã lưu văn bản thành phiên bản mới.'),
          backgroundColor: Colors.green,
        ),
      );
      context.go('/documents/${widget.documentId}');
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(describeManualEditError(error)),
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
      title: 'Hủy phiên chỉnh sửa',
      message:
          'Phiên chỉnh sửa thủ công sẽ bị hủy và không tạo phiên bản mới. Tiếp tục?',
      cancelLabel: 'Đóng',
      confirmLabel: 'Hủy phiên',
    );
    if (!confirmed) return;

    setState(() => _cancelLoading = true);
    try {
      await ref.read(documentManualEditApiProvider).cancelSession(session.id);
      _heartbeatTimer?.cancel();
      _leaving = true;
      setBeforeUnloadGuard(false);
      if (!mounted) return;
      refreshDocumentCollections(ref);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã hủy phiên chỉnh sửa thủ công.'),
          backgroundColor: Colors.orange,
        ),
      );
      context.go('/documents/${widget.documentId}');
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(describeManualEditError(error)),
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

  bool _isCompactLayout(BoxConstraints constraints) {
    return _isCompactViewportSize(
      Size(constraints.maxWidth, constraints.maxHeight),
    );
  }

  bool _controlsCollapsed(BoxConstraints constraints) {
    return _controlsCollapsedOverride ?? _isCompactLayout(constraints);
  }

  Widget _buildSessionSidePanel(
    BuildContext context,
    DocumentManualEditSession session, {
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
            'Trạng thái phiên',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 10),
          Text('Provider: ${session.provider}'),
          const SizedBox(height: 6),
          Text('Trạng thái: ${session.status}'),
          const SizedBox(height: 6),
          Text('Base version: v${session.baseVersionNumber}'),
          if ((session.lockMessage ?? '').isNotEmpty) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Text(
                session.lockMessage!,
                style: TextStyle(
                  fontSize: 12.5,
                  color: Colors.blue.shade900,
                ),
              ),
            ),
          ],
          const SizedBox(height: 20),
          TextField(
            controller: _changeNoteCtrl,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Ghi chú phiên bản mới',
              hintText: 'Ví dụ: Chỉnh sửa thủ công trên web editor',
              border: OutlineInputBorder(),
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
            label: const Text('Lưu & hoàn tất'),
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
            label: const Text('Hủy phiên'),
          ),
          const SizedBox(height: 10),
          TextButton(
            onPressed: () => context.go('/documents/${widget.documentId}'),
            child: const Text('Quay lại chi tiết'),
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
                    child: const Text('Thu lai'),
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
      return const Center(child: Text('Không tìm thấy phiên chỉnh sửa.'));
    }

    if (!session.isActive) {
      final closedMessage = switch (session.status) {
        'expired' => 'Phien chinh sua da het han. Bam thu lai de mo phien moi.',
        'cancelled' => 'Phien chinh sua da bi huy.',
        'finished' => 'Phien chinh sua da duoc luu thanh phien ban moi.',
        'failed' => 'Phien chinh sua da loi. Bam thu lai de mo phien moi.',
        _ => 'Phien chinh sua khong con hoat dong.',
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
                  const Icon(Icons.history_toggle_off,
                      size: 40, color: Colors.orange),
                  const SizedBox(height: 12),
                  Text(closedMessage, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _loadSession,
                    child: const Text('Thu lai'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () =>
                        context.go('/documents/${widget.documentId}'),
                    child: const Text('Quay lại chi tiết'),
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
                          const Icon(Icons.link_off,
                              color: Colors.orange, size: 40),
                          const SizedBox(height: 12),
                          Text(
                            !kIsWeb
                                ? 'Manual editor chi duoc ho tro tren Flutter Web.'
                                : (session.providerStatusDetail
                                            ?.trim()
                                            .isNotEmpty ??
                                        false)
                                    ? session.providerStatusDetail!.trim()
                                    : 'Provider Collabora/CODE chua duoc cau hinh day du. Editor URL chua san sang.',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );

        if (controlsCollapsed) {
          return editor;
        }

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
    final title = _session?.documentTitle ?? 'Chinh sua van ban';
    final isCompactViewport = _isCompactViewportSize(MediaQuery.sizeOf(context));
    final showControlsToggle =
        _session?.isActive == true && (_controlsCollapsedOverride != null || isCompactViewport);
    final controlsCollapsed =
        _controlsCollapsedOverride ?? isCompactViewport;
    return PopScope(
      canPop: !_hasUnsavedRisk,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop || !_hasUnsavedRisk) {
          return;
        }
        final leave = await showPlatformConfirmDialog(
          context: context,
          title: 'Có thay đổi chưa lưu',
          message:
              'Ban co thay doi chua luu trong phien chinh sua. Roi khoi trang ma khong luu?',
          cancelLabel: 'Tiep tuc chinh sua',
          confirmLabel: 'Roi khoi trang',
        );
        if (!leave || !mounted) {
          return;
        }
        _leaving = true;
        setBeforeUnloadGuard(false);
        if (context.canPop()) {
          context.pop();
        } else {
          context.go('/documents/${widget.documentId}');
        }
      },
      child: Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          if (showControlsToggle)
            IconButton(
              tooltip: controlsCollapsed
                  ? 'Hien bang thao tac phien'
                  : 'An bang thao tac phien',
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
                  'Phien dang mo',
                  style: TextStyle(color: Colors.green.shade800),
                ),
              ),
            ),
        ],
      ),
      body: _buildBody(),
      ),
    );
  }
}
