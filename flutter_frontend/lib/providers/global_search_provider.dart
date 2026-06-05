import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/global_search_result.dart';

final globalSearchProvider =
    FutureProvider.family.autoDispose<GlobalSearchResults?, String>(
  (ref, rawQuery) async {
    final query = rawQuery.trim();
    if (query.length < 2) {
      return null;
    }

    final cancelToken = CancelToken();
    ref.onDispose(cancelToken.cancel);

    final response = await ApiClient().dio.get(
      'search/',
      queryParameters: {'q': query},
      cancelToken: cancelToken,
    );
    return GlobalSearchResults.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  },
);
