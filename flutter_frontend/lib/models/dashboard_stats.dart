// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `DashboardStats` triển khai phần việc `Dashboard Stats` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DashboardStats {
  final int totalTemplates;
  final int totalDocuments;
  final int templatesThisMonth;
  final int documentsThisMonth;
  final String currentLlmModel;
  final int aiApiCalls;
  final int aiSessions;
  final int aiMessages;
  final List<DayCount> docsLast7Days;
  final List<PieSlice> templatesByVisibility;
  final List<PieSlice> documentsByStatus;
  final List<RecentItem> recentTemplates;
  final List<RecentItem> recentDocuments;
  final OrgContext orgContext;
  final ScopeSummary templateStructure;
  final ScopeSummary documentStructure;
  final ScopeSummary monthlyDocumentStructure;
  final AiOverview aiOverview;
  final OrgStructure orgStructure;

  const DashboardStats({
    required this.totalTemplates,
    required this.totalDocuments,
    required this.templatesThisMonth,
    required this.documentsThisMonth,
    required this.currentLlmModel,
    required this.aiApiCalls,
    required this.aiSessions,
    required this.aiMessages,
    required this.docsLast7Days,
    required this.templatesByVisibility,
    required this.documentsByStatus,
    required this.recentTemplates,
    required this.recentDocuments,
    required this.orgContext,
    required this.templateStructure,
    required this.documentStructure,
    required this.monthlyDocumentStructure,
    required this.aiOverview,
    required this.orgStructure,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> j) => DashboardStats(
    totalTemplates: j['total_templates'] ?? 0,
    totalDocuments: j['total_documents'] ?? 0,
    templatesThisMonth: j['templates_this_month'] ?? 0,
    documentsThisMonth: j['documents_this_month'] ?? 0,
    currentLlmModel: j['current_llm_model'] ?? '',
    aiApiCalls: j['ai_api_calls'] ?? 0,
    aiSessions: j['ai_sessions'] ?? 0,
    aiMessages: j['ai_messages'] ?? 0,
    docsLast7Days: (j['docs_last_7_days'] as List? ?? [])
        .map((e) => DayCount.fromJson(e)).toList(),
    templatesByVisibility: (j['templates_by_visibility'] as List? ?? [])
        .map((e) => PieSlice.fromJson(e)).toList(),
    documentsByStatus: (j['documents_by_status'] as List? ?? [])
        .map((e) => PieSlice.fromJson(e)).toList(),
    recentTemplates: (j['recent_templates'] as List? ?? [])
        .map((e) => RecentItem.fromJson(e)).toList(),
    recentDocuments: (j['recent_documents'] as List? ?? [])
        .map((e) => RecentItem.fromJson(e)).toList(),
    orgContext: OrgContext.fromJson(
      (j['org_context'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
    templateStructure: ScopeSummary.fromJson(
      (j['template_structure'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
    documentStructure: ScopeSummary.fromJson(
      (j['document_structure'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
    monthlyDocumentStructure: ScopeSummary.fromJson(
      (j['monthly_document_structure'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
    aiOverview: AiOverview.fromJson(
      (j['ai_overview'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
    orgStructure: OrgStructure.fromJson(
      (j['org_structure'] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    ),
  );
}

// Mục đích: Lớp `OrgContext` triển khai phần việc `Org Context` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrgContext {
  final String roleLabel;
  final List<String> groupNames;
  final int groupCount;
  final int leaderGroupCount;
  final String summary;
  final bool canApprovePending;

  const OrgContext({
    required this.roleLabel,
    required this.groupNames,
    required this.groupCount,
    required this.leaderGroupCount,
    required this.summary,
    required this.canApprovePending,
  });

  factory OrgContext.fromJson(Map<String, dynamic> j) => OrgContext(
    roleLabel: j['role_label'] ?? '',
    groupNames: (j['group_names'] as List? ?? []).map((e) => '$e').toList(),
    groupCount: j['group_count'] ?? 0,
    leaderGroupCount: j['leader_group_count'] ?? 0,
    summary: j['summary'] ?? '',
    canApprovePending: j['can_approve_pending'] ?? false,
  );
}

// Mục đích: Lớp `ScopeSummary` triển khai phần việc `Scope Summary` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ScopeSummary {
  final int total;
  final String summary;
  final List<ScopeItem> items;

  const ScopeSummary({
    required this.total,
    required this.summary,
    required this.items,
  });

  factory ScopeSummary.fromJson(Map<String, dynamic> j) => ScopeSummary(
    total: j['total'] ?? 0,
    summary: j['summary'] ?? '',
    items: (j['items'] as List? ?? [])
        .map((e) => ScopeItem.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

// Mục đích: Lớp `ScopeItem` triển khai phần việc `Scope Item` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ScopeItem {
  final String key;
  final String label;
  final String description;
  final int count;

  const ScopeItem({
    required this.key,
    required this.label,
    required this.description,
    required this.count,
  });

  factory ScopeItem.fromJson(Map<String, dynamic> j) => ScopeItem(
    key: j['key'] ?? '',
    label: j['label'] ?? '',
    description: j['description'] ?? '',
    count: j['count'] ?? 0,
  );
}

// Mục đích: Lớp `AiOverview` triển khai phần việc `Ai Overview` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AiOverview {
  final String currentModel;
  final int sessions;
  final int messages;
  final int apiCalls;
  final String summary;

  const AiOverview({
    required this.currentModel,
    required this.sessions,
    required this.messages,
    required this.apiCalls,
    required this.summary,
  });

  factory AiOverview.fromJson(Map<String, dynamic> j) => AiOverview(
    currentModel: j['current_model'] ?? '',
    sessions: j['sessions'] ?? 0,
    messages: j['messages'] ?? 0,
    apiCalls: j['api_calls'] ?? 0,
    summary: j['summary'] ?? '',
  );
}

// Mục đích: Lớp `OrgStructure` triển khai phần việc `Org Structure` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrgStructure {
  final String summary;
  final List<OrgPerson> admins;
  final List<OrgPerson> leaders;
  final List<OrgPerson> employees;
  final List<OrgEdge> reportingEdges;
  final List<OrgEdge> teamEdges;

  const OrgStructure({
    required this.summary,
    required this.admins,
    required this.leaders,
    required this.employees,
    required this.reportingEdges,
    required this.teamEdges,
  });

  factory OrgStructure.fromJson(Map<String, dynamic> j) => OrgStructure(
    summary: j['summary'] ?? '',
    admins: (j['admins'] as List? ?? [])
        .map((e) => OrgPerson.fromJson(e as Map<String, dynamic>))
        .toList(),
    leaders: (j['leaders'] as List? ?? [])
        .map((e) => OrgPerson.fromJson(e as Map<String, dynamic>))
        .toList(),
    employees: (j['employees'] as List? ?? [])
        .map((e) => OrgPerson.fromJson(e as Map<String, dynamic>))
        .toList(),
    reportingEdges: (j['reporting_edges'] as List? ?? [])
        .map((e) => OrgEdge.fromJson(e as Map<String, dynamic>))
        .toList(),
    teamEdges: (j['team_edges'] as List? ?? [])
        .map((e) => OrgEdge.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

// Mục đích: Lớp `OrgPerson` triển khai phần việc `Org Person` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrgPerson {
  final String id;
  final int userId;
  final String name;
  final String username;
  final String title;
  final String role;
  final List<String> groupNames;

  const OrgPerson({
    required this.id,
    required this.userId,
    required this.name,
    required this.username,
    required this.title,
    required this.role,
    required this.groupNames,
  });

  factory OrgPerson.fromJson(Map<String, dynamic> j) => OrgPerson(
    id: j['id'] ?? '',
    userId: j['user_id'] ?? 0,
    name: j['name'] ?? '',
    username: j['username'] ?? '',
    title: j['title'] ?? '',
    role: j['role'] ?? '',
    groupNames: (j['group_names'] as List? ?? []).map((e) => '$e').toList(),
  );
}

// Mục đích: Lớp `OrgNodeStats` triển khai phần việc `Org Node Stats` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrgNodeStats {
  final int userId;
  final String name;
  final String username;
  final String title;
  final int templateCount;
  final int documentCount;
  final int documentsThisMonth;
  final int activityTotal;
  final List<DayCount> activityLast7Days;

  const OrgNodeStats({
    required this.userId,
    required this.name,
    required this.username,
    required this.title,
    required this.templateCount,
    required this.documentCount,
    required this.documentsThisMonth,
    required this.activityTotal,
    required this.activityLast7Days,
  });

  factory OrgNodeStats.fromJson(Map<String, dynamic> j) => OrgNodeStats(
    userId: j['user_id'] ?? 0,
    name: j['name'] ?? '',
    username: j['username'] ?? '',
    title: j['title'] ?? '',
    templateCount: j['template_count'] ?? 0,
    documentCount: j['document_count'] ?? 0,
    documentsThisMonth: j['documents_this_month'] ?? 0,
    activityTotal: j['activity_total'] ?? 0,
    activityLast7Days: (j['activity_last_7_days'] as List? ?? [])
        .map((e) => DayCount.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList(),
  );
}

// Mục đích: Lớp `OrgEdge` triển khai phần việc `Org Edge` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrgEdge {
  final String from;
  final String to;
  final String type;
  final String label;

  const OrgEdge({
    required this.from,
    required this.to,
    required this.type,
    required this.label,
  });

  factory OrgEdge.fromJson(Map<String, dynamic> j) => OrgEdge(
    from: j['from'] ?? '',
    to: j['to'] ?? '',
    type: j['type'] ?? '',
    label: j['label'] ?? '',
  );
}

// Mục đích: Lớp `DayCount` triển khai phần việc `Day Count` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DayCount {
  final String date;
  final int count;
  const DayCount({required this.date, required this.count});
  factory DayCount.fromJson(Map<String, dynamic> j) =>
      DayCount(date: j['date'], count: j['count'] ?? 0);
}

// Mục đích: Lớp `PieSlice` triển khai phần việc `Pie Slice` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class PieSlice {
  final String key;
  final String label;
  final int count;
  const PieSlice({required this.key, required this.label, required this.count});
  factory PieSlice.fromJson(Map<String, dynamic> j) => PieSlice(
    key: j['visibility'] ?? j['status'] ?? '',
    label: j['label'] ?? '',
    count: j['count'] ?? 0,
  );
}

// Mục đích: Lớp `RecentItem` triển khai phần việc `Recent Item` trong flutter_frontend/lib/models/dashboard_stats.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class RecentItem {
  final int id;
  final String title;
  final String status;
  final String createdAt;
  const RecentItem({required this.id, required this.title, required this.status, required this.createdAt});
  factory RecentItem.fromJson(Map<String, dynamic> j) => RecentItem(
    id: j['id'],
    title: j['title'] ?? '',
    status: j['status'] ?? '',
    createdAt: j['created_at'] ?? '',
  );
}
