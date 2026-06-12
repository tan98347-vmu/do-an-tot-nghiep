// === MÀN HÌNH QUẢN LÝ CÔNG TY (platform-admin) ===
// Liệt kê công ty ('platform/companies/'); tạo (_showCompanyDialog/_showBootstrapDialog), import hàng loạt từ Excel (_pickAndPreviewCompanyImport 'company-imports/preview/' -> commit).
// - Tải workbook mẫu/credentials, cấu hình AI cho công ty (_showAiConfigDialog 'ai-config/'), thùng rác công ty (/platform/companies/trash). Mở chi tiết (/platform/companies/<id>).

// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import 'platform_company_wizard.dart';

class PlatformCompaniesScreen extends StatefulWidget {
  const PlatformCompaniesScreen({
    super.key,
    this.initialViewMode = 'active',
  });

  final String initialViewMode;

  @override
  State<PlatformCompaniesScreen> createState() =>
      _PlatformCompaniesScreenState();
}

class _PlatformCompaniesScreenState extends State<PlatformCompaniesScreen> {
  final _searchCtrl = TextEditingController();
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _companies = const [];
  List<Map<String, dynamic>> _deletedCompanies = const [];
  late String _viewMode;

  AppStrings get _strings => AppStrings.of(context);

  String _pick(String vi, String en) => _strings.pick(vi, en);

  String _statusLabel(String value) {
    return switch (value) {
      'draft' => _pick('Nháp', 'Draft'),
      'active' => _pick('Hoạt động', 'Active'),
      'locked' => _pick('Bị khóa', 'Locked'),
      'archived' => _pick('Lưu trữ', 'Archived'),
      'deleted' => _pick('Đã xóa', 'Deleted'),
      _ => value,
    };
  }

  @override
  void initState() {
    super.initState();
    _viewMode = widget.initialViewMode == 'trash' ? 'trash' : 'active';
    _loadCompanies();
  }

  @override
  void didUpdateWidget(covariant PlatformCompaniesScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final nextViewMode = widget.initialViewMode == 'trash' ? 'trash' : 'active';
    if (nextViewMode != _viewMode) {
      setState(() => _viewMode = nextViewMode);
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadCompanies() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final queryParameters = {
        if (_searchCtrl.text.trim().isNotEmpty) 'q': _searchCtrl.text.trim(),
      };
      final responses = await Future.wait([
        ApiClient()
            .dio
            .get('platform/companies/', queryParameters: queryParameters),
        ApiClient()
            .dio
            .get('platform/companies/trash/', queryParameters: queryParameters),
      ]);
      final items = responses[0].data as List<dynamic>? ?? const [];
      final deletedItems = responses[1].data as List<dynamic>? ?? const [];
      if (!mounted) return;
      setState(() {
        _companies = items
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _deletedCompanies = deletedItems
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _loading = false;
      });
    } on DioException catch (error) {
      final payload = error.response?.data;
      if (!mounted) return;
      setState(() {
        _error = payload is Map && payload['detail'] is String
            ? payload['detail'] as String
            : _pick(
                'Không tải được danh sách công ty.',
                'Unable to load the company list.',
              );
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error =
            '${_pick('Không tải được danh sách công ty', 'Unable to load the company list')}: $error';
        _loading = false;
      });
    }
  }

  Future<Map<String, dynamic>> _loadCompanyDetail(int companyId) async {
    final response =
        await ApiClient().dio.get('platform/companies/$companyId/');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> _loadCompanyAiConfig(int companyId) async {
    final response =
        await ApiClient().dio.get('platform/companies/$companyId/ai-config/');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> _downloadOfficialTemplate() async {
    final response = await ApiClient().dio.get<List<int>>(
          'platform/company-imports/template/',
          options: Options(responseType: ResponseType.bytes),
        );
    final bytes = response.data ?? const <int>[];
    final blob = html.Blob([bytes],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    final url = html.Url.createObjectUrlFromBlob(blob);
    html.AnchorElement(href: url)
      ..download = 'company_import_template.xlsx'
      ..click();
    html.Url.revokeObjectUrl(url);
  }

  Future<void> _downloadCredentialWorkbook(Map<String, dynamic> payload) async {
    final company =
        Map<String, dynamic>.from(payload['company'] as Map? ?? const {});
    final credentialRows =
        (payload['credential_rows'] as List<dynamic>? ?? const [])
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
    if (company.isEmpty || credentialRows.isEmpty) {
      _showError(
        _pick(
          'Không có dữ liệu tài khoản để tải về.',
          'No account data is available for download.',
        ),
      );
      return;
    }
    final response = await ApiClient().dio.post<List<int>>(
          'platform/company-credentials/workbook/',
          data: {
            'company_name': company['name'],
            'company_code': company['code'],
            'credential_rows': credentialRows,
          },
          options: Options(responseType: ResponseType.bytes),
        );
    final bytes = response.data ?? const <int>[];
    final safeCode =
        (company['code'] as String? ?? 'company').replaceAll(' ', '_');
    final blob = html.Blob([bytes],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    final url = html.Url.createObjectUrlFromBlob(blob);
    html.AnchorElement(href: url)
      ..download = 'company_credentials_$safeCode.xlsx'
      ..click();
    html.Url.revokeObjectUrl(url);
  }

  Future<void> _pickAndPreviewCompanyImport() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['xlsx'],
      withData: true,
    );
    final files = result?.files ?? const <PlatformFile>[];
    if (files.isEmpty) return;
    final file = files.first;
    if (file.bytes == null) return;

    try {
      final response = await ApiClient().dio.post(
            'platform/company-imports/preview/',
            data: FormData.fromMap({
              'excel_file':
                  MultipartFile.fromBytes(file.bytes!, filename: file.name),
            }),
          );
      if (!mounted) return;
      final payload = Map<String, dynamic>.from(response.data as Map);
      await _showImportPreviewDialog(payload);
    } on DioException catch (error) {
      _showError(error.response?.data is Map &&
              error.response?.data['detail'] is String
          ? error.response?.data['detail'] as String
          : _pick(
              'Không xem trước được file Excel.',
              'Unable to preview the Excel file.',
            ));
    } catch (error) {
      _showError(
        '${_pick('Không xem trước được file Excel', 'Unable to preview the Excel file')}: $error',
      );
    }
  }

  Future<void> _showImportPreviewDialog(Map<String, dynamic> payload) async {
    final preview = Map<String, dynamic>.from(
        payload['preview_payload'] as Map? ?? const {});
    final company =
        Map<String, dynamic>.from(preview['company'] as Map? ?? const {});
    final groups = preview['groups'] as List<dynamic>? ?? const [];
    final employees = preview['employees'] as List<dynamic>? ?? const [];
    final errors = payload['validation_errors'] as List<dynamic>? ?? const [];
    final batchId = payload['batch_id'];
    bool saving = false;
    String? errorText;

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title:
              Text(_pick('Xem trước import công ty', 'Company import preview')),
          content: SizedBox(
            width: 680,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                      '${_pick('Công ty', 'Company')}: ${company['name'] ?? ''} (${company['code'] ?? ''})'),
                  const SizedBox(height: 8),
                  Text('${_pick('Nhóm', 'Groups')}: ${groups.length}'),
                  Text('${_pick('Nhân sự', 'Employees')}: ${employees.length}'),
                  if (errors.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Text(
                      _pick('Lỗi import', 'Import errors'),
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, color: Colors.red),
                    ),
                    const SizedBox(height: 8),
                    ...errors.map((item) {
                      final row = Map<String, dynamic>.from(item as Map);
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(
                          '- ${row['sheet'] ?? ''} / ${_pick('dòng', 'row')} ${row['row'] ?? ''}: ${row['message'] ?? ''}',
                          style: const TextStyle(color: Colors.red),
                        ),
                      );
                    }),
                  ],
                  if (errorText != null) ...[
                    const SizedBox(height: 12),
                    Text(errorText!, style: const TextStyle(color: Colors.red)),
                  ],
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.of(context).pop(),
              child: Text(_pick('Đóng', 'Close')),
            ),
            FilledButton(
              onPressed: saving || errors.isNotEmpty
                  ? null
                  : () async {
                      setLocal(() {
                        saving = true;
                        errorText = null;
                      });
                      final navigator = Navigator.of(context);
                      try {
                        final response = await ApiClient()
                            .dio
                            .post('platform/company-imports/$batchId/commit/');
                        if (!mounted) return;
                        navigator.pop();
                        await _loadCompanies();
                        if (response.data is Map) {
                          await _showCreationResultDialog(
                              Map<String, dynamic>.from(response.data as Map));
                        }
                      } on DioException catch (error) {
                        final payload = error.response?.data;
                        setLocal(() {
                          errorText =
                              payload is Map && payload['detail'] is String
                                  ? payload['detail'] as String
                                  : _pick('Commit import thất bại.',
                                      'Import commit failed.');
                          saving = false;
                        });
                      } catch (error) {
                        setLocal(() {
                          errorText =
                              '${_pick('Commit import thất bại', 'Import commit failed')}: $error';
                          saving = false;
                        });
                      }
                    },
              child: saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(
                      _pick('Commit tạo công ty', 'Commit company creation')),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showBootstrapDialog(Map<String, dynamic> bootstrap) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title:
            Text(_pick('Tài khoản admin bootstrap', 'Bootstrap admin account')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Username: ${bootstrap['username'] ?? ''}'),
            const SizedBox(height: 6),
            Text('Email: ${bootstrap['email'] ?? ''}'),
            const SizedBox(height: 6),
            Text('Password: ${bootstrap['password'] ?? ''}'),
            const SizedBox(height: 12),
            Text(
              _pick(
                'Mật khẩu này chỉ hiển thị một lần và sẽ bị buộc đổi ở lần đăng nhập đầu tiên.',
                'This password is shown only once and must be changed on the first login.',
              ),
            ),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_pick('Đóng', 'Close')),
          ),
        ],
      ),
    );
  }

  Future<void> _showCreationResultDialog(Map<String, dynamic> payload) async {
    final bootstrap = Map<String, dynamic>.from(
        payload['bootstrap_admin'] as Map? ?? const {});
    final credentialRows =
        payload['credential_rows'] as List<dynamic>? ?? const [];
    final company =
        Map<String, dynamic>.from(payload['company'] as Map? ?? const {});
    bool downloading = false;
    String? error;

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(
            _pick(
              'Đã tạo xong ${company['name'] ?? 'công ty'}',
              'Finished creating ${company['name'] ?? 'the company'}',
            ),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Bootstrap admin: ${bootstrap['username'] ?? ''}'),
              const SizedBox(height: 6),
              Text('Email: ${bootstrap['email'] ?? ''}'),
              const SizedBox(height: 6),
              Text('Password: ${bootstrap['password'] ?? ''}'),
              const SizedBox(height: 12),
              Text(
                '${_pick('Tổng tài khoản trong file credential', 'Total accounts in the credential file')}: ${credentialRows.length}',
              ),
              const SizedBox(height: 12),
              Text(
                _pick(
                  'Hãy tải file Excel tài khoản ngay bây giờ. Mật khẩu ngẫu nhiên của từng nhân sự chỉ có trong kết quả tạo công ty này.',
                  'Download the account Excel file now. Each employee random password is only available in this company creation result.',
                ),
              ),
              if (error != null) ...[
                const SizedBox(height: 12),
                Text(error!, style: const TextStyle(color: Colors.red)),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: downloading ? null : () => Navigator.of(context).pop(),
              child: Text(_pick('Đóng', 'Close')),
            ),
            FilledButton.icon(
              onPressed: downloading
                  ? null
                  : () async {
                      setLocal(() {
                        downloading = true;
                        error = null;
                      });
                      try {
                        await _downloadCredentialWorkbook(payload);
                        if (!mounted) return;
                        Navigator.of(context).pop();
                      } on DioException catch (dioError) {
                        final responseData = dioError.response?.data;
                        setLocal(() {
                          error = responseData is Map &&
                                  responseData['detail'] is String
                              ? responseData['detail'] as String
                              : _pick(
                                  'Không tải được file tài khoản.',
                                  'Unable to download the account file.',
                                );
                          downloading = false;
                        });
                      } catch (otherError) {
                        setLocal(() {
                          error =
                              '${_pick('Không tải được file tài khoản', 'Unable to download the account file')}: $otherError';
                          downloading = false;
                        });
                      }
                    },
              icon: downloading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.download_outlined),
              label: Text(_pick('Tải file tài khoản', 'Download account file')),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showCompanyDialog({Map<String, dynamic>? company}) async {
    final isEdit = company != null;
    final codeCtrl =
        TextEditingController(text: company?['code'] as String? ?? '');
    final nameCtrl =
        TextEditingController(text: company?['name'] as String? ?? '');
    final descriptionCtrl =
        TextEditingController(text: company?['description'] as String? ?? '');
    final industryCtrl =
        TextEditingController(text: company?['industry'] as String? ?? '');
    final addressCtrl =
        TextEditingController(text: company?['address'] as String? ?? '');
    final emailCtrl =
        TextEditingController(text: company?['email'] as String? ?? '');
    final phoneCtrl =
        TextEditingController(text: company?['phone'] as String? ?? '');
    final websiteCtrl =
        TextEditingController(text: company?['website'] as String? ?? '');
    final contextCtrl = TextEditingController(
        text: company?['company_context'] as String? ?? '');
    String status = company?['status'] as String? ?? 'active';
    bool saving = false;
    String? error;

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(
            isEdit
                ? _pick('Chỉnh sửa công ty', 'Edit company')
                : _pick('Thông tin công ty', 'Company information'),
          ),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text(error!,
                          style: const TextStyle(color: Colors.red)),
                    ),
                  TextField(
                      controller: codeCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Mã công ty', 'Company code'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                      controller: nameCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Tên công ty', 'Company name'),
                      )),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: status,
                    items: [
                      DropdownMenuItem(
                          value: 'draft', child: Text(_pick('Nháp', 'Draft'))),
                      DropdownMenuItem(
                          value: 'active',
                          child: Text(_pick('Hoạt động', 'Active'))),
                      DropdownMenuItem(
                          value: 'locked',
                          child: Text(_pick('Bị khóa', 'Locked'))),
                      DropdownMenuItem(
                          value: 'archived',
                          child: Text(_pick('Lưu trữ', 'Archived'))),
                    ],
                    onChanged: (value) =>
                        setLocal(() => status = value ?? 'draft'),
                    decoration: InputDecoration(
                      labelText: _pick('Trạng thái', 'Status'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                      controller: descriptionCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Mô tả', 'Description'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                      controller: industryCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Lĩnh vực', 'Industry'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                      controller: addressCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Địa chỉ', 'Address'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                      controller: emailCtrl,
                      decoration:
                          InputDecoration(labelText: _pick('Email', 'Email'))),
                  const SizedBox(height: 12),
                  TextField(
                      controller: phoneCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Điện thoại', 'Phone'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                      controller: websiteCtrl,
                      decoration: InputDecoration(
                        labelText: _pick('Website', 'Website'),
                      )),
                  const SizedBox(height: 12),
                  TextField(
                    controller: contextCtrl,
                    decoration: InputDecoration(
                      labelText: _pick('Ngữ cảnh công ty', 'Company context'),
                    ),
                    minLines: 4,
                    maxLines: 8,
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.of(context).pop(),
              child: Text(_pick('Đóng', 'Close')),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      final navigator = Navigator.of(context);
                      final payload = {
                        'code': codeCtrl.text.trim(),
                        'name': nameCtrl.text.trim(),
                        'status': status,
                        'description': descriptionCtrl.text.trim(),
                        'industry': industryCtrl.text.trim(),
                        'address': addressCtrl.text.trim(),
                        'email': emailCtrl.text.trim(),
                        'phone': phoneCtrl.text.trim(),
                        'website': websiteCtrl.text.trim(),
                        'company_context': contextCtrl.text.trim(),
                      };
                      try {
                        final response = isEdit
                            ? await ApiClient().dio.patch(
                                'platform/companies/${company['id']}/',
                                data: payload)
                            : await ApiClient()
                                .dio
                                .post('platform/companies/', data: payload);
                        if (!mounted) return;
                        navigator.pop();
                        await _loadCompanies();
                        if (!isEdit && response.data is Map) {
                          await _showCreationResultDialog(
                              Map<String, dynamic>.from(response.data as Map));
                        }
                      } on DioException catch (dioError) {
                        final payload = dioError.response?.data;
                        setLocal(() {
                          error = payload is Map && payload['detail'] is String
                              ? payload['detail'] as String
                              : _pick(
                                  'Không lưu được công ty.',
                                  'Unable to save the company.',
                                );
                          saving = false;
                        });
                      } catch (otherError) {
                        setLocal(() {
                          error =
                              '${_pick('Không lưu được công ty', 'Unable to save the company')}: $otherError';
                          saving = false;
                        });
                      }
                    },
              child: saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(
                      isEdit ? _pick('Lưu', 'Save') : _pick('Tạo', 'Create'),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showAiConfigDialog(Map<String, dynamic> company) async {
    final config = await _loadCompanyAiConfig(company['id'] as int);
    if (!mounted) return;
    final aiModelCtrl =
        TextEditingController(text: config['ai_model'] as String? ?? '');
    final ocrModelCtrl =
        TextEditingController(text: config['ocr_model'] as String? ?? '');
    final imageOcrModelCtrl =
        TextEditingController(text: config['image_ocr_model'] as String? ?? '');
    final embeddingCtrl =
        TextEditingController(text: config['embedding_model'] as String? ?? '');
    final temperatureCtrl =
        TextEditingController(text: '${config['ai_temperature'] ?? 0}');
    final maxResultsCtrl =
        TextEditingController(text: '${config['ai_max_results'] ?? 6}');
    final internetResultsCtrl =
        TextEditingController(text: '${config['ai_internet_results'] ?? 3}');
    final searchEngineCtrl = TextEditingController(
        text: config['ai_search_engine'] as String? ?? 'thuvienphapluat');
    final contextCtrl =
        TextEditingController(text: config['company_context'] as String? ?? '');
    bool saving = false;
    String? error;

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(
              '${_pick('Cấu hình AI', 'AI config')} - ${company['name'] ?? ''}'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                children: [
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text(error!,
                          style: const TextStyle(color: Colors.red)),
                    ),
                  TextField(
                      controller: aiModelCtrl,
                      decoration: InputDecoration(
                          labelText: _pick('Mô hình AI', 'AI model'))),
                  const SizedBox(height: 12),
                  TextField(
                      controller: ocrModelCtrl,
                      decoration: InputDecoration(
                          labelText: _pick('Mô hình OCR tài liệu/PDF',
                              'Document/PDF OCR model'))),
                  const SizedBox(height: 12),
                  TextField(
                      controller: imageOcrModelCtrl,
                      decoration: InputDecoration(
                          labelText:
                              _pick('Mô hình OCR ảnh', 'Image OCR model'))),
                  const SizedBox(height: 12),
                  TextField(
                      controller: embeddingCtrl,
                      decoration: InputDecoration(
                          labelText:
                              _pick('Mô hình embedding', 'Embedding model'))),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                          child: TextField(
                              controller: temperatureCtrl,
                              decoration: InputDecoration(
                                  labelText:
                                      _pick('Nhiệt độ', 'Temperature')))),
                      const SizedBox(width: 12),
                      Expanded(
                          child: TextField(
                              controller: maxResultsCtrl,
                              decoration: InputDecoration(
                                  labelText: _pick('Số kết quả AI tối đa',
                                      'AI max results')))),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                          child: TextField(
                              controller: internetResultsCtrl,
                              decoration: InputDecoration(
                                  labelText: _pick('Số kết quả Internet',
                                      'Internet results')))),
                      const SizedBox(width: 12),
                      Expanded(
                          child: TextField(
                              controller: searchEngineCtrl,
                              decoration: InputDecoration(
                                  labelText: _pick(
                                      'Công cụ tìm kiếm', 'Search engine')))),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: contextCtrl,
                    decoration: InputDecoration(
                      labelText: _pick('Ngữ cảnh công ty', 'Company context'),
                    ),
                    minLines: 5,
                    maxLines: 10,
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.of(context).pop(),
              child: Text(_pick('Đóng', 'Close')),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      setLocal(() {
                        saving = true;
                        error = null;
                      });
                      final navigator = Navigator.of(context);
                      try {
                        await ApiClient().dio.patch(
                          'platform/companies/${company['id']}/ai-config/',
                          data: {
                            'ai_model': aiModelCtrl.text.trim(),
                            'ocr_model': ocrModelCtrl.text.trim(),
                            'image_ocr_model': imageOcrModelCtrl.text.trim(),
                            'embedding_model': embeddingCtrl.text.trim(),
                            'ai_temperature':
                                double.tryParse(temperatureCtrl.text.trim()) ??
                                    0,
                            'ai_max_results':
                                int.tryParse(maxResultsCtrl.text.trim()) ?? 6,
                            'ai_internet_results':
                                int.tryParse(internetResultsCtrl.text.trim()) ??
                                    3,
                            'ai_search_engine': searchEngineCtrl.text.trim(),
                            'company_context': contextCtrl.text.trim(),
                          },
                        );
                        if (!mounted) return;
                        navigator.pop();
                        await _loadCompanies();
                      } on DioException catch (dioError) {
                        final payload = dioError.response?.data;
                        setLocal(() {
                          error = payload is Map && payload['detail'] is String
                              ? payload['detail'] as String
                              : _pick(
                                  'Không lưu được cấu hình AI.',
                                  'Unable to save the AI config.',
                                );
                          saving = false;
                        });
                      } catch (otherError) {
                        setLocal(() {
                          error =
                              '${_pick('Không lưu được cấu hình AI', 'Unable to save the AI config')}: $otherError';
                          saving = false;
                        });
                      }
                    },
              child: saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_pick('Lưu', 'Save')),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _resetBootstrap(Map<String, dynamic> company) async {
    try {
      final response = await ApiClient()
          .dio
          .post('platform/companies/${company['id']}/bootstrap-reset/');
      if (!mounted) return;
      await _showBootstrapDialog(
          Map<String, dynamic>.from(response.data as Map));
      await _loadCompanies();
    } on DioException catch (error) {
      _showError(error.response?.data is Map &&
              error.response?.data['detail'] is String
          ? error.response?.data['detail'] as String
          : _pick(
              'Không reset được bootstrap admin.',
              'Unable to reset the bootstrap admin.',
            ));
    } catch (error) {
      _showError(
        '${_pick('Không reset được bootstrap admin', 'Unable to reset the bootstrap admin')}: $error',
      );
    }
  }

  Future<void> _changeStatus(
      Map<String, dynamic> company, String status) async {
    try {
      await ApiClient().dio.patch('platform/companies/${company['id']}/',
          data: {'status': status});
      await _loadCompanies();
    } on DioException catch (error) {
      _showError(
        error.response?.data is Map && error.response?.data['detail'] is String
            ? error.response?.data['detail'] as String
            : _pick(
                'Không cập nhật được trạng thái công ty.',
                'Unable to update the company status.',
              ),
      );
    } catch (error) {
      _showError(
        '${_pick('Không cập nhật được trạng thái công ty', 'Unable to update the company status')}: $error',
      );
    }
  }

  Future<void> _restoreCompany(Map<String, dynamic> company) async {
    try {
      await ApiClient()
          .dio
          .post('platform/companies/${company['id']}/restore/');
      await _loadCompanies();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _pick(
              'Đã khôi phục ${company['name']}.',
              'Restored ${company['name']}.',
            ),
          ),
        ),
      );
    } on DioException catch (error) {
      _showError(
        error.response?.data is Map && error.response?.data['detail'] is String
            ? error.response?.data['detail'] as String
            : _pick(
                'Không khôi phục được công ty.',
                'Unable to restore the company.',
              ),
      );
    } catch (error) {
      _showError(
        '${_pick('Không khôi phục được công ty', 'Unable to restore the company')}: $error',
      );
    }
  }

  Future<void> _softDeleteCompany(Map<String, dynamic> company) async {
    await ApiClient().dio.delete('platform/companies/${company['id']}/');
    await _loadCompanies();
  }

  Future<void> _confirmSoftDelete(Map<String, dynamic> company) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(_pick('Xóa mềm công ty', 'Soft delete company')),
            content: Text(
              _pick(
                'Công ty ${company['name']} sẽ được đưa vào thùng rác. Sau đó có thể khôi phục hoặc xóa cứng.',
                '${company['name']} will be moved to trash. It can be restored or hard-deleted later.',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: Text(_pick('Hủy', 'Cancel')),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: Text(_pick('Xóa mềm', 'Soft delete')),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;
    try {
      await _softDeleteCompany(company);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _pick(
              'Đã đưa công ty vào thùng rác.',
              'Moved the company to trash.',
            ),
          ),
        ),
      );
    } on DioException catch (error) {
      _showError(
        error.response?.data is Map && error.response?.data['detail'] is String
            ? error.response?.data['detail'] as String
            : _pick(
                'Không xóa mềm được công ty.',
                'Unable to soft-delete the company.',
              ),
      );
    } catch (error) {
      _showError(
        '${_pick('Không xóa mềm được công ty', 'Unable to soft-delete the company')}: $error',
      );
    }
  }

  Future<void> _showHardDeleteDialog(Map<String, dynamic> company) async {
    final platformAdminPasswordCtrl = TextEditingController();
    final bootstrapAdmin = company['bootstrap_admin'];
    final bootstrapUsername = company['bootstrap_admin_username'] as String? ??
        (bootstrapAdmin is Map
            ? (bootstrapAdmin['username'] as String? ?? 'admin')
            : 'admin');
    bool deleting = false;
    String? error;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(_pick('Xóa cứng công ty', 'Hard delete company')),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${_pick('Công ty', 'Company')}: ${company['name']} (${company['code']})',
                ),
                const SizedBox(height: 8),
                Text(
                  '${_pick('Admin công ty đối chiếu', 'Bootstrap admin')}: $bootstrapUsername',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 12),
                Text(
                  _pick(
                    'Thao tác này sẽ xóa toàn bộ dữ liệu công ty, người dùng của công ty, file namespace và không thể hoàn tác.',
                    'This action deletes all company data, company users, file namespaces, and cannot be undone.',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: platformAdminPasswordCtrl,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: _pick(
                      'Mật khẩu admin quản trị nền tảng',
                      'Platform admin password',
                    ),
                    border: OutlineInputBorder(),
                  ),
                ),
                if (error != null) ...[
                  const SizedBox(height: 12),
                  Text(error!, style: const TextStyle(color: Colors.red)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: deleting ? null : () => Navigator.of(context).pop(),
              child: Text(_pick('Đóng', 'Close')),
            ),
            FilledButton(
              onPressed: deleting
                  ? null
                  : () async {
                      setLocal(() {
                        deleting = true;
                        error = null;
                      });
                      try {
                        await ApiClient().dio.post(
                          'platform/companies/${company['id']}/hard-delete/',
                          data: {
                            'platform_admin_password':
                                platformAdminPasswordCtrl.text,
                          },
                        );
                        if (!mounted) return;
                        Navigator.of(context).pop();
                        await _loadCompanies();
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              _pick(
                                'Đã xóa cứng ${company['name']}.',
                                'Hard-deleted ${company['name']}.',
                              ),
                            ),
                          ),
                        );
                      } on DioException catch (dioError) {
                        final payload = dioError.response?.data;
                        setLocal(() {
                          error = payload is Map && payload['detail'] is String
                              ? payload['detail'] as String
                              : _pick(
                                  'Không xóa cứng được công ty.',
                                  'Unable to hard-delete the company.',
                                );
                          deleting = false;
                        });
                      } catch (otherError) {
                        setLocal(() {
                          error =
                              '${_pick('Không xóa cứng được công ty', 'Unable to hard-delete the company')}: $otherError';
                          deleting = false;
                        });
                      }
                    },
              child: deleting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_pick('Xóa cứng', 'Hard delete')),
            ),
          ],
        ),
      ),
    );
    platformAdminPasswordCtrl.dispose();
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  Future<void> _showCompanyDetailDialog(Map<String, dynamic> company) async {
    final detail = await _loadCompanyDetail(company['id'] as int);
    if (!mounted) return;
    final isDeleted = (detail['status'] as String? ?? '') == 'deleted';
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${detail['name'] ?? ''} (${detail['code'] ?? ''})'),
        content: SizedBox(
          width: 720,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Wrap(
                  spacing: 16,
                  runSpacing: 8,
                  children: [
                    Text(
                        '${_pick('Trạng thái', 'Status')}: ${_statusLabel('${detail['status'] ?? ''}')}'),
                    Text(
                        '${_pick('Người dùng', 'Users')}: ${detail['user_count'] ?? 0}'),
                    Text(
                        '${_pick('Nhóm', 'Groups')}: ${detail['group_count'] ?? 0}'),
                  ],
                ),
                const SizedBox(height: 12),
                if ((detail['description'] as String? ?? '').isNotEmpty)
                  Text(
                      '${_pick('Mô tả', 'Description')}: ${detail['description']}'),
                if ((detail['industry'] as String? ?? '').isNotEmpty)
                  Text(
                      '${_pick('Lĩnh vực', 'Industry')}: ${detail['industry']}'),
                if ((detail['address'] as String? ?? '').isNotEmpty)
                  Text('${_pick('Địa chỉ', 'Address')}: ${detail['address']}'),
                if ((detail['email'] as String? ?? '').isNotEmpty)
                  Text('Email: ${detail['email']}'),
                if ((detail['phone'] as String? ?? '').isNotEmpty)
                  Text('${_pick('Điện thoại', 'Phone')}: ${detail['phone']}'),
                if ((detail['website'] as String? ?? '').isNotEmpty)
                  Text('Website: ${detail['website']}'),
                const SizedBox(height: 12),
                Text(_pick('Bootstrap admin', 'Bootstrap admin'),
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(
                    '${_pick('Tài khoản', 'Username')}: ${detail['bootstrap_admin']?['username'] ?? 'admin'}'),
                Text('Email: ${detail['bootstrap_admin']?['email'] ?? ''}'),
                const SizedBox(height: 12),
                Text(_pick('Ngữ cảnh công ty', 'Company context'),
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Text(
                      (detail['company_context'] as String? ?? '').isEmpty
                          ? _pick('Chưa có.', 'Not available yet.')
                          : detail['company_context'] as String),
                ),
                const SizedBox(height: 12),
                Text(_pick('Lịch sử import', 'Import history'),
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                ...(detail['recent_import_batches'] as List<dynamic>? ??
                        const [])
                    .map((item) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(
                            '- Batch #${item['id']} | ${item['source_type']} | ${item['status']} | ${_pick('lỗi', 'errors')}: ${item['validation_error_count']}',
                          ),
                        )),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_pick('Đóng', 'Close')),
          ),
          if (isDeleted)
            OutlinedButton(
              onPressed: () async {
                Navigator.of(context).pop();
                await _restoreCompany(detail);
              },
              child: Text(_pick('Khôi phục', 'Restore')),
            ),
          if (isDeleted)
            FilledButton.tonal(
              onPressed: () async {
                Navigator.of(context).pop();
                await _showHardDeleteDialog(detail);
              },
              child: Text(_pick('Xóa cứng', 'Hard delete')),
            ),
          if (!isDeleted)
            OutlinedButton(
              onPressed: () async {
                Navigator.of(context).pop();
                await _showAiConfigDialog(detail);
              },
              child: Text(_pick('Cấu hình AI', 'AI config')),
            ),
          if (!isDeleted)
            OutlinedButton(
              onPressed: () async {
                Navigator.of(context).pop();
                await _resetBootstrap(detail);
              },
              child: Text(_pick('Reset bootstrap', 'Reset bootstrap')),
            ),
          if (!isDeleted)
            FilledButton(
              onPressed: () async {
                Navigator.of(context).pop();
                await _showCompanyDialog(company: detail);
              },
              child: Text(_pick('Chỉnh sửa', 'Edit')),
            ),
        ],
      ),
    );
  }

  Future<void> _showManualWizard() async {
    final payload = await showPlatformCompanyWizard(context);
    if (payload == null) return;
    try {
      final response =
          await ApiClient().dio.post('platform/companies/', data: payload);
      if (!mounted) return;
      await _loadCompanies();
      if (response.data is Map) {
        await _showCreationResultDialog(
            Map<String, dynamic>.from(response.data as Map));
      }
    } on DioException catch (dioError) {
      final payload = dioError.response?.data;
      _showError(
        payload is Map && payload['detail'] is String
            ? payload['detail'] as String
            : _pick('Không tạo được công ty.', 'Unable to create the company.'),
      );
    } catch (otherError) {
      _showError(
        '${_pick('Không tạo được công ty', 'Unable to create the company')}: $otherError',
      );
    }
  }

  Future<void> _handleMenu(Map<String, dynamic> company, String value) async {
    // === BEGIN R5: dashboard navigate ===
    if (value == 'dashboard') {
      final id = company['id'];
      if (id is int) {
        context.go('/platform/companies/$id');
      }
      return;
    }
    // === END R5 ===
    if (value == 'detail') {
      await _showCompanyDetailDialog(company);
      return;
    }
    if (value == 'edit') {
      final detail = await _loadCompanyDetail(company['id'] as int);
      await _showCompanyDialog(company: detail);
      return;
    }
    if (value == 'ai') {
      await _showAiConfigDialog(company);
      return;
    }
    if (value == 'bootstrap') {
      await _resetBootstrap(company);
      return;
    }
    if (value == 'lock') {
      await _changeStatus(company, 'locked');
      return;
    }
    if (value == 'activate') {
      await _changeStatus(company, 'active');
      return;
    }
    if (value == 'archive') {
      await _changeStatus(company, 'archived');
      return;
    }
    if (value == 'restore') {
      await _restoreCompany(company);
      return;
    }
    if (value == 'hard_delete') {
      await _showHardDeleteDialog(company);
      return;
    }
    if (value == 'delete') {
      await _confirmSoftDelete(company);
    }
  }

  void _goToViewMode(String mode) {
    final normalized = mode == 'trash' ? 'trash' : 'active';
    if (!mounted) return;
    if (normalized == 'trash') {
      context.go('/platform/companies/trash');
      return;
    }
    context.go('/platform/companies');
  }

  Widget _buildSubNavChip({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF0F172A) : Colors.white,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected ? const Color(0xFF0F172A) : const Color(0xFFE2E8F0),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 18,
              color: selected ? Colors.white : const Color(0xFF475569),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: selected ? Colors.white : const Color(0xFF334155),
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final showingTrash = _viewMode == 'trash';
    final visibleCompanies = showingTrash ? _deletedCompanies : _companies;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _pick('Quản trị công ty', 'Company administration'),
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              FilledButton.icon(
                onPressed: _showManualWizard,
                icon: const Icon(Icons.account_tree_outlined),
                label: Text(
                    _pick('Tạo công ty thủ công', 'Create company manually')),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              OutlinedButton.icon(
                onPressed: _downloadOfficialTemplate,
                icon: const Icon(Icons.download_outlined),
                label: Text(
                    _pick('Tải template Excel', 'Download Excel template')),
              ),
              OutlinedButton.icon(
                onPressed: _pickAndPreviewCompanyImport,
                icon: const Icon(Icons.upload_file_outlined),
                label: Text(_pick(
                    'Import công ty từ Excel', 'Import companies from Excel')),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildSubNavChip(
                  label: _pick(
                    'Quản lý công ty (${_companies.length})',
                    'Companies (${_companies.length})',
                  ),
                  icon: Icons.business_outlined,
                  selected: !showingTrash,
                  onTap: () => _goToViewMode('active'),
                ),
                const SizedBox(width: 12),
                _buildSubNavChip(
                  label: _pick(
                    'Thùng rác (${_deletedCompanies.length})',
                    'Trash (${_deletedCompanies.length})',
                  ),
                  icon: Icons.delete_outline,
                  selected: showingTrash,
                  onTap: () => _goToViewMode('trash'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchCtrl,
                  decoration: InputDecoration(
                    hintText: _pick(
                      'Tìm theo tên hoặc mã công ty',
                      'Search by company name or code',
                    ),
                    prefixIcon: Icon(Icons.search),
                  ),
                  onSubmitted: (_) => _loadCompanies(),
                ),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _loadCompanies,
                icon: const Icon(Icons.refresh),
                label: Text(_pick('Tải lại', 'Reload')),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_loading)
            const Center(
                child: Padding(
                    padding: EdgeInsets.all(24),
                    child: CircularProgressIndicator()))
          else if (_error != null)
            Text(_error!, style: const TextStyle(color: Colors.red))
          else if (visibleCompanies.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  _pick('Không có dữ liệu phù hợp.', 'No matching data.'),
                ),
              ),
            )
          else
            Column(
              children: visibleCompanies
                  .map(
                    (company) => Card(
                      child: ListTile(
                        onTap: () => _showCompanyDetailDialog(company),
                        leading: CircleAvatar(
                          child: Icon(showingTrash
                              ? Icons.delete_outline
                              : Icons.apartment_outlined),
                        ),
                        title: Text('${company['name']} (${company['code']})'),
                        subtitle: Text(
                          showingTrash
                              ? '${_pick('Trong thùng rác', 'In trash')} | ${_pick('Admin đối chiếu', 'Bootstrap admin')}: ${company['bootstrap_admin_username'] ?? 'admin'} | ${_pick('Người dùng', 'Users')}: ${company['user_count'] ?? 0}'
                              : '${_pick('Trạng thái', 'Status')}: ${_statusLabel('${company['status'] ?? ''}')} | ${_pick('Người dùng', 'Users')}: ${company['user_count'] ?? 0} | ${_pick('Nhóm', 'Groups')}: ${company['group_count'] ?? 0}',
                        ),
                        trailing: PopupMenuButton<String>(
                          onSelected: (value) => _handleMenu(company, value),
                          itemBuilder: (_) => showingTrash
                              ? [
                                  PopupMenuItem(
                                      value: 'detail',
                                      child:
                                          Text(_pick('Chi tiết', 'Details'))),
                                  PopupMenuItem(
                                      value: 'restore',
                                      child:
                                          Text(_pick('Khôi phục', 'Restore'))),
                                  PopupMenuItem(
                                      value: 'hard_delete',
                                      child: Text(
                                          _pick('Xóa cứng', 'Hard delete'))),
                                ]
                              : [
                                  // === BEGIN R5: dashboard menu entry ===
                                  PopupMenuItem(
                                      value: 'dashboard',
                                      child:
                                          Text(_pick('Mở dashboard', 'Open dashboard'))),
                                  // === END R5 ===
                                  PopupMenuItem(
                                      value: 'detail',
                                      child:
                                          Text(_pick('Chi tiết', 'Details'))),
                                  PopupMenuItem(
                                      value: 'edit',
                                      child: Text(_pick('Chỉnh sửa', 'Edit'))),
                                  PopupMenuItem(
                                      value: 'ai',
                                      child: Text(
                                          _pick('Cấu hình AI', 'AI config'))),
                                  PopupMenuItem(
                                      value: 'bootstrap',
                                      child: Text(_pick('Reset bootstrap',
                                          'Reset bootstrap'))),
                                  PopupMenuItem(
                                      value: 'activate',
                                      child:
                                          Text(_pick('Kích hoạt', 'Activate'))),
                                  PopupMenuItem(
                                      value: 'lock',
                                      child: Text(_pick('Khóa', 'Lock'))),
                                  PopupMenuItem(
                                      value: 'archive',
                                      child: Text(_pick('Lưu trữ', 'Archive'))),
                                  PopupMenuItem(
                                      value: 'delete',
                                      child: Text(
                                          _pick('Xóa mềm', 'Soft delete'))),
                                ],
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }
}
