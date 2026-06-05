// r2/M4 — Card hien thi ket qua compliance check.
//   - Pass: banner xanh + text CHINH XAC (xem yeu cau goc).
//   - Fail: danh sach requirement chua dat.

import 'package:flutter/material.dart';

import '../../../models/compliance_result.dart';

class ComplianceResultCard extends StatelessWidget {
  final ComplianceResult result;
  final VoidCallback onRetry;

  const ComplianceResultCard({
    super.key,
    required this.result,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    if (result.passed) {
      return Card(
        color: Colors.green.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.check_circle, color: Colors.green.shade700, size: 28),
                const SizedBox(width: 8),
                const Expanded(
                  child: SelectableText(
                    // CHINH XAC theo yeu cau goc — KHONG sua chu nay.
                    ComplianceResult.passMessage,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF14532D),
                    ),
                  ),
                ),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 6, children: [
                OutlinedButton.icon(
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Kiểm tra lại'),
                  onPressed: onRetry,
                ),
              ]),
            ],
          ),
        ),
      );
    }

    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.gpp_bad, color: Colors.red.shade700, size: 24),
              const SizedBox(width: 8),
              const Text(
                'Văn bản chưa đáp ứng các yêu cầu sau:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
            ]),
            const SizedBox(height: 12),
            ...result.itemsMissing.map((item) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.cancel, color: Colors.red, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.requirement,
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              item.explanation,
                              style: const TextStyle(
                                fontStyle: FontStyle.italic,
                                color: Color(0xFF7F1D1D),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                )),
            const SizedBox(height: 12),
            Wrap(spacing: 6, children: [
              OutlinedButton.icon(
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Kiểm tra lại'),
                onPressed: onRetry,
              ),
            ]),
          ],
        ),
      ),
    );
  }
}
