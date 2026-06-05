// Dialog don gian de chon 1 UserGroup tu API `groups/`.

import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../models/share_grant.dart';

class GroupPickerDialog extends StatefulWidget {
  const GroupPickerDialog({super.key});

  static Future<GroupBrief?> show(BuildContext context) {
    return showDialog<GroupBrief>(
      context: context,
      builder: (_) => const GroupPickerDialog(),
    );
  }

  @override
  State<GroupPickerDialog> createState() => _GroupPickerDialogState();
}

class _GroupPickerDialogState extends State<GroupPickerDialog> {
  bool _loading = true;
  String? _error;
  List<GroupBrief> _groups = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final resp = await ApiClient().dio.get('groups/');
      final data = resp.data;
      final list = data is List
          ? data
          : (data is Map ? (data['results'] ?? data['groups'] ?? []) : []);
      setState(() {
        _groups = (list as List)
            .map((e) => GroupBrief.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Chọn nhóm'),
      content: SizedBox(
        width: 360,
        child: _loading
            ? const SizedBox(
                height: 80, child: Center(child: CircularProgressIndicator()))
            : _error != null
                ? Text(_error!, style: const TextStyle(color: Colors.red))
                : _groups.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 16),
                        child: Text(
                          'Không có nhóm để chia sẻ.\nTài khoản của bạn cần thuộc '
                          'một công ty có nhóm (hoặc là thành viên của một nhóm). '
                          'Liên hệ quản trị để được thêm vào nhóm.',
                          style: TextStyle(color: Colors.grey),
                        ),
                      )
                    : ListView.builder(
                        shrinkWrap: true,
                        itemCount: _groups.length,
                        itemBuilder: (_, i) {
                          final g = _groups[i];
                          return ListTile(
                            title: Text(g.name),
                            onTap: () => Navigator.of(context).pop(g),
                          );
                        },
                      ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
      ],
    );
  }
}
