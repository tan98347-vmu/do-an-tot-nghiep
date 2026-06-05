import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_strings.dart';
import '../../models/document.dart';
import '../../models/document_summary.dart';
import '../../providers/document_summaries_provider.dart';

class DocumentSummaryDiscoveryScreen extends ConsumerStatefulWidget {
  final Map<String, String> initialQueryParameters;

  const DocumentSummaryDiscoveryScreen({
    super.key,
    required this.initialQueryParameters,
  });

  @override
  ConsumerState<DocumentSummaryDiscoveryScreen> createState() =>
      _DocumentSummaryDiscoveryScreenState();
}

class _DocumentSummaryDiscoveryScreenState
    extends ConsumerState<DocumentSummaryDiscoveryScreen> {
  late DocumentSummaryDiscoveryParams _params;
  late final TextEditingController _searchController;
  late final TextEditingController _tagController;
  late final TextEditingController _docNumberController;
  late final FocusNode _searchFocusNode;

  Timer? _searchDebounce;
  Timer? _suggestionDebounce;
  int _suggestionRequestId = 0;
  bool _loadingSuggestions = false;
  List<DocumentSummarySuggestion> _suggestions = const [];

  AppStrings get _strings => AppStrings.of(context);
  String _tr(String vi, String en) => _strings.pick(vi, en);

  @override
  void initState() {
    super.initState();
    _params = DocumentSummaryDiscoveryParams.fromRouteQuery(
      widget.initialQueryParameters,
    );
    _searchController = TextEditingController(text: _params.q);
    _tagController = TextEditingController(text: _params.tag);
    _docNumberController = TextEditingController(text: _params.docNumber);
    _searchFocusNode = FocusNode()..addListener(_handleSearchFocusChanged);
    if (_params.q.trim().length >= 2) {
      _fetchSuggestions(_params.q.trim());
    }
  }

  @override
  void didUpdateWidget(covariant DocumentSummaryDiscoveryScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final routeParams = DocumentSummaryDiscoveryParams.fromRouteQuery(
      widget.initialQueryParameters,
    );
    if (routeParams == _params) {
      return;
    }
    _applyRouteParams(routeParams);
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _suggestionDebounce?.cancel();
    _searchController.dispose();
    _tagController.dispose();
    _docNumberController.dispose();
    _searchFocusNode
      ..removeListener(_handleSearchFocusChanged)
      ..dispose();
    super.dispose();
  }

  void _handleSearchFocusChanged() {
    if (!_searchFocusNode.hasFocus && mounted) {
      setState(() => _suggestions = const []);
    } else if (_searchFocusNode.hasFocus &&
        _searchController.text.trim().length >= 2) {
      _scheduleSuggestionFetch(_searchController.text);
    }
  }

  void _applyRouteParams(DocumentSummaryDiscoveryParams params) {
    setState(() {
      _params = params;
      _searchController.text = params.q;
      _tagController.text = params.tag;
      _docNumberController.text = params.docNumber;
    });
    _scheduleSuggestionFetch(params.q);
  }

  void _applyParams(
    DocumentSummaryDiscoveryParams nextParams, {
    bool syncRoute = true,
    bool refreshSuggestions = true,
  }) {
    setState(() {
      _params = nextParams;
    });
    if (refreshSuggestions) {
      _scheduleSuggestionFetch(_searchController.text);
    }
    if (!syncRoute || !mounted) {
      return;
    }
    final nextLocation = Uri(
      path: '/summaries',
      queryParameters: nextParams.toRouteQueryParameters(),
    ).toString();
    if (GoRouterState.of(context).uri.toString() != nextLocation) {
      context.go(nextLocation);
    }
  }

  void _scheduleSearchUpdate() {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 260), () {
      _applyParams(
        _params.copyWith(
          q: _searchController.text.trim(),
          offset: 0,
        ),
      );
    });
  }

  void _scheduleSuggestionFetch(String rawQuery) {
    _suggestionDebounce?.cancel();
    final query = rawQuery.trim();
    if (query.length < 2 || !_searchFocusNode.hasFocus) {
      setState(() {
        _loadingSuggestions = false;
        _suggestions = const [];
      });
      return;
    }
    _suggestionDebounce = Timer(const Duration(milliseconds: 220), () {
      _fetchSuggestions(query);
    });
  }

  Future<void> _fetchSuggestions(String query) async {
    final requestId = ++_suggestionRequestId;
    setState(() => _loadingSuggestions = true);
    try {
      final suggestions =
          await ref.read(documentSummaryApiProvider).fetchSuggestions(
                query: query,
                params: _params.copyWith(q: query, offset: 0),
              );
      if (!mounted || requestId != _suggestionRequestId) {
        return;
      }
      setState(() {
        _loadingSuggestions = false;
        _suggestions = suggestions;
      });
    } catch (_) {
      if (!mounted || requestId != _suggestionRequestId) {
        return;
      }
      setState(() {
        _loadingSuggestions = false;
        _suggestions = const [];
      });
    }
  }

  void _selectSuggestion(DocumentSummarySuggestion suggestion) {
    switch (suggestion.type) {
      case 'document':
        if (suggestion.documentId != null) {
          context.go('/summaries/${suggestion.documentId}');
        }
        break;
      case 'tag':
        _tagController.text = suggestion.value;
        _applyParams(
          _params.copyWith(
            tag: suggestion.value,
            offset: 0,
          ),
          refreshSuggestions: false,
        );
        break;
      case 'doc_number':
        _docNumberController.text = suggestion.value;
        _applyParams(
          _params.copyWith(
            docNumber: suggestion.value,
            offset: 0,
          ),
          refreshSuggestions: false,
        );
        break;
      default:
        _searchController.text = suggestion.value;
        _applyParams(
          _params.copyWith(
            q: suggestion.value,
            offset: 0,
          ),
        );
        break;
    }
    FocusScope.of(context).unfocus();
    setState(() => _suggestions = const []);
  }

  String _formatUpdatedAt(String rawValue) {
    try {
      final parsed = DateTime.parse(rawValue).toLocal();
      return DateFormat('dd/MM/yyyy HH:mm').format(parsed);
    } catch (_) {
      return rawValue;
    }
  }

  String _statusLabel(Document document) {
    switch (document.status) {
      case 'final':
        return _tr('Chính thức', 'Final');
      case 'archived':
        return _tr('Lưu trữ', 'Archived');
      default:
        return _tr('Nháp', 'Draft');
    }
  }

  String _visibilityLabel(Document document) {
    switch (document.visibility) {
      case 'group':
        return _tr('Nhóm', 'Group');
      case 'public':
        return _tr('Công khai', 'Public');
      default:
        return _tr('Riêng tư', 'Private');
    }
  }

  Color _chipBackgroundColor(String value) {
    switch (value) {
      case 'final':
      case 'public':
        return const Color(0xFFDCFCE7);
      case 'group':
        return const Color(0xFFE0E7FF);
      case 'archived':
        return const Color(0xFFE2E8F0);
      default:
        return const Color(0xFFFEF3C7);
    }
  }

  Widget _buildFilterDropdown({
    required String label,
    required String value,
    required List<DocumentSummaryFacetOption> options,
    required ValueChanged<String> onChanged,
  }) {
    final hasValue =
        value.isNotEmpty && options.any((option) => option.value == value);
    return DropdownButtonFormField<String>(
      initialValue: hasValue ? value : '',
      decoration: InputDecoration(
        labelText: label,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        filled: true,
        fillColor: Colors.white,
      ),
      items: [
        DropdownMenuItem(
          value: '',
          child: Text(_tr('Tất cả', 'All')),
        ),
        ...options.map(
          (option) => DropdownMenuItem(
            value: option.value,
            child: Text(option.label),
          ),
        ),
      ],
      onChanged: (next) => onChanged(next ?? ''),
    );
  }

  Widget _buildNamedFilterDropdown({
    required String label,
    required int? value,
    required List<DocumentSummaryNamedFacetOption> options,
    required ValueChanged<int?> onChanged,
  }) {
    final selectedValue =
        options.any((option) => option.id == value) ? value : null;
    return DropdownButtonFormField<int?>(
      initialValue: selectedValue,
      decoration: InputDecoration(
        labelText: label,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        filled: true,
        fillColor: Colors.white,
      ),
      items: [
        DropdownMenuItem<int?>(
          value: null,
          child: Text(_tr('Tất cả', 'All')),
        ),
        ...options.map(
          (option) => DropdownMenuItem<int?>(
            value: option.id,
            child: Text(option.label),
          ),
        ),
      ],
      onChanged: onChanged,
    );
  }

  Widget _buildFilterPanel(DocumentSummaryFacets facets) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.tune, color: Color(0xFF2563EB)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _tr('Bộ lọc tìm kiếm', 'Search filters'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildFilterDropdown(
            label: _tr('Phạm vi truy cập', 'Access scope'),
            value: _params.scope,
            options: facets.scopes,
            onChanged: (value) => _applyParams(
              _params.copyWith(scope: value.isEmpty ? 'all' : value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildFilterDropdown(
            label: _tr('Trạng thái văn bản', 'Document status'),
            value: _params.status,
            options: facets.statuses,
            onChanged: (value) => _applyParams(
              _params.copyWith(status: value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildFilterDropdown(
            label: _tr('Mức chia sẻ', 'Visibility'),
            value: _params.visibility,
            options: facets.visibilities,
            onChanged: (value) => _applyParams(
              _params.copyWith(visibility: value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildFilterDropdown(
            label: _tr('Trạng thái chia sẻ', 'Sharing status'),
            value: _params.shareStatus,
            options: facets.shareStatuses,
            onChanged: (value) => _applyParams(
              _params.copyWith(shareStatus: value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildFilterDropdown(
            label: _tr('Trạng thái ký số', 'Signing status'),
            value: _params.signingStatus,
            options: facets.signingStatuses,
            onChanged: (value) => _applyParams(
              _params.copyWith(signingStatus: value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildFilterDropdown(
            label: _tr('Nguồn tài liệu', 'Source type'),
            value: _params.sourceType,
            options: facets.sourceTypes,
            onChanged: (value) => _applyParams(
              _params.copyWith(sourceType: value, offset: 0),
            ),
          ),
          const SizedBox(height: 12),
          _buildNamedFilterDropdown(
            label: _tr('Danh mục', 'Category'),
            value: _params.categoryId,
            options: facets.categories,
            onChanged: (value) => _applyParams(
              _params.copyWith(
                categoryId: value,
                clearCategoryId: value == null,
                offset: 0,
              ),
            ),
          ),
          const SizedBox(height: 12),
          _buildNamedFilterDropdown(
            label: _tr('Nhóm', 'Group'),
            value: _params.groupId,
            options: facets.groups,
            onChanged: (value) => _applyParams(
              _params.copyWith(
                groupId: value,
                clearGroupId: value == null,
                offset: 0,
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _tagController,
            onSubmitted: (value) => _applyParams(
              _params.copyWith(tag: value.trim(), offset: 0),
              refreshSuggestions: false,
            ),
            decoration: InputDecoration(
              labelText: _tr('Tag', 'Tag'),
              hintText: facets.tags.take(4).join(', '),
              suffixIcon: IconButton(
                onPressed: () => _applyParams(
                  _params.copyWith(tag: _tagController.text.trim(), offset: 0),
                  refreshSuggestions: false,
                ),
                icon: const Icon(Icons.search),
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              filled: true,
              fillColor: Colors.white,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _docNumberController,
            onSubmitted: (value) => _applyParams(
              _params.copyWith(docNumber: value.trim(), offset: 0),
              refreshSuggestions: false,
            ),
            decoration: InputDecoration(
              labelText: _tr('Mã văn bản', 'Document number'),
              suffixIcon: IconButton(
                onPressed: () => _applyParams(
                  _params.copyWith(
                    docNumber: _docNumberController.text.trim(),
                    offset: 0,
                  ),
                  refreshSuggestions: false,
                ),
                icon: const Icon(Icons.tag_outlined),
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              filled: true,
              fillColor: Colors.white,
            ),
          ),
          const SizedBox(height: 8),
          SwitchListTile(
            value: _params.editableOnly,
            contentPadding: EdgeInsets.zero,
            title: Text(_tr('Chỉ hiện văn bản tôi có thể sửa',
                'Only show editable documents')),
            onChanged: (value) => _applyParams(
              _params.copyWith(editableOnly: value, offset: 0),
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: () {
                  _searchController.clear();
                  _tagController.clear();
                  _docNumberController.clear();
                  _applyParams(const DocumentSummaryDiscoveryParams());
                },
                icon: const Icon(Icons.restart_alt),
                label: Text(_tr('Đặt lại', 'Reset')),
              ),
              FilledButton.icon(
                onPressed: () => _applyParams(
                  _params.copyWith(
                    q: _searchController.text.trim(),
                    tag: _tagController.text.trim(),
                    docNumber: _docNumberController.text.trim(),
                    offset: 0,
                  ),
                ),
                icon: const Icon(Icons.check_circle_outline),
                label: Text(_tr('Áp dụng', 'Apply')),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _openFiltersOnMobile(DocumentSummaryFacets facets) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 8,
              bottom: MediaQuery.of(context).viewInsets.bottom + 16,
            ),
            child: SingleChildScrollView(
              child: _buildFilterPanel(facets),
            ),
          ),
        );
      },
    );
  }

  Widget _buildSuggestionList() {
    final showSuggestions = _searchFocusNode.hasFocus &&
        (_loadingSuggestions || _suggestions.isNotEmpty) &&
        _searchController.text.trim().length >= 2;
    if (!showSuggestions) {
      return const SizedBox.shrink();
    }
    return Container(
      margin: const EdgeInsets.only(top: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x140F172A),
            blurRadius: 24,
            offset: Offset(0, 14),
          ),
        ],
      ),
      child: _loadingSuggestions
          ? const Padding(
              padding: EdgeInsets.all(18),
              child: Center(child: CircularProgressIndicator()),
            )
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              shrinkWrap: true,
              itemCount: _suggestions.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final suggestion = _suggestions[index];
                final icon = switch (suggestion.type) {
                  'tag' => Icons.sell_outlined,
                  'doc_number' => Icons.badge_outlined,
                  _ => Icons.description_outlined,
                };
                return ListTile(
                  onTap: () => _selectSuggestion(suggestion),
                  leading: Icon(icon, color: const Color(0xFF2563EB)),
                  title: Text(suggestion.label),
                  subtitle: suggestion.caption.isEmpty
                      ? null
                      : Text(
                          suggestion.caption,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                  trailing: Text(
                    suggestion.matchedField,
                    style: const TextStyle(
                      fontSize: 11,
                      color: Color(0xFF64748B),
                    ),
                  ),
                );
              },
            ),
    );
  }

  Widget _buildDocumentCard(Document document) {
    final strings = _strings;
    final metadataParts = <String>[
      if ((document.docNumber ?? '').trim().isNotEmpty)
        document.docNumber!.trim(),
      if ((document.categoryName ?? '').trim().isNotEmpty)
        document.categoryName!.trim(),
      if ((document.groupName ?? '').trim().isNotEmpty)
        document.groupName!.trim(),
      if ((document.departmentName ?? '').trim().isNotEmpty)
        document.departmentName!.trim(),
    ];
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(
                label: Text(_statusLabel(document)),
                backgroundColor: _chipBackgroundColor(document.status),
              ),
              Chip(
                label: Text(_visibilityLabel(document)),
                backgroundColor: _chipBackgroundColor(document.visibility),
              ),
              if (document.isFavorite)
                Chip(
                  label: Text(strings.pick('Yêu thích', 'Favorite')),
                  backgroundColor: const Color(0xFFFFF3C4),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            document.title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF0F172A),
                ),
          ),
          if (metadataParts.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              metadataParts.join(' • '),
              style: const TextStyle(
                color: Color(0xFF475569),
                height: 1.45,
              ),
            ),
          ],
          const SizedBox(height: 10),
          Text(
            strings.pick(
              'Chủ sở hữu: ${document.ownerName} • Cập nhật ${_formatUpdatedAt(document.updatedAt)}',
              'Owner: ${document.ownerName} • Updated ${_formatUpdatedAt(document.updatedAt)}',
            ),
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 12.5,
            ),
          ),
          if (document.tags.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: document.tags
                  .map(
                    (tag) => ActionChip(
                      label: Text('#$tag'),
                      onPressed: () {
                        _tagController.text = tag;
                        _applyParams(
                          _params.copyWith(tag: tag, offset: 0),
                          refreshSuggestions: false,
                        );
                      },
                    ),
                  )
                  .toList(),
            ),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: () => context.go('/summaries/${document.id}'),
                icon: const Icon(Icons.summarize_outlined),
                label:
                    Text(_tr('Mở workspace tóm tắt', 'Open summary workspace')),
              ),
              OutlinedButton.icon(
                onPressed: () => context.push('/documents/${document.id}'),
                icon: const Icon(Icons.open_in_new),
                label: Text(_tr('Mở văn bản gốc', 'Open original document')),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final discoveryAsync = ref.watch(documentSummaryDiscoveryProvider(_params));
    final facets =
        discoveryAsync.asData?.value.facets ?? const DocumentSummaryFacets();
    final isMobile = MediaQuery.sizeOf(context).width < 920;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(0xFFF8FAFC),
            Color(0xFFE0F2FE),
            Color(0xFFDBEAFE),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => ref.refresh(
            documentSummaryDiscoveryProvider(_params).future,
          ),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
              isMobile ? 16 : 24,
              18,
              isMobile ? 16 : 24,
              28,
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1380),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _tr('Tóm tắt văn bản', 'Document summaries'),
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w800,
                                color: const Color(0xFF0F172A),
                              ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _tr(
                        'Tìm mọi văn bản bạn có quyền truy cập, lọc sâu theo phạm vi, trạng thái, tag, mã, rồi mở workspace tóm tắt chuyên biệt.',
                        'Find every document you can access, filter deeply by scope, status, tags, and document number, then open the dedicated summary workspace.',
                      ),
                      style: const TextStyle(
                        color: Color(0xFF334155),
                        height: 1.6,
                      ),
                    ),
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.92),
                        borderRadius: BorderRadius.circular(28),
                        border: Border.all(color: const Color(0xFFDCE7F3)),
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x140F172A),
                            blurRadius: 30,
                            offset: Offset(0, 16),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _searchController,
                                  focusNode: _searchFocusNode,
                                  onChanged: (value) {
                                    _scheduleSearchUpdate();
                                    _scheduleSuggestionFetch(value);
                                  },
                                  decoration: InputDecoration(
                                    hintText: _tr(
                                      'Tìm theo tên văn bản như Google, gõ tới đâu gợi ý tới đó...',
                                      'Search document titles like Google, with live suggestions as you type...',
                                    ),
                                    prefixIcon: const Icon(Icons.search),
                                    suffixIcon: _searchController.text.isEmpty
                                        ? null
                                        : IconButton(
                                            onPressed: () {
                                              _searchController.clear();
                                              _applyParams(
                                                _params.copyWith(
                                                    q: '', offset: 0),
                                              );
                                            },
                                            icon: const Icon(Icons.close),
                                          ),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(999),
                                      borderSide: const BorderSide(
                                        color: Color(0xFFDCE7F3),
                                      ),
                                    ),
                                    enabledBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(999),
                                      borderSide: const BorderSide(
                                        color: Color(0xFFDCE7F3),
                                      ),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(999),
                                      borderSide: const BorderSide(
                                        color: Color(0xFF2563EB),
                                        width: 1.4,
                                      ),
                                    ),
                                    filled: true,
                                    fillColor: const Color(0xFFF8FAFC),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              if (isMobile)
                                FilledButton.tonalIcon(
                                  onPressed: () => _openFiltersOnMobile(facets),
                                  icon: const Icon(Icons.tune),
                                  label: Text(_tr('Bộ lọc', 'Filters')),
                                )
                              else
                                OutlinedButton.icon(
                                  onPressed: () => _openFiltersOnMobile(facets),
                                  icon: const Icon(Icons.tune),
                                  label: Text(_tr('Mở bộ lọc dạng popup',
                                      'Open popup filters')),
                                ),
                            ],
                          ),
                          _buildSuggestionList(),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final showSidePanel = constraints.maxWidth >= 1180;
                        final content = _DiscoveryResultSection(
                          discoveryAsync: discoveryAsync,
                          params: _params,
                          strings: _strings,
                          formatUpdatedAt: _formatUpdatedAt,
                          buildDocumentCard: _buildDocumentCard,
                          onLoadMore: () => _applyParams(
                            _params.copyWith(
                              offset: _params.offset + _params.limit,
                            ),
                            refreshSuggestions: false,
                          ),
                        );
                        if (!showSidePanel) {
                          return content;
                        }
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 340,
                              child: _buildFilterPanel(facets),
                            ),
                            const SizedBox(width: 18),
                            Expanded(child: content),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DiscoveryResultSection extends StatelessWidget {
  final AsyncValue<DocumentSummaryDiscoveryResult> discoveryAsync;
  final DocumentSummaryDiscoveryParams params;
  final AppStrings strings;
  final String Function(String rawValue) formatUpdatedAt;
  final Widget Function(Document document) buildDocumentCard;
  final VoidCallback onLoadMore;

  const _DiscoveryResultSection({
    required this.discoveryAsync,
    required this.params,
    required this.strings,
    required this.formatUpdatedAt,
    required this.buildDocumentCard,
    required this.onLoadMore,
  });

  String _tr(String vi, String en) => strings.pick(vi, en);

  @override
  Widget build(BuildContext context) {
    return discoveryAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 80),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, _) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: const Color(0xFFFCA5A5)),
        ),
        child: Column(
          children: [
            const Icon(Icons.error_outline, color: Color(0xFFDC2626), size: 36),
            const SizedBox(height: 12),
            Text(
              _tr(
                'Không tải được danh sách văn bản cho tính năng tóm tắt.',
                'Unable to load the summary document list.',
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              error.toString(),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFFB91C1C)),
            ),
          ],
        ),
      ),
      data: (discovery) {
        final isWideGrid = MediaQuery.sizeOf(context).width >= 1320;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Wrap(
                spacing: 18,
                runSpacing: 10,
                children: [
                  Text(
                    _tr(
                      'Tìm thấy ${discovery.totalCount} văn bản phù hợp',
                      'Found ${discovery.totalCount} matching documents',
                    ),
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  Text(
                    _tr(
                      'Phạm vi: ${discovery.scope}',
                      'Scope: ${discovery.scope}',
                    ),
                    style: const TextStyle(color: Color(0xFF475569)),
                  ),
                  if (params.tag.trim().isNotEmpty)
                    Text(
                      '#${params.tag.trim()}',
                      style: const TextStyle(color: Color(0xFF2563EB)),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (discovery.items.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.search_off_outlined,
                      size: 40,
                      color: Color(0xFF94A3B8),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _tr(
                        'Không có văn bản nào khớp bộ lọc hiện tại.',
                        'No documents match the current filters.',
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              )
            else if (isWideGrid)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: discovery.items.length,
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 1.34,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                ),
                itemBuilder: (context, index) {
                  return buildDocumentCard(discovery.items[index]);
                },
              )
            else
              Column(
                children: [
                  for (final document in discovery.items) ...[
                    buildDocumentCard(document),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            if (discovery.hasMore) ...[
              const SizedBox(height: 8),
              Center(
                child: FilledButton.tonalIcon(
                  onPressed: onLoadMore,
                  icon: const Icon(Icons.expand_more),
                  label: Text(_tr('Tải thêm', 'Load more')),
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}
