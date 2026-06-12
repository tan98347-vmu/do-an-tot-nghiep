// === MÀN HÌNH ĐĂNG NHẬP ===
// Cho người dùng đăng nhập theo 2 chế độ (_LoginMode): theo CÔNG TY hoặc theo PLATFORM ADMIN.
// - Chế độ công ty: gõ tên công ty -> _onCompanyChanged (debounce 280ms) gọi authProvider.fetchCompanySuggestions để gợi ý, chọn 1 công ty rồi nhập định danh (username/email/mã nhân viên) + mật khẩu.
// - _login(): validate form rồi gọi authProvider xác thực; lỗi -> hiện _error.
// Có lối vào cổng khách (route /guest). Provider: authProvider.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';

enum _LoginMode { company, platform }

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _companyCtrl = TextEditingController();
  final _identifierCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();

  Timer? _debounce;
  _LoginMode _mode = _LoginMode.company;
  List<CompanySuggestion> _suggestions = const [];
  CompanySuggestion? _selectedCompany;
  bool _loading = false;
  bool _obscure = true;
  String? _error;

  @override
  void dispose() {
    _debounce?.cancel();
    _companyCtrl.dispose();
    _identifierCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  void _onCompanyChanged(String value) {
    if (_selectedCompany != null && value.trim() != _selectedCompany!.name) {
      setState(() => _selectedCompany = null);
    }
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 280), () async {
      final query = value.trim();
      if (query.isEmpty || _mode != _LoginMode.company) {
        if (mounted) {
          setState(() => _suggestions = const []);
        }
        return;
      }
      try {
        final suggestions = await ref
            .read(authProvider.notifier)
            .fetchCompanySuggestions(query);
        if (!mounted) return;
        setState(() => _suggestions = suggestions);
      } catch (_) {
        if (!mounted) return;
        setState(() => _suggestions = const []);
      }
    });
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final error = await ref.read(authProvider.notifier).login(
          identifier: _identifierCtrl.text.trim(),
          password: _passwordCtrl.text,
          loginScope: _mode == _LoginMode.platform ? 'platform' : 'company',
          companyId: _mode == _LoginMode.company ? _selectedCompany?.id : null,
        );
    if (!mounted) return;
    if (error != null) {
      setState(() {
        _loading = false;
        _error = error;
      });
      return;
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            elevation: 4,
            margin: const EdgeInsets.all(24),
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.apartment_outlined,
                        size: 56, color: Color(0xFF1565C0)),
                    const SizedBox(height: 10),
                    Text(
                      'AI Document Manager',
                      textAlign: TextAlign.center,
                      style: Theme.of(context)
                          .textTheme
                          .titleLarge
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _mode == _LoginMode.company
                          ? strings.pick('Đăng nhập theo công ty của bạn',
                              'Sign in to your company')
                          : strings.pick('Đăng nhập quản trị nền tảng',
                              'Platform administrator sign in'),
                      textAlign: TextAlign.center,
                      style: Theme.of(context)
                          .textTheme
                          .bodyMedium
                          ?.copyWith(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 24),
                    SegmentedButton<_LoginMode>(
                      segments: [
                        ButtonSegment<_LoginMode>(
                          value: _LoginMode.company,
                          icon: const Icon(Icons.business_outlined),
                          label: Text(strings.pick('Công ty', 'Company')),
                        ),
                        const ButtonSegment<_LoginMode>(
                          value: _LoginMode.platform,
                          icon: Icon(Icons.admin_panel_settings_outlined),
                          label: Text('Platform'),
                        ),
                      ],
                      selected: {_mode},
                      onSelectionChanged: (selection) {
                        final nextMode = selection.first;
                        setState(() {
                          _mode = nextMode;
                          _error = null;
                          _suggestions = const [];
                          if (nextMode == _LoginMode.platform) {
                            _selectedCompany = null;
                            _companyCtrl.clear();
                          }
                        });
                      },
                    ),
                    const SizedBox(height: 20),
                    if (_error != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Text(
                          _error!,
                          style: TextStyle(
                              color: Colors.red.shade700, fontSize: 13),
                        ),
                      ),
                    if (_mode == _LoginMode.company) ...[
                      TextFormField(
                        controller: _companyCtrl,
                        decoration: InputDecoration(
                          labelText:
                              strings.pick('Tên công ty', 'Company name'),
                          hintText: strings.pick('Nhập tên công ty để tìm kiếm',
                              'Type a company name to search'),
                          prefixIcon: const Icon(Icons.search),
                          suffixIcon: _selectedCompany != null
                              ? IconButton(
                                  onPressed: () {
                                    setState(() {
                                      _selectedCompany = null;
                                      _companyCtrl.clear();
                                      _suggestions = const [];
                                    });
                                  },
                                  icon: const Icon(Icons.close),
                                )
                              : null,
                        ),
                        onChanged: _onCompanyChanged,
                        validator: (_) {
                          if (_mode != _LoginMode.company) return null;
                          if (_selectedCompany == null) {
                            return strings.pick(
                                'Vui lòng chọn công ty từ gợi ý.',
                                'Please choose a company from the suggestions.');
                          }
                          return null;
                        },
                      ),
                      if (_selectedCompany != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Wrap(
                            spacing: 8,
                            children: [
                              Chip(
                                avatar: const Icon(Icons.check_circle_outline,
                                    size: 18),
                                label: Text(
                                    '${_selectedCompany!.name} (${_selectedCompany!.code})'),
                              ),
                            ],
                          ),
                        ),
                      if (_selectedCompany == null && _suggestions.isNotEmpty)
                        Container(
                          margin: const EdgeInsets.only(top: 8),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.grey.shade300),
                            color: Colors.white,
                          ),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 220),
                            child: ListView.separated(
                              shrinkWrap: true,
                              itemCount: _suggestions.length,
                              separatorBuilder: (_, __) => Divider(
                                  height: 1, color: Colors.grey.shade200),
                              itemBuilder: (context, index) {
                                final company = _suggestions[index];
                                return ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.business_outlined,
                                      size: 18),
                                  title: Text(company.name),
                                  subtitle: Text(company.code),
                                  onTap: () {
                                    setState(() {
                                      _selectedCompany = company;
                                      _companyCtrl.text = company.name;
                                      _suggestions = const [];
                                    });
                                  },
                                );
                              },
                            ),
                          ),
                        ),
                      const SizedBox(height: 16),
                    ],
                    TextFormField(
                      controller: _identifierCtrl,
                      decoration: InputDecoration(
                        labelText: _mode == _LoginMode.platform
                            ? strings.pick(
                                'Tài khoản quản trị', 'Administrator account')
                            : strings.pick('Username / Email / Mã nhân viên',
                                'Username / Email / Employee code'),
                        prefixIcon: const Icon(Icons.person_outline),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return strings.pick(
                              'Vui lòng nhập thông tin đăng nhập.',
                              'Please enter your sign-in information.');
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordCtrl,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: strings.pick('Mật khẩu', 'Password'),
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          onPressed: () => setState(() => _obscure = !_obscure),
                          icon: Icon(_obscure
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined),
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return strings.pick('Vui lòng nhập mật khẩu.',
                              'Please enter your password.');
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _loading ? null : _login,
                      child: _loading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : Text(
                              _mode == _LoginMode.platform
                                  ? strings.pick(
                                      'Đăng nhập quản trị', 'Admin sign in')
                                  : strings.pick('Đăng nhập', 'Sign in'),
                            ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      strings.pick(
                        'Tài khoản chính thức được cấp bởi hệ thống quản trị công ty. Đăng ký tự do và social login đã được tắt ở phiên bản multi-company.',
                        'Official accounts are provisioned by the company administration system. Self-registration and social login are disabled in the multi-company version.',
                      ),
                      textAlign: TextAlign.center,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: _loading ? null : () => context.go('/guest'),
                      icon: const Icon(Icons.bolt_outlined, size: 18),
                      label: Text(strings.pick('Dùng thử không cần đăng nhập',
                          'Try without signing in')),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
