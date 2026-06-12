// === MÀN HÌNH CẤU HÌNH AI (admin) ===
// Cấu hình AI cho công ty: chọn model chat (_buildChatAiModelCard, danh sách từ 'admin/ollama-models/') và NGỮ CẢNH CÔNG TY (_buildCompanyContextCard, _saveCompanyContext) dùng cho prefill/trợ lý.
// - _loadConfig(): GET 'admin/ai-config/'; _save()/_saveChatAiModel(): lưu cấu hình.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/admin/ai_config_screen.dart.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';

// Widget màn CẤU HÌNH AI của công ty (admin) — ConsumerStatefulWidget.

class AiConfigScreen extends ConsumerStatefulWidget {
  const AiConfigScreen({super.key});

  @override
  ConsumerState<AiConfigScreen> createState() => _AiConfigScreenState();
}

// State màn cấu hình AI: nạp/sửa cấu hình model, ngữ cảnh công ty, model ChatAI.

class _AiConfigScreenState extends ConsumerState<AiConfigScreen> {
  AppStrings get _strings => AppStrings.of(context);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  // Config values
  String _model = '';
  String _chatAiModel = '';
  String _ocrModel = '';
  String _imageOcrModel = '';
  String _embeddingModel = '';
  String _searchEngine = 'thuvienphapluat';
  double _temperature = 0.0;
  int _maxResults = 3;
  int _internetResults = 3;
  String _companyContext = '';

  // Dropdown options from Ollama
  List<String> _chatModels = [];
  List<String> _embedModels = [];
  String? _ollamaError;

  bool _loading = true;
  bool _saving = false;
  bool _editing = false;

  bool _editingChatAiModel = false;
  bool _savingChatAiModel = false;

  bool _editingCompany = false;
  bool _savingCompany = false;

  final _maxResultsCtrl = TextEditingController();
  final _internetResultsCtrl = TextEditingController();
  final _companyContextCtrl = TextEditingController();

  @override
  // Mở màn: nạp toàn bộ cấu hình AI (_loadAll).

  void initState() {
    super.initState();
    _loadAll();
  }

  @override
  // Rời màn: dọn các controller.

  void dispose() {
    _maxResultsCtrl.dispose();
    _internetResultsCtrl.dispose();
    _companyContextCtrl.dispose();
    super.dispose();
  }

  // Nạp song song: cấu hình AI + danh sách model Ollama.

  Future<void> _loadAll() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    await Future.wait([_loadConfig(), _loadOllamaModels()]);
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = false);
  }

  // Nạp cấu hình AI hiện tại của công ty ('ai-config/').

  Future<void> _loadConfig() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('admin/ai-config/');
      final cfg = resp.data as Map<String, dynamic>;
      _model = cfg['ai_model'] ?? '';
      _chatAiModel = cfg['chat_ai_model'] ?? '';
      _ocrModel = cfg['ocr_model'] ?? '';
      _imageOcrModel = cfg['image_ocr_model'] ?? '';
      _embeddingModel = cfg['embedding_model'] ?? '';
      _searchEngine = 'thuvienphapluat';
      _maxResults = (cfg['ai_max_results'] ?? 3) as int;
      _internetResults = (cfg['ai_internet_results'] ?? 3) as int;
      _temperature = ((cfg['ai_temperature'] ?? 0.0) as num).toDouble();
      _companyContext = cfg['company_context'] ?? '';
      _maxResultsCtrl.text = _maxResults.toString();
      _internetResultsCtrl.text = _internetResults.toString();
      _companyContextCtrl.text = _companyContext;
    } catch (_) {}
  }

  // Nạp danh sách model Ollama khả dụng để chọn.

  Future<void> _loadOllamaModels() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('admin/ollama-models/');
      final data = resp.data as Map<String, dynamic>;
      _chatModels = List<String>.from(data['chat_models'] ?? []);
      _embedModels = List<String>.from(data['embed_models'] ?? []);
      _ollamaError = data['error'] as String?;
      if (_ollamaError != null && _ollamaError!.isEmpty) _ollamaError = null;
    } catch (e) {
      _ollamaError = e.toString();
    }
  }

  // Nút Lưu: lưu cấu hình AI (model, search engine...) cho công ty.

  Future<void> _save() async {
    final maxR = int.tryParse(_maxResultsCtrl.text.trim()) ?? _maxResults;
    final internetR =
        int.tryParse(_internetResultsCtrl.text.trim()) ?? _internetResults;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _saving = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.patch('admin/ai-config/', data: {
        'ai_model': _model,
        'ocr_model': _ocrModel,
        'image_ocr_model': _imageOcrModel,
        'embedding_model': _embeddingModel,
        'ai_search_engine': _searchEngine,
        'ai_max_results': maxR,
        'ai_internet_results': internetR,
        'ai_temperature': _temperature,
      });
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          _saving = false;
          _editing = false;
          _maxResults = maxR;
          _internetResults = internetR;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
                  _pick('Da luu cau hinh AI.', 'Saved the AI configuration.')),
              backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${_pick('Loi', 'Error')}: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
  }

  // Lưu ngữ cảnh công ty (dùng cho điền tự động/ChatAI).

  Future<void> _saveCompanyContext() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _savingCompany = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.patch('admin/ai-config/', data: {
        'company_context': _companyContextCtrl.text,
      });
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          _savingCompany = false;
          _editingCompany = false;
          _companyContext = _companyContextCtrl.text;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(_pick(
                  'Da luu ngu canh cong ty.', 'Saved the company context.')),
              backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _savingCompany = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${_pick('Loi', 'Error')}: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
  }

  // Nhãn công cụ tìm kiếm web (cho cấu hình RAG).

  String _searchEngineLabel(String value) {
    switch (value) {
      case 'thuvienphapluat':
        return 'THU VIEN PHAP LUAT';
      default:
        return 'THU VIEN PHAP LUAT';
    }
  }

  @override
  // Dựng màn: chế độ chỉ đọc / form sửa cấu hình AI.

  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                const Icon(Icons.psychology_outlined,
                    size: 24, color: Color(0xFF1565C0)),
                const SizedBox(width: 10),
                Text(_pick('Cau hinh AI', 'AI configuration'),
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const Spacer(),
                if (!_editing && !_loading)
                  FilledButton.icon(
                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                    onPressed: () => setState(() => _editing = true),
                    icon: const Icon(Icons.edit, size: 16),
                    label: Text(_pick('Chinh sua', 'Edit')),
                  ),
              ]),
              const SizedBox(height: 4),
              Text(
                  _pick('Cai dat model AI va tham so cho toan he thong.',
                      'Configure AI models and shared parameters for the whole system.'),
                  style: TextStyle(color: Colors.grey.shade600)),
              const SizedBox(height: 24),
              if (_loading)
                const Center(child: CircularProgressIndicator())
              else ...[
                // Ollama warning banner
                if (_ollamaError != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 10),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      border: Border.all(color: Colors.orange.shade300),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(children: [
                      Icon(Icons.warning_amber_outlined,
                          color: Colors.orange.shade700, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _pick(
                            'Khong the ket noi Ollama. Ban van co the nhap ten model thu cong.',
                            'Could not connect to Ollama. You can still type model names manually.',
                          ),
                          style: TextStyle(
                              color: Colors.orange.shade800, fontSize: 13),
                        ),
                      ),
                    ]),
                  ),
                ],

                // ── Chat AI Model (separate config section, on top) ─────
                _buildChatAiModelCard(),

                const SizedBox(height: 18),

                // ── AI Config Card ─────────────────────────────────────
                Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: _editing ? _buildEditForm() : _buildReadOnly(),
                  ),
                ),
                if (_editing) ...[
                  const SizedBox(height: 20),
                  Row(children: [
                    FilledButton.icon(
                      onPressed: _saving ? null : _save,
                      icon: _saving
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.save_outlined, size: 16),
                      label: Text(_pick('Luu cau hinh', 'Save configuration')),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton(
                      onPressed: _saving
                          ? null
                          : () {
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              setState(() => _editing = false);
                              _loadAll();
                            },
                      child: Text(_pick('Huy', 'Cancel')),
                    ),
                  ]),
                ],

                const SizedBox(height: 32),

                // ── Company Context Card ────────────────────────────────
                _buildCompanyContextCard(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // Lưu riêng model dùng cho ChatAI.

  Future<void> _saveChatAiModel() async {
    setState(() => _savingChatAiModel = true);
    try {
      await ApiClient().dio.patch('admin/ai-config/', data: {
        'chat_ai_model': _chatAiModel,
      });
      if (!mounted) return;
      setState(() {
        _savingChatAiModel = false;
        _editingChatAiModel = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_pick(
              'Da luu model Tro ly Chat AI.', 'Saved Chat AI assistant model.')),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _savingChatAiModel = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${_pick('Loi', 'Error')}: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Widget _buildChatAiModelCard() {
    final defaultLabel = _pick('Mac dinh: kimi-k2.6:cloud',
        'Default: kimi-k2.6:cloud');
    final effective = _chatAiModel.trim().isEmpty
        ? (_model.trim().isEmpty ? 'kimi-k2.6:cloud' : _model)
        : _chatAiModel;
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1D4ED8), Color(0xFF3B82F6)],
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.forum_outlined,
                    color: Colors.white, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _pick('Model Tro ly Chat AI',
                          'Chat AI assistant model'),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _pick(
                        'Model dung rieng cho ChatAI + Voice AI. Co the chon model Ollama local hoac cloud.',
                        'Dedicated model for ChatAI + Voice AI. Pick a local or cloud Ollama model.',
                      ),
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFF64748B)),
                    ),
                  ],
                ),
              ),
              if (!_editingChatAiModel)
                TextButton.icon(
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  label: Text(_pick('Sua', 'Edit')),
                  onPressed: () =>
                      setState(() => _editingChatAiModel = true),
                ),
            ]),
            const SizedBox(height: 16),
            if (_editingChatAiModel) ...[
              _buildModelDropdown(
                label: _pick('Chon model cho Chat AI',
                    'Pick a model for Chat AI'),
                icon: Icons.auto_awesome_outlined,
                value: _chatAiModel.trim().isEmpty
                    ? 'kimi-k2.6:cloud'
                    : _chatAiModel,
                options: _chatModels,
                onChanged: (v) => setState(
                    () => _chatAiModel = v ?? _chatAiModel),
              ),
              const SizedBox(height: 8),
              Text(
                defaultLabel,
                style: const TextStyle(
                    fontSize: 11, color: Color(0xFF94A3B8)),
              ),
              const SizedBox(height: 14),
              Row(children: [
                FilledButton.icon(
                  onPressed: _savingChatAiModel ? null : _saveChatAiModel,
                  icon: _savingChatAiModel
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.save_outlined, size: 16),
                  label:
                      Text(_pick('Luu model Chat AI', 'Save Chat AI model')),
                ),
                const SizedBox(width: 10),
                OutlinedButton(
                  onPressed: _savingChatAiModel
                      ? null
                      : () {
                          setState(() {
                            _editingChatAiModel = false;
                          });
                          _loadConfig();
                        },
                  child: Text(_pick('Huy', 'Cancel')),
                ),
              ]),
            ] else
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFBFDBFE)),
                ),
                child: Row(children: [
                  const Icon(Icons.auto_awesome,
                      color: Color(0xFF1D4ED8), size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          effective,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF1E3A8A),
                          ),
                        ),
                        if (_chatAiModel.trim().isEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 2),
                            child: Text(
                              _pick(
                                  '(Dang ke thua tu Model AI chinh)',
                                  '(Inherited from primary AI model)'),
                              style: const TextStyle(
                                  fontSize: 11,
                                  color: Color(0xFF64748B),
                                  fontStyle: FontStyle.italic),
                            ),
                          ),
                      ],
                    ),
                  ),
                ]),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompanyContextCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          const Icon(Icons.business_outlined,
              size: 22, color: Color(0xFF1565C0)),
          const SizedBox(width: 10),
          Text(_pick('Ngu canh cong ty', 'Company context'),
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const Spacer(),
          if (!_editingCompany)
            FilledButton.icon(
              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

              onPressed: () => setState(() {
                _editingCompany = true;
                _companyContextCtrl.text = _companyContext;
              }),
              icon: const Icon(Icons.edit, size: 16),
              label: Text(_pick('Chinh sua', 'Edit')),
            ),
        ]),
        const SizedBox(height: 4),
        Text(
          _pick(
            'Thong tin cong ty (ten, ma so thue, dia chi, nguoi dai dien...). AI se dung thong tin nay de tu dong dien vao van ban khi sinh VB.',
            'Company details such as name, tax code, address, and representative. AI uses this context to prefill generated documents.',
          ),
          style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
        ),
        const SizedBox(height: 16),
        Card(
          elevation: 1,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: _editingCompany
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _companyContextCtrl,
                        minLines: 8,
                        maxLines: 20,
                        decoration: InputDecoration(
                          labelText:
                              _pick('Ngu canh cong ty', 'Company context'),
                          hintText: _pick(
                            'Vi du:\nTen cong ty: Cong ty TNHH ABC\n'
                                'Ma so thue: 0123456789\n'
                                'Dia chi: 123 Nguyen Hue, Quan 1, TP.HCM\n'
                                'Nguoi dai dien phap luat: Nguyen Van A\n'
                                'Chuc vu: Giam doc\n'
                                'Dien thoai: 028 1234 5678\n'
                                'Website: www.abc.com.vn',
                            'Example:\nCompany name: ABC Co., Ltd.\n'
                                'Tax code: 0123456789\n'
                                'Address: 123 Nguyen Hue, District 1, Ho Chi Minh City\n'
                                'Legal representative: Nguyen Van A\n'
                                'Title: Director\n'
                                'Phone: 028 1234 5678\n'
                                'Website: www.abc.com.vn',
                          ),
                          border: const OutlineInputBorder(),
                          alignLabelWithHint: true,
                          contentPadding: const EdgeInsets.all(14),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(children: [
                        FilledButton.icon(
                          onPressed:
                              _savingCompany ? null : _saveCompanyContext,
                          icon: _savingCompany
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.save_outlined, size: 16),
                          label: Text(_pick('Luu ngu canh', 'Save context')),
                        ),
                        const SizedBox(width: 12),
                        OutlinedButton(
                          onPressed: _savingCompany
                              ? null
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              : () => setState(() {
                                    _editingCompany = false;
                                    _companyContextCtrl.text = _companyContext;
                                  }),
                          child: Text(_pick('Huy', 'Cancel')),
                        ),
                      ]),
                    ],
                  )
                : _companyContext.isNotEmpty
                    ? Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.grey.shade200),
                        ),
                        child: Text(
                          _companyContext,
                          style: const TextStyle(fontSize: 14, height: 1.6),
                        ),
                      )
                    : Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 32),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: Colors.grey.shade200,
                              style: BorderStyle.solid),
                        ),
                        child: Column(children: [
                          Icon(Icons.business_center_outlined,
                              size: 40, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text(
                              _pick('Chua co ngu canh cong ty.',
                                  'No company context yet.'),
                              style: TextStyle(color: Colors.grey.shade500)),
                          const SizedBox(height: 4),
                          Text(
                              _pick('Nhan "Chinh sua" de them thong tin.',
                                  'Press "Edit" to add context.'),
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey.shade400)),
                        ]),
                      ),
          ),
        ),
      ],
    );
  }

  // Dựng chế độ xem cấu hình (chỉ đọc).

  Widget _buildReadOnly() {
    return LayoutBuilder(builder: (context, cs) {
      final wide = cs.maxWidth >= 500;
      final tiles = [
        _cfgTile(
            Icons.smart_toy_outlined, _pick('Model AI', 'AI model'), _model),
        _cfgTile(
            Icons.picture_as_pdf_outlined,
            _pick('Model OCR tai lieu/PDF', 'Document/PDF OCR model'),
            _ocrModel),
        _cfgTile(Icons.document_scanner_outlined,
            _pick('Model OCR anh', 'Image OCR model'), _imageOcrModel),
        _cfgTile(Icons.memory_outlined, 'Embedding Model', _embeddingModel),
        _cfgTile(
            Icons.travel_explore_outlined,
            _pick('Nguon Internet', 'Internet source'),
            _searchEngineLabel(_searchEngine)),
        _cfgTile(Icons.thermostat_outlined, _pick('Nhiệt độ', 'Temperature'),
            _temperature.toStringAsFixed(2)),
        _cfgTile(
            Icons.format_list_numbered_outlined,
            _pick('So ket qua RAG toi da', 'Maximum RAG results'),
            _maxResults.toString()),
      ];
      tiles.add(_cfgTile(
          Icons.public_outlined,
          _pick('So ket qua Internet', 'Internet result count'),
          _internetResults.toString()));
      if (wide) {
        return Column(children: [
          Row(children: [
            Expanded(child: tiles[0]),
            const SizedBox(width: 12),
            Expanded(child: tiles[1]),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: tiles[2]),
            const SizedBox(width: 12),
            Expanded(child: tiles[3]),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: tiles[4]),
            const SizedBox(width: 12),
            Expanded(child: tiles[5]),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: tiles[6]),
            const SizedBox(width: 12),
            Expanded(child: tiles[7]),
          ]),
        ]);
      }
      return Column(children: tiles);
    });
  }

  // Dựng 1 dòng cấu hình (icon + nhãn + giá trị) ở chế độ chỉ đọc.

  Widget _cfgTile(IconData icon, String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(children: [
        Icon(icon, size: 18, color: Colors.blueGrey.shade400),
        const SizedBox(width: 12),
        Expanded(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label,
                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500)),
            const SizedBox(height: 3),
            Text(value.isNotEmpty ? value : '—',
                style:
                    const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          ]),
        ),
      ]),
    );
  }

  // Dựng form chỉnh sửa cấu hình AI.

  Widget _buildEditForm() {
    final searchEngineField = DropdownButtonFormField<String>(
      value: _searchEngine,
      decoration: InputDecoration(
        labelText: _pick('Nguon Internet', 'Internet source'),
        prefixIcon: Icon(Icons.travel_explore_outlined, size: 18),
        border: const OutlineInputBorder(),
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      ),
      items: const [
        DropdownMenuItem(
            value: 'thuvienphapluat', child: Text('THU VIEN PHAP LUAT')),
      ],
      onChanged: (value) {
        if (value == null || value.isEmpty) return;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _searchEngine = value);
      },
    );
    final maxResultsField = TextFormField(
      controller: _maxResultsCtrl,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(
        labelText: _pick('So ket qua RAG toi da', 'Maximum RAG results'),
        prefixIcon: Icon(Icons.format_list_numbered_outlined, size: 18),
        border: const OutlineInputBorder(),
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        hintText: '1 - 20',
      ),
    );
    final internetResultsField = TextFormField(
      controller: _internetResultsCtrl,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(
        labelText: _pick('So ket qua Internet', 'Internet result count'),
        prefixIcon: Icon(Icons.public_outlined, size: 18),
        border: const OutlineInputBorder(),
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        hintText: '0 - 20',
        helperText:
            _pick('0 = tat goi y Internet', '0 = disable internet suggestions'),
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(builder: (context, cs) {
          final wide = cs.maxWidth >= 500;
          final f1 = _buildModelDropdown(
            label: 'Model AI',
            icon: Icons.smart_toy_outlined,
            value: _model,
            options: _chatModels,
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            onChanged: (v) => setState(() => _model = v ?? _model),
          );
          final f2 = _buildModelDropdown(
            label: _pick('Model OCR tai lieu/PDF', 'Document/PDF OCR model'),
            icon: Icons.picture_as_pdf_outlined,
            value: _ocrModel,
            options: _chatModels,
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            onChanged: (v) => setState(() => _ocrModel = v ?? _ocrModel),
          );
          final f3 = _buildModelDropdown(
            label: _pick('Model OCR anh', 'Image OCR model'),
            icon: Icons.document_scanner_outlined,
            value: _imageOcrModel,
            options: _chatModels,
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            onChanged: (v) =>
                setState(() => _imageOcrModel = v ?? _imageOcrModel),
          );
          final f4 = _buildModelDropdown(
            label: 'Embedding Model',
            icon: Icons.memory_outlined,
            value: _embeddingModel,
            options: _embedModels,
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            onChanged: (v) =>
                setState(() => _embeddingModel = v ?? _embeddingModel),
          );
          if (wide) {
            return Column(
              children: [
                Row(children: [
                  Expanded(child: f1),
                  const SizedBox(width: 14),
                  Expanded(child: f2),
                ]),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: f3),
                  const SizedBox(width: 14),
                  Expanded(child: f4),
                ]),
              ],
            );
          }
          return Column(
            children: [
              f1,
              const SizedBox(height: 12),
              f2,
              const SizedBox(height: 12),
              f3,
              const SizedBox(height: 12),
              f4,
            ],
          );
        }),
        const SizedBox(height: 20),

        // Temperature slider
        Row(children: [
          const Icon(Icons.thermostat_outlined,
              size: 16, color: Colors.blueGrey),
          const SizedBox(width: 8),
          Text('${_pick('Nhiệt độ', 'Temperature')}: ',
              style: const TextStyle(fontWeight: FontWeight.w500)),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
                _pick(
                  '(0.0 = chính xác · 1.0 = sáng tạo)',
                  '(0.0 = precise · 1.0 = creative)',
                ),
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
          ),
        ]),
        Slider(
          value: _temperature,
          min: 0.0, max: 2.0, divisions: 40,
          label: _temperature.toStringAsFixed(2),
          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

          onChanged: (v) => setState(() => _temperature = v),
        ),
        const SizedBox(height: 12),
        searchEngineField,
        const SizedBox(height: 12),

        SizedBox(
          width: 220,
          child: TextFormField(
            controller: _maxResultsCtrl,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: _pick('So ket qua RAG toi da', 'Maximum RAG results'),
              prefixIcon:
                  const Icon(Icons.format_list_numbered_outlined, size: 18),
              border: const OutlineInputBorder(),
              isDense: true,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              hintText: '1 - 20',
            ),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: 260,
          child: TextFormField(
            controller: _internetResultsCtrl,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: _pick('So ket qua Internet', 'Internet result count'),
              prefixIcon: const Icon(Icons.public_outlined, size: 18),
              border: const OutlineInputBorder(),
              isDense: true,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              hintText: '0 - 20',
              helperText: _pick(
                  '0 = tat goi y Internet', '0 = disable internet suggestions'),
            ),
          ),
        ),
      ],
    );
  }

  /// Dropdown nếu Ollama trả về danh sách, fallback TextFormField nếu không có.
  // Dựng dropdown chọn model AI.

  Widget _buildModelDropdown({
    required String label,
    required IconData icon,
    required String value,
    required List<String> options,
    required ValueChanged<String?> onChanged,
  }) {
    // Nếu không có danh sách (Ollama lỗi) → dùng text field
    if (options.isEmpty) {
      return TextFormField(
        initialValue: value,
        onChanged: onChanged,
        decoration: InputDecoration(
          labelText: label,
          hintText:
              _pick('Nhap ten model thu cong', 'Enter a model name manually'),
          prefixIcon: Icon(icon, size: 18),
          border: const OutlineInputBorder(),
          isDense: true,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
      );
    }

    // Đảm bảo value nằm trong options; nếu không → thêm vào đầu
    final allOptions = options.contains(value)
        ? options
        : (value.isNotEmpty ? [value, ...options] : options);

    final currentValue = allOptions.contains(value) ? value : allOptions.first;

    return DropdownButtonFormField<String>(
      value: currentValue,
      isExpanded: true,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, size: 18),
        border: const OutlineInputBorder(),
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      ),
      items: allOptions
          .map((m) => DropdownMenuItem(
                value: m,
                child: Text(m, overflow: TextOverflow.ellipsis),
              ))
          .toList(),
      onChanged: onChanged,
    );
  }
}
