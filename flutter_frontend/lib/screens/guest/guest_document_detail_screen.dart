// === MÀN HÌNH CỔNG KHÁCH — CHI TIẾT VĂN BẢN KHÁCH ===
// Xem trước (_buildPreview 'guest/document/content-html/') và tải DOCX (_downloadDocx 'guest/document/download/') cho văn bản khách vừa tạo.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/guest/guest_document_detail_screen.dart.
import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/iframe_blocker.dart';

// Widget màn CHI TIẾT VĂN BẢN KHÁCH (cổng guest).

class GuestDocumentDetailScreen extends StatefulWidget {
  // Widget màn CHI TIẾT VĂN BẢN KHÁCH (cổng guest, không đăng nhập).
  const GuestDocumentDetailScreen({super.key});

  @override
  State<GuestDocumentDetailScreen> createState() => _GuestDocumentDetailScreenState();
}

// State màn khách: tải văn bản vừa tạo, xem trước, tải DOCX.

class _GuestDocumentDetailScreenState extends State<GuestDocumentDetailScreen> {
  Map<String, dynamic>? _document;
  String? _contentHtml;
  bool _loading = true;
  String? _error;
  int _iframeKey = 0;

  @override
  // Mở màn: nạp văn bản khách vừa tạo (_load 'guest/document/').
  void initState() {
    super.initState();
    _load();
  }

  // Tải văn bản khách từ server ('guest/document/').

  Future<void> _load() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final responses = await Future.wait([
        ApiClient().dio.get('guest/document/'),
        ApiClient().dio.get('guest/document/content-html/'),
      ]);
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _document = Map<String, dynamic>.from(responses[0].data as Map);
        _contentHtml = responses[1].data['html'] as String? ?? '';
        _iframeKey++;
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = e.response?.data?['detail']?.toString() ?? 'Khong tai duoc van ban tam thoi.';
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = 'Khong tai duoc van ban tam thoi: $e';
        _loading = false;
      });
    }
  }

  // Tải file DOCX của văn bản khách ('guest/document/download/').
  Future<void> _downloadDocx() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'guest/document/download/',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = resp.data as List<int>;
      final blob = html.Blob(
        [bytes],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      final url = html.Url.createObjectUrlFromBlob(blob);
      final title = (_document?['title'] as String?) ?? 'van_ban_guest';
      html.AnchorElement(href: url)
        ..setAttribute('download', '$title.docx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Loi tai file: $e'), backgroundColor: Colors.red),
      );
    }
  }

  // Dựng khung xem trước nội dung HTML của văn bản ('content-html/').
  Widget _buildPreview() {
    if (_contentHtml == null || _contentHtml!.isEmpty) {
      return const SizedBox(
        height: 160,
        child: Center(child: Text('Chua co noi dung de hien thi.')),
      );
    }

    final viewKey = 'guest-document-content-$_iframeKey';
    ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
      final frame = html.IFrameElement()
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.pointerEvents = 'auto'
        ..srcdoc = _contentHtml!;
      return frame;
    });

    return SizedBox(
      height: 820,
      child: IframeBlocker(child: HtmlElementView(viewType: viewKey)),
    );
  }

  @override
  // Dựng màn: thông tin + xem trước + nút tải; nút quay về cổng khách (/guest).
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.description_outlined, size: 48, color: Colors.grey),
                  const SizedBox(height: 12),
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    onPressed: () => context.go('/guest'),
                    icon: const Icon(Icons.auto_awesome),
                    label: const Text('Sinh van ban moi'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final doc = _document!;
    final screenWidth = MediaQuery.of(context).size.width;
    final isWide = screenWidth >= 960;

    final leftColumn = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _MetaBadge(icon: Icons.person_outline, label: 'Guest: ${doc['owner_name']}'),
            const _MetaBadge(icon: Icons.auto_awesome, label: 'Tạo bằng AI'),
            const _MetaBadge(icon: Icons.timelapse, label: 'Lưu tạm thời'),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton.icon(
              onPressed: _downloadDocx,
              icon: const Icon(Icons.download),
              label: const Text('Tai Word'),
            ),
            OutlinedButton.icon(
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () => context.go('/guest'),
              icon: const Icon(Icons.refresh),
              label: const Text('Sinh van ban moi'),
            ),
          ],
        ),
        const SizedBox(height: 18),
        Text(
          'Noi dung van ban',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: Colors.grey.shade200),
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.04),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: _buildPreview(),
        ),
      ],
    );

    final rightColumn = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Thong tin van ban',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                _InfoRow('Tieu de', doc['title']?.toString() ?? ''),
                _InfoRow('Tao tu mau', doc['template_title']?.toString() ?? ''),
                _InfoRow('Nguoi tao', doc['owner_name']?.toString() ?? ''),
                _InfoRow('Ngay tao', _shortDate(doc['created_at']?.toString() ?? '')),
                _InfoRow('Cap nhat', _shortDate(doc['updated_at']?.toString() ?? '')),
                _InfoRow('Trang thai', 'Van ban tam thoi'),
                _InfoRow('Quyen', 'Khach tam thoi, khong tham gia phan quyen he thong'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.amber.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.amber.shade200),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.lock_clock_outlined, color: Colors.amber.shade800, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Session guest',
                    style: TextStyle(
                      color: Colors.amber.shade900,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Van ban nay chi ton tai tam thoi trong session hien tai. '
                'Tat trinh duyet hoac roi khoi guest flow se xoa file tam.',
                style: TextStyle(color: Colors.amber.shade900, fontSize: 12.5),
              ),
            ],
          ),
        ),
      ],
    );

    if (isWide) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: leftColumn),
            const SizedBox(width: 24),
            SizedBox(width: 300, child: rightColumn),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          leftColumn,
          const SizedBox(height: 24),
          rightColumn,
        ],
      ),
    );
  }

  // Định dạng ngày ngắn gọn để hiển thị.
  String _shortDate(String value) {
    if (value.length >= 10) return value.substring(0, 10);
    return value;
  }
}

// Widget dòng thông tin (nhãn + giá trị).

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  // Dựng 1 dòng thông tin.

  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}

// Widget badge metadata nhỏ.

class _MetaBadge extends StatelessWidget {
  final IconData icon;
  final String label;
  const _MetaBadge({required this.icon, required this.label});

  @override
  // Dựng badge metadata.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.blue.shade100),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.blue.shade700),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Colors.blue.shade800,
            ),
          ),
        ],
      ),
    );
  }
}
