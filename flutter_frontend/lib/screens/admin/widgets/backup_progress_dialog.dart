import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../../../core/api_client.dart';

class BackupProgressResult {
  final bool success;
  final String message;
  final int? backupId;

  const BackupProgressResult(
      {required this.success, required this.message, this.backupId});
}

class BackupProgressDialog extends StatefulWidget {
  final int backupId;
  final String fileName;

  const BackupProgressDialog({
    super.key,
    required this.backupId,
    required this.fileName,
  });

  static Future<BackupProgressResult?> show(BuildContext context,
      {required int backupId, required String fileName}) {
    return showDialog<BackupProgressResult>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BackupProgressDialog(backupId: backupId, fileName: fileName),
    );
  }

  @override
  State<BackupProgressDialog> createState() => _BackupProgressDialogState();
}

class _BackupProgressDialogState extends State<BackupProgressDialog> {
  Timer? _timer;
  int _percent = 0;
  String _stage = 'Đang khởi tạo';
  String _detail = '';
  String _status = 'creating';
  int? _sizeBytes;
  String _error = '';
  bool _finalized = false;
  DateTime _startedAt = DateTime.now();

  @override
  void initState() {
    super.initState();
    _startedAt = DateTime.now();
    _poll();
    _timer = Timer.periodic(const Duration(milliseconds: 800), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    if (_finalized) return;
    try {
      final resp = await ApiClient().dio.get(
        'admin/backups/${widget.backupId}/progress/',
      );
      if (!mounted) return;
      final data = Map<String, dynamic>.from(resp.data as Map);
      setState(() {
        _percent = (data['progress_percent'] ?? 0) as int;
        _stage = (data['progress_stage'] ?? '') as String;
        _detail = (data['progress_detail'] ?? '') as String;
        _status = (data['status'] ?? 'creating') as String;
        _sizeBytes = data['size_bytes'] as int?;
        _error = (data['error_message'] ?? '') as String;
      });
      if (_status == 'ready' || _status == 'failed') {
        _finalize();
      }
    } on DioException {
      // ignore transient network error, will retry next tick
    } catch (_) {
      // ignore
    }
  }

  void _finalize() {
    if (_finalized) return;
    _finalized = true;
    _timer?.cancel();
    setState(() {});
  }

  String _sizeDisplay(int? bytes) {
    if (bytes == null || bytes <= 0) return '';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  String _elapsed() {
    final d = DateTime.now().difference(_startedAt);
    final s = d.inSeconds;
    if (s < 60) return '${s}s';
    return '${s ~/ 60}m ${(s % 60).toString().padLeft(2, '0')}s';
  }

  Widget _icon() {
    if (_status == 'ready') {
      return const Icon(Icons.check_circle, size: 36, color: Colors.green);
    }
    if (_status == 'failed') {
      return const Icon(Icons.error_outline, size: 36, color: Colors.red);
    }
    return const SizedBox(
      width: 36, height: 36,
      child: CircularProgressIndicator(strokeWidth: 3),
    );
  }

  String _titleText() {
    if (_status == 'ready') return 'Tạo backup thành công';
    if (_status == 'failed') return 'Tạo backup thất bại';
    return 'Đang tạo bản sao lưu...';
  }

  @override
  Widget build(BuildContext context) {
    final isFinal = _status == 'ready' || _status == 'failed';
    final percentNormalized = (_percent.clamp(0, 100)) / 100.0;
    return AlertDialog(
      title: Row(children: [
        _icon(),
        const SizedBox(width: 10),
        Expanded(
          child: Text(_titleText(),
              style: const TextStyle(fontWeight: FontWeight.bold)),
        ),
      ]),
      content: SizedBox(
        width: 460,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.fileName,
                style: const TextStyle(
                    fontFamily: 'monospace', fontSize: 12, color: Colors.blueGrey),
                overflow: TextOverflow.ellipsis),
            const SizedBox(height: 16),
            Stack(alignment: Alignment.center, children: [
              SizedBox(
                height: 18,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(9),
                  child: LinearProgressIndicator(
                    value: _status == 'failed' ? 0.0 : percentNormalized,
                    minHeight: 18,
                    backgroundColor: Colors.grey.shade200,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      _status == 'ready'
                          ? Colors.green
                          : _status == 'failed'
                              ? Colors.red
                              : Colors.blue,
                    ),
                  ),
                ),
              ),
              Text(
                '$_percent%',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: percentNormalized > 0.5 ? Colors.white : Colors.black87,
                ),
              ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              const Icon(Icons.flag_outlined, size: 14, color: Colors.grey),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  _stage.isEmpty ? '...' : _stage,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ]),
            if (_detail.isNotEmpty) ...[
              const SizedBox(height: 4),
              Padding(
                padding: const EdgeInsets.only(left: 18),
                child: Text(
                  _detail,
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
            const SizedBox(height: 8),
            Wrap(spacing: 12, runSpacing: 4, children: [
              Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.timer_outlined, size: 12, color: Colors.grey),
                const SizedBox(width: 3),
                Text('Thời gian: ${_elapsed()}',
                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
              ]),
              if (_sizeBytes != null && _sizeBytes! > 0)
                Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.folder_zip_outlined, size: 12, color: Colors.grey),
                  const SizedBox(width: 3),
                  Text('Kích thước: ${_sizeDisplay(_sizeBytes)}',
                      style: const TextStyle(fontSize: 11, color: Colors.grey)),
                ]),
            ]),
            if (_status == 'failed' && _error.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(_error,
                    style: const TextStyle(fontSize: 12, color: Colors.red)),
              ),
            ],
            if (!isFinal) ...[
              const SizedBox(height: 12),
              Text(
                'Vui lòng giữ tab mở để hệ thống tiếp tục cập nhật tiến trình. '
                'Nếu đóng dialog, backup vẫn chạy nền và có thể xem trong tab Danh sách.',
                style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
              ),
            ],
          ],
        ),
      ),
      actions: [
        if (!isFinal)
          TextButton(
            onPressed: () => Navigator.of(context).pop(
                BackupProgressResult(success: false, message: 'Đang chạy nền', backupId: widget.backupId)),
            child: const Text('Chạy nền'),
          ),
        if (isFinal)
          FilledButton(
            onPressed: () => Navigator.of(context).pop(BackupProgressResult(
              success: _status == 'ready',
              message: _status == 'ready' ? 'Hoàn tất' : _error,
              backupId: widget.backupId,
            )),
            child: const Text('Đóng'),
          ),
      ],
    );
  }
}
