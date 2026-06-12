import 'package:flutter/material.dart';

import '../../screens/help/help_content.dart';
import 'help_video_player.dart';

class HelpArticle extends StatelessWidget {
  final HelpSectionData section;
  final List<HelpStep> steps;
  final bool isEnglish;
  final int currentIndex;
  final int sectionCount;
  final ScrollController scrollController;
  final VoidCallback onOpenFeature;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;

  const HelpArticle({
    super.key,
    required this.section,
    required this.steps,
    required this.isEnglish,
    required this.currentIndex,
    required this.sectionCount,
    required this.scrollController,
    required this.onOpenFeature,
    required this.onPrevious,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: SingleChildScrollView(
        controller: scrollController,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _ArticleToolbar(
              sectionTitle: section.title.resolve(isEnglish),
              isEnglish: isEnglish,
            ),
            _ArticleHeader(
              section: section,
              stepCount: steps.length,
              currentIndex: currentIndex,
              sectionCount: sectionCount,
              isEnglish: isEnglish,
              onOpenFeature: onOpenFeature,
            ),
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 900),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 30, 24, 64),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (section.videoAsset != null)
                        _InstructionVideo(
                          section: section,
                          isEnglish: isEnglish,
                        ),
                      if (section.prerequisites.isNotEmpty) ...[
                        const SizedBox(height: 34),
                        _SectionTitle(
                          icon: Icons.fact_check_outlined,
                          eyebrow: isEnglish ? 'PREPARATION' : 'CHUẨN BỊ',
                          title:
                              isEnglish ? 'Before you start' : 'Trước khi bắt đầu',
                        ),
                        const SizedBox(height: 14),
                        _PrerequisiteList(
                          items: section.prerequisites,
                          isEnglish: isEnglish,
                        ),
                      ],
                      const SizedBox(height: 38),
                      _SectionTitle(
                        icon: Icons.route_outlined,
                        eyebrow: isEnglish ? 'WORKFLOW' : 'QUY TRÌNH',
                        title: isEnglish
                            ? 'Follow these steps'
                            : 'Thực hiện theo từng bước',
                      ),
                      const SizedBox(height: 20),
                      for (var index = 0; index < steps.length; index++)
                        _TimelineStep(
                          number: index + 1,
                          step: steps[index],
                          isEnglish: isEnglish,
                          isLast: index == steps.length - 1,
                        ),
                      if (section.tips.isNotEmpty) ...[
                        const SizedBox(height: 28),
                        _AdvicePanel(
                          icon: Icons.lightbulb_outline,
                          title: isEnglish ? 'Practical tips' : 'Mẹo sử dụng',
                          items: section.tips,
                          isEnglish: isEnglish,
                          background: const Color(0xFFEFF6FF),
                          border: const Color(0xFFBFDBFE),
                          foreground: const Color(0xFF1E3A8A),
                        ),
                      ],
                      if (section.warning != null) ...[
                        const SizedBox(height: 16),
                        _AdvicePanel(
                          icon: Icons.warning_amber_outlined,
                          title: isEnglish ? 'Important note' : 'Lưu ý quan trọng',
                          items: [section.warning!],
                          isEnglish: isEnglish,
                          background: const Color(0xFFFFFBEB),
                          border: const Color(0xFFFDE68A),
                          foreground: const Color(0xFF92400E),
                        ),
                      ],
                      const SizedBox(height: 42),
                      const Divider(),
                      const SizedBox(height: 18),
                      _ArticlePager(
                        isEnglish: isEnglish,
                        onPrevious: onPrevious,
                        onNext: onNext,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ArticleToolbar extends StatelessWidget {
  final String sectionTitle;
  final bool isEnglish;

  const _ArticleToolbar({
    required this.sectionTitle,
    required this.isEnglish,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 52,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      alignment: Alignment.centerLeft,
      color: Colors.white,
      child: Row(
        children: [
          const Icon(
            Icons.help_outline,
            size: 18,
            color: Color(0xFF64748B),
          ),
          const SizedBox(width: 9),
          Text(
            isEnglish ? 'User guide' : 'Hướng dẫn sử dụng',
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontWeight: FontWeight.w600,
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 9),
            child: Icon(
              Icons.chevron_right,
              size: 17,
              color: Color(0xFF94A3B8),
            ),
          ),
          Expanded(
            child: Text(
              sectionTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFF0F172A),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ArticleHeader extends StatelessWidget {
  final HelpSectionData section;
  final int stepCount;
  final int currentIndex;
  final int sectionCount;
  final bool isEnglish;
  final VoidCallback onOpenFeature;

  const _ArticleHeader({
    required this.section,
    required this.stepCount,
    required this.currentIndex,
    required this.sectionCount,
    required this.isEnglish,
    required this.onOpenFeature,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFEFF6FF),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 34),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final description = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isEnglish
                        ? 'GUIDE ${currentIndex + 1} OF $sectionCount'
                        : 'HƯỚNG DẪN ${currentIndex + 1} / $sectionCount',
                    style: const TextStyle(
                      color: Color(0xFF1D4ED8),
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 9),
                  Text(
                    section.title.resolve(isEnglish),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          color: const Color(0xFF0F172A),
                          fontWeight: FontWeight.w800,
                          height: 1.18,
                        ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    section.summary.resolve(isEnglish),
                    style: const TextStyle(
                      color: Color(0xFF475569),
                      fontSize: 16,
                      height: 1.55,
                    ),
                  ),
                  const SizedBox(height: 17),
                  Wrap(
                    spacing: 16,
                    runSpacing: 8,
                    children: [
                      _HeaderMeta(
                        icon: Icons.format_list_numbered,
                        label: isEnglish ? '$stepCount steps' : '$stepCount bước',
                      ),
                      if (section.videoAsset != null)
                        _HeaderMeta(
                          icon: Icons.play_circle_outline,
                          label: isEnglish
                              ? 'Includes video'
                              : 'Có video hướng dẫn',
                        ),
                      _HeaderMeta(
                        icon: Icons.verified_user_outlined,
                        label: isEnglish
                            ? 'Based on account access'
                            : 'Theo quyền tài khoản',
                      ),
                    ],
                  ),
                ],
              );
              final icon = Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: const Color(0xFF1D4ED8),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(section.icon, size: 34, color: Colors.white),
              );
              final button = FilledButton.icon(
                onPressed: onOpenFeature,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF1D4ED8),
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                ),
                icon: const Icon(Icons.open_in_new, size: 18),
                label: Text(
                  isEnglish ? 'Open feature' : 'Mở chức năng',
                ),
              );

              if (constraints.maxWidth < 680) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    icon,
                    const SizedBox(height: 18),
                    description,
                    const SizedBox(height: 22),
                    button,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  icon,
                  const SizedBox(width: 22),
                  Expanded(child: description),
                  const SizedBox(width: 24),
                  button,
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _HeaderMeta extends StatelessWidget {
  final IconData icon;
  final String label;

  const _HeaderMeta({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: const Color(0xFF1D4ED8)),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF475569),
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _InstructionVideo extends StatelessWidget {
  final HelpSectionData section;
  final bool isEnglish;

  const _InstructionVideo({
    required this.section,
    required this.isEnglish,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionTitle(
          icon: Icons.ondemand_video_outlined,
          eyebrow: isEnglish ? 'WATCH FIRST' : 'XEM TRƯỚC',
          title: isEnglish ? 'Instruction video' : 'Video hướng dẫn',
        ),
        const SizedBox(height: 14),
        DecoratedBox(
          decoration: BoxDecoration(
            color: const Color(0xFF111827),
            border: Border.all(color: const Color(0xFFCBD5E1)),
            borderRadius: BorderRadius.circular(8),
            boxShadow: const [
              BoxShadow(
                color: Color(0x1F0F172A),
                blurRadius: 18,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(7),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: HelpVideoPlayer(
                viewKey: 'help-video-${section.id}',
                assetPath: section.videoAsset!,
                unavailableMessage: isEnglish
                    ? 'This browser cannot play the instruction video.'
                    : 'Trình duyệt không phát được video hướng dẫn này.',
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          isEnglish
              ? 'Watch the full video, then follow the detailed steps below.'
              : 'Xem hết video, sau đó thực hiện theo các bước chi tiết bên dưới.',
          style: const TextStyle(
            color: Color(0xFF64748B),
            fontSize: 13,
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String eyebrow;
  final String title;

  const _SectionTitle({
    required this.icon,
    required this.eyebrow,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: const Color(0xFFDBEAFE),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: const Color(0xFF1D4ED8), size: 20),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                eyebrow,
                style: const TextStyle(
                  color: Color(0xFF1D4ED8),
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                title,
                style: const TextStyle(
                  color: Color(0xFF0F172A),
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _PrerequisiteList extends StatelessWidget {
  final List<HelpText> items;
  final bool isEnglish;

  const _PrerequisiteList({
    required this.items,
    required this.isEnglish,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          for (final item in items)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.check_circle,
                    color: Color(0xFF1D4ED8),
                    size: 19,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      item.resolve(isEnglish),
                      style: const TextStyle(
                        color: Color(0xFF334155),
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _TimelineStep extends StatelessWidget {
  final int number;
  final HelpStep step;
  final bool isEnglish;
  final bool isLast;

  const _TimelineStep({
    required this.number,
    required this.step,
    required this.isEnglish,
    required this.isLast,
  });

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 38,
            child: Column(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: number == 1
                        ? const Color(0xFF1D4ED8)
                        : const Color(0xFFDBEAFE),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '$number',
                    style: TextStyle(
                      color: number == 1
                          ? Colors.white
                          : const Color(0xFF1D4ED8),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      margin: const EdgeInsets.symmetric(vertical: 7),
                      color: const Color(0xFFBFDBFE),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    step.title.resolve(isEnglish),
                    style: const TextStyle(
                      color: Color(0xFF0F172A),
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    step.description.resolve(isEnglish),
                    style: const TextStyle(
                      color: Color(0xFF475569),
                      fontSize: 15,
                      height: 1.62,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AdvicePanel extends StatelessWidget {
  final IconData icon;
  final String title;
  final List<HelpText> items;
  final bool isEnglish;
  final Color background;
  final Color border;
  final Color foreground;

  const _AdvicePanel({
    required this.icon,
    required this.title,
    required this.items,
    required this.isEnglish,
    required this.background,
    required this.border,
    required this.foreground,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: background,
        border: Border.all(color: border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: foreground),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: foreground,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                for (final item in items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: Text(
                      item.resolve(isEnglish),
                      style: TextStyle(color: foreground, height: 1.5),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ArticlePager extends StatelessWidget {
  final bool isEnglish;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;

  const _ArticlePager({
    required this.isEnglish,
    required this.onPrevious,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (onPrevious != null)
          OutlinedButton.icon(
            onPressed: onPrevious,
            icon: const Icon(Icons.arrow_back, size: 18),
            label: Text(isEnglish ? 'Previous guide' : 'Bài trước'),
          ),
        const Spacer(),
        if (onNext != null)
          FilledButton.icon(
            onPressed: onNext,
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF1D4ED8),
              foregroundColor: Colors.white,
            ),
            icon: const Icon(Icons.arrow_forward, size: 18),
            label: Text(isEnglish ? 'Next guide' : 'Bài tiếp theo'),
          ),
      ],
    );
  }
}
