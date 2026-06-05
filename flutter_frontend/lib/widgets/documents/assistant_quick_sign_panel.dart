import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../../models/assistant_quick_sign.dart';

class AssistantQuickSignPanel extends StatelessWidget {
  final AssistantQuickSignPlanAction plan;
  final bool compact;
  final bool busy;
  final String? busyLabel;
  final VoidCallback onQuickSign;
  final VoidCallback onEditRecipient;
  final VoidCallback onDismiss;

  const AssistantQuickSignPanel({
    super.key,
    required this.plan,
    required this.compact,
    required this.busy,
    required this.busyLabel,
    required this.onQuickSign,
    required this.onEditRecipient,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final recipient = plan.recipient;
    final ctaLabel = plan.canRetryForward
        ? strings.pick('Gửi lại ngay', 'Retry forward')
        : strings.pick('Ký nhanh ngay', 'Quick sign now');
    final status = _statusData(strings);
    final tone = status.color;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFDCE7F7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(status.icon, color: tone),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.pick('Ký nhanh với trợ lý AI', 'AI quick sign'),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      plan.message.trim().isNotEmpty
                          ? plan.message
                          : strings.pick(
                              'Trợ lý AI đã chuẩn bị luồng ký và chuyển tiếp cho văn bản này.',
                              'The AI assistant prepared the signing and forwarding flow for this document.',
                            ),
                      style: const TextStyle(
                        color: Color(0xFF475569),
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _chip(
                label: status.label,
                foreground: tone,
                background: tone.withOpacity(0.12),
              ),
              _chip(
                label: _signatureModeLabel(strings),
                foreground: const Color(0xFF1D4ED8),
                background: const Color(0xFFDBEAFE),
              ),
              if (plan.credentialRequired)
                _chip(
                  label: strings.pick(
                    'Cần credential ký',
                    'Signing credential required',
                  ),
                  foreground: const Color(0xFFB45309),
                  background: const Color(0xFFFDE68A),
                ),
              if (plan.requiresReauthPassword)
                _chip(
                  label: strings.pick(
                    'Xác nhận mật khẩu',
                    'Password confirmation',
                  ),
                  foreground: const Color(0xFF166534),
                  background: const Color(0xFFDCFCE7),
                ),
            ],
          ),
          const SizedBox(height: 14),
          _recipientCard(context),
          if (_errorText().isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              _errorText(),
              style: const TextStyle(
                color: Color(0xFFB91C1C),
                height: 1.45,
              ),
            ),
          ],
          const SizedBox(height: 16),
          compact
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: _actionButtons(context, ctaLabel),
                )
              : Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: _actionButtons(context, ctaLabel),
                ),
        ],
      ),
    );
  }

  List<Widget> _actionButtons(BuildContext context, String ctaLabel) {
    final strings = AppStrings.of(context);
    return [
      FilledButton.icon(
        onPressed: busy || !plan.canExecute ? null : onQuickSign,
        icon: busy
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Icon(
                plan.canRetryForward
                    ? Icons.forward_to_inbox_outlined
                    : Icons.draw_outlined,
              ),
        label: Text(busyLabel ?? ctaLabel),
      ),
      OutlinedButton.icon(
        onPressed: busy ? null : onEditRecipient,
        icon: const Icon(Icons.person_search_outlined),
        label: Text(strings.pick('Sửa người nhận', 'Change recipient')),
      ),
      TextButton(
        onPressed: busy ? null : onDismiss,
        child: Text(strings.pick('Bỏ qua', 'Dismiss')),
      ),
    ];
  }

  Widget _recipientCard(BuildContext context) {
    final strings = AppStrings.of(context);
    final recipient = plan.recipient;
    final message = switch (plan.recipientResolution.status) {
      'ambiguous' => strings.pick(
          'Trợ lý chưa chốt được người nhận. Hãy sửa người nhận để tiếp tục ký nhanh.',
          'The assistant has not confirmed the recipient yet. Update the recipient to continue.',
        ),
      'not_found' => strings.pick(
          'Chưa tìm thấy người nhận phù hợp. Hãy chọn lại người nhận để tiếp tục.',
          'No matching recipient was found. Choose a recipient to continue.',
        ),
      _ when recipient == null => strings.pick(
          'Người nhận chưa được xác nhận. Hãy sửa người nhận trước khi ký nhanh.',
          'The recipient is not confirmed yet. Update the recipient before quick signing.',
        ),
      _ => '',
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: recipient == null
          ? Text(
              message,
              style: const TextStyle(
                color: Color(0xFF475569),
                height: 1.45,
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  strings.pick('Người nhận dự kiến', 'Planned recipient'),
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  recipient.displayName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
                if (recipient.subtitle.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    recipient.subtitle,
                    style: const TextStyle(
                      color: Color(0xFF475569),
                      height: 1.45,
                    ),
                  ),
                ],
                if (recipient.aliasSummary.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    strings.pick(
                      'Alias: ${recipient.aliasSummary}',
                      'Aliases: ${recipient.aliasSummary}',
                    ),
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 12.5,
                    ),
                  ),
                ],
              ],
            ),
    );
  }

  String _errorText() {
    if (plan.blockingReason.trim().isNotEmpty) {
      return plan.blockingReason;
    }
    if (plan.lastErrorMessage.trim().isNotEmpty) {
      return plan.lastErrorMessage;
    }
    return '';
  }

  String _signatureModeLabel(AppStrings strings) {
    switch (plan.signatureMode) {
      case 'pkcs7':
        return strings.pick('Ký số PKCS#7', 'PKCS#7 signing');
      case 'approval':
        return strings.pick('Duyệt nội bộ', 'Internal approval');
      default:
        return strings.pick('Luồng ký nhanh', 'Quick-sign flow');
    }
  }

  _QuickSignStatusData _statusData(AppStrings strings) {
    if (plan.isCompleted) {
      return _QuickSignStatusData(
        label: strings.pick('Đã hoàn tất', 'Completed'),
        icon: Icons.verified_outlined,
        color: const Color(0xFF166534),
      );
    }
    if (plan.isPartial) {
      return _QuickSignStatusData(
        label: strings.pick('Thành công một phần', 'Partially completed'),
        icon: Icons.forward_to_inbox_outlined,
        color: const Color(0xFFB45309),
      );
    }
    if (plan.isFailed) {
      return _QuickSignStatusData(
        label: strings.pick('Quick-sign thất bại', 'Quick sign failed'),
        icon: Icons.error_outline,
        color: const Color(0xFFB91C1C),
      );
    }
    if (plan.isBlocked) {
      return _QuickSignStatusData(
        label: strings.pick('Chưa thể ký nhanh', 'Not ready for quick sign'),
        icon: Icons.lock_outline,
        color: const Color(0xFF92400E),
      );
    }
    return _QuickSignStatusData(
      label: strings.pick('Sẵn sàng ký nhanh', 'Ready for quick sign'),
      icon: Icons.bolt_outlined,
      color: const Color(0xFF1D4ED8),
    );
  }

  Widget _chip({
    required String label,
    required Color foreground,
    required Color background,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: foreground,
          fontSize: 12.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _QuickSignStatusData {
  final String label;
  final IconData icon;
  final Color color;

  const _QuickSignStatusData({
    required this.label,
    required this.icon,
    required this.color,
  });
}
