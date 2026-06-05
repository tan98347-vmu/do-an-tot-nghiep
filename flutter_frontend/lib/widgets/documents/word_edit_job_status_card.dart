import 'package:flutter/material.dart';

import '../../core/word_ai_user_messages.dart';
import '../../models/word_ai_job.dart';

class WordEditJobStatusCard extends StatelessWidget {
  final WordAiJob job;
  final VoidCallback? onCancel;

  const WordEditJobStatusCard({
    super.key,
    required this.job,
    this.onCancel,
  });

  Color _statusColor() {
    switch (job.status) {
      case 'completed':
        return const Color(0xFF166534);
      case 'failed':
      case 'needs_review':
        return const Color(0xFFB91C1C);
      case 'claimed':
      case 'editing':
      case 'uploading':
        return const Color(0xFF1D4ED8);
      case 'cancelled':
        return const Color(0xFF6B7280);
      default:
        return const Color(0xFFD97706);
    }
  }

  String _shortChecksum(dynamic rawValue) {
    final text = (rawValue ?? '').toString();
    if (text.isEmpty) {
      return 'n/a';
    }
    return text.length <= 12 ? text : text.substring(0, 12);
  }

  Widget _buildToolChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFE2E8F0),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 11,
          color: Color(0xFF334155),
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final color = _statusColor();
    final latestMessage = job.latestEvent?.message.trim() ?? '';
    final latestIsWarning = job.latestEvent?.level == 'warning' && latestMessage.isNotEmpty;
    final summary = wordAiSummaryForUser(job);
    final technicalDetail = wordAiTechnicalDetailForUser(job);
    final summaryColor = switch (job.status) {
      'completed' => const Color(0xFF166534),
      'failed' || 'needs_review' => const Color(0xFF991B1B),
      'queued' => const Color(0xFF9A3412),
      _ => const Color(0xFF334155),
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Job #${job.id}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  wordAiStatusLabel(job.status),
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            summary,
            style: TextStyle(
              height: 1.45,
              color: summaryColor,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (latestIsWarning) ...[
            const SizedBox(height: 8),
            const Text(
              'Gợi ý: kiểm tra xem Word AI Worker đã mở và đang kết nối hay chưa.',
              style: TextStyle(
                fontSize: 12,
                color: Color(0xFFB45309),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            'Chế độ xử lý: ${job.runtimeLabel} | Kế hoạch: ${job.planMode.isEmpty ? 'đang chuẩn bị' : job.planMode} | Slot: ${job.currentSlotLabel.isEmpty ? 'chưa gán' : job.currentSlotLabel}',
            style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 8),
          Text(
            'Bước hiện tại: ${job.currentPhaseLabel}',
            style: const TextStyle(fontSize: 12, color: Color(0xFF475569), fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            'Các bước Word AI: ${job.transcriptPreview}',
            style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
          ),
          if (job.toolStepLabels.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: job.toolStepLabels.take(8).map(_buildToolChip).toList(),
            ),
          ],
          const SizedBox(height: 6),
          Text(
            'Kiểm tra cuối cùng: ${job.verificationSummaryText}',
            style: TextStyle(
              fontSize: 12,
              color: job.hasVerification
                  ? (job.isVerified ? const Color(0xFF166534) : const Color(0xFFB45309))
                  : const Color(0xFF64748B),
              fontWeight: FontWeight.w600,
            ),
          ),
          if (job.verificationEvidenceLines.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...job.verificationEvidenceLines.map(
              (line) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  line,
                  style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                ),
              ),
            ),
          ],
          if (technicalDetail != null) ...[
            const SizedBox(height: 6),
            Text(
              'Chi tiết kỹ thuật: $technicalDetail',
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF64748B),
              ),
            ),
          ],
          if (job.documentChecksums.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'Tệp kết quả: ${job.artifactManifest['output_kind'] ?? 'n/a'} | SHA256: ${_shortChecksum(job.documentChecksums['output_docx_sha256'])}',
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
          ],
          if (job.hasExportArtifactVerification) ...[
            const SizedBox(height: 6),
            Text(
              job.exportArtifactSummary,
              style: TextStyle(
                fontSize: 12,
                color: job.exportArtifactVerified ? const Color(0xFF166534) : const Color(0xFF991B1B),
              ),
            ),
          ],
          if (job.canCancel && onCancel != null) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: onCancel,
                icon: const Icon(Icons.cancel_outlined, size: 16),
                label: const Text('Hủy yêu cầu'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
