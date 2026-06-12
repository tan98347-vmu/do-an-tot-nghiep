// === MÀN HÌNH TẠO / SỬA PROMPT ===
// Form cấu hình một Prompt (khuôn điều khiển AI): system_content (hệ tư tưởng) + rules_content (quy tắc), phạm vi private/group/public (chọn nhóm qua GET 'groups/'), tags.
// - _loadExisting(): nạp prompt khi sửa ('prompts/<id>/'); _loadGroups(): nạp nhóm.
// - _checkPrompt(): gọi kiểm tra AN TOÀN prompt (pipeline chống prompt-injection) — BẮT BUỘC pass mới cho lưu nếu có quy tắc.
// - _save(): POST/PUT 'prompts/'. _refreshPromptSharingState/_approvalHint: hiển thị trạng thái duyệt theo phạm vi.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/browser_alert.dart';
import '../../providers/prompt_preflight_provider.dart';
import '../../providers/prompts_provider.dart';
import '../../providers/recent_prompts_provider.dart';
import '../../widgets/sharing/unified_share_sheet.dart';

class PromptFormScreen extends ConsumerStatefulWidget {
  final int? promptId;
  const PromptFormScreen({super.key, this.promptId});

  @override
  ConsumerState<PromptFormScreen> createState() => _PromptFormScreenState();
}

class _PromptFormScreenState extends ConsumerState<PromptFormScreen> {
  final _titleCtrl = TextEditingController();
  final _rulesCtrl = TextEditingController();
  final _systemCtrl = TextEditingController();
  final _tagsCtrl = TextEditingController();
  String _visibility = 'private';
  int? _groupId;
  final Set<String> _usageScopes = {'template_fill'};
  bool _loading = false;
  bool _saving = false;
  bool _checkingPrompt = false;
  String? _promptCheckToken;
  String? _error;
  List<Map<String, dynamic>> _groups = [];

  bool get _isEdit => widget.promptId != null;
  bool get _shareSettingsManagedInPanel => _isEdit && widget.promptId != null;

  @override
  void initState() {
    super.initState();
    _loadGroups();
    if (_isEdit) _loadExisting();
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _rulesCtrl.dispose();
    _systemCtrl.dispose();
    _tagsCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadGroups() async {
    try {
      final resp = await ApiClient().dio.get('groups/');
      final data = resp.data;
      final list = data is List
          ? data
          : (data is Map ? (data['results'] ?? data['groups'] ?? []) : []);
      if (!mounted) return;
      setState(() {
        _groups = (list as List)
            .map<Map<String, dynamic>>(
                (e) => Map<String, dynamic>.from(e as Map))
            .toList();
      });
    } catch (_) {}
  }

  Future<void> _loadExisting() async {
    setState(() => _loading = true);
    try {
      final resp = await ApiClient().dio.get('prompts/${widget.promptId}/');
      final d = resp.data as Map;
      _titleCtrl.text = (d['title'] ?? '') as String;
      _rulesCtrl.text = (d['rules_content'] ?? '') as String;
      _systemCtrl.text = (d['system_content'] ?? '') as String;
      _tagsCtrl.text = (d['tags'] ?? '') as String;
      _visibility = (d['visibility'] ?? 'private') as String;
      _groupId = d['group'] as int?;
      final rawScopes = (d['usage_scope'] as List?) ?? const [];
      _usageScopes
        ..clear()
        ..addAll(rawScopes.map((item) => item.toString()));
      if (_usageScopes.isEmpty) {
        _usageScopes.add('template_fill');
      }
    } on DioException catch (e) {
      _error = e.response?.data?.toString() ?? e.message;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refreshPromptSharingState() async {
    if (!_shareSettingsManagedInPanel) return;
    try {
      final resp = await ApiClient().dio.get('prompts/${widget.promptId}/');
      final d = resp.data as Map;
      if (!mounted) return;
      setState(() {
        _visibility = (d['visibility'] ?? _visibility) as String;
        _groupId = d['group'] as int?;
      });
      ref.invalidate(promptsProvider);
      ref.invalidate(recentPromptsProvider);
    } catch (_) {}
  }

  String get _promptText => [
        _systemCtrl.text.trim(),
        _rulesCtrl.text.trim(),
      ].where((part) => part.isNotEmpty).join('\n\n');

  void _invalidatePromptCheck() {
    if (_promptCheckToken != null) {
      setState(() => _promptCheckToken = null);
    }
  }

  Future<void> _checkPrompt() async {
    final promptText = _promptText;
    if (promptText.isEmpty) {
      await showBrowserAlert(context, 'Vui lòng nhập nội dung prompt trước khi kiểm tra.');
      return;
    }
    setState(() {
      _checkingPrompt = true;
      _error = null;
    });
    final result = await checkPromptPreflight(
      scope: 'saved_prompt',
      context: 'prompt_library',
      promptRole: 'saved_prompt',
      promptText: promptText,
    );
    if (!mounted) return;
    if (_promptText != promptText) {
      setState(() {
        _checkingPrompt = false;
        _promptCheckToken = null;
      });
      return;
    }
    setState(() {
      _checkingPrompt = false;
      _promptCheckToken = result.promptCheckToken;
    });
    if (!result.passed) {
      await showBrowserAlert(context, promptPreflightFailureMessage(result));
    }
  }

  Future<void> _save() async {
    final title = _titleCtrl.text.trim();
    if (title.isEmpty) {
      _showSnack('Vui long nhap ten prompt.');
      return;
    }
    if (!_shareSettingsManagedInPanel &&
        _visibility == 'group' &&
        _groupId == null) {
      _showSnack('Vui long chon nhom khi pham vi la "Phong ban".');
      return;
    }
    if (_usageScopes.isEmpty) {
      _showSnack('Vui long chon it nhat 1 pham vi su dung.');
      return;
    }
    if ((_promptCheckToken ?? '').isEmpty) {
      await showBrowserAlert(context, 'Hãy bấm "Check prompt" và sửa prompt nếu cần trước khi lưu.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final body = {
        'title': title,
        'rules_content': _rulesCtrl.text,
        'system_content': _systemCtrl.text,
        'tags': _tagsCtrl.text,
        'usage_scope': _usageScopes.toList(),
        'prompt_check_token': _promptCheckToken,
        if (!_shareSettingsManagedInPanel) 'visibility': _visibility,
        if (!_shareSettingsManagedInPanel && _visibility == 'group')
          'group': _groupId,
      };
      if (_isEdit) {
        await ApiClient().dio.patch('prompts/${widget.promptId}/', data: body);
      } else {
        await ApiClient().dio.post('prompts/', data: body);
      }
      if (!mounted) return;
      ref.invalidate(promptsProvider);
      ref.invalidate(recentPromptsProvider);
      _showSnack(_isEdit ? 'Da cap nhat prompt.' : 'Da tao prompt.');
      context.go('/prompts');
    } on DioException catch (e) {
      final data = e.response?.data;
      String msg = e.message ?? 'Loi khong xac dinh';
      if (data is Map) {
        if (data['title'] != null) {
          msg = data['title'].toString();
        } else if (data['group'] != null) {
          msg = data['group'].toString();
        } else if (data['detail'] != null) {
          msg = data['detail'].toString();
        }
      }
      setState(() => _error = msg);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _showSnack(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  String _approvalHint() {
    switch (_visibility) {
      case 'public':
        return 'Prompt cong khai can ADMIN duyet truoc khi hien voi moi nguoi.';
      case 'group':
        return 'Prompt phong ban can TRUONG NHOM duyet truoc khi cac thanh vien dung duoc.';
      default:
        return 'Prompt rieng tu: chi minh ban dung. Khong can duyet.';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isEdit ? 'Sửa prompt' : 'Tạo prompt mới'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/prompts'),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    if (_error != null)
                      Container(
                        padding: const EdgeInsets.all(10),
                        margin: const EdgeInsets.only(bottom: 12),
                        color: Colors.red.shade50,
                        child: Text(_error!,
                            style: const TextStyle(color: Colors.red)),
                      ),
                    TextField(
                      controller: _titleCtrl,
                      maxLength: 200,
                      decoration: const InputDecoration(
                        labelText: 'Tên prompt *',
                        helperText:
                            'Bắt buộc. Không được trùng với prompt khác của bạn.',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _rulesCtrl,
                      minLines: 4,
                      maxLines: 12,
                      onChanged: (_) => _invalidatePromptCheck(),
                      decoration: const InputDecoration(
                        labelText: 'Yêu cầu / quy tắc (rules)',
                        helperText:
                            'Mô tả phong cách AI nên áp dụng khi sinh văn bản.',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _systemCtrl,
                      minLines: 2,
                      maxLines: 5,
                      onChanged: (_) => _invalidatePromptCheck(),
                      decoration: const InputDecoration(
                        labelText:
                            'Phần hệ tư tưởng (system content) - nâng cao',
                        helperText:
                            'Không bắt buộc. Chỉ dùng khi muốn ghi đè identity AI.',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: _checkingPrompt || _saving ? null : _checkPrompt,
                      icon: _checkingPrompt
                          ? const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Icon(
                              (_promptCheckToken ?? '').isEmpty
                                  ? Icons.fact_check_outlined
                                  : Icons.verified_user_outlined,
                              size: 16,
                            ),
                      label: Text(
                        _checkingPrompt
                            ? 'Đang kiểm tra...'
                            : (_promptCheckToken ?? '').isEmpty
                                ? 'Check prompt'
                                : 'Prompt đạt yêu cầu',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _tagsCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Tags',
                        helperText:
                            'Cách nhau bằng dấu phẩy. Ví dụ: hành-chính, kế-toán',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text('Phạm vi sử dụng',
                        style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: promptScopeLabels.entries.map((entry) {
                        final selected = _usageScopes.contains(entry.key);
                        return FilterChip(
                          label: Text(entry.value),
                          selected: selected,
                          onSelected: (value) {
                            setState(() {
                              if (value) {
                                _usageScopes.add(entry.key);
                              } else if (_usageScopes.length > 1) {
                                _usageScopes.remove(entry.key);
                              }
                            });
                          },
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 18),
                    Text('Phạm vi chia sẻ',
                        style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 6),
                    if (_shareSettingsManagedInPanel)
                      Card(
                        margin: EdgeInsets.zero,
                        child: ListTile(
                          leading: Icon(
                            switch (_visibility) {
                              'public' => Icons.public_outlined,
                              'group' => Icons.groups_outlined,
                              _ => Icons.lock_outline,
                            },
                          ),
                          title: Text(
                            switch (_visibility) {
                              'public' => 'Công khai',
                              'group' => 'Phòng ban / đang chờ duyệt',
                              _ => 'Riêng tư',
                            },
                          ),
                          subtitle: const Text(
                            'Khi sửa prompt đã tồn tại, quyền chia sẻ được quản lý tại bảng bên dưới để tránh ghi đè ngược scope hiện có.',
                          ),
                        ),
                      )
                    else
                      Card(
                        child: Column(
                          children: [
                            RadioListTile<String>(
                              value: 'private',
                              groupValue: _visibility,
                              title: const Text('Riêng tư'),
                              subtitle: const Text('Chỉ mình bạn dùng'),
                              dense: true,
                              onChanged: (v) =>
                                  setState(() => _visibility = v!),
                            ),
                            RadioListTile<String>(
                              value: 'group',
                              groupValue: _visibility,
                              title: const Text('Phòng ban'),
                              subtitle: const Text(
                                  'Cả phòng ban dùng (cần trưởng nhóm duyệt)'),
                              dense: true,
                              onChanged: (v) =>
                                  setState(() => _visibility = v!),
                            ),
                            RadioListTile<String>(
                              value: 'public',
                              groupValue: _visibility,
                              title: const Text('Công khai'),
                              subtitle: const Text(
                                  'Tất cả mọi người dùng (cần admin duyệt)'),
                              dense: true,
                              onChanged: (v) =>
                                  setState(() => _visibility = v!),
                            ),
                          ],
                        ),
                      ),
                    if (!_shareSettingsManagedInPanel &&
                        _visibility == 'group') ...[
                      const SizedBox(height: 8),
                      DropdownButtonFormField<int?>(
                        value: _groupId,
                        decoration: const InputDecoration(
                          labelText: 'Chọn phòng ban *',
                          border: OutlineInputBorder(),
                        ),
                        items: [
                          const DropdownMenuItem<int?>(
                              value: null, child: Text('-- Chọn --')),
                          ..._groups.map((g) => DropdownMenuItem<int?>(
                                value: g['id'] as int?,
                                child: Text((g['name'] ?? '') as String),
                              )),
                        ],
                        onChanged: (v) => setState(() => _groupId = v),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(10),
                      color: Colors.amber.shade50,
                      child: Row(children: [
                        const Icon(Icons.info_outline,
                            color: Colors.amber, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                            child: Text(_approvalHint(),
                                style: const TextStyle(fontSize: 12))),
                      ]),
                    ),
                    if (_isEdit && widget.promptId != null)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Card(
                          margin: EdgeInsets.zero,
                          child: Padding(
                            padding: const EdgeInsets.all(8),
                            child: UnifiedShareSheet(
                              entityType: 'prompts',
                              entityId: widget.promptId!,
                              entityTitle: 'Prompt #${widget.promptId}',
                              presentation: SharePresentation.inlinePanel,
                              onChanged: _refreshPromptSharingState,
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed:
                              _saving ? null : () => context.go('/prompts'),
                          child: const Text('Hủy'),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                          icon: _saving
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.save),
                          label: Text(_isEdit ? 'Luu thay doi' : 'Tao prompt'),
                          onPressed:
                              _saving || (_promptCheckToken ?? '').isEmpty
                                  ? null
                                  : _save,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
