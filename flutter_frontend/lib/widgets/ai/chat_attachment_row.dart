import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// Mot mau attachment se gui kem mot turn ChatAI/VoiceAI.
/// Co the la PDF (qua `bytes` + `name`) hoac anh (qua `bytes` + `name`).
class ChatAttachmentItem {
  final Uint8List bytes;
  final String name;
  final bool isPdf;
  ChatAttachmentItem({
    required this.bytes,
    required this.name,
    required this.isPdf,
  });
}

/// Hang chip hien thi cac file da dinh kem + nut them.
///
/// Per-turn: sau khi parent goi `clear()` (vd: sau khi send xong) UI khong
/// con hien thi gi. State luu o parent qua [items].
class ChatAttachmentRow extends StatelessWidget {
  final List<ChatAttachmentItem> items;
  final ValueChanged<ChatAttachmentItem> onAdd;
  final ValueChanged<int> onRemove;
  final bool compact;
  final int maxItems;

  const ChatAttachmentRow({
    super.key,
    required this.items,
    required this.onAdd,
    required this.onRemove,
    this.compact = false,
    this.maxItems = 10,
  });

  Future<void> _pickPdf(BuildContext context) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;
    final f = result.files.first;
    final bytes = f.bytes;
    if (bytes == null) return;
    if (bytes.length > 20 * 1024 * 1024) {
      _toast(context, 'PDF vượt quá 20MB');
      return;
    }
    onAdd(ChatAttachmentItem(bytes: bytes, name: f.name, isPdf: true));
  }

  Future<void> _pickImage(BuildContext context, {bool useCamera = false}) async {
    // Web: dung html.FileUploadInputElement de truy cap camera tren mobile browsers.
    final input = html.FileUploadInputElement();
    input.accept = 'image/*';
    if (useCamera) {
      input.setAttribute('capture', 'environment');
    }
    input.click();
    await input.onChange.first;
    final files = input.files;
    if (files == null || files.isEmpty) return;
    final file = files.first;
    final reader = html.FileReader();
    reader.readAsArrayBuffer(file);
    await reader.onLoad.first;
    final dynamic raw = reader.result;
    if (raw is! List<int> && raw is! Uint8List) return;
    final bytes = Uint8List.fromList(List<int>.from(raw as Iterable));
    if (bytes.length > 10 * 1024 * 1024) {
      _toast(context, 'Ảnh vượt quá 10MB');
      return;
    }
    onAdd(ChatAttachmentItem(bytes: bytes, name: file.name, isPdf: false));
  }

  void _toast(BuildContext context, String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  bool _supportsCameraCapture() {
    final ua = html.window.navigator.userAgent.toLowerCase();
    return RegExp(r'android|iphone|ipad|ipod').hasMatch(ua);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final atLimit = items.length >= maxItems;
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        PopupMenuButton<String>(
          enabled: !atLimit,
          tooltip: 'Đính kèm file',
          itemBuilder: (_) => [
            const PopupMenuItem(
              value: 'pdf',
              child: ListTile(
                leading: Icon(Icons.picture_as_pdf, size: 18, color: Color(0xFFB91C1C)),
                title: Text('Chọn PDF', style: TextStyle(fontSize: 13)),
                dense: true,
              ),
            ),
            const PopupMenuItem(
              value: 'gallery',
              child: ListTile(
                leading: Icon(Icons.photo_library_outlined, size: 18),
                title: Text('Chọn ảnh từ thư viện', style: TextStyle(fontSize: 13)),
                dense: true,
              ),
            ),
            if (_supportsCameraCapture())
              const PopupMenuItem(
                value: 'camera',
                child: ListTile(
                  leading: Icon(Icons.photo_camera_outlined, size: 18),
                  title: Text('Chụp ảnh', style: TextStyle(fontSize: 13)),
                  dense: true,
                ),
              ),
          ],
          onSelected: (v) {
            switch (v) {
              case 'pdf':
                _pickPdf(context);
                break;
              case 'gallery':
                _pickImage(context, useCamera: false);
                break;
              case 'camera':
                _pickImage(context, useCamera: true);
                break;
            }
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              border: Border.all(color: theme.dividerColor),
              borderRadius: BorderRadius.circular(10),
              color: atLimit ? Colors.grey.shade100 : null,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.attach_file, size: 16, color: atLimit ? Colors.grey : null),
                const SizedBox(width: 4),
                Text(
                  atLimit ? 'Đã đầy' : 'Đính kèm',
                  style: TextStyle(
                    fontSize: 12,
                    color: atLimit ? Colors.grey : null,
                  ),
                ),
              ],
            ),
          ),
        ),
        for (int i = 0; i < items.length; i++)
          _AttachmentChip(
            item: items[i],
            onRemove: () => onRemove(i),
          ),
      ],
    );
  }
}

class _AttachmentChip extends StatelessWidget {
  final ChatAttachmentItem item;
  final VoidCallback onRemove;
  const _AttachmentChip({required this.item, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = item.isPdf ? const Color(0xFFB91C1C) : const Color(0xFF1D4ED8);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        border: Border.all(color: color.withOpacity(0.4)),
        borderRadius: BorderRadius.circular(16),
        color: color.withOpacity(0.06),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            item.isPdf ? Icons.picture_as_pdf : Icons.image_outlined,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 4),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 140),
            child: Text(
              item.name,
              style: TextStyle(fontSize: 11.5, color: color, fontWeight: FontWeight.w500),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 4),
          InkWell(
            onTap: onRemove,
            customBorder: const CircleBorder(),
            child: Padding(
              padding: const EdgeInsets.all(2),
              child: Icon(Icons.close, size: 13, color: color),
            ),
          ),
        ],
      ),
    );
  }
}
