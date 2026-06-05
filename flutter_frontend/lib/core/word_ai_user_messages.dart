import 'dart:convert';

import '../models/word_ai_job.dart';

String wordAiStatusLabel(String status) {
  switch (status) {
    case 'queued':
      return 'Đang chờ';
    case 'claimed':
      return 'Đã nhận job';
    case 'editing':
      return 'Đang chỉnh sửa';
    case 'uploading':
      return 'Đang tải kết quả';
    case 'completed':
      return 'Hoàn tất';
    case 'failed':
      return 'Thất bại';
    case 'cancelled':
      return 'Đã hủy';
    case 'needs_review':
      return 'Cần xem lại';
    default:
      return status;
  }
}

String wordAiQueuedMessageForUser(WordAiJob job) {
  final latestMessage = job.latestEvent?.message.trim() ?? '';
  if (latestMessage.contains('No active Word worker is connected')) {
    return 'Yêu cầu đã được đưa vào hàng đợi, nhưng máy hiện chưa thấy Word AI Worker đang hoạt động. '
        'Hãy mở worker hoặc đợi worker kết nối rồi theo dõi lại ở mục Lịch sử Word AI.';
  }
  return 'Yêu cầu đã được đưa vào hàng đợi. Bạn có thể theo dõi tiến độ ở mục Lịch sử Word AI ngay bên dưới.';
}

String wordAiSummaryForUser(WordAiJob job) {
  switch (job.status) {
    case 'completed':
      if (job.changeNote.trim().isNotEmpty) {
        return 'Word AI đã hoàn tất. ${job.changeNote.trim()}';
      }
      return 'Word AI đã hoàn tất và tạo một phiên bản mới cho văn bản này.';
    case 'failed':
      return wordAiFailureForUser(job);
    case 'needs_review':
      return 'Word AI không thể tự động xử lý an toàn yêu cầu này. Hãy đổi cách ra lệnh rõ hơn hoặc chỉnh sửa thủ công.';
    case 'cancelled':
      return 'Yêu cầu Word AI đã bị hủy trước khi tạo phiên bản mới.';
    case 'queued':
      return wordAiQueuedMessageForUser(job);
    case 'claimed':
      return 'Word AI đã nhận yêu cầu và đang chuẩn bị mở Word worker để xử lý.';
    case 'editing':
      return 'Word AI đang chỉnh sửa văn bản và đối chiếu từng bước trong Word.';
    case 'uploading':
      return 'Word AI đã xong phần chỉnh sửa và đang đưa kết quả về hệ thống.';
    default:
      return job.resultSummary.isNotEmpty
          ? job.resultSummary
          : 'Word AI đang xử lý yêu cầu này.';
  }
}

String wordAiFailureForUser(WordAiJob job) {
  final parsed = _tryParseFailurePayload(job.failureReasonText);
  if (parsed != null) {
    final targetText = '${parsed['target_text'] ?? ''}'.trim();
    final replacementText = '${parsed['replacement_text'] ?? ''}'.trim();
    final targetCount = _asInt(parsed['target_count']);
    final replacementCount = _asInt(parsed['replacement_count']);
    final verified = parsed['verified'] == true;

    if (targetCount == 0 && targetText.isNotEmpty) {
      final replacementPart = replacementText.isEmpty
          ? ''
          : ' để đổi thành "$replacementText"';
      return 'Word AI không tìm thấy cụm "$targetText"$replacementPart trong văn bản hiện tại, '
          'nên chưa thể thực hiện yêu cầu. Hãy kiểm tra lại nội dung gốc hoặc viết lại lệnh cụ thể hơn.';
    }

    if (targetCount > 0 && replacementCount == 0 && targetText.isNotEmpty) {
      return 'Word AI có tìm thấy nội dung "$targetText", nhưng bước thay thế không tạo ra kết quả hợp lệ. '
          'Hãy thử viết lại yêu cầu rõ hơn và chạy lại.';
    }

    if (!verified) {
      return 'Word AI đã thử chỉnh sửa, nhưng bước kiểm tra cuối cùng không đạt, '
          'nên hệ thống không tạo phiên bản mới để tránh sai nội dung.';
    }
  }

  if (job.errorCode == 'word_runtime_failed' || job.errorDetail.contains('modal dialog')) {
    return 'Word AI đang bị chặn bởi một hộp thoại hoặc cửa sổ Word trên máy chủ. '
        'Cần đóng hộp thoại này rồi chạy lại job.';
  }
  if (job.errorCode == 'native_word_addin_missing') {
    return 'Máy chủ chưa có Word AI add-in sẵn sàng, nên hệ thống chưa thể sửa văn bản bằng Word AI. '
        'Cần cài đặt add-in Word AI rồi chạy lại.';
  }
  if (job.errorCode == 'native_word_addin_stale') {
    return 'Bộ Word AI add-in trên máy chủ đang là bản cũ hơn source hiện tại, nên hệ thống đã dừng job để tránh sửa sai. '
        'Cần cập nhật lại add-in Word AI rồi chạy lại.';
  }
  if (job.errorCode == 'plan_failed') {
    return 'Word AI không lập được kế hoạch sửa văn bản an toàn từ yêu cầu vừa nhập. '
        'Hãy viết ngắn hơn và cụ thể hơn.';
  }

  final latestMessage = job.latestEvent?.message.trim() ?? '';
  if (latestMessage.contains('No active Word worker is connected')) {
    return 'Word AI chưa bắt đầu được vì máy hiện tại chưa thấy Word AI Worker đang hoạt động.';
  }

  return 'Word AI chưa thể hoàn tất yêu cầu này. Hãy kiểm tra lại nội dung lệnh, '
      'hoặc thử lại sau khi worker sẵn sàng.';
}

String? wordAiTechnicalDetailForUser(WordAiJob job) {
  final failureText = job.failureReasonText.trim();
  if (failureText.isNotEmpty && _tryParseFailurePayload(failureText) == null) {
    return failureText;
  }
  final latestMessage = job.latestEvent?.message.trim() ?? '';
  if (latestMessage.isNotEmpty &&
      latestMessage != wordAiSummaryForUser(job) &&
      !latestMessage.startsWith('{')) {
    return latestMessage;
  }
  return null;
}

Map<String, dynamic>? _tryParseFailurePayload(String raw) {
  final text = raw.trim();
  if (text.isEmpty || !text.startsWith('{')) {
    return null;
  }
  try {
    final decoded = jsonDecode(text);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    if (decoded is Map) {
      return decoded.cast<String, dynamic>();
    }
  } catch (_) {}
  return null;
}

int _asInt(Object? raw) {
  if (raw is int) {
    return raw;
  }
  if (raw is num) {
    return raw.toInt();
  }
  return int.tryParse('$raw') ?? 0;
}
