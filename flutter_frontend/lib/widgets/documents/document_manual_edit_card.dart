import 'package:flutter/material.dart';

import '../../models/document.dart';

class DocumentManualEditCard extends StatelessWidget {
  final Document document;
  final VoidCallback onOpen;

  const DocumentManualEditCard({
    super.key,
    required this.document,
    required this.onOpen,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final canOpen = document.hasFile && document.canManualEdit;
    final actionLabel = document.canResumeManualEdit
        ? 'Tiep tuc phien chinh sua'
        : 'Chinh sua van ban';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Chinh sua thu cong',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              document.hasFile
                  ? 'Mo trinh sua web de sua truc tiep file DOCX hien tai va luu thanh phien ban moi.'
                  : 'Van ban nay chua co DOCX committed de mo trong trinh sua thu cong.',
              style: theme.textTheme.bodySmall,
            ),
            if ((document.manualEditLockMessage ?? '').isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.amber.shade200),
                ),
                child: Text(
                  document.manualEditLockMessage!,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: Colors.amber.shade900,
                  ),
                ),
              ),
            ],
            if ((document.manualEditLockedByName ?? '').isNotEmpty &&
                !document.canResumeManualEdit) ...[
              const SizedBox(height: 8),
              Text(
                'Nguoi dang giu phien: ${document.manualEditLockedByName}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.grey.shade700,
                ),
              ),
            ],
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: canOpen ? onOpen : null,
                icon: const Icon(Icons.edit_document),
                label: Text(actionLabel),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
