import 'package:flutter/material.dart';

import '../../models/share_grant.dart';

class GrantStatusBadge extends StatelessWidget {
  final ShareApprovalStatus status;

  const GrantStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      ShareApprovalStatus.active => (Colors.green, 'Đã kích hoạt'),
      ShareApprovalStatus.pendingLeader =>
        (Colors.orange, 'Chờ trưởng nhóm duyệt'),
      ShareApprovalStatus.pendingAdmin =>
        (Colors.deepOrange, 'Chờ admin duyệt'),
      ShareApprovalStatus.rejected => (Colors.red, 'Bị từ chối'),
      ShareApprovalStatus.draft => (Colors.grey, 'Nháp'),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color.shade800,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

extension on Color {
  Color get shade800 {
    if (this is MaterialColor) return (this as MaterialColor).shade800;
    return this;
  }
}
