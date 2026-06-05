import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../models/signing.dart';
import '../../providers/notifications_provider.dart';
import '../../providers/signing_summary_provider.dart';

final _pendingSigningProposalProvider =
    FutureProvider.autoDispose<List<SigningProposal>>((ref) async {
  final resp = await ApiClient().dio.get('signing/proposals/pending-hr/');
  return (resp.data as List)
      .map(
        (item) => SigningProposal.fromJson(
          Map<String, dynamic>.from(item as Map),
        ),
      )
      .toList();
});

class SigningProposalReviewScreen extends ConsumerWidget {
  final int? initialProposalId;

  const SigningProposalReviewScreen({
    super.key,
    this.initialProposalId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proposalsAsync = ref.watch(_pendingSigningProposalProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Duyệt đề xuất ký'),
      ),
      body: proposalsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Lỗi: $error')),
        data: (proposals) {
          if (proposals.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.verified_outlined,
                    size: 56,
                    color: Colors.green.shade400,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Không còn đề xuất ký nào chờ duyệt.',
                    style: TextStyle(fontSize: 15),
                  ),
                ],
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(_pendingSigningProposalProvider);
              await Future<void>.delayed(const Duration(milliseconds: 250));
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: proposals.length,
              itemBuilder: (context, index) {
                final proposal = proposals[index];
                return _ProposalCard(
                  proposal: proposal,
                  highlighted: proposal.id == initialProposalId,
                  onApprove: () => _approve(context, ref, proposal),
                  onReject: () => _reject(context, ref, proposal),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Future<void> _approve(
    BuildContext context,
    WidgetRef ref,
    SigningProposal proposal,
  ) async {
    try {
      await ApiClient().dio.post(
        'signing/proposals/${proposal.id}/approve/',
      );
      _invalidate(ref);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã duyệt đề xuất ký.')),
      );
    } on DioException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Lỗi: ${error.response?.data?['detail'] ?? error.message}',
          ),
        ),
      );
    }
  }

  Future<void> _reject(
    BuildContext context,
    WidgetRef ref,
    SigningProposal proposal,
  ) async {
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Từ chối đề xuất ký'),
        content: TextField(
          controller: noteCtrl,
          minLines: 2,
          maxLines: 5,
          decoration: const InputDecoration(
            labelText: 'Lý do từ chối *',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Từ chối'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    final note = noteCtrl.text.trim();
    if (note.isEmpty) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Phải có lý do từ chối.')),
      );
      return;
    }

    try {
      await ApiClient().dio.post(
        'signing/proposals/${proposal.id}/reject/',
        data: {'review_note': note},
      );
      _invalidate(ref);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã từ chối đề xuất ký.')),
      );
    } on DioException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Lỗi: ${error.response?.data?['detail'] ?? error.message}',
          ),
        ),
      );
    }
  }

  void _invalidate(WidgetRef ref) {
    ref.invalidate(_pendingSigningProposalProvider);
    ref.invalidate(signingSummaryProvider);
    ref.invalidate(notificationsProvider);
    ref.invalidate(unreadNotificationCountProvider);
  }
}

class _ProposalCard extends StatelessWidget {
  final SigningProposal proposal;
  final bool highlighted;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  const _ProposalCard({
    required this.proposal,
    required this.highlighted,
    required this.onApprove,
    required this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    final borderColor = highlighted ? Colors.blue : Colors.grey.shade300;
    final background = highlighted ? Colors.blue.shade50 : Colors.white;
    return Card(
      color: background,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        side: BorderSide(color: borderColor),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.description_outlined, color: Colors.blue),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        proposal.documentTitle,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Nguoi de xuat: ${proposal.proposedByName}',
                        style: TextStyle(
                          color: Colors.grey.shade700,
                          fontSize: 12.5,
                        ),
                      ),
                      Text(
                        'Nguoi so huu van ban: ${proposal.documentOwnerName}',
                        style: TextStyle(
                          color: Colors.grey.shade700,
                          fontSize: 12.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (proposal.proposalNote.trim().isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Text(proposal.proposalNote),
              ),
            ],
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: proposal.signers
                  .map(
                    (signer) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade100,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        'B${signer.stepNo}: ${signer.signerName} - ${signer.displayRole}',
                        style: const TextStyle(fontSize: 11.5),
                      ),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    proposal.createdAt.replaceFirst('T', ' ').substring(
                          0,
                          proposal.createdAt.length >= 16
                              ? 16
                              : proposal.createdAt.length,
                        ),
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 12,
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: onReject,
                  icon: const Icon(Icons.close, size: 16),
                  label: const Text('Từ chối'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.red,
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: onApprove,
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text('Duyệt'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
