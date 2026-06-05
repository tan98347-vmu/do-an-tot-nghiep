import 'package:flutter/material.dart';

/// Hai nut gat dieu khien viec backend prefill bien tu ho so + ngu canh cong ty
/// khi nguoi dung ra lenh sinh van ban qua VoiceAI hoac ChatAI.
///
/// Default ca hai bat. Khi user tat 1 cai, backend nhan flag tuong ung va se
/// bo qua nguon context do trong [build_effective_ai_context].
class PrefillToggleRow extends StatelessWidget {
  final bool autoFillProfile;
  final bool autoFillCompany;
  final ValueChanged<bool> onProfileChanged;
  final ValueChanged<bool> onCompanyChanged;
  final bool compact;

  const PrefillToggleRow({
    super.key,
    required this.autoFillProfile,
    required this.autoFillCompany,
    required this.onProfileChanged,
    required this.onCompanyChanged,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < 520 || compact;
        final profile = _ToggleChip(
          icon: Icons.person_outline,
          label: 'Tự điền từ hồ sơ',
          value: autoFillProfile,
          onChanged: onProfileChanged,
        );
        final company = _ToggleChip(
          icon: Icons.business_outlined,
          label: 'Tự điền ngữ cảnh công ty',
          value: autoFillCompany,
          onChanged: onCompanyChanged,
        );
        if (isNarrow) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              profile,
              const SizedBox(height: 6),
              company,
            ],
          );
        }
        return Row(
          children: [
            Expanded(child: profile),
            const SizedBox(width: 8),
            Expanded(child: company),
          ],
        );
      },
    );
  }
}

class _ToggleChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _ToggleChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final activeColor = scheme.primary;
    final bg = value ? scheme.primary.withOpacity(0.08) : Colors.transparent;
    return Material(
      color: bg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: value ? activeColor.withOpacity(0.5) : Theme.of(context).dividerColor,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => onChanged(!value),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 18, color: value ? activeColor : Colors.grey),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: value ? activeColor : Colors.grey.shade700,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              SizedBox(
                height: 24,
                child: Switch.adaptive(
                  value: value,
                  onChanged: onChanged,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
