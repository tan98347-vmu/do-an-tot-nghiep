// === WIZARD TẠO CÔNG TY (nhiều bước) ===
// Dialog nhiều bước: thông tin công ty (_buildCompanyInfoStep) -> nhóm (_buildGroupStep) -> nhân viên (_buildEmployeeStep, _EmployeeDialog) -> xem lại (_buildReviewStep).
// - _validateCurrentStep kiểm tra trước khi sang bước (_continue/_back).

import 'package:flutter/material.dart';

Future<Map<String, dynamic>?> showPlatformCompanyWizard(BuildContext context) {
  return showDialog<Map<String, dynamic>>(
    context: context,
    barrierDismissible: false,
    builder: (context) => const _PlatformCompanyWizardDialog(),
  );
}

class _PlatformCompanyWizardDialog extends StatefulWidget {
  const _PlatformCompanyWizardDialog();

  @override
  State<_PlatformCompanyWizardDialog> createState() =>
      _PlatformCompanyWizardDialogState();
}

class _PlatformCompanyWizardDialogState
    extends State<_PlatformCompanyWizardDialog> {
  final _codeCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  final _industryCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _websiteCtrl = TextEditingController();
  final _contextCtrl = TextEditingController();
  final _adminNameCtrl = TextEditingController(text: 'Company Admin');
  final _adminEmailCtrl = TextEditingController();
  final _adminPasswordCtrl = TextEditingController();

  // Nghiệp vụ NHÓM: tạo danh sách nhóm, mỗi nhân sự gán nhiều nhóm + vai trò.
  final List<Map<String, dynamic>> _groups = [];
  final List<Map<String, dynamic>> _employees = [];

  int _currentStep = 0;
  String _status = 'active';
  String? _error;

  @override
  void dispose() {
    _codeCtrl.dispose();
    _nameCtrl.dispose();
    _descriptionCtrl.dispose();
    _industryCtrl.dispose();
    _addressCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _websiteCtrl.dispose();
    _contextCtrl.dispose();
    _adminNameCtrl.dispose();
    _adminEmailCtrl.dispose();
    _adminPasswordCtrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final error = _validateCurrentStep();
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    if (_currentStep < 3) {
      setState(() {
        _error = null;
        _currentStep += 1;
      });
      return;
    }
    Navigator.of(context).pop(_buildPayload());
  }

  void _back() {
    if (_currentStep == 0) {
      Navigator.of(context).pop();
      return;
    }
    setState(() {
      _error = null;
      _currentStep -= 1;
    });
  }

  String? _validateCurrentStep() {
    if (_currentStep == 0) {
      if (_codeCtrl.text.trim().isEmpty) {
        return 'Cần nhập mã công ty.';
      }
      if (_nameCtrl.text.trim().isEmpty) {
        return 'Cần nhập tên công ty.';
      }
      return null;
    }
    if (_currentStep == 1 && _groups.isEmpty) {
      return 'Cần tạo ít nhất 1 nhóm.';
    }
    if (_currentStep == 2) {
      if (_employees.isEmpty) {
        return 'Cần tạo ít nhất 1 nhân sự.';
      }
      for (final employee in _employees) {
        final fullName = (employee['full_name'] as String? ?? '').trim();
        final groups = (employee['groups'] as List? ?? const []);
        if (fullName.isEmpty) {
          return 'Nhân sự phải có họ tên.';
        }
        if (groups.isEmpty) {
          return 'Mỗi nhân sự phải được gán ít nhất 1 nhóm.';
        }
      }
    }
    return null;
  }

  Map<String, dynamic> _buildPayload() {
    return {
      'code': _codeCtrl.text.trim(),
      'name': _nameCtrl.text.trim(),
      'status': _status,
      'description': _descriptionCtrl.text.trim(),
      'industry': _industryCtrl.text.trim(),
      'address': _addressCtrl.text.trim(),
      'email': _emailCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'website': _websiteCtrl.text.trim(),
      'company_context': _contextCtrl.text.trim(),
      'admin_full_name': _adminNameCtrl.text.trim(),
      'admin_email': _adminEmailCtrl.text.trim(),
      'admin_password': _adminPasswordCtrl.text.trim(),
      'groups': _groups,
      'employees': _employees,
    };
  }

  Future<void> _editGroup({int? index}) async {
    final current = index == null ? null : _groups[index];
    final item = await _showCatalogItemDialog(
      context: context,
      title: index == null ? 'Thêm nhóm' : 'Chỉnh sửa nhóm',
      initialValue: current,
      nameLabel: 'Tên nhóm',
      descriptionLabel: 'Mô tả nhóm',
    );
    if (item == null) return;
    setState(() {
      if (index == null) {
        _groups.add(item);
      } else {
        _groups[index] = item;
      }
    });
  }

  Future<void> _editEmployee({int? index}) async {
    final current = index == null ? null : _employees[index];
    final item = await _showEmployeeDialog(
      context: context,
      initialValue: current,
      groups: _groups,
    );
    if (item == null) return;
    setState(() {
      if (index == null) {
        _employees.add(item);
      } else {
        _employees[index] = item;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
      child: SizedBox(
        width: 980,
        height: 760,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Tạo công ty thủ công chi tiết',
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child:
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                ),
              ),
            Expanded(
              child: Stepper(
                currentStep: _currentStep,
                onStepTapped: (value) => setState(() => _currentStep = value),
                onStepContinue: _continue,
                onStepCancel: _back,
                controlsBuilder: (context, details) => Row(
                  children: [
                    FilledButton(
                      onPressed: details.onStepContinue,
                      child:
                          Text(_currentStep == 3 ? 'Tạo công ty' : 'Tiếp tục'),
                    ),
                    const SizedBox(width: 12),
                    TextButton(
                      onPressed: details.onStepCancel,
                      child: Text(_currentStep == 0 ? 'Dong' : 'Quay lai'),
                    ),
                  ],
                ),
                steps: [
                  Step(
                    title: const Text('Thông tin công ty'),
                    isActive: _currentStep >= 0,
                    content: _buildCompanyInfoStep(),
                  ),
                  Step(
                    title: const Text('Nhóm'),
                    isActive: _currentStep >= 1,
                    content: _buildGroupStep(),
                  ),
                  Step(
                    title: const Text('Nhân sự'),
                    isActive: _currentStep >= 2,
                    content: _buildEmployeeStep(),
                  ),
                  Step(
                    title: const Text('Review'),
                    isActive: _currentStep >= 3,
                    content: _buildReviewStep(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompanyInfoStep() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
                child: _outlinedField(
                    controller: _codeCtrl, label: 'Mã công ty *')),
            const SizedBox(width: 12),
            Expanded(
                child: _outlinedField(
                    controller: _nameCtrl, label: 'Tên công ty *')),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _status,
                decoration: const InputDecoration(
                    labelText: 'Trạng thái', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'draft', child: Text('Draft')),
                  DropdownMenuItem(value: 'active', child: Text('Active')),
                  DropdownMenuItem(value: 'locked', child: Text('Locked')),
                  DropdownMenuItem(value: 'archived', child: Text('Archived')),
                ],
                onChanged: (value) =>
                    setState(() => _status = value ?? 'active'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
                child: _outlinedField(
                    controller: _industryCtrl, label: 'Lĩnh vực')),
          ],
        ),
        const SizedBox(height: 12),
        _outlinedField(
            controller: _descriptionCtrl,
            label: 'Mô tả',
            minLines: 2,
            maxLines: 4),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child: _outlinedField(
                    controller: _emailCtrl, label: 'Email công ty')),
            const SizedBox(width: 12),
            Expanded(
                child: _outlinedField(
                    controller: _phoneCtrl, label: 'Điện thoại')),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child:
                    _outlinedField(controller: _addressCtrl, label: 'Địa chỉ')),
            const SizedBox(width: 12),
            Expanded(
                child:
                    _outlinedField(controller: _websiteCtrl, label: 'Website')),
          ],
        ),
        const SizedBox(height: 12),
        _outlinedField(
          controller: _contextCtrl,
          label: 'Ngữ cảnh công ty',
          minLines: 5,
          maxLines: 8,
        ),
        const SizedBox(height: 16),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text('Bootstrap admin',
              style: TextStyle(fontWeight: FontWeight.bold)),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
                child: _outlinedField(
                    controller: _adminNameCtrl, label: 'Tên admin bootstrap')),
            const SizedBox(width: 12),
            Expanded(
                child: _outlinedField(
                    controller: _adminEmailCtrl,
                    label: 'Email admin bootstrap')),
          ],
        ),
        const SizedBox(height: 12),
        _outlinedField(
          controller: _adminPasswordCtrl,
          label: 'Mật khẩu bootstrap admin (để trống để sinh ngẫu nhiên)',
        ),
      ],
    );
  }

  Widget _buildGroupStep() {
    return _collectionSection(
      title: 'Nhóm',
      emptyText: 'Chưa có nhóm nào.',
      items: _groups,
      onAdd: () => _editGroup(),
      onEdit: _editGroup,
      onDelete: (index) => setState(() => _groups.removeAt(index)),
      titleBuilder: (item) => item['name'] as String? ?? '',
      subtitleBuilder: (item) => [
        if ((item['description'] as String? ?? '').isNotEmpty)
          item['description'] as String,
      ].join(' | '),
    );
  }

  Widget _buildEmployeeStep() {
    return _collectionSection(
      title: 'Nhân sự',
      emptyText: 'Chưa có nhân sự nào.',
      items: _employees,
      onAdd: () => _editEmployee(),
      onEdit: _editEmployee,
      onDelete: (index) => setState(() => _employees.removeAt(index)),
      titleBuilder: (item) => item['full_name'] as String? ?? '',
      subtitleBuilder: (item) => [
        if ((item['employee_code'] as String? ?? '').isNotEmpty)
          'Mã NV: ${item['employee_code']}',
        if ((item['chuc_danh'] as String? ?? '').isNotEmpty)
          'Chức danh: ${item['chuc_danh']}',
        if ((item['groups'] as List? ?? const []).isNotEmpty)
          'Nhóm: ${_employeeGroupSummary(item['groups'] as List)}',
        if ((item['email'] as String? ?? '').isNotEmpty)
          'Email: ${item['email']}',
      ].join(' | '),
    );
  }

  String _employeeGroupSummary(List groups) {
    return groups.map((g) {
      final m = g as Map;
      final name = (m['group'] ?? m['name'] ?? '').toString();
      final role = (m['role'] ?? 'member').toString();
      return role == 'leader' ? '$name (trưởng nhóm)' : name;
    }).join(', ');
  }

  Widget _buildReviewStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Công ty: ${_nameCtrl.text.trim()} (${_codeCtrl.text.trim()})'),
        const SizedBox(height: 6),
        Text('Trạng thái: $_status'),
        const SizedBox(height: 6),
        Text('Nhóm: ${_groups.length}'),
        Text('Nhân sự: ${_employees.length}'),
        const SizedBox(height: 12),
        Text(
            'Bootstrap admin: ${_adminNameCtrl.text.trim().isEmpty ? 'Company Admin' : _adminNameCtrl.text.trim()}'),
        if (_adminEmailCtrl.text.trim().isNotEmpty)
          Text('Email bootstrap: ${_adminEmailCtrl.text.trim()}'),
        // (label giữ tiếng Anh "Email bootstrap" theo thuật ngữ kỹ thuật)
        const SizedBox(height: 12),
        const Text('Ngữ cảnh công ty',
            style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Text(_contextCtrl.text.trim().isEmpty
              ? 'Chưa có.'
              : _contextCtrl.text.trim()),
        ),
      ],
    );
  }

  Widget _collectionSection({
    required String title,
    required String emptyText,
    required List<Map<String, dynamic>> items,
    required VoidCallback onAdd,
    required Future<void> Function({int? index}) onEdit,
    required ValueChanged<int> onDelete,
    required String Function(Map<String, dynamic>) titleBuilder,
    required String Function(Map<String, dynamic>) subtitleBuilder,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: onAdd,
            icon: const Icon(Icons.add),
            label: Text('Thêm $title'),
          ),
        ),
        const SizedBox(height: 12),
        if (items.isEmpty)
          Text(emptyText)
        else
          ...items.asMap().entries.map(
                (entry) => Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    title: Text(titleBuilder(entry.value)),
                    subtitle: Text(subtitleBuilder(entry.value)),
                    trailing: Wrap(
                      spacing: 4,
                      children: [
                        IconButton(
                          onPressed: () => onEdit(index: entry.key),
                          icon: const Icon(Icons.edit_outlined),
                        ),
                        IconButton(
                          onPressed: () => onDelete(entry.key),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
      ],
    );
  }
}

class _CatalogItemDialog extends StatefulWidget {
  const _CatalogItemDialog({
    required this.title,
    this.codeLabel,
    required this.nameLabel,
    required this.descriptionLabel,
    this.initialValue,
  });

  final String title;
  final String? codeLabel;
  final String nameLabel;
  final String descriptionLabel;
  final Map<String, dynamic>? initialValue;

  @override
  State<_CatalogItemDialog> createState() => _CatalogItemDialogState();
}

class _CatalogItemDialogState extends State<_CatalogItemDialog> {
  late final TextEditingController _codeCtrl;
  late final TextEditingController _nameCtrl;
  late final TextEditingController _descriptionCtrl;
  String? _error;

  @override
  void initState() {
    super.initState();
    _codeCtrl = TextEditingController(
        text: widget.initialValue?['code'] as String? ?? '');
    _nameCtrl = TextEditingController(
        text: widget.initialValue?['name'] as String? ?? '');
    _descriptionCtrl = TextEditingController(
        text: widget.initialValue?['description'] as String? ?? '');
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    _nameCtrl.dispose();
    _descriptionCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 520,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            if (widget.codeLabel != null) ...[
              _outlinedField(controller: _codeCtrl, label: widget.codeLabel!),
              const SizedBox(height: 12),
            ],
            _outlinedField(
                controller: _nameCtrl, label: '${widget.nameLabel} *'),
            const SizedBox(height: 12),
            _outlinedField(
              controller: _descriptionCtrl,
              label: widget.descriptionLabel,
              minLines: 3,
              maxLines: 5,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: () {
            if (_nameCtrl.text.trim().isEmpty) {
              setState(() => _error = 'Cần nhập tên.');
              return;
            }
            Navigator.of(context).pop(
              {
                if (widget.codeLabel != null) 'code': _codeCtrl.text.trim(),
                'name': _nameCtrl.text.trim(),
                'description': _descriptionCtrl.text.trim(),
              },
            );
          },
          child: const Text('Lưu'),
        ),
      ],
    );
  }
}

class _EmployeeDialog extends StatefulWidget {
  const _EmployeeDialog({
    this.initialValue,
    required this.groups,
  });

  final Map<String, dynamic>? initialValue;
  final List<Map<String, dynamic>> groups;

  @override
  State<_EmployeeDialog> createState() => _EmployeeDialogState();
}

class _EmployeeDialogState extends State<_EmployeeDialog> {
  late final TextEditingController _fullNameCtrl;
  late final TextEditingController _ageCtrl;
  late final TextEditingController _emailCtrl;
  late final TextEditingController _phoneCtrl;
  late final TextEditingController _addressCtrl;
  late final TextEditingController _employeeCodeCtrl;
  late final TextEditingController _cccdCtrl;
  late final TextEditingController _localUsernameCtrl;
  late final TextEditingController _passwordCtrl;
  late final TextEditingController _profileCtrl;
  late final TextEditingController _chucDanhCtrl;
  // Ten nhom -> vai tro ('leader'|'member'); chi cac nhom da chon.
  final Map<String, String> _groupRoles = {};
  String? _error;

  @override
  void initState() {
    super.initState();
    final initial = widget.initialValue ?? const <String, dynamic>{};
    _fullNameCtrl =
        TextEditingController(text: initial['full_name'] as String? ?? '');
    _ageCtrl = TextEditingController(text: '${initial['age_years'] ?? ''}');
    _emailCtrl = TextEditingController(text: initial['email'] as String? ?? '');
    _phoneCtrl = TextEditingController(text: initial['phone'] as String? ?? '');
    _addressCtrl =
        TextEditingController(text: initial['address'] as String? ?? '');
    _employeeCodeCtrl =
        TextEditingController(text: initial['employee_code'] as String? ?? '');
    _cccdCtrl = TextEditingController(text: initial['cccd'] as String? ?? '');
    _localUsernameCtrl =
        TextEditingController(text: initial['local_username'] as String? ?? '');
    _passwordCtrl =
        TextEditingController(text: initial['password'] as String? ?? '');
    _profileCtrl =
        TextEditingController(text: initial['profile_text'] as String? ?? '');
    _chucDanhCtrl =
        TextEditingController(text: initial['chuc_danh'] as String? ?? '');
    for (final entry in (initial['groups'] as List? ?? const [])) {
      final m = entry as Map;
      final name = (m['group'] ?? m['name'] ?? '').toString().trim();
      if (name.isNotEmpty) {
        _groupRoles[name] = (m['role'] ?? 'member').toString();
      }
    }
  }

  @override
  void dispose() {
    _fullNameCtrl.dispose();
    _ageCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _addressCtrl.dispose();
    _employeeCodeCtrl.dispose();
    _cccdCtrl.dispose();
    _localUsernameCtrl.dispose();
    _passwordCtrl.dispose();
    _profileCtrl.dispose();
    _chucDanhCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final groupNames = widget.groups
        .map((item) => (item['name'] as String? ?? '').trim())
        .where((value) => value.isNotEmpty)
        .toList();
    return AlertDialog(
      title: Text(
          widget.initialValue == null ? 'Thêm nhân sự' : 'Chỉnh sửa nhân sự'),
      content: SizedBox(
        width: 720,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.red)),
                  ),
                ),
              Row(
                children: [
                  Expanded(
                      child: _outlinedField(
                          controller: _fullNameCtrl, label: 'Họ tên *')),
                  const SizedBox(width: 12),
                  Expanded(
                      child:
                          _outlinedField(controller: _ageCtrl, label: 'Tuổi')),
                ],
              ),
              const SizedBox(height: 12),
              _outlinedField(
                  controller: _chucDanhCtrl,
                  label: 'Chức danh (tuỳ chọn)'),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: Text('Nhóm * (chọn nhóm và vai trò)',
                    style: Theme.of(context).textTheme.titleSmall),
              ),
              const SizedBox(height: 4),
              if (groupNames.isEmpty)
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Chưa có nhóm nào. Hãy quay lại bước "Nhóm" để tạo nhóm trước.',
                    style: TextStyle(color: Colors.orange),
                  ),
                )
              else
                ...groupNames.map((name) {
                  final selected = _groupRoles.containsKey(name);
                  return Row(
                    children: [
                      Expanded(
                        child: CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          dense: true,
                          controlAffinity: ListTileControlAffinity.leading,
                          title: Text(name),
                          value: selected,
                          onChanged: (v) => setState(() {
                            if (v == true) {
                              _groupRoles[name] = 'member';
                            } else {
                              _groupRoles.remove(name);
                            }
                          }),
                        ),
                      ),
                      SizedBox(
                        width: 160,
                        child: DropdownButtonFormField<String>(
                          value: selected ? _groupRoles[name] : null,
                          isDense: true,
                          decoration: const InputDecoration(
                            labelText: 'Vai trò',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          items: const [
                            DropdownMenuItem(
                                value: 'member', child: Text('Thành viên')),
                            DropdownMenuItem(
                                value: 'leader', child: Text('Trưởng nhóm')),
                          ],
                          onChanged: selected
                              ? (v) => setState(
                                  () => _groupRoles[name] = v ?? 'member')
                              : null,
                        ),
                      ),
                    ],
                  );
                }),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                      child: _outlinedField(
                          controller: _emailCtrl, label: 'Email')),
                  const SizedBox(width: 12),
                  Expanded(
                      child: _outlinedField(
                          controller: _phoneCtrl, label: 'Số điện thoại')),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                      child: _outlinedField(
                          controller: _employeeCodeCtrl,
                          label: 'Mã nhân viên')),
                  const SizedBox(width: 12),
                  Expanded(
                      child:
                          _outlinedField(controller: _cccdCtrl, label: 'CCCD')),
                ],
              ),
              const SizedBox(height: 12),
              _outlinedField(controller: _addressCtrl, label: 'Địa chỉ'),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                      child: _outlinedField(
                          controller: _localUsernameCtrl,
                          label: 'Username nội bộ (tuỳ chọn)')),
                  const SizedBox(width: 12),
                  Expanded(
                      child: _outlinedField(
                          controller: _passwordCtrl,
                          label: 'Mật khẩu (tuỳ chọn)')),
                ],
              ),
              const SizedBox(height: 12),
              _outlinedField(
                controller: _profileCtrl,
                label: 'Hồ sơ nhân sự',
                minLines: 5,
                maxLines: 8,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: () {
            if (_fullNameCtrl.text.trim().isEmpty) {
              setState(() => _error = 'Cần nhập họ tên nhân sự.');
              return;
            }
            if (_groupRoles.isEmpty) {
              setState(() => _error = 'Cần gán nhân sự vào ít nhất 1 nhóm.');
              return;
            }
            Navigator.of(context).pop(
              {
                'full_name': _fullNameCtrl.text.trim(),
                'age_years': _ageCtrl.text.trim(),
                'chuc_danh': _chucDanhCtrl.text.trim(),
                'groups': _groupRoles.entries
                    .map((e) => {'group': e.key, 'role': e.value})
                    .toList(),
                'email': _emailCtrl.text.trim(),
                'phone': _phoneCtrl.text.trim(),
                'address': _addressCtrl.text.trim(),
                'employee_code': _employeeCodeCtrl.text.trim(),
                'cccd': _cccdCtrl.text.trim(),
                'local_username': _localUsernameCtrl.text.trim(),
                'password': _passwordCtrl.text.trim(),
                'profile_text': _profileCtrl.text.trim(),
              },
            );
          },
          child: const Text('Lưu'),
        ),
      ],
    );
  }
}

Future<Map<String, dynamic>?> _showCatalogItemDialog({
  required BuildContext context,
  required String title,
  String? codeLabel,
  required String nameLabel,
  required String descriptionLabel,
  Map<String, dynamic>? initialValue,
}) {
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => _CatalogItemDialog(
      title: title,
      codeLabel: codeLabel,
      nameLabel: nameLabel,
      descriptionLabel: descriptionLabel,
      initialValue: initialValue,
    ),
  );
}

Future<Map<String, dynamic>?> _showEmployeeDialog({
  required BuildContext context,
  Map<String, dynamic>? initialValue,
  required List<Map<String, dynamic>> groups,
}) {
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => _EmployeeDialog(
      initialValue: initialValue,
      groups: groups,
    ),
  );
}

Widget _outlinedField({
  required TextEditingController controller,
  required String label,
  int minLines = 1,
  int maxLines = 1,
}) {
  return TextField(
    controller: controller,
    minLines: minLines,
    maxLines: maxLines,
    decoration: InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
    ),
  );
}
