class WordAiJobEvent {
  final int id;
  final String createdAt;
  final String level;
  final String step;
  final String status;
  final String message;
  final Map<String, dynamic> payload;

  const WordAiJobEvent({
    required this.id,
    required this.createdAt,
    required this.level,
    required this.step,
    required this.status,
    required this.message,
    required this.payload,
  });

  factory WordAiJobEvent.fromJson(Map<String, dynamic> json) => WordAiJobEvent(
        id: json['id'] ?? 0,
        createdAt: json['created_at'] ?? '',
        level: json['level'] ?? 'info',
        step: json['step'] ?? '',
        status: json['status'] ?? '',
        message: json['message'] ?? '',
        payload: (json['payload'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
      );
}

class WordAiToolStep {
  final String id;
  final String toolName;
  final String status;
  final Map<String, dynamic> input;
  final Map<String, dynamic> result;

  const WordAiToolStep({
    required this.id,
    required this.toolName,
    required this.status,
    required this.input,
    required this.result,
  });

  factory WordAiToolStep.fromJson(Map<String, dynamic> json) => WordAiToolStep(
        id: json['id'] ?? '',
        toolName: json['tool_name'] ?? '',
        status: json['status'] ?? '',
        input: (json['input'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
        result: (json['result'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
      );
}

class WordAiJob {
  final int id;
  final int documentId;
  final String documentTitle;
  final String instruction;
  final String editMode;
  final String planMode;
  final String currentSlotLabel;
  final bool trackChanges;
  final String status;
  final String llmModelName;
  final double llmTemperature;
  final String resultSummary;
  final String changeNote;
  final String errorCode;
  final String errorDetail;
  final String createdAt;
  final String updatedAt;
  final List<WordAiToolStep> toolTranscript;
  final Map<String, dynamic> verificationSummary;
  final Map<String, dynamic> artifactManifest;
  final Map<String, dynamic> documentChecksums;
  final WordAiJobEvent? latestEvent;

  const WordAiJob({
    required this.id,
    required this.documentId,
    required this.documentTitle,
    required this.instruction,
    required this.editMode,
    required this.planMode,
    required this.currentSlotLabel,
    required this.trackChanges,
    required this.status,
    required this.llmModelName,
    required this.llmTemperature,
    required this.resultSummary,
    required this.changeNote,
    required this.errorCode,
    required this.errorDetail,
    required this.createdAt,
    required this.updatedAt,
    required this.toolTranscript,
    required this.verificationSummary,
    required this.artifactManifest,
    required this.documentChecksums,
    this.latestEvent,
  });

  bool get isActive => switch (status) {
        'queued' || 'claimed' || 'editing' || 'uploading' => true,
        _ => false,
      };

  bool get canCancel => status == 'queued' || status == 'claimed' || status == 'editing';

  String get statusLabel => switch (status) {
        'queued' => 'Đang chờ',
        'claimed' => 'Đã nhận job',
        'editing' => 'Đang chỉnh sửa',
        'uploading' => 'Đang tải kết quả',
        'completed' => 'Hoàn tất',
        'failed' => 'Thất bại',
        'cancelled' => 'Đã hủy',
        'needs_review' => 'Cần xem lại',
        _ => status,
      };

  String get runtimeLabel => switch (editMode) {
        'direct_addin_mcp' => 'Word thật (xử lý từng bước)',
        _ => editMode,
      };

  bool get hasVerification => verificationSummary.isNotEmpty;

  bool get isVerified => verificationSummary['verified'] == true;

  bool get hasExportArtifactVerification {
    final exportState =
        (verificationSummary['export_artifact'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    return exportState.isNotEmpty;
  }

  bool get exportArtifactVerified {
    final exportState =
        (verificationSummary['export_artifact'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    return exportState['file_exists'] == true;
  }

  List<String> get toolStepLabels =>
      toolTranscript.map((item) => _toolNameLabel(item.toolName)).toList(growable: false);

  String get currentPhaseLabel {
    if (toolTranscript.isEmpty) {
      return statusLabel;
    }
    return _toolNameLabel(toolTranscript.last.toolName);
  }

  String get transcriptPreview {
    if (toolTranscript.isEmpty) {
      return 'Chưa có bước xử lý nào được ghi lại.';
    }
    return toolTranscript.take(5).map((item) => _toolNameLabel(item.toolName)).join(' -> ');
  }

  String get verificationSummaryText {
    if (verificationSummary.isEmpty) {
      return 'Hệ thống chưa chạy bước kiểm tra cuối cùng.';
    }
    if (verificationSummary['verified'] == true) {
      return 'Kiểm tra cuối cùng đã đạt trước khi lưu kết quả.';
    }
    final caseState = (verificationSummary['case'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final formatState =
        (verificationSummary['format'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    if (caseState.isNotEmpty && caseState['is_all_uppercase'] != true) {
      return 'Kiểm tra viết hoa chưa đạt.';
    }
    if (formatState.isNotEmpty && formatState['matches_expected_format'] != true) {
      return 'Kiểm tra định dạng chưa đạt.';
    }
    return 'Bước kiểm tra cuối cùng chưa hoàn tất.';
  }

  List<String> get verificationEvidenceLines {
    final lines = <String>[];
    final caseState = (verificationSummary['case'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final formatState =
        (verificationSummary['format'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final replacementState =
        (verificationSummary['replacement'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final exportState =
        (verificationSummary['export_artifact'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};

    if (caseState.isNotEmpty) {
      final ratio = caseState['uppercase_ratio'];
      final summary = caseState['is_all_uppercase'] == true
          ? 'Kiểm tra viết hoa đạt.'
          : 'Kiểm tra viết hoa chưa đạt.';
      lines.add(ratio == null ? summary : '$summary Tỷ lệ: $ratio');
    }
    if (formatState.isNotEmpty) {
      final ratio = formatState['bold_run_ratio'];
      final summary = formatState['matches_expected_format'] == true
          ? 'Kiểm tra độ phủ định dạng đạt.'
          : 'Kiểm tra độ phủ định dạng chưa đạt.';
      lines.add(ratio == null ? summary : '$summary Tỷ lệ: $ratio');
    }
    if (replacementState.isNotEmpty) {
      lines.add(
        replacementState['matches_expected_replacement'] == true
            ? 'Kiểm tra nội dung thay thế đã đạt.'
            : 'Kiểm tra nội dung thay thế chưa đạt.',
      );
    }
    if (exportState.isNotEmpty) {
      lines.add(
        exportState['file_exists'] == true
            ? 'Đã xác nhận tệp kết quả tồn tại.'
            : 'Chưa xác nhận được tệp kết quả.',
      );
    }
    return lines;
  }

  String get exportArtifactSummary {
    final exportState =
        (verificationSummary['export_artifact'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    if (exportState.isEmpty) {
      return 'Chưa có dữ liệu kiểm tra tệp kết quả.';
    }
    final checksum = (exportState['checksum_sha256'] ?? '').toString();
    final size = exportState['size_bytes'];
    final checksumPreview = checksum.isEmpty ? 'n/a' : (checksum.length <= 12 ? checksum : checksum.substring(0, 12));
    return 'Tệp kết quả: ${exportState['file_exists'] == true ? 'có' : 'không có'} | Kích thước: ${size ?? 'n/a'} | SHA256: $checksumPreview';
  }

  String get failureReasonText {
    if (errorDetail.isNotEmpty) {
      return errorDetail;
    }
    if (errorCode.isNotEmpty) {
      return errorCode;
    }
    final latestMessage = latestEvent?.message.trim() ?? '';
    if (latestMessage.isNotEmpty && latestEvent?.level == 'error') {
      return latestMessage;
    }
    return '';
  }

  String _toolNameLabel(String raw) {
    switch (raw) {
      case 'inspect_document':
        return 'Đọc và phân tích văn bản';
      case 'inspect_text_matches':
        return 'Kiểm tra đoạn cần sửa';
      case 'replace_text_matches':
        return 'Thay nội dung trong văn bản';
      case 'replace_selection_text':
        return 'Thay nội dung ở đoạn đang chọn';
      case 'normalize_case_whole_document':
        return 'Chuẩn hóa kiểu chữ cho toàn văn bản';
      case 'normalize_case_selection':
        return 'Chuẩn hóa kiểu chữ ở đoạn đang chọn';
      case 'apply_format_whole_document':
        return 'Áp dụng định dạng cho toàn văn bản';
      case 'apply_format_selection':
        return 'Áp dụng định dạng cho đoạn đang chọn';
      case 'clear_format_selection':
        return 'Xóa định dạng ở đoạn đang chọn';
      case 'toggle_track_changes':
        return 'Bật/tắt theo dõi sửa đổi';
      case 'replace_in_headers':
        return 'Thay nội dung ở đầu trang';
      case 'replace_in_footers':
        return 'Thay nội dung ở chân trang';
      case 'replace_in_tables':
        return 'Thay nội dung trong bảng';
      case 'insert_comment_selection':
        return 'Chèn nhận xét vào đoạn đang chọn';
      case 'set_paragraph_alignment':
        return 'Căn lề đoạn văn';
      case 'set_line_spacing':
        return 'Chỉnh giãn dòng';
      case 'set_paragraph_spacing':
        return 'Chỉnh khoảng cách trước và sau đoạn';
      case 'verify_text_replacement':
        return 'Kiểm tra nội dung đã thay';
      case 'verify_selection_text':
        return 'Kiểm tra đoạn đang chọn sau khi thay';
      case 'verify_document_case':
        return 'Kiểm tra kiểu chữ của văn bản';
      case 'verify_selection_case':
        return 'Kiểm tra kiểu chữ ở đoạn đang chọn';
      case 'verify_document_format_coverage':
        return 'Kiểm tra định dạng của văn bản';
      case 'verify_selection_format':
        return 'Kiểm tra định dạng ở đoạn đang chọn';
      case 'verify_track_changes_state':
        return 'Kiểm tra chế độ theo dõi sửa đổi';
      case 'verify_header_replacement':
        return 'Kiểm tra kết quả ở đầu trang';
      case 'verify_footer_replacement':
        return 'Kiểm tra kết quả ở chân trang';
      case 'verify_table_replacement':
        return 'Kiểm tra kết quả trong bảng';
      case 'verify_comment_selection':
        return 'Kiểm tra nhận xét đã chèn';
      case 'verify_export_artifact':
        return 'Kiểm tra tệp kết quả';
      case 'export_document':
        return 'Lưu và xuất tệp kết quả';
      default:
        return raw.replaceAll('_', ' ');
    }
  }

  factory WordAiJob.fromJson(Map<String, dynamic> json) => WordAiJob(
        id: json['id'] ?? 0,
        documentId: json['document'] ?? 0,
        documentTitle: json['document_title'] ?? '',
        instruction: json['instruction'] ?? '',
        editMode: json['edit_mode'] ?? 'direct_addin_mcp',
        planMode: json['plan_mode'] ?? '',
        currentSlotLabel: json['current_slot_label'] ?? '',
        trackChanges: json['track_changes'] ?? false,
        status: json['status'] ?? 'queued',
        llmModelName: json['llm_model_name'] ?? '',
        llmTemperature: (json['llm_temperature'] as num?)?.toDouble() ?? 0,
        resultSummary: json['result_summary'] ?? '',
        changeNote: json['change_note'] ?? '',
        errorCode: json['error_code'] ?? '',
        errorDetail: json['error_detail'] ?? '',
        createdAt: json['created_at'] ?? '',
        updatedAt: json['updated_at'] ?? '',
        toolTranscript: ((json['tool_transcript'] as List?) ?? const <dynamic>[])
            .whereType<Map>()
            .map((item) => WordAiToolStep.fromJson(item.cast<String, dynamic>()))
            .toList(),
        verificationSummary:
            (json['verification_summary'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
        artifactManifest: (json['artifact_manifest'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
        documentChecksums:
            (json['document_checksums'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{},
        latestEvent: json['latest_event'] is Map<String, dynamic>
            ? WordAiJobEvent.fromJson(json['latest_event'] as Map<String, dynamic>)
            : null,
      );
}
