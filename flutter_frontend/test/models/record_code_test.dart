import 'package:flutter_test/flutter_test.dart';

import 'package:ai_doc_manager/models/document.dart';
import 'package:ai_doc_manager/models/template.dart';

void main() {
  test('document reads API record code and falls back to its id', () {
    final fromApi = Document.fromJson({
      'id': 12,
      'record_code': 'VB-000012',
      'title': 'Van ban',
      'status': 'draft',
      'visibility': 'private',
      'share_status': 'active',
      'owner_name': 'Tester',
      'is_archived': false,
      'has_file': false,
      'created_at': '',
      'updated_at': '',
      'is_favorite': false,
      'can_edit': true,
      'can_delete': true,
    });
    const fallback = Document(
      id: 34,
      title: 'Van ban',
      status: 'draft',
      visibility: 'private',
      shareStatus: 'active',
      ownerName: 'Tester',
      isArchived: false,
      hasFile: false,
      createdAt: '',
      updatedAt: '',
      isFavorite: false,
      canEdit: true,
      canDelete: true,
    );

    expect(fromApi.recordCode, 'VB-000012');
    expect(fallback.recordCode, 'VB-000034');
  });

  test('template reads API record code and falls back to its id', () {
    final fromApi = DocumentTemplate.fromJson({
      'id': 56,
      'record_code': 'MVB-000056',
      'title': 'Mau',
      'description': '',
      'status': 'draft',
      'visibility': 'private',
      'version': '1.0',
      'owner_name': 'Tester',
      'variable_count': 0,
      'is_favorite': false,
      'can_use': true,
      'can_edit': true,
      'can_delete': true,
      'created_at': '',
      'updated_at': '',
    });
    const fallback = DocumentTemplate(
      id: 78,
      title: 'Mau',
      description: '',
      status: 'draft',
      visibility: 'private',
      version: '1.0',
      ownerName: 'Tester',
      variableCount: 0,
      isFavorite: false,
      canUse: true,
      canEdit: true,
      canDelete: true,
      createdAt: '',
      updatedAt: '',
    );

    expect(fromApi.recordCode, 'MVB-000056');
    expect(fallback.recordCode, 'MVB-000078');
  });
}
