import 'package:flutter/material.dart';

import '../../models/peer_audience.dart';

class PermissionLevelDropdown extends StatelessWidget {
  final PeerPermission value;
  final ValueChanged<PeerPermission> onChanged;
  final bool enabled;

  const PermissionLevelDropdown({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final options = PeerPermission.values
        .where((permission) => permission != PeerPermission.owner)
        .toList();

    return DropdownButtonFormField<PeerPermission>(
      value: value == PeerPermission.owner ? PeerPermission.delete : value,
      isDense: true,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        isDense: true,
        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      ),
      items: options
          .map(
            (permission) => DropdownMenuItem<PeerPermission>(
              value: permission,
              child: Text(
                peerPermissionLabel(permission),
                style: const TextStyle(fontSize: 12),
              ),
            ),
          )
          .toList(),
      onChanged: enabled
          ? (permission) {
              if (permission != null) onChanged(permission);
            }
          : null,
    );
  }
}
