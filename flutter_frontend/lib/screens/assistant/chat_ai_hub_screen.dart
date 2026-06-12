// === MÀN HÌNH CHỌN CHẾ ĐỘ CHATAI ===
// 3 thẻ (_ModeCard) dẫn tới: chat văn bản (/chat/text), chat giọng nói (/chat/voice), thư viện audio (/chat/audio).

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../widgets/tasks/task_done_popup.dart';
import '../../widgets/tasks/task_inbox_button.dart';

class ChatAiHubScreen extends StatelessWidget {
  // Widget màn CHỌN CHẾ ĐỘ CHATAI.
  const ChatAiHubScreen({super.key});

  // Dựng 3 thẻ chế độ: chat văn bản / chat giọng nói / thư viện audio.
  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isMobile = MediaQuery.sizeOf(context).width < 760;

    return TaskDonePopupHost(
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFFF8FAFC),
              Color(0xFFEFF6FF),
              Color(0xFFDBEAFE),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: EdgeInsets.symmetric(
                horizontal: isMobile ? 16 : 28,
                vertical: isMobile ? 18 : 28,
              ),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1080),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            strings.pick('Chat AI', 'AI Chat'),
                            style: Theme.of(context)
                                .textTheme
                                .headlineMedium
                                ?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  color: const Color(0xFF0F172A),
                                ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const TaskInboxButton(),
                      ],
                    ),
                  const SizedBox(height: 10),
                  Text(
                    strings.pick(
                      'Chọn chế độ tương tác phù hợp. Cả hai đều dùng chung trợ lý AI để điều phối công cụ tạo văn bản và hỏi đáp tài liệu.',
                      'Choose the interaction mode that fits best. Both modes use the same AI assistant to orchestrate document generation and document Q&A tools.',
                    ),
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: const Color(0xFF334155),
                          height: 1.6,
                        ),
                  ),
                  const SizedBox(height: 24),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final narrow = constraints.maxWidth < 860;
                      final cards = [
                        Expanded(
                          child: _ModeCard(
                            icon: Icons.chat_bubble_outline,
                            accent: const Color(0xFF2563EB),
                            title: strings.pick(
                              'Trò chuyện bằng chat',
                              'Text chat',
                            ),
                            subtitle: strings.pick(
                              'Phù hợp khi cần xem đầy đủ lịch sử, nguồn tham khảo, văn bản sinh ra và thao tác theo từng bước.',
                              'Best when you want the full history, citations, generated documents, and a step-by-step workflow.',
                            ),
                            bullets: [
                              strings.pick(
                                'Giao diện chat kiểu trợ lý',
                                'Assistant-style chat interface',
                              ),
                              strings.pick(
                                'Hiển thị kết quả hỏi đáp và nguồn tham khảo',
                                'Shows answers and cited sources',
                              ),
                              strings.pick(
                                'Mở thẳng văn bản đã tạo khi cần',
                                'Open generated documents directly',
                              ),
                            ],
                            cta: strings.pick('Mở chat AI', 'Open AI chat'),
                            onTap: () => context.go('/chat/text'),
                          ),
                        ),
                        Expanded(
                          child: _ModeCard(
                            icon: Icons.mic_none_outlined,
                            accent: const Color(0xFF7C3AED),
                            title: strings.pick(
                              'Tương tác bằng giọng nói',
                              'Voice interaction',
                            ),
                            subtitle: strings.pick(
                              'Phù hợp khi cần ra lệnh nhanh theo phong cách voice assistant, có transcript realtime và log debug ngay trên UI.',
                              'Best for quick voice-assistant style commands, with real-time transcript and inline debug logs on the UI.',
                            ),
                            bullets: [
                              strings.pick(
                                'Nghe tối đa 20 giây mỗi lượt',
                                'Listens up to 20 seconds per turn',
                              ),
                              strings.pick(
                                'Tự xử lý sau 3 giây im lặng',
                                'Auto-processes after 3 seconds of silence',
                              ),
                              strings.pick(
                                'Có transcript realtime và log debug',
                                'Includes real-time transcript and debug logs',
                              ),
                            ],
                            cta: strings.pick(
                              'Mở giọng nói AI',
                              'Open AI voice',
                            ),
                            onTap: () => context.go('/chat/voice'),
                          ),
                        ),
                      ];

                      if (narrow) {
                        return Column(
                          children: [
                            cards[0],
                            const SizedBox(height: 16),
                            cards[1],
                          ],
                        );
                      }

                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          cards[0],
                          const SizedBox(width: 20),
                          cards[1],
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton.icon(
                    onPressed: () => context.go('/chat/audio'),
                    icon: const Icon(Icons.library_music_outlined),
                    label: Text(
                      strings.pick(
                        'Mở thư viện audio đã lưu',
                        'Open saved audio library',
                      ),
                    ),
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

class _ModeCard extends StatelessWidget {
  // Thẻ một chế độ ChatAI: icon + nhãn + điều hướng tới route tương ứng khi bấm.
  const _ModeCard({
    required this.icon,
    required this.accent,
    required this.title,
    required this.subtitle,
    required this.bullets,
    required this.cta,
    required this.onTap,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String subtitle;
  final List<String> bullets;
  final String cta;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: accent.withOpacity(0.18)),
        boxShadow: [
          BoxShadow(
            color: accent.withOpacity(0.08),
            blurRadius: 32,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.12),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Icon(icon, color: accent, size: 28),
          ),
          const SizedBox(height: 18),
          Text(
            title,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            subtitle,
            style: const TextStyle(
              color: Color(0xFF475569),
              height: 1.6,
            ),
          ),
          const SizedBox(height: 16),
          ...bullets.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Icon(
                      Icons.check_circle,
                      color: accent,
                      size: 16,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(
                        color: Color(0xFF334155),
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const Spacer(),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: onTap,
            icon: const Icon(Icons.arrow_forward),
            style: FilledButton.styleFrom(
              backgroundColor: accent,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            ),
            label: Text(cta),
          ),
        ],
      ),
    );
  }
}
