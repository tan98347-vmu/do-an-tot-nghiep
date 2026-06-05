import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'api_client.dart';

/// Ket qua xoa mau.
enum TemplateDeleteOutcome { deleted, cancelled }

/// Xoa mot mau van ban, xu ly thong nhat truong hop mau dang duoc su dung.
///
/// - 204: xoa thanh cong -> tra ve `deleted`.
/// - 409 (mau dang dung): hien hop thoai xac nhan; neu nguoi dung dong y se
///   goi lai voi `force=true`. Neu huy -> tra ve `cancelled`.
/// - Loi khac: nem lai DioException de caller hien thong bao.
///
/// Dung chung cho moi man (danh sach, the mau, chi tiet, form) de khong con
/// cho nao bo sot viec xu ly 409.
Future<TemplateDeleteOutcome> deleteTemplateWithUsageGuard(
  BuildContext context,
  int templateId,
) async {
  Future<void> doDelete({required bool force}) {
    return ApiClient().dio.delete(
          'templates/$templateId/',
          queryParameters: force ? {'force': 'true'} : null,
        );
  }

  try {
    await doDelete(force: false);
    return TemplateDeleteOutcome.deleted;
  } on DioException catch (e) {
    if (e.response?.statusCode != 409) {
      rethrow;
    }
    final data = e.response?.data;
    final usage = (data is Map) ? data['usage_count'] : null;
    if (!context.mounted) {
      return TemplateDeleteOutcome.cancelled;
    }
    final force = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mẫu đang được sử dụng'),
        content: Text(
          'Mẫu này đang được dùng trong ${usage ?? 'một số'} văn bản đã sinh. '
          'Các văn bản đã tạo sẽ không bị ảnh hưởng. Bạn vẫn muốn xóa mẫu?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Vẫn xóa'),
          ),
        ],
      ),
    );
    if (force == true) {
      await doDelete(force: true);
      return TemplateDeleteOutcome.deleted;
    }
    return TemplateDeleteOutcome.cancelled;
  }
}
