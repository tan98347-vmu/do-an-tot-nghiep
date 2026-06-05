import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_doc_manager/models/document.dart';
import 'package:ai_doc_manager/widgets/documents/document_ai_edit_panel.dart';
import 'package:ai_doc_manager/widgets/documents/document_manual_edit_card.dart';

Document _buildDocument({
  bool canManualEdit = true,
  bool canResumeManualEdit = false,
  String? manualEditLockMessage,
  String? manualEditLockedByName,
}) {
  return Document(
    id: 1,
    title: 'Van ban thu nghiem',
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
    canManualEdit: canManualEdit,
    canResumeManualEdit: canResumeManualEdit,
    manualEditLockMessage: manualEditLockMessage,
    manualEditLockedByName: manualEditLockedByName,
  );
}

void main() {
  testWidgets('manual edit card shows resume label and active lock context', (tester) async {
    final document = _buildDocument(
      canManualEdit: true,
      canResumeManualEdit: true,
      manualEditLockMessage: 'Ban dang co phien chinh sua thu cong dang mo cho van ban nay.',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DocumentManualEditCard(
            document: document,
            onOpen: () {},
          ),
        ),
      ),
    );

    expect(find.text('Tiep tuc phien chinh sua'), findsOneWidget);
    expect(find.textContaining('phien chinh sua thu cong'), findsOneWidget);
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNotNull);
  });

  testWidgets('manual edit card disables open button when another user holds the lock', (tester) async {
    final document = _buildDocument(
      canManualEdit: false,
      canResumeManualEdit: false,
      manualEditLockMessage:
          'Van ban dang duoc chinh sua thu cong trong trinh sua web. Hoan tat hoac huy phien chinh sua truoc khi thuc hien thao tac nay.',
      manualEditLockedByName: 'Nguoi khac',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DocumentManualEditCard(
            document: document,
            onOpen: () {},
          ),
        ),
      ),
    );

    expect(find.textContaining('Nguoi dang giu phien'), findsOneWidget);
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull);
  });

  testWidgets('word ai panel shows disabled reason when manual edit lock is active', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: DocumentAiEditPanel(
              documentId: 1,
              canEdit: false,
              disabledReason:
                  'Van ban dang duoc chinh sua thu cong trong trinh sua web. Hoan tat hoac huy phien chinh sua truoc khi thuc hien thao tac nay.',
            ),
          ),
        ),
      ),
    );

    expect(find.text('Edit with Word AI'), findsOneWidget);
    expect(find.textContaining('Van ban dang duoc chinh sua thu cong'), findsOneWidget);
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull);
  });

  testWidgets('word ai panel fills the editor from a quick prompt chip', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 900,
              child: DocumentAiEditPanel(
                documentId: 1,
                canEdit: true,
              ),
            ),
          ),
        ),
      ),
    );

    final suggestionFinder = find.textContaining('Chuan hoa giong van');
    expect(suggestionFinder, findsOneWidget);
    await tester.tap(suggestionFinder);
    await tester.pumpAndSettle();

    final textField = tester.widget<TextField>(find.byType(TextField));
    expect(textField.controller?.text, contains('Chuan hoa giong van'));
  });
}
