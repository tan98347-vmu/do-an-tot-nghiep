// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:flutter/widgets.dart';

final Set<String> _registeredManualEditViews = <String>{};
final Map<String, html.IFrameElement> _manualEditFrames =
    <String, html.IFrameElement>{};
final Map<String, String> _manualEditUrls = <String, String>{};
final Map<String, _ManualEditFrameBridge> _manualEditBridges =
    <String, _ManualEditFrameBridge>{};
StreamSubscription<html.MessageEvent>? _manualEditMessageSubscription;

Future<void> requestManualEditIFrameSave({required String viewKey}) {
  _ensureManualEditMessageBridge();
  final bridge = _manualEditBridges[viewKey];
  if (bridge == null) {
    throw StateError('Trinh sua web chua san sang de dong bo noi dung moi.');
  }
  return bridge.save();
}

void _ensureManualEditMessageBridge() {
  _manualEditMessageSubscription ??= html.window.onMessage.listen((event) {
    for (final bridge in _manualEditBridges.values) {
      if (bridge.handleMessage(event)) {
        break;
      }
    }
  });
}

Map<String, dynamic>? _decodeManualEditMessage(dynamic raw) {
  if (raw is String && raw.trim().isNotEmpty) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      if (decoded is Map) {
        return decoded.cast<String, dynamic>();
      }
      return null;
    } on FormatException {
      return null;
    }
  }
  if (raw is Map<String, dynamic>) {
    return raw;
  }
  if (raw is Map) {
    return raw.cast<String, dynamic>();
  }
  return null;
}

class _ManualEditFrameBridge {
  _ManualEditFrameBridge();

  static const int _saveAttemptCount = 3;
  static const Duration _saveRetryDelay = Duration(milliseconds: 750);
  static const Duration _saveResponseTimeout = Duration(seconds: 2);

  html.IFrameElement? _frame;
  String? _src;
  bool _postMessageReady = false;
  bool _frameReady = false;
  bool _documentLoaded = false;
  bool _hostReadySent = false;
  Completer<void>? _saveCompleter;

  void attachFrame(html.IFrameElement frame, String src) {
    _frame = frame;
    final srcChanged = _src != src;
    _src = src;
    if (srcChanged) {
      _resetDocumentState();
    }
  }

  bool handleMessage(html.MessageEvent event) {
    final frame = _frame;
    if (frame == null) {
      return false;
    }
    if (!_matchesFrameEvent(event, frame)) {
      return false;
    }
    final message = _decodeManualEditMessage(event.data);
    if (message == null) {
      return false;
    }
    final messageId = '${message['MessageId'] ?? ''}'.trim();
    if (messageId.isEmpty) {
      return false;
    }
    if (messageId == 'App_LoadingStatus') {
      final values = message['Values'];
      final status = values is Map ? '${values['Status'] ?? ''}'.trim() : '';
      if (status == 'Initialized') {
        _postMessageReady = true;
      } else if (status == 'Frame_Ready') {
        _postMessageReady = true;
        _frameReady = true;
      } else if (status == 'Document_Loaded') {
        _postMessageReady = true;
        _frameReady = true;
        _documentLoaded = true;
      }
      return true;
    }
    if (messageId == 'Action_Save_Resp') {
      final values = message['Values'];
      final success = values is Map && values['success'] == true;
      final errorMessage =
          values is Map ? '${values['errorMsg'] ?? ''}'.trim() : '';
      if (success) {
        _saveCompleter?.complete();
      } else {
        _saveCompleter?.completeError(
          StateError(
            errorMessage.isNotEmpty
                ? errorMessage
                : 'Trinh sua web khong luu duoc thay doi moi vao working copy.',
          ),
        );
      }
      _saveCompleter = null;
      return true;
    }
    return false;
  }

  bool _matchesFrameEvent(html.MessageEvent event, html.IFrameElement frame) {
    final targetOrigin = _targetOrigin;
    if (targetOrigin != '*' &&
        event.origin.trim().isNotEmpty &&
        event.origin != targetOrigin) {
      return false;
    }
    final source = frame.contentWindow;
    if (source == null) {
      return false;
    }
    if (event.source == source || identical(event.source, source)) {
      return true;
    }
    return targetOrigin != '*' && event.origin == targetOrigin;
  }

  void notifyFrameLoaded() {
    _resetDocumentState();
    _ensureHostReady();
  }

  Future<void> save() async {
    final frame = _frame;
    if (frame == null || frame.contentWindow == null) {
      throw StateError('Trinh sua web chua tai xong.');
    }

    Object? lastError;
    for (var attempt = 0; attempt < _saveAttemptCount; attempt++) {
      try {
        await _requestSave(frame);
        return;
      } on TimeoutException catch (error) {
        lastError = error;
      } on StateError catch (error) {
        lastError = error;
      }
      _hostReadySent = false;
      await Future<void>.delayed(_saveRetryDelay);
    }

    if (lastError is StateError) {
      throw lastError;
    }
    if (!_postMessageReady) {
      throw StateError(
        'Trinh sua web chua san sang de nhan lenh luu. Vui long doi editor khoi tao xong roi thu lai.',
      );
    }
    if (!_frameReady) {
      throw StateError(
        'Giao dien trinh sua web chua san sang de luu. Vui long doi editor hien day du roi thu lai.',
      );
    }
    if (!_documentLoaded) {
      throw StateError(
        'Trinh sua web chua san sang de luu. Vui long doi tai lieu tai xong roi thu lai.',
      );
    }
    throw StateError(
      'Trinh sua web da nhan lenh luu nhung khong tra phan hoi xac nhan. Vui long thu lai.',
    );
  }

  Future<void> _requestSave(html.IFrameElement frame) async {
    _ensureHostReady();
    final completer = Completer<void>();
    _saveCompleter = completer;
    frame.contentWindow!.postMessage(
      jsonEncode(
        <String, dynamic>{
          'MessageId': 'Action_Save',
          'Values': <String, dynamic>{
            'DontTerminateEdit': true,
            'DontSaveIfUnmodified': false,
            'Notify': true,
          },
        },
      ),
      _targetOrigin,
    );
    try {
      return await completer.future.timeout(_saveResponseTimeout);
    } finally {
      _saveCompleter = null;
    }
  }

  String get _targetOrigin {
    final src = _src ?? '';
    final uri = Uri.tryParse(src);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      return '*';
    }
    return uri.origin;
  }

  void _ensureHostReady() {
    final frame = _frame;
    if (frame?.contentWindow == null || _hostReadySent) {
      return;
    }
    frame!.contentWindow!.postMessage(
      jsonEncode(<String, dynamic>{'MessageId': 'Host_PostmessageReady'}),
      _targetOrigin,
    );
    _hostReadySent = true;
  }

  void _resetDocumentState() {
    _postMessageReady = false;
    _frameReady = false;
    _documentLoaded = false;
    _hostReadySent = false;
    _saveCompleter = null;
  }
}

class ManualEditIFrame extends StatelessWidget {
  final String viewKey;
  final String src;

  const ManualEditIFrame({
    super.key,
    required this.viewKey,
    required this.src,
  });

  @override
  Widget build(BuildContext context) {
    _ensureManualEditMessageBridge();
    if (_registeredManualEditViews.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int _) {
        final bridge = _manualEditBridges.putIfAbsent(
          viewKey,
          () => _ManualEditFrameBridge(),
        );
        final frame = html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..allow = 'clipboard-read; clipboard-write'
          ..src = src;
        frame.onLoad.listen((_) => bridge.notifyFrameLoaded());
        _manualEditFrames[viewKey] = frame;
        _manualEditUrls[viewKey] = src;
        bridge.attachFrame(frame, src);
        return frame;
      });
    }
    final existing = _manualEditFrames[viewKey];
    final bridge = _manualEditBridges.putIfAbsent(
      viewKey,
      () => _ManualEditFrameBridge(),
    );
    if (existing != null && _manualEditUrls[viewKey] != src) {
      existing.src = src;
      _manualEditUrls[viewKey] = src;
      bridge.attachFrame(existing, src);
    } else if (existing != null) {
      bridge.attachFrame(existing, src);
    }
    return HtmlElementView(viewType: viewKey);
  }
}
