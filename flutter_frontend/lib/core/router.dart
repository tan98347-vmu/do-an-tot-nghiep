// Tệp này dùng để: định nghĩa hạ tầng client như router, API client, theme hoặc locale trong flutter_frontend/lib/core/router.dart.
// Cách hoạt động: được nạp sớm khi app Flutter khởi động để các màn và provider dùng chung cấu hình nền.
// Vai trò trong hệ thống: Đây là lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: quyết định cách frontend khởi chạy, điều hướng và gọi API.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'iframe_blocker.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/dashboard/dashboard_hub_screen.dart';
import '../screens/templates/template_list_screen.dart';
import '../screens/templates/template_detail_screen.dart';
import '../screens/templates/template_form_screen.dart';
import '../screens/templates/template_creation_hub_screen.dart';
import '../screens/templates/template_manual_edit_screen.dart';
import '../screens/documents/document_list_screen.dart';
import '../screens/documents/document_detail_screen.dart';
import '../screens/documents/document_manual_edit_screen.dart';
import '../screens/documents/mailbox_screen_modern.dart';
import '../screens/documents/mailbox_detail_screen_modern.dart';
import '../screens/summaries/document_summary_discovery_screen.dart';
import '../screens/summaries/document_summary_workspace_screen.dart';
import '../screens/ai_doc/ai_doc_screen.dart';
import '../screens/ai_doc/ai_doc_fill_screen.dart';
import '../screens/assistant/chat_ai_hub_screen.dart';
import '../screens/assistant/assistant_chat_screen.dart';
import '../screens/assistant/assistant_rag_result_screen.dart';
import '../screens/assistant/assistant_voice_screen.dart';
import '../screens/assistant/assistant_audio_library_screen.dart';
import '../screens/rag/rag_history_screen.dart';
import '../screens/prompts/prompt_list_screen.dart';
import '../screens/prompts/prompt_form_screen.dart';
import '../screens/help/help_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/sharing/pending_approvals_screen.dart' as share_inbox;
import '../screens/admin/admin_screen.dart';
import '../screens/admin/ai_config_screen.dart';
import '../screens/admin/company_backup_screen.dart';
import '../screens/platform/platform_companies_screen.dart';
// === BEGIN R5: imports ===
import '../screens/platform/platform_company_detail_screen.dart';
// === END R5 ===
// === BEGIN R2: imports ===
import '../screens/compliance/compliance_check_screen.dart';
// === END R2 ===
import '../screens/system/trash_screen.dart';
import '../screens/signing/signing_delegation_screen.dart';
import '../screens/signing/signing_inbox_screen_modern.dart';
import '../screens/signing/signing_proposal_review_screen.dart';
import '../screens/signing/signing_task_detail_screen_pki.dart';
import '../screens/signing/signed_pdf_list_screen_modern.dart';
import '../screens/signing/signed_pdf_detail_screen_pki.dart';
import '../screens/templates/bulk_upload_screen.dart';
import '../screens/guest/guest_ai_screen.dart';
import '../screens/guest/guest_document_detail_screen.dart';
import '../widgets/shell/app_shell.dart';
import '../widgets/shell/guest_shell.dart';
import '../widgets/shell/platform_shell.dart';

// Mục đích: Provider `routerProvider` triển khai phần việc `router Provider` trong flutter_frontend/lib/core/router.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final routerProvider = Provider<GoRouter>((ref) {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  final authState = ref.watch(authStateProvider);
  return GoRouter(
    initialLocation: '/dashboard',
    // Tu dong tam an iframe preview khi co dialog/popup (tranh de len Flutter).
    observers: [IframeBlockerObserver()],
    redirect: (context, state) {
      final currentUser = authState.when(
        data: (user) => user,
        loading: () => null,
        error: (_, __) => null,
      );
      final isLoggedIn = currentUser != null;
      final isAuthRoute = state.matchedLocation.startsWith('/login') ||
          state.matchedLocation.startsWith('/register') ||
          state.matchedLocation.startsWith('/guest');
      final isPlatformRoute = state.matchedLocation.startsWith('/platform');
      final isPlatformProfileRoute =
          state.matchedLocation == '/platform/profile';
      final isCompanyAdminRoute = state.matchedLocation == '/admin' ||
          state.matchedLocation.startsWith('/admin/');
      if (!isLoggedIn && !isAuthRoute) return '/login';
      if (isLoggedIn && currentUser.mustChangePassword && !isAuthRoute) {
        final passwordRoute =
            currentUser.isPlatformAdmin ? '/platform/profile' : '/profile';
        if (state.matchedLocation != passwordRoute) {
          return passwordRoute;
        }
      }
      if (isLoggedIn && isAuthRoute) {
        return currentUser.isPlatformAdmin
            ? '/platform/companies'
            : '/dashboard';
      }
      if (isLoggedIn &&
          currentUser.isPlatformAdmin &&
          !isAuthRoute &&
          !isPlatformRoute) {
        return '/platform/companies';
      }
      if (isLoggedIn &&
          currentUser.isPlatformAdmin &&
          isPlatformProfileRoute &&
          !currentUser.mustChangePassword) {
        return '/platform/companies';
      }
      if (isPlatformRoute && currentUser?.isPlatformAdmin != true) {
        return '/dashboard';
      }
      if (isCompanyAdminRoute &&
          currentUser?.isPlatformAdmin != true &&
          currentUser?.isCompanyAdmin != true) {
        return '/dashboard';
      }
      return null;
    },
    routes: [
      // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      // Nhóm nhiều route dưới cùng một shell để chia sẻ layout và navigation chung.

      ShellRoute(
        observers: [IframeBlockerObserver()],
        builder: (_, __, child) => GuestShell(child: child),
        routes: [
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(path: '/guest', builder: (_, __) => const GuestAiScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
              path: '/guest/document',
              builder: (_, __) => const GuestDocumentDetailScreen()),
        ],
      ),
      // Nhóm nhiều route dưới cùng một shell để chia sẻ layout và navigation chung.

      ShellRoute(
        observers: [IframeBlockerObserver()],
        builder: (context, state, child) => PlatformShell(child: child),
        routes: [
          GoRoute(
            path: '/platform/companies',
            builder: (_, __) => const PlatformCompaniesScreen(),
          ),
          GoRoute(
            path: '/platform/companies/trash',
            builder: (_, __) =>
                const PlatformCompaniesScreen(initialViewMode: 'trash'),
          ),
          // === BEGIN R5: platform company detail dashboard ===
          GoRoute(
            path: '/platform/companies/:id',
            builder: (_, state) {
              final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
              return PlatformCompanyDetailScreen(companyId: id);
            },
          ),
          // === END R5 ===
          GoRoute(
            path: '/platform/profile',
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),
      ShellRoute(
        observers: [IframeBlockerObserver()],
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          // === BEGIN R4 ===
          // Global search runs inside AppShell as an overlay, so r4 does not
          // register a standalone route here.
          // === END R4 ===
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
              path: '/dashboard', builder: (_, __) => const DashboardScreen()),
          GoRoute(
              path: '/sharing/pending',
              builder: (_, __) =>
                  const share_inbox.PendingShareApprovalsScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/templates',
            builder: (_, state) => TemplateListScreen(
                group: state.uri.queryParameters['group'] ?? ''),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: 'create',
                builder: (_, state) {
                  final sourceUrl = state.uri.queryParameters['source_url'];
                  final sourceTitle = state.uri.queryParameters['source_title'];
                  final mode = state.uri.queryParameters['mode'];
                  if ((sourceUrl ?? '').isNotEmpty || mode == 'quick') {
                    return TemplateFormScreen(
                      sourceUrl: sourceUrl,
                      sourceTitle: sourceTitle,
                    );
                  }
                  return const TemplateCreationHubScreen();
                },
              ),
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                  path: 'bulk-upload',
                  builder: (_, __) => const BulkUploadScreen()),
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':id',
                builder: (_, state) => TemplateDetailScreen(
                    id: int.parse(state.pathParameters['id']!)),
                routes: [
                  // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

                  GoRoute(
                    path: 'edit',
                    builder: (_, state) => TemplateFormScreen(
                        id: int.tryParse(state.pathParameters['id'] ?? '')),
                  ),
                  GoRoute(
                    path: 'manual-edit',
                    builder: (_, state) => TemplateManualEditScreen(
                      templateId: int.parse(state.pathParameters['id']!),
                      returnTo:
                          state.uri.queryParameters['return_to'] ?? 'detail',
                    ),
                  ),
                ],
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/documents',
            builder: (_, state) => DocumentListScreen(
                group: state.uri.queryParameters['group'] ?? ''),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':id',
                builder: (_, state) => DocumentDetailScreen(
                    id: int.parse(state.pathParameters['id']!)),
                routes: [
                  GoRoute(
                    path: 'manual-edit',
                    builder: (_, state) => DocumentManualEditScreen(
                      documentId: int.parse(state.pathParameters['id']!),
                    ),
                  ),
                ],
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/summaries',
            builder: (_, state) => DocumentSummaryDiscoveryScreen(
              initialQueryParameters: state.uri.queryParameters,
            ),
            routes: [
              GoRoute(
                path: ':id',
                builder: (_, state) => DocumentSummaryWorkspaceScreen(
                  documentId: int.parse(state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          // === BEGIN R2: compliance check route ===
          GoRoute(
            path: '/compliance-check',
            builder: (_, __) => const ComplianceCheckScreen(),
          ),
          // === END R2 ===
          GoRoute(
            path: '/ai-doc',
            builder: (_, state) => AiDocScreen(
                preselectedTemplateId: int.tryParse(
                    state.uri.queryParameters['template_id'] ?? '')),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':templateId',
                builder: (_, state) => AiDocFillScreen(
                  templateId: int.parse(state.pathParameters['templateId']!),
                  prefill: state.uri.queryParameters['prefill'] == '1',
                ),
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/chat',
            builder: (_, __) => const ChatAiHubScreen(),
            routes: [
              // === BEGIN R3 ===
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: 'text',
                builder: (_, state) => AssistantChatScreen(
                  conversationId: int.tryParse(
                    state.uri.queryParameters['conversation_id'] ?? '',
                  ),
                ),
              ),
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: 'voice',
                builder: (_, state) => AssistantVoiceScreen(
                  conversationId: int.tryParse(
                    state.uri.queryParameters['conversation_id'] ?? '',
                  ),
                ),
              ),
              // === END R3 ===
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: 'audio',
                builder: (_, __) => const AssistantAudioLibraryScreen(),
              ),
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: 'rag-result',
                builder: (_, state) => AssistantRagResultScreen(
                  assistantSessionId: int.parse(
                      state.uri.queryParameters['assistant_session_id']!),
                  assistantMessageId: int.parse(
                      state.uri.queryParameters['assistant_message_id']!),
                  mode: state.uri.queryParameters['mode'] == 'document'
                      ? 'document'
                      : 'template',
                  returnTo: state.uri.queryParameters['return_to'],
                  returnLabel: state.uri.queryParameters['return_label'],
                ),
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/mailbox',
            builder: (_, __) => const MailboxScreen(),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':id',
                builder: (_, state) => MailboxDetailScreen(
                  threadId: int.parse(state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/chat-rag-result',
            builder: (_, state) => AssistantRagResultScreen(
              assistantSessionId:
                  int.parse(state.uri.queryParameters['assistant_session_id']!),
              assistantMessageId:
                  int.parse(state.uri.queryParameters['assistant_message_id']!),
              mode: state.uri.queryParameters['mode'] == 'document'
                  ? 'document'
                  : 'template',
              returnTo: state.uri.queryParameters['return_to'],
              returnLabel: state.uri.queryParameters['return_label'],
            ),
          ),
          // === BEGIN R3 ===
          GoRoute(
            path: '/assistant/voice',
            builder: (_, state) => AssistantVoiceScreen(
              conversationId: int.tryParse(
                state.uri.queryParameters['conversation_id'] ?? '',
              ),
            ),
          ),
          // === END R3 ===
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(path: '/rag', builder: (_, __) => const RagHistoryScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/prompts',
            builder: (_, state) => PromptListScreen(
              groupParam: state.uri.queryParameters['group'],
            ),
          ),
          GoRoute(
              path: '/prompts/new',
              builder: (_, __) => const PromptFormScreen()),
          GoRoute(
            path: '/prompts/:id/edit',
            builder: (_, state) => PromptFormScreen(
              promptId: int.tryParse(state.pathParameters['id'] ?? ''),
            ),
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/help',
            builder: (_, state) => HelpScreen(
              initialSection: state.uri.queryParameters['section'],
            ),
          ),
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(path: '/trash', builder: (_, __) => const TrashScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/signing/tasks',
            builder: (_, __) => const SigningInboxScreen(),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':id',
                builder: (_, state) => SigningTaskDetailScreen(
                  taskId: int.parse(state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/signing/proposals/review',
            builder: (_, state) => SigningProposalReviewScreen(
              initialProposalId: int.tryParse(
                state.uri.queryParameters['proposal'] ?? '',
              ),
            ),
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
              path: '/signing/access',
              builder: (_, __) => const SigningDelegationScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
            path: '/signed-pdfs',
            builder: (_, __) => const SignedPdfListScreen(),
            routes: [
              // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

              GoRoute(
                path: ':id',
                builder: (_, state) => SignedPdfDetailScreen(
                  id: int.parse(state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(path: '/admin', builder: (_, __) => const AdminScreen()),
          // Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.

          GoRoute(
              path: '/admin/ai-config',
              builder: (_, __) => const AiConfigScreen()),
          GoRoute(
              path: '/admin/backups',
              builder: (_, __) => const CompanyBackupScreen()),
        ],
      ),
    ],
  );
});
