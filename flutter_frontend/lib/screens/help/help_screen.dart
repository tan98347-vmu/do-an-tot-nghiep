// === MÀN HÌNH TRỢ GIÚP ===
// Hiển thị nội dung hướng dẫn theo từng MỤC (section), hỗ trợ deep-link /help?section=...
// - _selectSection(): đổi mục đang xem.
// - _correctUnauthorizedDeepLink(): nếu user không có quyền xem mục (theo currentUserProvider + signingSummaryProvider) thì tự chuyển về mục hợp lệ.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/signing_summary_provider.dart';
import '../../widgets/help/help_article.dart';
import '../../widgets/help/help_navigation_panel.dart';
import 'help_access.dart';
import 'help_content.dart';

class HelpScreen extends ConsumerStatefulWidget {
  final String? initialSection;

  // Widget màn TRỢ GIÚP; nhận initialSection (mục mở sẵn theo deep-link).
  const HelpScreen({super.key, this.initialSection});

  @override
  ConsumerState<HelpScreen> createState() => _HelpScreenState();
}

class _HelpScreenState extends ConsumerState<HelpScreen> {
  final _scrollController = ScrollController();
  final _searchController = TextEditingController();
  late String _requestedSectionId;
  String _searchQuery = '';
  String? _correctedSectionId;
  bool? _navigationCollapsedOverride;

  // Mở màn: chọn mục ban đầu và kiểm tra quyền xem (deep-link).
  @override
  void initState() {
    super.initState();
    _requestedSectionId = widget.initialSection ?? helpSections.first.id;
  }

  // Khi đổi initialSection (đổi deep-link /help?section=...) -> chọn lại mục tương ứng.
  @override
  void didUpdateWidget(covariant HelpScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialSection != widget.initialSection) {
      _requestedSectionId = widget.initialSection ?? helpSections.first.id;
    }
  }

  // Rời màn: dọn controller cuộn.
  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  // Chọn mục help đang xem + cập nhật URL (/help?section=...).
  void _selectSection(String sectionId) {
    if (_requestedSectionId != sectionId) {
      setState(() => _requestedSectionId = sectionId);
    }
    _scrollController.animateTo(
      0,
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
    );
    context.go('/help?section=$sectionId');
  }

  // Nếu user không có quyền xem mục yêu cầu -> tự chuyển về mục hợp lệ.
  void _correctUnauthorizedDeepLink(String sectionId) {
    if (_correctedSectionId == sectionId) return;
    _correctedSectionId = sectionId;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.go('/help?section=$sectionId');
    });
  }

  // Dựng màn: menu các mục bên trái + nội dung mục đang chọn bên phải.
  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isEnglish = strings.isEnglish;
    final user = ref.watch(currentUserProvider);
    final signingSummary = ref.watch(signingSummaryProvider).asData?.value;
    final accessPolicy = HelpAccessPolicy(
      user: user,
      signingSummary: signingSummary,
    );
    final visibleSections = helpSections
        .where((section) => accessPolicy.allows(section.access))
        .toList(growable: false);

    if (visibleSections.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    final activeSection = visibleSections.firstWhere(
      (section) => section.id == _requestedSectionId,
      orElse: () => visibleSections.first,
    );
    if (activeSection.id != _requestedSectionId) {
      _correctUnauthorizedDeepLink(activeSection.id);
    } else {
      _correctedSectionId = null;
    }

    final normalizedQuery = _searchQuery.trim().toLowerCase();
    final navigationSections = normalizedQuery.isEmpty
        ? visibleSections
        : visibleSections.where((section) {
            final searchableText = [
              section.title.vi,
              section.title.en,
              section.summary.vi,
              section.summary.en,
            ].join(' ').toLowerCase();
            return searchableText.contains(normalizedQuery);
          }).toList(growable: false);
    final activeIndex = visibleSections.indexOf(activeSection);
    final visibleSteps = activeSection.steps
        .where((step) => accessPolicy.allows(step.access))
        .toList(growable: false);
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isWide = screenWidth >= 1080;
    final navigationCollapsed =
        _navigationCollapsedOverride ?? screenWidth < 1440;

    final article = HelpArticle(
      section: activeSection,
      steps: visibleSteps,
      isEnglish: isEnglish,
      currentIndex: activeIndex,
      sectionCount: visibleSections.length,
      scrollController: _scrollController,
      onOpenFeature: () => context.go(activeSection.route),
      onPrevious: activeIndex > 0
          ? () => _selectSection(visibleSections[activeIndex - 1].id)
          : null,
      onNext: activeIndex < visibleSections.length - 1
          ? () => _selectSection(visibleSections[activeIndex + 1].id)
          : null,
    );

    return ColoredBox(
      color: const Color(0xFFF3F6F8),
      child: isWide
          ? Row(
              children: [
                SizedBox(
                  width: navigationCollapsed ? 76 : 272,
                  child: HelpNavigationPanel(
                    sections: navigationCollapsed
                        ? visibleSections
                        : navigationSections,
                    activeSectionId: activeSection.id,
                    isEnglish: isEnglish,
                    collapsed: navigationCollapsed,
                    searchQuery: _searchQuery,
                    searchController: _searchController,
                    onToggleCollapsed: () {
                      final nextValue = !navigationCollapsed;
                      if (nextValue) {
                        _searchController.clear();
                      }
                      setState(() {
                        _navigationCollapsedOverride = nextValue;
                        if (nextValue) _searchQuery = '';
                      });
                    },
                    onSearchChanged: (value) {
                      setState(() => _searchQuery = value);
                    },
                    onSelected: _selectSection,
                  ),
                ),
                const VerticalDivider(width: 1, thickness: 1),
                Expanded(child: article),
              ],
            )
          : Column(
              children: [
                HelpMobileNavigation(
                  sections: visibleSections,
                  activeSectionId: activeSection.id,
                  isEnglish: isEnglish,
                  onSelected: _selectSection,
                ),
                const Divider(height: 1),
                Expanded(child: article),
              ],
            ),
    );
  }
}
