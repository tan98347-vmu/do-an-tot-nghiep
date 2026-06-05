// r5/M10 — Hien thi badge bao mat cho backup record:
//   - "Da ma hoa" / "Chua ma hoa"
//   - "Da ky so" / "Chu ky khong hop le" / "Chua ky"
//
// Cach dung:
//   BackupSecurityBadge(
//     isEncrypted: backup.isEncrypted,
//     signatureStatus: backup.signatureStatus,
//     algorithm: backup.encryptionAlgorithm,
//   )

import 'package:flutter/material.dart';

class BackupSecurityBadge extends StatelessWidget {
  final bool isEncrypted;
  final String signatureStatus; // 'unsigned' | 'signed' | 'invalid'
  final String algorithm;
  final bool compact;

  const BackupSecurityBadge({
    super.key,
    required this.isEncrypted,
    required this.signatureStatus,
    this.algorithm = '',
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[
      _encryptionChip(context),
      _signatureChip(context),
    ];
    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: children,
    );
  }

  Widget _encryptionChip(BuildContext context) {
    if (isEncrypted) {
      final label = compact
          ? 'Da ma hoa'
          : 'Da ma hoa${algorithm.isNotEmpty ? ' ($algorithm)' : ''}';
      return Tooltip(
        message: 'File luu disk dang ciphertext AES-256-GCM',
        child: Chip(
          avatar: const Icon(Icons.lock, size: 16, color: Colors.green),
          label: Text(label),
          backgroundColor: const Color(0xFFE8F5E9),
          visualDensity: VisualDensity.compact,
        ),
      );
    }
    return Tooltip(
      message: 'File luu disk dang plaintext (chua ma hoa)',
      child: Chip(
        avatar: const Icon(Icons.lock_open, size: 16, color: Colors.orange),
        label: const Text('Chua ma hoa'),
        backgroundColor: const Color(0xFFFFF3E0),
        visualDensity: VisualDensity.compact,
      ),
    );
  }

  Widget _signatureChip(BuildContext context) {
    switch (signatureStatus) {
      case 'signed':
        return Tooltip(
          message: 'Đã ký số RSA-PSS SHA256',
          child: Chip(
            avatar: const Icon(Icons.verified_user, size: 16, color: Colors.green),
            label: const Text('Đã ký số'),
            backgroundColor: const Color(0xFFE8F5E9),
            visualDensity: VisualDensity.compact,
          ),
        );
      case 'invalid':
        return Tooltip(
          message: 'Chu ky khong khop noi dung — backup co the bi thay doi!',
          child: Chip(
            avatar: const Icon(Icons.gpp_bad, size: 16, color: Colors.red),
            label: const Text('Chu ky khong hop le'),
            backgroundColor: const Color(0xFFFFEBEE),
            visualDensity: VisualDensity.compact,
          ),
        );
      default:
        return Tooltip(
          message: 'Backup nay chua duoc ky so',
          child: Chip(
            avatar: const Icon(Icons.gpp_maybe, size: 16, color: Colors.grey),
            label: const Text('Chua ky'),
            backgroundColor: const Color(0xFFEEEEEE),
            visualDensity: VisualDensity.compact,
          ),
        );
    }
  }
}
