// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';

// Mục đích: Lớp `_GuestTemplateMode` triển khai phần việc `Guest Template Mode` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

enum _GuestTemplateMode { existingVariables, autoDetect }

// Mục đích: Lớp `_FilePicker` triển khai phần việc `File Picker` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _FilePicker {
  late final html.FileUploadInputElement _el;
  // Mục đích: Phương thức `Function` triển khai phần việc `Function` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void Function(html.File)? onFile;

  _FilePicker({String accept = '*'}) {
    _el = html.FileUploadInputElement()
      ..accept = accept
      ..style.cssText =
          'position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0;';
    html.document.body!.append(_el);
    _el.onChange.listen((_) {
      final files = _el.files;
      if (files != null && files.isNotEmpty) onFile?.call(files[0]);
      _el.value = '';
    });
  }

  // Mục đích: Phương thức `trigger` triển khai phần việc `trigger` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void trigger() => _el.click();

  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() => _el.remove();
}

// Mục đích: Hàm `_readBytes` triển khai phần việc `read Bytes` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

Future<Uint8List?> _readBytes(html.File file) {
  final completer = Completer<Uint8List?>();
  final reader = html.FileReader();
  reader.onLoad.listen((_) {
    try {
      final url = reader.result as String;
      final index = url.indexOf(',');
      completer.complete(index == -1 ? null : base64Decode(url.substring(index + 1)));
    } catch (_) {
      completer.complete(null);
    }
  });
  reader.onError.listen((_) => completer.complete(null));
  reader.readAsDataUrl(file);
  return completer.future;
}

// Mục đích: Widget `GuestAiScreen` triển khai phần việc `Guest Ai Screen` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class GuestAiScreen extends StatefulWidget {
  const GuestAiScreen({super.key});

  @override
  State<GuestAiScreen> createState() => _GuestAiScreenState();
}

// Mục đích: Widget `_GuestAiScreenState` triển khai phần việc `Guest Ai Screen State` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _GuestAiScreenState extends State<GuestAiScreen> {
  late final _templatePicker = _FilePicker(accept: '.docx');
  late final _infoPicker = _FilePicker(accept: '.xlsx,.xls');
  late final _pdfPicker = _FilePicker(accept: '.pdf');

  String? _templateName;
  Uint8List? _templateBytes;
  List<String> _variables = [];
  final Map<String, TextEditingController> _controllers = {};
  String _preview = '';
  _GuestTemplateMode _templateMode = _GuestTemplateMode.existingVariables;

  bool _parsingTemplate = false;
  bool _loadingInfo = false;
  bool _loadingPdf = false;
  bool _generating = false;

  String? _parseError;
  String? _templateStatus;
  String? _generateError;
  String? _infoFileName;
  String? _pdfFileName;
  String? _pdfStatus;
  String? _pdfPreview;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _templatePicker.onFile = _onTemplateFile;
    _infoPicker.onFile = _onInfoFile;
    _pdfPicker.onFile = _onPdfFile;
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _templatePicker.dispose();
    _infoPicker.dispose();
    _pdfPicker.dispose();
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  // Mục đích: Phương thức `_clearImportedTemplateState` triển khai phần việc `clear Imported Template State` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _clearImportedTemplateState({bool keepTemplateMode = true}) {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    _controllers.clear();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _templateName = null;
      _templateBytes = null;
      _variables = [];
      _preview = '';
      _parsingTemplate = false;
      _parseError = null;
      _templateStatus = null;
      _generateError = null;
      _infoFileName = null;
      _pdfFileName = null;
      _pdfStatus = null;
      _pdfPreview = null;
      if (!keepTemplateMode) {
        _templateMode = _GuestTemplateMode.existingVariables;
      }
    });
  }

  // Mục đích: Phương thức `_onTemplateFile` triển khai phần việc `on Template File` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _onTemplateFile(html.File file) async {
    final bytes = await _readBytes(file);
    if (bytes == null) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _parseError = 'Khong doc duoc file mau van ban.');
      return;
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _parsingTemplate = true;
      _parseError = null;
      _templateStatus = null;
      _templateName = file.name;
      _templateBytes = bytes;
    });

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
        'guest/parse/',
        data: FormData.fromMap({
          'docx_file': MultipartFile.fromBytes(bytes, filename: file.name),
          'auto_detect': _templateMode == _GuestTemplateMode.autoDetect ? 'true' : 'false',
        }),
        options: ApiClient.ollamaOptions(contentType: 'multipart/form-data'),
      );

      final vars = List<String>.from(
        resp.data['detected_vars'] ?? resp.data['variables'] ?? const [],
      );
      final autoDetected = resp.data['auto_detect'] == true;
      for (final controller in _controllers.values) {
        controller.dispose();
      }
      _controllers.clear();
      for (final variable in vars) {
        _controllers[variable] = TextEditingController();
      }

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _variables = vars;
        _preview = resp.data['preview'] as String? ?? '';
        _parsingTemplate = false;
        _templateStatus = _templateMode == _GuestTemplateMode.autoDetect
            ? (autoDetected
                ? 'AI da detect ${vars.length} bien tu file DOCX.'
                : 'AI detect khong sinh them bien moi, dang dung cac bien co san trong file.')
            : 'Da doc ${vars.length} bien co san trong file DOCX.';
        _generateError = null;
        _pdfStatus = null;
        _pdfPreview = null;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _parsingTemplate = false;
        _parseError = e.response?.data?['detail']?.toString() ?? 'Loi phan tich mau van ban.';
      });
    } catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _parsingTemplate = false;
        _parseError = 'Loi phan tich mau van ban: $e';
      });
    }
  }

  // Mục đích: Phương thức `_onInfoFile` triển khai phần việc `on Info File` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _onInfoFile(html.File file) async {
    final bytes = await _readBytes(file);
    if (bytes == null) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loadingInfo = true;
      _infoFileName = file.name;
    });

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
        'guest/parse-info/',
        data: FormData.fromMap({
          'info_file': MultipartFile.fromBytes(bytes, filename: file.name),
        }),
      );
      final values = Map<String, dynamic>.from(resp.data['values'] ?? {});
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        for (final entry in values.entries) {
          if (_controllers.containsKey(entry.key)) {
            _controllers[entry.key]!.text = entry.value.toString();
          }
        }
        _loadingInfo = false;
      });
    } catch (_) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loadingInfo = false;
      });
    }
  }

  // Mục đích: Phương thức `_onPdfFile` triển khai phần việc `on Pdf File` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _onPdfFile(html.File file) async {
    final bytes = await _readBytes(file);
    if (bytes == null) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loadingPdf = true;
      _pdfFileName = file.name;
      _pdfStatus = 'Dang phan tich PDF bang AI...';
      _pdfPreview = null;
    });

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
        'guest/parse-pdf/',
        data: FormData.fromMap({
          'pdf_file': MultipartFile.fromBytes(bytes, filename: file.name),
          'variables': jsonEncode(_variables),
        }),
        options: ApiClient.ollamaOptions(contentType: 'multipart/form-data'),
      );
      final values = Map<String, dynamic>.from(resp.data['values'] ?? {});
      final matched = resp.data['matched'] as int? ?? 0;
      final total = resp.data['total'] as int? ?? _variables.length;
      final preview = resp.data['raw_preview'] as String? ?? '';

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        for (final entry in values.entries) {
          if (_controllers.containsKey(entry.key) && entry.value.toString().isNotEmpty) {
            _controllers[entry.key]!.text = entry.value.toString();
          }
        }
        _loadingPdf = false;
        _pdfPreview = preview.length > 220 ? '${preview.substring(0, 220)}...' : preview;
        _pdfStatus = matched > 0
            ? 'AI dien duoc $matched/$total bien tu PDF.'
            : 'AI khong tim thay thong tin phu hop trong PDF.';
      });
    } on DioException catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loadingPdf = false;
        _pdfStatus = e.response?.data?['detail']?.toString() ?? 'Loi phan tich PDF.';
      });
    } catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loadingPdf = false;
        _pdfStatus = 'Loi phan tich PDF: $e';
      });
    }
  }

  // Mục đích: Phương thức `_generate` triển khai phần việc `generate` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _generate() async {
    if (_templateBytes == null || _generating) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _generating = true;
      _generateError = null;
    });

    final values = {
      for (final entry in _controllers.entries) entry.key: entry.value.text.trim(),
    };

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
        'guest/generate/',
        data: FormData.fromMap({
          'values': jsonEncode(values),
          'title': _templateName?.replaceAll('.docx', '') ?? 'van_ban_guest',
        }),
      );
      if (!mounted) return;
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      context.go('/guest/document');
    } on DioException catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _generating = false;
        _generateError = e.response?.data?['detail']?.toString() ?? 'Loi tao van ban.';
      });
    } catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _generating = false;
        _generateError = 'Loi tao van ban: $e';
      });
    }
  }

  // Mục đích: Phương thức `_resetTemplate` triển khai phần việc `reset Template` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _resetTemplate() {
    _clearImportedTemplateState();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final hasTemplate = _templateBytes != null;
    final screenWidth = MediaQuery.of(context).size.width;
    final isWide = screenWidth >= 980;

    final hero = _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: const [
              _HeroBadge(icon: Icons.lock_clock_outlined, label: 'Session tạm thời'),
              _HeroBadge(icon: Icons.upload_file_outlined, label: 'Tự upload mẫu văn bản'),
              _HeroBadge(icon: Icons.download_outlined, label: 'Chỉ tải Word sau khi sinh'),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Tao van ban nhanh khong can dang nhap',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          Text(
            'Guest chi duoc dung luong Sinh van ban bang AI. Mau van ban va file sinh ra '
            'duoc luu tam trong session hien tai va se bi xoa khi session ket thuc.',
            style: TextStyle(fontSize: 13.5, color: Colors.grey.shade700, height: 1.5),
          ),
        ],
      ),
    );

    final templatePanel = _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle('1. Upload mau van ban'),
          const SizedBox(height: 8),
          Text(
            'Chon mot trong hai cach: file DOCX da co san {{tham_so}}, hoac de AI tu dong detect '
            'tham so can dien tu noi dung mau van ban.',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
          ),
          const SizedBox(height: 16),
          SegmentedButton<_GuestTemplateMode>(
            segments: const [
              ButtonSegment<_GuestTemplateMode>(
                value: _GuestTemplateMode.existingVariables,
                icon: Icon(Icons.data_object_outlined, size: 16),
                label: Text('VB co san tham so'),
              ),
              ButtonSegment<_GuestTemplateMode>(
                value: _GuestTemplateMode.autoDetect,
                icon: Icon(Icons.auto_fix_high_outlined, size: 16),
                label: Text('Tu dong detect tham so'),
              ),
            ],
            selected: {_templateMode},
            onSelectionChanged: _parsingTemplate
                ? null
                : (selection) {
                    if (selection.first == _templateMode) return;
                    _clearImportedTemplateState();
                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                    setState(() {
                      _templateMode = selection.first;
                    });
                  },
            style: ButtonStyle(
              textStyle: WidgetStateProperty.all(const TextStyle(fontSize: 12.5)),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _templateMode == _GuestTemplateMode.existingVariables
                ? 'Dung khi file DOCX da co san placeholder dang {{ten_bien}}.'
                : 'Dung khi file DOCX la van ban thuong, AI se tim va chuyen cac cho can dien thanh {{ten_bien}}.',
            style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _parsingTemplate ? null : () => _templatePicker.trigger(),
              icon: _parsingTemplate
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.upload_file),
              label: Text(
                _parsingTemplate
                    ? (_templateMode == _GuestTemplateMode.autoDetect
                        ? 'Dang upload va AI detect tham so...'
                        : 'Dang doc tham so tu file mau...')
                    : _templateName == null
                        ? 'Chon file mau .docx'
                        : 'Chon file mau khac',
              ),
            ),
          ),
          if (_templateName != null) ...[
            const SizedBox(height: 12),
            _InfoStrip(icon: Icons.description_outlined, label: _templateName!),
          ],
          if (_parseError != null) ...[
            const SizedBox(height: 12),
            _ErrorBanner(_parseError!),
          ],
          if (_templateStatus != null) ...[
            const SizedBox(height: 12),
            _InfoStrip(
              icon: _templateMode == _GuestTemplateMode.autoDetect
                  ? Icons.auto_fix_high_outlined
                  : Icons.check_circle_outline,
              label: _templateStatus!,
            ),
          ],
          if (_preview.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              _templateMode == _GuestTemplateMode.autoDetect
                  ? 'Xem nhanh noi dung sau khi detect tham so'
                  : 'Xem nhanh noi dung mau',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Text(
                _preview,
                style: const TextStyle(fontSize: 12.5, height: 1.5),
              ),
            ),
          ],
        ],
      ),
    );

    final fillPanel = _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle('2. Dien du lieu va sinh van ban'),
          const SizedBox(height: 8),
          Text(
            'Guest co the dien tay, nap file Excel thong tin, hoac de AI doc PDF de goi y gia tri cho cac bien.',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: _loadingInfo ? null : () => _infoPicker.trigger(),
                icon: _loadingInfo
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.table_chart_outlined, size: 16),
                label: Text(_infoFileName ?? 'Nap file Excel'),
              ),
              OutlinedButton.icon(
                onPressed: _loadingPdf ? null : () => _pdfPicker.trigger(),
                icon: _loadingPdf
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.picture_as_pdf_outlined, size: 16),
                label: Text(_pdfFileName ?? 'AI doc PDF'),
              ),
            ],
          ),
          if (_pdfStatus != null) ...[
            const SizedBox(height: 12),
            _InfoStrip(icon: Icons.psychology_outlined, label: _pdfStatus!),
          ],
          if (_pdfPreview != null && _pdfPreview!.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.deepPurple.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.deepPurple.shade100),
              ),
              child: Text(
                _pdfPreview!,
                style: TextStyle(fontSize: 12.5, color: Colors.deepPurple.shade900),
              ),
            ),
          ],
          const SizedBox(height: 18),
          if (_variables.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.orange.shade200),
              ),
              child: Row(
                children: [
                  Icon(Icons.warning_amber_outlined, color: Colors.orange.shade800),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      hasTemplate
                          ? 'Mau van ban khong co bien {{...}}. Van co the sinh file giong ban goc.'
                          : 'Can upload mau van ban truoc khi dien du lieu.',
                      style: TextStyle(color: Colors.orange.shade900),
                    ),
                  ),
                ],
              ),
            )
          else
            ..._variables.map((variable) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: TextField(
                  controller: _controllers[variable],
                  decoration: InputDecoration(
                    labelText: variable.replaceAll('_', ' '),
                    hintText: '{{$variable}}',
                    prefixIcon: const Icon(Icons.edit_outlined, size: 18),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              );
            }),
          if (_generateError != null) ...[
            const SizedBox(height: 12),
            _ErrorBanner(_generateError!),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: hasTemplate && !_generating ? _resetTemplate : null,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Nhập lại mẫu'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  onPressed: hasTemplate && !_generating ? _generate : null,
                  icon: _generating
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.auto_awesome),
                  label: Text(_generating ? 'Dang sinh van ban...' : 'Sinh van ban bang AI'),
                ),
              ),
            ],
          ),
        ],
      ),
    );

    final sidePanel = _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle('Trang thai session'),
          const SizedBox(height: 12),
          _StatusRow(label: 'Mau van ban', value: _templateName ?? 'Chua upload'),
          _StatusRow(
            label: 'Che do',
            value: _templateMode == _GuestTemplateMode.autoDetect
                ? 'Tu dong detect tham so'
                : 'VB co san tham so',
          ),
          _StatusRow(label: 'So bien', value: '${_variables.length}'),
          _StatusRow(
            label: 'Quyen guest',
            value: 'Chi sinh van ban va tai Word',
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.amber.shade200),
            ),
            child: Text(
              'Khong co luu tru, chia se, yeu thich, phe duyet hay quan ly phan quyen trong guest mode.',
              style: TextStyle(fontSize: 12.5, color: Colors.amber.shade900),
            ),
          ),
        ],
      ),
    );

    if (isWide) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: Column(
                children: [
                  hero,
                  const SizedBox(height: 20),
                  templatePanel,
                  const SizedBox(height: 20),
                  fillPanel,
                ],
              ),
            ),
            const SizedBox(width: 20),
            SizedBox(
              width: 310,
              child: sidePanel,
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          hero,
          const SizedBox(height: 16),
          sidePanel,
          const SizedBox(height: 16),
          templatePanel,
          const SizedBox(height: 16),
          fillPanel,
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_Panel` triển khai phần việc `Panel` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Panel extends StatelessWidget {
  final Widget child;
  const _Panel({required this.child});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
  }
}

// Mục đích: Lớp `_SectionTitle` triển khai phần việc `Section Title` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Text(
      text,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
    );
  }
}

// Mục đích: Lớp `_HeroBadge` triển khai phần việc `Hero Badge` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _HeroBadge extends StatelessWidget {
  final IconData icon;
  final String label;
  const _HeroBadge({required this.icon, required this.label});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFE0F2FE),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: const Color(0xFF0369A1)),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: Color(0xFF075985),
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_InfoStrip` triển khai phần việc `Info Strip` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _InfoStrip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoStrip({required this.icon, required this.label});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: const Color(0xFF0F172A)),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12.5))),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_ErrorBanner` triển khai phần việc `Error Banner` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ErrorBanner extends StatelessWidget {
  final String message;
  const _ErrorBanner(this.message);

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red.shade700, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(fontSize: 12.5, color: Colors.red.shade900),
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_StatusRow` triển khai phần việc `Status Row` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _StatusRow extends StatelessWidget {
  final String label;
  final String value;
  const _StatusRow({required this.label, required this.value});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/guest/guest_ai_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(
              label,
              style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
