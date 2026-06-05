import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../models/peer_audience.dart';
import 'peer_user_search_dialog.dart';
import 'permission_level_dropdown.dart';

class PeerAudienceSection extends ConsumerStatefulWidget {
  final String entityType;
  final int entityId;
  final bool readOnly;

  const PeerAudienceSection({
    super.key,
    required this.entityType,
    required this.entityId,
    this.readOnly = false,
  });

  @override
  ConsumerState<PeerAudienceSection> createState() => _PeerAudienceSectionState();
}

class _PeerAudienceSectionState extends ConsumerState<PeerAudienceSection> {
  bool _loading = true;
  bool _busy = false;
  String? _error;
  PeerAudienceState? _state;

  String get _audienceUrl => '${widget.entityType}/${widget.entityId}/audience/';
  String get _submitUrl => '${widget.entityType}/${widget.entityId}/peer-submit/';

  @override
  void initState() {
    super.initState();
    _loadAudience();
  }

  Future<void> _loadAudience() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final resp = await ApiClient().dio.get(_audienceUrl);
      if (!mounted) return;
      setState(() {
        _state = PeerAudienceState.fromJson(Map<String, dynamic>.from(resp.data as Map));
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _extractDetail(e);
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  String _extractDetail(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString();
    }
    return error.message ?? 'Loi khong xac dinh';
  }

  Future<void> _withBusy(Future<void> Function() task) async {
    setState(() => _busy = true);
    try {
      await task();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _syncAudience(List<PeerAudienceEntry> audiences) async {
    await _withBusy(() async {
      try {
        final resp = await ApiClient().dio.put(
          _audienceUrl,
          data: {
            'audiences': audiences.map((item) => item.toAudiencePayload()).toList(),
          },
        );
        if (!mounted) return;
        setState(() {
          _state = PeerAudienceState.fromJson(Map<String, dynamic>.from(resp.data as Map));
          _error = null;
        });
      } on DioException catch (e) {
        if (!mounted) return;
        _showSnack(_extractDetail(e), isError: true);
      }
    });
  }

  Future<void> _addPeers() async {
    final current = _state;
    if (current == null) return;
    final existingIds = current.audiences.map((item) => item.userId).toSet();
    final picked = await PeerUserSearchDialog.show(
      context,
      alreadyInAudience: existingIds,
    );
    if (picked == null || picked.isEmpty) return;

    final merged = [
      ...current.audiences,
      ...picked
          .where((userId) => !existingIds.contains(userId))
          .map((userId) => PeerAudienceEntry(userId: userId, permissionLevel: PeerPermission.view)),
    ];
    await _syncAudience(merged);
  }

  Future<void> _removePeer(int userId) async {
    final current = _state;
    if (current == null) return;
    await _syncAudience(
      current.audiences.where((item) => item.userId != userId).toList(),
    );
  }

  Future<void> _changePermission(PeerAudienceEntry entry, PeerPermission value) async {
    final current = _state;
    if (current == null) return;
    await _syncAudience(
      current.audiences
          .map((item) => item.userId == entry.userId ? item.copyWith(permissionLevel: value) : item)
          .toList(),
    );
  }

  Future<void> _submitForApproval() async {
    await _withBusy(() async {
      try {
        await ApiClient().dio.post(_submitUrl);
        await _loadAudience();
        _showSnack('Da gui yeu cau duyet.');
      } on DioException catch (e) {
        if (!mounted) return;
        _showSnack(_extractDetail(e), isError: true);
      }
    });
  }

  void _showSnack(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
      ),
    );
  }

  Color _statusColor(String s) => switch (s) {
        'active' => Colors.green,
        'pending_leader' => Colors.orange,
        'rejected' => Colors.red,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    final state = _state;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: _loading
            ? const SizedBox(
                height: 80,
                child: Center(child: CircularProgressIndicator()),
              )
            : _error != null
                ? Text('Loi: $_error', style: const TextStyle(color: Colors.red))
                : state == null
                    ? const Text('Khong tai duoc audience.')
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.people_alt_outlined, size: 18, color: Colors.blue),
                              const SizedBox(width: 6),
                              const Expanded(
                                child: Text(
                                  'Chia se cho dong nghiep',
                                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: _statusColor(state.status).withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  state.statusLabel,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: _statusColor(state.status),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          if (state.status == 'rejected' && state.approverNote.isNotEmpty)
                            Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: Colors.red.shade200),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Ly do tu choi tu truong nhom:',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.red,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(state.approverNote, style: const TextStyle(fontSize: 12)),
                                ],
                              ),
                            ),
                          const Text(
                            'Nguoi duoc chia se:',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                          const SizedBox(height: 8),
                          if (state.audiences.isEmpty)
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 8),
                              child: Text(
                                'Chua co ai. Bam "Them dong nghiep" de chon.',
                                style: TextStyle(color: Colors.grey, fontSize: 12),
                              ),
                            )
                          else
                            Column(
                              children: state.audiences
                                  .map(
                                    (entry) => Container(
                                      margin: const EdgeInsets.only(bottom: 8),
                                      padding: const EdgeInsets.all(10),
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: Colors.grey.shade300),
                                      ),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          CircleAvatar(
                                            radius: 18,
                                            backgroundColor: Colors.blue.shade100,
                                            child: Text(
                                              entry.displayName.substring(0, 1).toUpperCase(),
                                              style: const TextStyle(fontSize: 12),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  entry.displayName,
                                                  style: const TextStyle(
                                                    fontWeight: FontWeight.w600,
                                                    fontSize: 13,
                                                  ),
                                                ),
                                                if ((entry.userEmail ?? '').isNotEmpty)
                                                  Text(
                                                    entry.userEmail!,
                                                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                                                  ),
                                                if ((entry.userPosition ?? '').isNotEmpty)
                                                  Text(
                                                    entry.userPosition!,
                                                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                                                  ),
                                              ],
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          SizedBox(
                                            width: 150,
                                            child: PermissionLevelDropdown(
                                              value: entry.permissionLevel,
                                              enabled: !widget.readOnly && !_busy,
                                              onChanged: (value) => _changePermission(entry, value),
                                            ),
                                          ),
                                          const SizedBox(width: 6),
                                          IconButton(
                                            tooltip: 'Xoa khoi audience',
                                            onPressed: widget.readOnly || _busy
                                                ? null
                                                : () => _removePeer(entry.userId),
                                            icon: const Icon(Icons.close, size: 18),
                                          ),
                                        ],
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                          const SizedBox(height: 10),
                          if (!widget.readOnly)
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                OutlinedButton.icon(
                                  icon: const Icon(Icons.person_add_alt, size: 16),
                                  label: const Text('Them dong nghiep'),
                                  onPressed: _busy ? null : _addPeers,
                                ),
                                if (state.audiences.isNotEmpty &&
                                    (state.status == 'none' || state.status == 'rejected'))
                                  FilledButton.icon(
                                    icon: _busy
                                        ? const SizedBox(
                                            width: 14,
                                            height: 14,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white,
                                            ),
                                          )
                                        : const Icon(Icons.send, size: 16),
                                    label: Text(
                                      state.status == 'rejected'
                                          ? 'Gui lai de duyet'
                                          : 'Gui duyet',
                                    ),
                                    onPressed: _busy ? null : _submitForApproval,
                                  ),
                              ],
                            ),
                        ],
                      ),
      ),
    );
  }
}
