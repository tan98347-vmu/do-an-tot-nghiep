import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_locale.dart';
import '../../screens/help/help_content.dart';

class HelpNavigationPanel extends StatelessWidget {
  final List<HelpSectionData> sections;
  final String activeSectionId;
  final bool isEnglish;
  final bool collapsed;
  final String searchQuery;
  final TextEditingController searchController;
  final VoidCallback onToggleCollapsed;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<String> onSelected;

  const HelpNavigationPanel({
    super.key,
    required this.sections,
    required this.activeSectionId,
    required this.isEnglish,
    required this.collapsed,
    required this.searchQuery,
    required this.searchController,
    required this.onToggleCollapsed,
    required this.onSearchChanged,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.white,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: EdgeInsets.fromLTRB(
                collapsed ? 12 : 20,
                20,
                collapsed ? 12 : 14,
                collapsed ? 12 : 18,
              ),
              child: collapsed
                  ? Column(
                      children: [
                        _HelpLogo(),
                        const SizedBox(height: 8),
                        IconButton(
                          tooltip: isEnglish
                              ? 'Expand help navigation'
                              : 'Mở rộng thanh trợ giúp',
                          onPressed: onToggleCollapsed,
                          icon: const Icon(Icons.chevron_right),
                        ),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const _HelpLogo(),
                            const SizedBox(width: 11),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    isEnglish
                                        ? 'Help center'
                                        : 'Trung tâm trợ giúp',
                                    style: const TextStyle(
                                      color: Color(0xFF0F172A),
                                      fontSize: 17,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  Text(
                                    isEnglish
                                        ? 'Guides for your account'
                                        : 'Hướng dẫn dành cho bạn',
                                    style: const TextStyle(
                                      color: Color(0xFF64748B),
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              tooltip: isEnglish
                                  ? 'Collapse help navigation'
                                  : 'Thu gọn thanh trợ giúp',
                              onPressed: onToggleCollapsed,
                              icon: const Icon(Icons.chevron_left),
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        TextField(
                          controller: searchController,
                          onChanged: onSearchChanged,
                          decoration: InputDecoration(
                            hintText: isEnglish
                                ? 'Find a guide...'
                                : 'Tìm hướng dẫn...',
                            prefixIcon: const Icon(Icons.search, size: 20),
                            suffixIcon: searchQuery.isNotEmpty
                                ? IconButton(
                                    tooltip: isEnglish
                                        ? 'Clear search'
                                        : 'Xóa tìm kiếm',
                                    onPressed: () {
                                      searchController.clear();
                                      onSearchChanged('');
                                    },
                                    icon: const Icon(Icons.close, size: 18),
                                  )
                                : null,
                            isDense: true,
                            filled: true,
                            fillColor: const Color(0xFFF8FAFC),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(
                                color: Color(0xFFE2E8F0),
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(
                                color: Color(0xFFE2E8F0),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
            const Divider(height: 1),
            if (!collapsed)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 9),
                child: Text(
                  isEnglish ? 'AVAILABLE GUIDES' : 'HƯỚNG DẪN CÓ THỂ SỬ DỤNG',
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            Expanded(
              child: sections.isEmpty
                  ? _EmptySearchResult(isEnglish: isEnglish)
                  : ListView.builder(
                      padding: EdgeInsets.fromLTRB(
                        collapsed ? 8 : 10,
                        collapsed ? 10 : 0,
                        collapsed ? 8 : 10,
                        16,
                      ),
                      itemCount: sections.length,
                      itemBuilder: (context, index) {
                        final section = sections[index];
                        return _GuideNavigationItem(
                          section: section,
                          active: section.id == activeSectionId,
                          isEnglish: isEnglish,
                          collapsed: collapsed,
                          onTap: () => onSelected(section.id),
                        );
                      },
                    ),
            ),
            const Divider(height: 1),
            Padding(
              padding: EdgeInsets.fromLTRB(
                collapsed ? 12 : 16,
                12,
                collapsed ? 12 : 16,
                16,
              ),
              child: collapsed
                  ? _LanguageSelector(isEnglish: isEnglish, compact: true)
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _LanguageSelector(isEnglish: isEnglish),
                        const SizedBox(height: 10),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.verified_user_outlined,
                              color: Color(0xFF1D4ED8),
                              size: 16,
                            ),
                            const SizedBox(width: 7),
                            Expanded(
                              child: Text(
                                isEnglish
                                    ? 'Only features available to your account are shown.'
                                    : 'Chỉ hiển thị chức năng tài khoản của bạn được phép sử dụng.',
                                style: const TextStyle(
                                  color: Color(0xFF64748B),
                                  height: 1.35,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HelpLogo extends StatelessWidget {
  const _HelpLogo();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: const Color(0xFF1D4ED8),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Icon(
        Icons.menu_book_outlined,
        color: Colors.white,
        size: 21,
      ),
    );
  }
}

class HelpMobileNavigation extends StatelessWidget {
  final List<HelpSectionData> sections;
  final String activeSectionId;
  final bool isEnglish;
  final ValueChanged<String> onSelected;

  const HelpMobileNavigation({
    super.key,
    required this.sections,
    required this.activeSectionId,
    required this.isEnglish,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.white,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: Row(
            children: [
              const Icon(
                Icons.menu_book_outlined,
                color: Color(0xFF1D4ED8),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<String>(
                  key: ValueKey(activeSectionId),
                  initialValue: activeSectionId,
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: isEnglish ? 'Guide' : 'Mục hướng dẫn',
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    for (final section in sections)
                      DropdownMenuItem(
                        value: section.id,
                        child: Text(
                          section.title.resolve(isEnglish),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) onSelected(value);
                  },
                ),
              ),
              const SizedBox(width: 10),
              _LanguageSelector(isEnglish: isEnglish, compact: true),
            ],
          ),
        ),
      ),
    );
  }
}

class _GuideNavigationItem extends StatelessWidget {
  final HelpSectionData section;
  final bool active;
  final bool isEnglish;
  final bool collapsed;
  final VoidCallback onTap;

  const _GuideNavigationItem({
    required this.section,
    required this.active,
    required this.isEnglish,
    required this.collapsed,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final title = section.title.resolve(isEnglish);
    final item = Material(
      color: active ? const Color(0xFFEFF6FF) : Colors.transparent,
      borderRadius: BorderRadius.circular(7),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(7),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: collapsed ? 8 : 10,
            vertical: 10,
          ),
          child: Row(
            mainAxisAlignment: collapsed
                ? MainAxisAlignment.center
                : MainAxisAlignment.start,
            children: [
              Container(
                width: 31,
                height: 31,
                decoration: BoxDecoration(
                  color: active
                      ? const Color(0xFFDBEAFE)
                      : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Icon(
                  section.icon,
                  size: 17,
                  color: active
                      ? const Color(0xFF1D4ED8)
                      : const Color(0xFF64748B),
                ),
              ),
              if (!collapsed) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: active
                          ? const Color(0xFF1E3A8A)
                          : const Color(0xFF334155),
                      fontSize: 13,
                      height: 1.25,
                      fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                ),
                if (active)
                  const Icon(
                    Icons.chevron_right,
                    size: 18,
                    color: Color(0xFF2563EB),
                  ),
              ],
            ],
          ),
        ),
      ),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 3),
      child: collapsed
          ? Tooltip(message: title, child: item)
          : item,
    );
  }
}

class _LanguageSelector extends ConsumerWidget {
  final bool isEnglish;
  final bool compact;

  const _LanguageSelector({
    required this.isEnglish,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (compact) {
      return IconButton.outlined(
        tooltip: isEnglish ? 'Tiếng Việt' : 'English',
        onPressed: () {
          ref
              .read(appLocaleProvider.notifier)
              .setLanguageCode(isEnglish ? 'vi' : 'en');
        },
        icon: Text(
          isEnglish ? 'VI' : 'EN',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
        ),
      );
    }

    return SegmentedButton<String>(
      segments: const [
        ButtonSegment(value: 'vi', label: Text('Tiếng Việt')),
        ButtonSegment(value: 'en', label: Text('English')),
      ],
      selected: {isEnglish ? 'en' : 'vi'},
      showSelectedIcon: false,
      onSelectionChanged: (selection) {
        ref
            .read(appLocaleProvider.notifier)
            .setLanguageCode(selection.first);
      },
    );
  }
}

class _EmptySearchResult extends StatelessWidget {
  final bool isEnglish;

  const _EmptySearchResult({required this.isEnglish});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.search_off, size: 34, color: Color(0xFF94A3B8)),
          const SizedBox(height: 10),
          Text(
            isEnglish ? 'No matching guide found.' : 'Không tìm thấy hướng dẫn phù hợp.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF64748B)),
          ),
        ],
      ),
    );
  }
}
