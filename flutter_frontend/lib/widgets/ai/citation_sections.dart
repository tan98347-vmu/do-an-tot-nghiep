// Tệp này dùng để: đóng gói khối giao diện hoặc hành vi lặp lại trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác.

import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';

// Mục đích: Lớp `CitationSections` triển khai phần việc `Citation Sections` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class CitationSections extends StatelessWidget {
  final List<dynamic> citations;
  final String? returnTo;
  final String? returnLabel;

  const CitationSections({
    super.key,
    required this.citations,
    this.returnTo,
    this.returnLabel,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final items = citations
        .whereType<Map>()
        .map((citation) => Map<String, dynamic>.from(citation))
        .toList();
    final localItems =
        items.where((citation) => !_isInternetCitation(citation)).toList();
    final internetItems = items.where(_isInternetCitation).toList();
    final bieuMauItems = internetItems
        .where((citation) => _internetSourceType(citation) == 'bieumau')
        .toList();
    final hopDongItems = internetItems
        .where((citation) => _internetSourceType(citation) == 'hopdong')
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (localItems.isNotEmpty)
          _CitationSection(
            title: strings.pick('Kết quả nội bộ', 'Local results'),
            icon: Icons.folder_open_outlined,
            citations: localItems,
            returnTo: returnTo,
            returnLabel: returnLabel,
          ),
        if (bieuMauItems.isNotEmpty) ...[
          if (localItems.isNotEmpty) const SizedBox(height: 10),
          _CitationSection(
            title: strings.pick(
              'Biểu mẫu từ THƯ VIỆN PHÁP LUẬT',
              'Templates from THƯ VIỆN PHÁP LUẬT',
            ),
            icon: Icons.description_outlined,
            citations: bieuMauItems,
            returnTo: returnTo,
            returnLabel: returnLabel,
          ),
        ],
        if (hopDongItems.isNotEmpty) ...[
          if (localItems.isNotEmpty || bieuMauItems.isNotEmpty)
            const SizedBox(height: 10),
          _CitationSection(
            title: strings.pick(
              'Hợp đồng từ THƯ VIỆN PHÁP LUẬT',
              'Contracts from THƯ VIỆN PHÁP LUẬT',
            ),
            icon: Icons.public_outlined,
            citations: hopDongItems,
            returnTo: returnTo,
            returnLabel: returnLabel,
          ),
        ],
      ],
    );
  }

  // Mục đích: Phương thức `_isInternetCitation` triển khai phần việc `is Internet Citation` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _isInternetCitation(Map<String, dynamic> citation) {
    return '${citation['source_group'] ?? citation['type'] ?? ''}' ==
        'internet';
  }

  // Mục đích: Phương thức `_internetSourceType` triển khai phần việc `internet Source Type` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _internetSourceType(Map<String, dynamic> citation) {
    final sourceType = '${citation['source_type'] ?? ''}'.trim().toLowerCase();
    if (sourceType == 'hopdong') return 'hopdong';
    return 'bieumau';
  }
}

// Mục đích: Lớp `_CitationSection` triển khai phần việc `Citation Section` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _CitationSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Map<String, dynamic>> citations;
  final String? returnTo;
  final String? returnLabel;

  const _CitationSection({
    required this.title,
    required this.icon,
    required this.citations,
    this.returnTo,
    this.returnLabel,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: Colors.blueGrey.shade700),
            const SizedBox(width: 6),
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: Colors.blueGrey.shade700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...citations.map(
          (citation) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _CitationTile(
              citation: citation,
              returnTo: returnTo,
              returnLabel: returnLabel,
            ),
          ),
        ),
      ],
    );
  }
}

// Mục đích: Lớp `_CitationTile` triển khai phần việc `Citation Tile` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _CitationTile extends StatelessWidget {
  final Map<String, dynamic> citation;
  final String? returnTo;
  final String? returnLabel;

  const _CitationTile({
    required this.citation,
    this.returnTo,
    this.returnLabel,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final type = '${citation['type'] ?? ''}';
    final title = '${citation['title'] ?? citation}';
    final icon = switch (type) {
      'template' => Icons.description_outlined,
      'document' => Icons.article_outlined,
      'internet' => Icons.public_outlined,
      _ => Icons.link_outlined,
    };
    final metaParts = <String>[
      if ('${citation['status'] ?? ''}'.isNotEmpty) '${citation['status']}',
      if ('${citation['category'] ?? ''}'.isNotEmpty) '${citation['category']}',
      if ('${citation['doc_number'] ?? ''}'.isNotEmpty)
        '${citation['doc_number']}',
    ];

    return Material(
      color: const Color(0xFFF8FAFC),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openCitation(context),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              Icon(icon, size: 18, color: Colors.blueGrey.shade700),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (metaParts.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        metaParts.join(' | '),
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.blueGrey.shade600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.open_in_new,
                  size: 16, color: Colors.blueGrey.shade500),
            ],
          ),
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_openCitation` triển khai phần việc `open Citation` trong flutter_frontend/lib/widgets/ai/citation_sections.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _openCitation(BuildContext context) {
    final strings = AppStrings.of(context);
    final externalUrl = _citationExternalUrl();
    if (externalUrl != null) {
      html.window.open(externalUrl, '_blank');
      return;
    }

    final route = _citationRoute();
    if (route == null || route.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            strings.pick(
              'Không mở được nguồn tham khảo này.',
              'Unable to open this source.',
            ),
          ),
        ),
      );
      return;
    }
    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

    context.go(route);
  }

  String? _citationExternalUrl() {
    final candidate =
        '${citation['external_url'] ?? citation['url'] ?? ''}'.trim();
    if (candidate.startsWith('http://') || candidate.startsWith('https://')) {
      return candidate;
    }
    return null;
  }

  String? _citationRoute() {
    final routeValue = citation['route'];
    var route = '';
    if (routeValue is String && routeValue.trim().isNotEmpty) {
      if (routeValue.startsWith('http://') ||
          routeValue.startsWith('https://')) {
        return null;
      }
      final uri = Uri.tryParse(routeValue.trim());
      route = routeValue.trim();
      if (uri != null && uri.path.isNotEmpty) {
        route = uri.path;
        if (uri.hasQuery) {
          route = '$route?${uri.query}';
        }
      }
      if (route.length > 1 && route.endsWith('/')) {
        route = route.substring(0, route.length - 1);
      }
    } else {
      final type = '${citation['type'] ?? ''}';
      final id = citation['id'];
      if (id == null) return null;
      if (type == 'template') route = '/templates/$id';
      if (type == 'document') route = '/documents/$id';
    }

    if (route.isEmpty || returnTo == null || returnTo!.trim().isEmpty) {
      return route;
    }

    final uri = Uri.parse(route);
    final params = Map<String, String>.from(uri.queryParameters);
    params['return_to'] = returnTo!;
    if (returnLabel != null && returnLabel!.trim().isNotEmpty) {
      params['return_label'] = returnLabel!;
    }
    return uri.replace(queryParameters: params).toString();
  }
}
