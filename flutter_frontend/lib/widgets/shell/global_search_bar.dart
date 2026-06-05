import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/debouncer.dart';
import '../../l10n/app_strings.dart';
import '../../models/global_search_result.dart';
import '../../providers/global_search_provider.dart';

class GlobalSearchBar extends ConsumerStatefulWidget {
  const GlobalSearchBar({super.key});

  @override
  ConsumerState<GlobalSearchBar> createState() => _GlobalSearchBarState();
}

class _GlobalSearchBarState extends ConsumerState<GlobalSearchBar> {
  static const _debounceDelay = Duration(milliseconds: 350);
  static const _minQueryLength = 2;

  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final LayerLink _layerLink = LayerLink();
  final Debouncer _debouncer = Debouncer();

  OverlayEntry? _overlayEntry;
  String _draftQuery = '';
  String _submittedQuery = '';
  int _highlightedIndex = 0;

  bool get _isCompactMode => MediaQuery.sizeOf(context).width < 600;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(_handleFocusChange);
    HardwareKeyboard.instance.addHandler(_handleGlobalShortcut);
  }

  @override
  void dispose() {
    HardwareKeyboard.instance.removeHandler(_handleGlobalShortcut);
    _hideOverlay();
    _debouncer.cancel();
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  bool _handleGlobalShortcut(KeyEvent event) {
    if (event is! KeyDownEvent || !mounted) {
      return false;
    }
    final keyboard = HardwareKeyboard.instance;
    final wantsSearch = event.logicalKey == LogicalKeyboardKey.keyK &&
        (keyboard.isControlPressed || keyboard.isMetaPressed);
    if (wantsSearch) {
      if (_isCompactMode) {
        _openMobileSearch();
      } else {
        _focusNode.requestFocus();
        _ensureOverlayVisible();
      }
      return true;
    }
    if (event.logicalKey == LogicalKeyboardKey.escape) {
      if (_overlayEntry != null) {
        _focusNode.unfocus();
        _hideOverlay();
        return true;
      }
    }
    return false;
  }

  void _handleFocusChange() {
    if (_focusNode.hasFocus && _draftQuery.length >= _minQueryLength) {
      _ensureOverlayVisible();
      return;
    }
    if (!_focusNode.hasFocus) {
      // Khi nguoi dung bam vao mot ket qua, text field mat focus TRUOC khi
      // InkWell.onTap kip chay. Neu an overlay ngay thi widget bi go khoi cay
      // va cu click bi mat -> "khong click duoc ket qua". Tre viec an overlay
      // mot nhip de onTap chay xong (selection se tu an overlay ngay sau do).
      Future.delayed(const Duration(milliseconds: 200), () {
        if (mounted && !_focusNode.hasFocus) {
          _hideOverlay();
        }
      });
    }
  }

  void _onChanged(String value) {
    _draftQuery = value.trim();
    if (_draftQuery.length < _minQueryLength) {
      _submittedQuery = '';
      _highlightedIndex = 0;
      _debouncer.cancel();
      _hideOverlay();
      setState(() {});
      return;
    }

    _ensureOverlayVisible();
    _debouncer.run(_debounceDelay, () {
      if (!mounted) {
        return;
      }
      setState(() {
        _submittedQuery = _draftQuery;
        _highlightedIndex = 0;
      });
      _markOverlayNeedsBuild();
    });
    setState(() {});
    _markOverlayNeedsBuild();
  }

  void _ensureOverlayVisible() {
    if (_overlayEntry != null || _isCompactMode) {
      _markOverlayNeedsBuild();
      return;
    }
    _overlayEntry = OverlayEntry(
      builder: (context) {
        final width = math.min(540.0, MediaQuery.sizeOf(context).width - 32);
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () {
                  _focusNode.unfocus();
                  _hideOverlay();
                },
              ),
            ),
            Positioned.fill(
              child: CompositedTransformFollower(
                link: _layerLink,
                showWhenUnlinked: false,
                offset: const Offset(0, 52),
                child: Align(
                  alignment: Alignment.topLeft,
                  child: Material(
                    elevation: 14,
                    borderRadius: BorderRadius.circular(20),
                    clipBehavior: Clip.antiAlias,
                    child: SizedBox(
                      width: width,
                      child: Consumer(
                        builder: (context, ref, _) {
                          return _DropdownResultsView(
                            draftQuery: _draftQuery,
                            submittedQuery: _submittedQuery,
                            highlightedIndex: _highlightedIndex,
                            onHighlightChanged: _setHighlightedIndex,
                            onRetry: _retrySearch,
                            onSelect: _handleSelection,
                            asyncResults: _submittedQuery.length >= _minQueryLength
                                ? ref.watch(globalSearchProvider(_submittedQuery))
                                : const AsyncData(null),
                          );
                        },
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
    Overlay.of(context, rootOverlay: true).insert(_overlayEntry!);
  }

  void _hideOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  void _markOverlayNeedsBuild() {
    _overlayEntry?.markNeedsBuild();
  }

  void _setHighlightedIndex(int nextIndex) {
    setState(() => _highlightedIndex = nextIndex);
    _markOverlayNeedsBuild();
  }

  void _retrySearch() {
    if (_submittedQuery.length < _minQueryLength) {
      return;
    }
    ref.invalidate(globalSearchProvider(_submittedQuery));
    _markOverlayNeedsBuild();
  }

  void _handleSelection(GlobalSearchItem item) {
    // Lay router + messenger truoc khi go overlay/unfocus de tranh dung context
    // da thay doi sau khi overlay bi go.
    final router = GoRouter.of(context);
    final messenger = ScaffoldMessenger.maybeOf(context);
    _hideOverlay();
    _focusNode.unfocus();
    if (item.deeplink.isEmpty) {
      messenger?.showSnackBar(
        const SnackBar(content: Text('Không có đường dẫn chi tiết cho kết quả này.')),
      );
      return;
    }
    try {
      router.go(item.deeplink);
    } catch (e) {
      messenger?.showSnackBar(
        SnackBar(content: Text('Không mở được kết quả: $e')),
      );
    }
  }

  Future<void> _openMobileSearch() async {
    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      useSafeArea: true,
      builder: (context) => const Dialog.fullscreen(
        child: _GlobalSearchFullscreenDialog(),
      ),
    );
  }

  KeyEventResult _handleFieldKey(
    FocusNode node,
    KeyEvent event,
    AsyncValue<GlobalSearchResults?> asyncResults,
  ) {
    if (event is! KeyDownEvent) {
      return KeyEventResult.ignored;
    }

    final results = asyncResults.asData?.value;
    final items = results?.flatten() ?? const <GlobalSearchItem>[];
    if (event.logicalKey == LogicalKeyboardKey.arrowDown && items.isNotEmpty) {
      final nextIndex = (_highlightedIndex + 1) % items.length;
      _setHighlightedIndex(nextIndex);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.arrowUp && items.isNotEmpty) {
      final nextIndex =
          (_highlightedIndex - 1 + items.length) % items.length;
      _setHighlightedIndex(nextIndex);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.enter && items.isNotEmpty) {
      final safeIndex = _highlightedIndex.clamp(0, items.length - 1);
      _handleSelection(items[safeIndex]);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.escape) {
      _focusNode.unfocus();
      _hideOverlay();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (_isCompactMode) {
      return IconButton(
        tooltip: strings.r4_globalSearchHint,
        icon: const Icon(Icons.search),
        onPressed: _openMobileSearch,
      );
    }

    final asyncResults = _submittedQuery.length >= _minQueryLength
        ? ref.watch(globalSearchProvider(_submittedQuery))
        : const AsyncData<GlobalSearchResults?>(null);
    final screenWidth = MediaQuery.sizeOf(context).width;
    final fieldWidth = math.min(500.0, math.max(260.0, screenWidth * 0.28));

    return CompositedTransformTarget(
      link: _layerLink,
      child: Focus(
        onKeyEvent: (node, event) => _handleFieldKey(node, event, asyncResults),
        child: SizedBox(
          width: fieldWidth,
          child: TextField(
            controller: _controller,
            focusNode: _focusNode,
            cursorColor: const Color(0xFF1D4ED8),
            style: const TextStyle(
              color: Color(0xFF0F172A),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
            decoration: InputDecoration(
              hintText: strings.r4_globalSearchHint,
              hintStyle: const TextStyle(
                color: Color(0xFF64748B),
                fontWeight: FontWeight.w500,
              ),
              prefixIcon: const Icon(Icons.search, color: Color(0xFF475569)),
              suffixIcon: Padding(
                padding: const EdgeInsets.only(right: 10),
                child: Center(
                  widthFactor: 1,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      'Ctrl+K',
                      style: TextStyle(
                        fontSize: 10.5,
                        color: Color(0xFF475569),
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
              isDense: true,
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(
                    color: Color(0xFF2563EB), width: 1.6),
              ),
            ),
            textInputAction: TextInputAction.search,
            onChanged: _onChanged,
            onTap: () {
              if (_draftQuery.length >= _minQueryLength) {
                _ensureOverlayVisible();
              }
            },
          ),
        ),
      ),
    );
  }
}

class _GlobalSearchFullscreenDialog extends ConsumerStatefulWidget {
  const _GlobalSearchFullscreenDialog();

  @override
  ConsumerState<_GlobalSearchFullscreenDialog> createState() =>
      _GlobalSearchFullscreenDialogState();
}

class _GlobalSearchFullscreenDialogState
    extends ConsumerState<_GlobalSearchFullscreenDialog> {
  static const _debounceDelay = Duration(milliseconds: 350);
  static const _minQueryLength = 2;

  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final Debouncer _debouncer = Debouncer();

  String _draftQuery = '';
  String _submittedQuery = '';
  int _highlightedIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _focusNode.requestFocus();
      }
    });
  }

  @override
  void dispose() {
    _debouncer.cancel();
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    _draftQuery = value.trim();
    if (_draftQuery.length < _minQueryLength) {
      setState(() {
        _submittedQuery = '';
        _highlightedIndex = 0;
      });
      _debouncer.cancel();
      return;
    }

    _debouncer.run(_debounceDelay, () {
      if (!mounted) {
        return;
      }
      setState(() {
        _submittedQuery = _draftQuery;
        _highlightedIndex = 0;
      });
    });
    setState(() {});
  }

  void _setHighlightedIndex(int value) {
    setState(() => _highlightedIndex = value);
  }

  void _handleSelection(GlobalSearchItem item) {
    // Capture router truoc khi pop dialog: sau khi pop, context cua dialog bi
    // go khoi cay widget nen context.go() se khong dieu huong duoc.
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    if (item.deeplink.isNotEmpty) {
      router.go(item.deeplink);
    }
  }

  KeyEventResult _handleKeyEvent(
    FocusNode node,
    KeyEvent event,
    AsyncValue<GlobalSearchResults?> asyncResults,
  ) {
    if (event is! KeyDownEvent) {
      return KeyEventResult.ignored;
    }
    final items = asyncResults.asData?.value?.flatten() ?? const [];
    if (event.logicalKey == LogicalKeyboardKey.arrowDown && items.isNotEmpty) {
      _setHighlightedIndex((_highlightedIndex + 1) % items.length);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.arrowUp && items.isNotEmpty) {
      _setHighlightedIndex((_highlightedIndex - 1 + items.length) % items.length);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.enter && items.isNotEmpty) {
      final safeIndex = _highlightedIndex.clamp(0, items.length - 1);
      _handleSelection(items[safeIndex]);
      return KeyEventResult.handled;
    }
    if (event.logicalKey == LogicalKeyboardKey.escape) {
      Navigator.of(context).pop();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final asyncResults = _submittedQuery.length >= _minQueryLength
        ? ref.watch(globalSearchProvider(_submittedQuery))
        : const AsyncData<GlobalSearchResults?>(null);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(strings.r4_globalSearchTitle),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Focus(
                onKeyEvent: (node, event) =>
                    _handleKeyEvent(node, event, asyncResults),
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  decoration: InputDecoration(
                    hintText: strings.r4_globalSearchHint,
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                    ),
                  ),
                  textInputAction: TextInputAction.search,
                  onChanged: _onChanged,
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: _DropdownResultsView(
                  draftQuery: _draftQuery,
                  submittedQuery: _submittedQuery,
                  highlightedIndex: _highlightedIndex,
                  onHighlightChanged: _setHighlightedIndex,
                  onRetry: () {
                    if (_submittedQuery.length >= _minQueryLength) {
                      ref.invalidate(globalSearchProvider(_submittedQuery));
                    }
                  },
                  onSelect: _handleSelection,
                  asyncResults: asyncResults,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DropdownResultsView extends StatelessWidget {
  final String draftQuery;
  final String submittedQuery;
  final int highlightedIndex;
  final void Function(int value) onHighlightChanged;
  final VoidCallback onRetry;
  final void Function(GlobalSearchItem item) onSelect;
  final AsyncValue<GlobalSearchResults?> asyncResults;

  const _DropdownResultsView({
    required this.draftQuery,
    required this.submittedQuery,
    required this.highlightedIndex,
    required this.onHighlightChanged,
    required this.onRetry,
    required this.onSelect,
    required this.asyncResults,
  });

  String _sectionLabel(AppStrings strings, SearchResultType type) {
    return switch (type) {
      SearchResultType.template => strings.r4_globalSearchTemplates,
      SearchResultType.document => strings.r4_globalSearchDocuments,
      SearchResultType.prompt => strings.r4_globalSearchPrompts,
      SearchResultType.summary => strings.r4_globalSearchSummaries,
      SearchResultType.conversation => strings.r4_globalSearchConversations,
    };
  }

  IconData _iconForType(SearchResultType type) {
    return switch (type) {
      SearchResultType.template => Icons.description_outlined,
      SearchResultType.document => Icons.article_outlined,
      SearchResultType.prompt => Icons.bolt_outlined,
      SearchResultType.summary => Icons.summarize_outlined,
      SearchResultType.conversation => Icons.forum_outlined,
    };
  }

  String _formatDate(DateTime value) {
    if (value.millisecondsSinceEpoch == 0) {
      return '';
    }
    return DateFormat('dd/MM/yyyy HH:mm').format(value.toLocal());
  }

  TextSpan _highlightText(
    BuildContext context,
    String source,
    String query, {
    FontWeight matchedWeight = FontWeight.w800,
  }) {
    final style = DefaultTextStyle.of(context).style;
    final trimmedQuery = query.trim();
    if (trimmedQuery.isEmpty) {
      return TextSpan(text: source, style: style);
    }
    final lowerSource = source.toLowerCase();
    final lowerQuery = trimmedQuery.toLowerCase();
    final matchIndex = lowerSource.indexOf(lowerQuery);
    if (matchIndex < 0) {
      return TextSpan(text: source, style: style);
    }
    final endIndex = matchIndex + trimmedQuery.length;
    return TextSpan(
      style: style,
      children: [
        TextSpan(text: source.substring(0, matchIndex)),
        TextSpan(
          text: source.substring(matchIndex, endIndex),
          style: style.copyWith(
            fontWeight: matchedWeight,
            backgroundColor: const Color(0xFFFFF3B0),
          ),
        ),
        TextSpan(text: source.substring(endIndex)),
      ],
    );
  }

  Widget _buildSkeleton() {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: List.generate(
        3,
        (index) => Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              _SkeletonLine(widthFactor: 0.46, height: 14),
              SizedBox(height: 10),
              _SkeletonLine(widthFactor: 0.88, height: 12),
              SizedBox(height: 8),
              _SkeletonLine(widthFactor: 0.54, height: 12),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (draftQuery.length < 2) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            strings.r4_globalSearchMinChars,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: const Color(0xFF64748B),
                ),
          ),
        ),
      );
    }

    if (submittedQuery != draftQuery) {
      return _buildSkeleton();
    }

    return asyncResults.when(
      loading: _buildSkeleton,
      error: (error, _) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  error.toString(),
                  style: const TextStyle(color: Colors.red),
                ),
              ),
              TextButton(
                onPressed: onRetry,
                child: Text(strings.r4_globalSearchRetry),
              ),
            ],
          ),
        );
      },
      data: (results) {
        if (results == null || results.isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Text(
                strings.r4_globalSearchEmpty(draftQuery),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFF64748B),
                    ),
              ),
            ),
          );
        }

        final items = results.flatten();
        final safeHighlight = highlightedIndex.clamp(0, items.length - 1);
        if (safeHighlight != highlightedIndex) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            onHighlightChanged(safeHighlight);
          });
        }

        var flatIndex = 0;
        return ListView(
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: [
            for (final section in results.sections)
              if (section.items.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
                  child: Text(
                    _sectionLabel(strings, section.type),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: const Color(0xFF334155),
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                for (final item in section.items)
                  Builder(
                    builder: (context) {
                      final currentIndex = flatIndex++;
                      final isHighlighted = currentIndex == safeHighlight;
                      return InkWell(
                        onTap: () => onSelect(item),
                        onHover: (hovering) {
                          if (hovering) {
                            onHighlightChanged(currentIndex);
                          }
                        },
                        child: Container(
                          margin: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: isHighlighted
                                ? const Color(0xFFEFF6FF)
                                : Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: isHighlighted
                                  ? const Color(0xFF93C5FD)
                                  : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                _iconForType(item.type),
                                color: const Color(0xFF2563EB),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    RichText(
                                      text: _highlightText(
                                        context,
                                        item.title,
                                        draftQuery,
                                      ),
                                    ),
                                    if (item.snippet.trim().isNotEmpty) ...[
                                      const SizedBox(height: 6),
                                      RichText(
                                        text: TextSpan(
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodySmall
                                              ?.copyWith(
                                                color: const Color(0xFF64748B),
                                                height: 1.45,
                                              ),
                                          children: [
                                            _highlightText(
                                              context,
                                              item.snippet,
                                              draftQuery,
                                              matchedWeight: FontWeight.w700,
                                            ),
                                          ],
                                        ),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                              const SizedBox(width: 10),
                              Text(
                                _formatDate(item.updatedAt),
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(
                                      color: const Color(0xFF94A3B8),
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
              ],
          ],
        );
      },
    );
  }
}

class _SkeletonLine extends StatelessWidget {
  final double widthFactor;
  final double height;

  const _SkeletonLine({
    required this.widthFactor,
    required this.height,
  });

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          color: const Color(0xFFE2E8F0),
          borderRadius: BorderRadius.circular(999),
        ),
      ),
    );
  }
}
