# AI Loading Integration Guide

Backend endpoints async đã sẵn sàng. Frontend tích hợp bằng cách thay thế các `dio.post()` cũ bằng `runAITask()`.

## Endpoints async sẵn có

| Tính năng | Endpoint async | Style dialog đề xuất |
|---|---|---|
| Sinh văn bản từ mẫu | `ai/doc/create-async/` | `linear` |
| Điền từ hồ sơ | `ai/doc/prefill-profile-async/` | `linear` |
| Điền từ ngữ cảnh công ty | `ai/doc/prefill-company-async/` | `linear` |
| Trích xuất PDF | `ai/doc/extract-pdf-async/` | `linear` (cancel hard) |
| Trích xuất ảnh/camera | `ai/doc/extract-image-async/` | `linear` (cancel hard) |
| Tóm tắt văn bản | `documents/<id>/summarize-async/` | `linear` |
| Chat AI | `ai/chat-async/` | `circularCompact` (inline bubble) |
| Voice AI | `assistant/turn-async/` | `circularExpanded` (modal) |

## Pattern tích hợp chuẩn (linear)

```dart
import '../../core/run_ai_task.dart';
import '../../widgets/ai_loading/ai_task_dialog.dart';

try {
  final result = await runAITask(
    context: context,
    ref: ref,
    endpoint: 'ai/doc/create-async/',
    jsonPayload: {
      'template_id': widget.templateId,
      'variables': vars,
      'doc_title': _titleCtrl.text,
      // ... các field khác
    },
    style: AITaskDialogStyle.linear,
    dialogTitle: 'Tạo văn bản',
  );
  // result = task.result đã trả về từ backend
  final docId = result['document_id'] as int;
  // ... xử lý docId
} on AITaskCancelledException {
  _snack('Đã dừng tạo văn bản');
} on AITaskFailedException catch (e) {
  _snack('Lỗi: ${e.message}', color: Colors.red);
}
```

## Pattern upload file (extract PDF / image)

```dart
final formData = FormData.fromMap({
  'template_id': widget.templateId,
  'pdf_file': await MultipartFile.fromFile(file.path, filename: file.name),
});

final result = await runAITask(
  context: context, ref: ref,
  endpoint: 'ai/doc/extract-pdf-async/',
  formPayload: formData,
  style: AITaskDialogStyle.linear,
  dialogTitle: 'Trích xuất PDF',
);
// result.variables = {biến: giá trị}
```

## Pattern chat (circular compact inline)

Trong `assistant_chat_screen.dart`, thay vì spinner trên bubble đang gõ:

```dart
// Khi user gửi tin nhắn:
final taskResp = await ApiClient().dio.post('ai/chat-async/', data: {
  'q': question, 'session_id': sessionId,
});
final taskId = taskResp.data['task_id'];

// Render trong bubble AI đang sinh:
Row(children: [
  AITaskCircularProgress(
    taskId: taskId,
    size: CircularSize.compact,
    onStreamingUpdate: (chunks) {
      setState(() => _bubbleText = chunks.join(''));
    },
    onComplete: (state) {
      setState(() {
        _bubbleText = state.result?['answer'] ?? '';
        _streaming = false;
      });
    },
  ),
  Expanded(child: Text(_bubbleText)),
]);
```

## Pattern voice (modal expanded)

```dart
final result = await runAITask(
  context: context, ref: ref,
  endpoint: 'assistant/turn-async/',
  formPayload: FormData.fromMap({
    'input': transcript,
    'mode': 'voice',
    'voice_audio': await MultipartFile.fromFile(audioFile.path),
  }),
  style: AITaskDialogStyle.circularExpanded,
  dialogTitle: 'Trợ lý giọng nói',
  showStreamingText: true,
);
final answer = result['answer'] as String?;
```

## Polling endpoint trực tiếp (nếu cần custom UI)

```dart
final stateAsync = ref.watch(aiTaskProgressProvider(
  AITaskPollConfig(taskId: myTaskId),
));
stateAsync.when(
  data: (state) => Text('${state.percent}% — ${state.stage}'),
  ...
);
```

## Cancel manual

```dart
await ApiClient().dio.post('ai-tasks/$taskId/cancel/');
```

## Endpoint state

`GET /api/ai-tasks/<task_id>/` trả:
```json
{
  "task_id": "uuid",
  "status": "running|completed|failed|cancelled",
  "progress_percent": 45,
  "progress_stage": "AI điền biến rỗng",
  "progress_detail": "Gọi LLM apply prompt",
  "cancel_requested": false,
  "result": {...},
  "error_message": "",
  "streaming_chunks": ["token1", "token2", ...]
}
```

## Mobile responsive

`AITaskLinearProgress` và `AITaskCircularProgress` đã có `LayoutBuilder` built-in:
- Mobile (<700px): linear bar height 6, font 12-18sp, compact circular 56px
- Desktop: linear bar height 8, font 14-22sp, expanded circular 120px

Voice modal nên dùng `Dialog.fullscreen` trên mobile, `AlertDialog` centered trên desktop.

## Cleanup task DB

Chạy thủ công: `python manage.py cleanup_ai_tasks --days 7`
APScheduler (Module 20) tự chạy hằng ngày 3h sáng.
