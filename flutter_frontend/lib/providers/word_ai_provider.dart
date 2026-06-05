import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/word_ai_job.dart';

final wordAiRefreshTickProvider = NotifierProvider<WordAiRefreshTickNotifier, int>(
  WordAiRefreshTickNotifier.new,
);

class WordAiRefreshTickNotifier extends Notifier<int> {
  @override
  int build() => 0;

  void bump() => state++;
}

void refreshWordAiJobs(WidgetRef ref) {
  ref.read(wordAiRefreshTickProvider.notifier).bump();
}

final wordAiJobHistoryProvider =
    FutureProvider.autoDispose.family<List<WordAiJob>, int>((ref, documentId) async {
  ref.watch(wordAiRefreshTickProvider);
  final response = await ApiClient().dio.get(
    'word-ai/jobs/',
    queryParameters: {'document_id': documentId, 'limit': 10},
  );
  return (response.data as List)
      .map((item) => WordAiJob.fromJson((item as Map).cast<String, dynamic>()))
      .toList();
});

Future<WordAiJob> createWordAiJob({
  required int documentId,
  required String instruction,
  required bool trackChanges,
}) async {
  final response = await ApiClient().dio.post(
    'word-ai/jobs/',
    data: {
      'document_id': documentId,
      'instruction': instruction,
      'track_changes': trackChanges,
      'edit_mode': 'direct_addin_mcp',
    },
  );
  return WordAiJob.fromJson((response.data as Map).cast<String, dynamic>());
}

Future<void> cancelWordAiJob(int jobId) async {
  await ApiClient().dio.post('word-ai/jobs/$jobId/cancel/');
}
