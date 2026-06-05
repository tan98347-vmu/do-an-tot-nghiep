import 'package:flutter/material.dart';

class ViewModeToggle extends StatelessWidget {
  final String value;
  final ValueChanged<String> onChanged;
  final String cardLabel;
  final String listLabel;

  const ViewModeToggle({
    super.key,
    required this.value,
    required this.onChanged,
    required this.cardLabel,
    required this.listLabel,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ModeButton(
            icon: Icons.grid_view_rounded,
            label: cardLabel,
            selected: value == 'cards',
            onTap: () => onChanged('cards'),
          ),
          const SizedBox(width: 4),
          _ModeButton(
            icon: Icons.view_list_rounded,
            label: listLabel,
            selected: value == 'compact_list',
            onTap: () => onChanged('compact_list'),
          ),
        ],
      ),
    );
  }
}

class _ModeButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _ModeButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final selectedColor = Theme.of(context).colorScheme.primary;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? selectedColor.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: selected ? selectedColor : const Color(0xFF64748B),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: selected ? selectedColor : const Color(0xFF475569),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
