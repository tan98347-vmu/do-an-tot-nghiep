import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_locale.dart';
import '../../core/preferences_helper.dart';

/// Bọc editor prompt bằng nút ẩn/hiện có lưu trạng thái theo `storageKey`.
///
/// Cách dùng:
/// ```dart
/// PromptToggleSection(
///   storageKey: 'prompt_toggle_ai_doc_fill',
///   child: Column(
///     children: [
///       TextField(controller: _extraRulesCtrl),
///       DropdownButton<String>(value: _tone, items: [...], onChanged: ...),
///     ],
///   ),
/// )
/// ```
///
/// Lưu ý:
/// `TextEditingController` và state form phải nằm ở parent screen để nội dung
/// không bị reset khi người dùng ẩn/hiện phần tùy chỉnh.
class PromptToggleSection extends ConsumerStatefulWidget {
  final Widget child;
  final String storageKey;
  final bool defaultExpanded;
  final String labelHidden;
  final String labelShown;

  const PromptToggleSection({
    super.key,
    required this.child,
    required this.storageKey,
    this.defaultExpanded = false,
    this.labelHidden = 'T\u00f9y ch\u1ec9nh prompt',
    this.labelShown = '\u1ea8n t\u00f9y ch\u1ec9nh',
  });

  @override
  ConsumerState<PromptToggleSection> createState() =>
      _PromptToggleSectionState();
}

class _PromptToggleSectionState extends ConsumerState<PromptToggleSection> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    final preferences = ref.read(sharedPreferencesProvider);
    _expanded = PreferencesHelper.getBool(
      preferences,
      widget.storageKey,
      defaultValue: widget.defaultExpanded,
    );
  }

  Future<void> _toggle() async {
    final nextValue = !_expanded;
    setState(() => _expanded = nextValue);
    final preferences = ref.read(sharedPreferencesProvider);
    await PreferencesHelper.setBool(
      preferences,
      widget.storageKey,
      nextValue,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        OutlinedButton.icon(
          onPressed: _toggle,
          icon: Icon(_expanded ? Icons.close : Icons.tune),
          label: Text(_expanded ? widget.labelShown : widget.labelHidden),
        ),
        AnimatedCrossFade(
          duration: const Duration(milliseconds: 250),
          firstChild: const SizedBox.shrink(),
          secondChild: Padding(
            padding: const EdgeInsets.only(top: 8),
            child: widget.child,
          ),
          crossFadeState: _expanded
              ? CrossFadeState.showSecond
              : CrossFadeState.showFirst,
        ),
      ],
    );
  }
}
