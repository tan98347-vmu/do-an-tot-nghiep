import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:ai_doc_manager/models/document.dart';
import 'package:ai_doc_manager/models/document_manual_edit_session.dart';
import 'package:ai_doc_manager/providers/document_manual_edit_provider.dart';
import 'package:ai_doc_manager/screens/documents/document_manual_edit_screen.dart';

class _FakeManualEditApi extends DocumentManualEditApi {
  _FakeManualEditApi({
    required this.session,
    required this.document,
    this.ensureError,
  });

  final DocumentManualEditSession session;
  final Document document;
  final Object? ensureError;
  int ensureCalls = 0;
  int finishCalls = 0;
  int cancelCalls = 0;
  int heartbeatCalls = 0;

  @override
  Future<DocumentManualEditSession> ensureSession(int documentId) async {
    ensureCalls++;
    if (ensureError != null) {
      throw ensureError!;
    }
    return session;
  }

  @override
  Future<DocumentManualEditSession> heartbeatSession(int sessionId) async {
    heartbeatCalls++;
    return session;
  }

  @override
  Future<DocumentManualEditSession> getSession(int sessionId) async {
    return session;
  }

  @override
  Future<DocumentManualEditFinishResponse> finishSession(
    int sessionId, {
    String changeNote = '',
  }) async {
    finishCalls++;
    return DocumentManualEditFinishResponse(
      session: session,
      document: document,
    );
  }

  @override
  Future<DocumentManualEditSession> cancelSession(int sessionId) async {
    cancelCalls++;
    return session;
  }
}

DocumentManualEditSession _buildSession({
  String status = 'active',
  bool isActive = true,
}) {
  return DocumentManualEditSession(
    id: 91,
    documentId: 7,
    documentTitle: 'Van ban chinh sua',
    createdById: 1,
    createdByName: 'Tester',
    status: status,
    provider: 'collabora',
    baseVersionNumber: 3,
    editorUrl: 'http://collabora.test/editor',
    providerReady: true,
    providerStatusCode: 'ready',
    providerStatusDetail: 'Collabora manual edit provider is ready.',
    isActive: isActive,
    lockMessage:
        'Ban dang co phien chinh sua thu cong dang mo cho van ban nay.',
    expiresAt: '2026-05-12T12:00:00Z',
  );
}

Document _buildDocument() {
  return const Document(
    id: 7,
    title: 'Van ban chinh sua',
    status: 'draft',
    visibility: 'private',
    shareStatus: 'none',
    ownerName: 'Tester',
    isArchived: false,
    hasFile: true,
    createdAt: '2026-05-12T00:00:00Z',
    updatedAt: '2026-05-12T00:00:00Z',
    isFavorite: false,
    canEdit: true,
    canDelete: true,
    canManualEdit: true,
  );
}

Widget _buildApp(_FakeManualEditApi api) {
  final router = GoRouter(
    initialLocation: '/documents/7/manual-edit',
    routes: [
      GoRoute(
        path: '/documents/:id/manual-edit',
        builder: (_, __) => const DocumentManualEditScreen(documentId: 7),
      ),
      GoRoute(
        path: '/documents/:id',
        builder: (_, state) => Scaffold(
          body: Text('detail-${state.pathParameters['id']}'),
        ),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      documentManualEditApiProvider.overrideWithValue(api),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('manual edit screen shows retry when session load fails',
      (tester) async {
    final api = _FakeManualEditApi(
      session: _buildSession(),
      document: _buildDocument(),
      ensureError: Exception('Khong mo duoc trinh sua thu cong'),
    );

    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    expect(find.text('Thu lai'), findsOneWidget);
    expect(find.textContaining('Khong mo duoc trinh sua thu cong'),
        findsOneWidget);
  });

  testWidgets('manual edit screen finishes and returns to detail route',
      (tester) async {
    final api = _FakeManualEditApi(
      session: _buildSession(),
      document: _buildDocument(),
    );

    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    expect(find.text('Luu & hoan tat'), findsOneWidget);
    await tester.tap(find.text('Luu & hoan tat'));
    await tester.pumpAndSettle();

    expect(api.finishCalls, 1);
    expect(find.text('detail-7'), findsOneWidget);
  });

  testWidgets('manual edit screen cancels and returns to detail route',
      (tester) async {
    final api = _FakeManualEditApi(
      session: _buildSession(),
      document: _buildDocument(),
    );

    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Huy phien'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Huy phien'));
    await tester.pumpAndSettle();

    expect(api.cancelCalls, 1);
    expect(find.text('detail-7'), findsOneWidget);
  });
}
