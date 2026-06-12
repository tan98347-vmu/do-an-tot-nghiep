// === DỮ LIỆU NỘI DUNG TRỢ GIÚP ===
// Định nghĩa cấu trúc nội dung Help: HelpText / HelpStep / HelpSectionData (các mục + bước hướng dẫn song ngữ).
// HelpSectionData.resolve(...) lấy nội dung theo ngôn ngữ hiện tại. Đây là DATA cho help_screen, không phải màn hình.

import 'package:flutter/material.dart';

import 'help_access.dart';

class HelpText {
  final String vi;
  final String en;

  const HelpText(this.vi, this.en);

  String resolve(bool isEnglish) => isEnglish ? en : vi;
}

class HelpStep {
  final HelpText title;
  final HelpText description;
  final HelpAccess access;

  const HelpStep(
    this.title,
    this.description, {
    this.access = HelpAccess.standard,
  });
}

class HelpSectionData {
  final String id;
  final IconData icon;
  final HelpText title;
  final HelpText summary;
  final String route;
  final String? videoAsset;
  final HelpAccess access;
  final List<HelpText> prerequisites;
  final List<HelpStep> steps;
  final List<HelpText> tips;
  final HelpText? warning;

  const HelpSectionData({
    required this.id,
    required this.icon,
    required this.title,
    required this.summary,
    required this.route,
    this.videoAsset,
    this.access = HelpAccess.standard,
    this.prerequisites = const [],
    required this.steps,
    this.tips = const [],
    this.warning,
  });
}

const helpSections = <HelpSectionData>[
  HelpSectionData(
    id: 'dashboard',
    icon: Icons.dashboard_outlined,
    title: HelpText('Bảng điều khiển', 'Dashboard'),
    summary: HelpText(
      'Xem nhanh tình trạng văn bản, mẫu, người dùng và truy cập các thao tác thường dùng.',
      'Review document, template, and user activity, then open common actions quickly.',
    ),
    route: '/dashboard',
    steps: [
      HelpStep(
        HelpText('Đọc phần tổng quan', 'Read the overview'),
        HelpText(
          'Sau khi đăng nhập, mở Bảng điều khiển. Các ô số liệu cho biết số lượng văn bản, mẫu, người dùng và hoạt động gần đây mà tài khoản của bạn được phép xem.',
          'After signing in, open Dashboard. The summary metrics show documents, templates, users, and recent activity that your account is allowed to view.',
        ),
      ),
      HelpStep(
        HelpText('Đổi ngôn ngữ', 'Change language'),
        HelpText(
          'Dùng bộ chọn ngôn ngữ ở đầu trang để chuyển giữa Tiếng Việt và English. Lựa chọn được lưu trên trình duyệt và tiếp tục được dùng ở lần mở sau.',
          'Use the language selector at the top of the page to switch between Vietnamese and English. The choice is saved in the browser for future visits.',
        ),
      ),
      HelpStep(
        HelpText('Mở một thao tác nhanh', 'Open a quick action'),
        HelpText(
          'Chọn thao tác nhanh ở cuối trang để đi thẳng đến sinh văn bản, quản lý mẫu, quản lý văn bản hoặc chức năng liên quan mà không cần tìm lại trong thanh điều hướng.',
          'Choose a quick action near the bottom of the page to open document generation, template management, document management, or another related feature.',
        ),
      ),
      HelpStep(
        HelpText('Làm mới số liệu', 'Refresh the data'),
        HelpText(
          'Kéo trang xuống để làm mới trên thiết bị cảm ứng, hoặc tải lại trang khi cần xem số liệu mới nhất. Một số số liệu cũng được hệ thống tự cập nhật định kỳ.',
          'Pull down to refresh on touch devices, or reload the page when you need the latest data. Some metrics are also refreshed automatically.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Nếu một mục không xuất hiện, tài khoản của bạn có thể chưa được cấp quyền cho chức năng đó.',
        'If an item is not visible, your account may not have permission to use that feature.',
      ),
    ],
  ),
  HelpSectionData(
    id: 'ai-doc',
    icon: Icons.auto_awesome,
    title: HelpText('Sinh văn bản từ mẫu', 'Generate documents from templates'),
    summary: HelpText(
      'Chọn mẫu có sẵn, điền thông tin bằng tay hoặc nhờ AI hỗ trợ, xem trước rồi tạo file Word.',
      'Choose a template, enter information manually or with AI assistance, preview it, and create a Word file.',
    ),
    route: '/ai-doc',
    videoAsset: 'assets/videos/generate_from_template.mp4',
    prerequisites: [
      HelpText(
        'Bạn cần có quyền sử dụng ít nhất một mẫu văn bản.',
        'You need permission to use at least one document template.',
      ),
      HelpText(
        'Nên cập nhật Hồ sơ cá nhân và Ngữ cảnh công ty trước nếu muốn dùng chức năng tự động điền.',
        'Update your Profile and Company context first if you plan to use automatic filling.',
      ),
    ],
    steps: [
      HelpStep(
        HelpText('Tìm mẫu phù hợp', 'Find a suitable template'),
        HelpText(
          'Mở Sinh văn bản từ mẫu. Nhập từ khóa theo tên mẫu, mô tả hoặc tag; dùng bộ lọc phạm vi và trạng thái nếu danh sách dài. Chọn đúng mẫu cần tạo.',
          'Open Generate from templates. Search by template name, description, or tag; use visibility and status filters when the list is long. Select the template you need.',
        ),
      ),
      HelpStep(
        HelpText('Chọn cách bắt đầu', 'Choose how to start'),
        HelpText(
          'Khi hệ thống hỏi có tự động điền hay không, chọn tự động điền nếu muốn AI dùng dữ liệu sẵn có. Chọn cách thông thường nếu bạn muốn tự nhập từng trường.',
          'When asked whether to auto-fill, choose it if you want AI to use available information. Choose the regular flow if you prefer entering each field yourself.',
        ),
      ),
      HelpStep(
        HelpText('Nhập tiêu đề và các trường', 'Enter the title and fields'),
        HelpText(
          'Nhập Tiêu đề văn bản bắt buộc. Điền lần lượt các trường của mẫu. Kiểm tra kỹ tên người, ngày tháng, số văn bản, đơn vị và các con số vì đây là dữ liệu sẽ xuất hiện trong file cuối.',
          'Enter the required document title. Complete each template field. Carefully check names, dates, document numbers, organizations, and numeric values because they will appear in the final file.',
        ),
      ),
      HelpStep(
        HelpText('Dùng nguồn tự động điền khi cần', 'Use an automatic source when needed'),
        HelpText(
          'Bạn có thể chọn Điền từ hồ sơ, Điền từ ngữ cảnh công ty, tải PDF, hoặc chọn ảnh để OCR. Sau khi AI điền, hãy đọc lại từng trường; bạn vẫn có thể sửa thủ công trước khi tạo.',
          'You may fill from your profile, company context, an uploaded PDF, or an image through OCR. Review every AI-filled field and correct it manually before generating the document.',
        ),
      ),
      HelpStep(
        HelpText('Thêm yêu cầu tùy chỉnh', 'Add custom instructions'),
        HelpText(
          'Nếu cần thay đổi cách diễn đạt, chọn một prompt đã lưu hoặc nhập yêu cầu bổ sung. Ví dụ: “Dùng văn phong trang trọng và nhấn mạnh thời hạn hoàn thành”. Không nhập dữ liệu bí mật không cần thiết.',
          'To adjust wording, select a saved prompt or enter an extra instruction. Example: “Use a formal tone and emphasize the completion deadline.” Do not enter unnecessary confidential data.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra prompt', 'Check the prompt'),
        HelpText(
          'Nếu đã nhập yêu cầu bổ sung, bấm Check prompt. Khi hệ thống báo đạt yêu cầu, nút tiếp tục mới được bật. Nếu bạn sửa nội dung sau đó, phải bấm Check prompt lại.',
          'If you entered an extra instruction, click Check prompt. Continue only after it passes. If you edit the instruction afterward, run Check prompt again.',
        ),
      ),
      HelpStep(
        HelpText('Xem trước', 'Preview'),
        HelpText(
          'Bấm Xem trước để kiểm tra bố cục và nội dung đã ghép vào mẫu. Nếu có dữ liệu sai, đóng cửa sổ xem trước và sửa lại trường tương ứng; không tạo file khi chưa kiểm tra.',
          'Click Preview to inspect the layout and merged content. If anything is incorrect, close the preview and fix the corresponding field before creating the file.',
        ),
      ),
      HelpStep(
        HelpText('Tạo và mở văn bản', 'Create and open the document'),
        HelpText(
          'Bấm Tạo văn bản. Chờ tác vụ hoàn tất, sau đó mở trang chi tiết để tải Word, chỉnh sửa, chia sẻ, tóm tắt hoặc gửi vào quy trình ký.',
          'Click Create document. Wait for the task to finish, then open the detail page to download Word, edit, share, summarize, or send it into a signing workflow.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Để trống trường mà bạn chưa chắc chắn còn tốt hơn nhập một giá trị phỏng đoán.',
        'Leaving an uncertain field blank is safer than entering a guessed value.',
      ),
      HelpText(
        'Tên văn bản nên ngắn, rõ và có dấu hiệu nhận biết như loại văn bản, đơn vị hoặc thời gian.',
        'Use a short, clear title that includes a recognizable document type, organization, or date.',
      ),
    ],
    warning: HelpText(
      'AI hỗ trợ điền dữ liệu nhưng người dùng vẫn phải chịu trách nhiệm kiểm tra nội dung trước khi phát hành hoặc ký.',
      'AI assists with data entry, but the user remains responsible for reviewing content before issuing or signing it.',
    ),
  ),
  HelpSectionData(
    id: 'summaries',
    icon: Icons.summarize_outlined,
    title: HelpText('Tóm tắt văn bản', 'Document summaries'),
    summary: HelpText(
      'Chọn văn bản nguồn, cấu hình độ dài và phong cách, kiểm tra prompt rồi tạo bản tóm tắt.',
      'Choose a source document, configure length and style, validate the prompt, and generate a summary.',
    ),
    route: '/summaries',
    videoAsset: 'assets/videos/document_summary.mp4',
    prerequisites: [
      HelpText(
        'Văn bản phải có nội dung hoặc file Word mà hệ thống có thể đọc.',
        'The document must contain readable text or an accessible Word file.',
      ),
      HelpText(
        'Bạn phải có quyền xem văn bản nguồn.',
        'You must have permission to view the source document.',
      ),
    ],
    steps: [
      HelpStep(
        HelpText('Tìm văn bản cần tóm tắt', 'Find the document'),
        HelpText(
          'Mở Tóm tắt văn bản. Tìm theo tiêu đề, tag, mã văn bản hoặc bộ lọc nâng cao. Chọn Mở workspace tóm tắt tại đúng văn bản.',
          'Open Document summaries. Search by title, tag, document number, or advanced filters. Select Open summary workspace for the correct document.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra văn bản nguồn', 'Review the source document'),
        HelpText(
          'Đọc tiêu đề, mã, tag và thông tin nguồn ở đầu workspace. Nếu nội dung vừa được sửa, bấm Làm mới dữ liệu nguồn trước khi tóm tắt.',
          'Review the title, number, tags, and source details at the top of the workspace. If the document was recently edited, refresh the source data first.',
        ),
      ),
      HelpStep(
        HelpText('Chọn độ dài, ngôn ngữ và phong cách', 'Choose length, language, and style'),
        HelpText(
          'Chọn bản ngắn, tiêu chuẩn hoặc chi tiết; chọn ngôn ngữ đầu ra; sau đó chọn phong cách như điều hành, gạch đầu dòng hoặc việc cần làm. Có thể đặt số từ tối đa nếu cần.',
          'Choose brief, standard, or detailed length; select the output language; then choose a style such as executive, bullets, or action items. Set a maximum word count if needed.',
        ),
      ),
      HelpStep(
        HelpText('Chọn prompt hoặc nhập yêu cầu bổ sung', 'Select a prompt or add instructions'),
        HelpText(
          'Bạn có thể chọn prompt tóm tắt đã lưu hoặc nhập yêu cầu như “nhấn mạnh rủi ro pháp lý” hay “ưu tiên các mốc thời gian”. Yêu cầu này chỉ nên mô tả cách tóm tắt.',
          'Select a saved summary prompt or add an instruction such as “emphasize legal risks” or “prioritize deadlines.” Keep the instruction focused on how to summarize.',
        ),
      ),
      HelpStep(
        HelpText('Bấm Check prompt', 'Run Check prompt'),
        HelpText(
          'Khi có yêu cầu bổ sung, bấm Check prompt và đọc thông báo. Nếu bị chặn, sửa câu cho rõ hành động mong muốn rồi kiểm tra lại. Mọi thay đổi sau khi đạt yêu cầu đều làm kết quả check cũ mất hiệu lực.',
          'When extra instructions are present, click Check prompt and read the result. If blocked, rewrite it as a clear requested action and check again. Any later edit invalidates the previous check.',
        ),
      ),
      HelpStep(
        HelpText('Preview prompt', 'Preview the prompt'),
        HelpText(
          'Bấm Preview prompt để xem các phần sẽ được gửi cho AI. Phần hệ thống được che; văn bản nguồn và yêu cầu của bạn được đánh dấu là dữ liệu không tin cậy.',
          'Click Preview prompt to inspect the parts sent to AI. The system section is hidden, while the source document and your instructions are marked as untrusted data.',
        ),
      ),
      HelpStep(
        HelpText('Tạo bản tóm tắt', 'Generate the summary'),
        HelpText(
          'Bấm Tóm tắt văn bản và chờ xử lý. Văn bản dài có thể mất nhiều thời gian vì hệ thống phải chia nội dung thành nhiều phần rồi tổng hợp.',
          'Click Generate summary and wait for processing. Long documents may take more time because the system splits and recombines the content.',
        ),
      ),
      HelpStep(
        HelpText('Đọc, tải xuống hoặc làm lại', 'Review, download, or regenerate'),
        HelpText(
          'Đọc toàn bộ kết quả và đối chiếu với văn bản nguồn. Dùng Tải .docx hoặc Tải .md khi cần lưu. Chọn Tóm tắt lại nếu muốn đổi cấu hình hoặc cập nhật theo nội dung mới.',
          'Read the entire result and compare it with the source. Download DOCX or Markdown when needed. Choose Regenerate summary after changing options or updating the source.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Yêu cầu tốt: “Tóm tắt cho lãnh đạo, tập trung vào quyết định, rủi ro và việc cần làm”.',
        'Good instruction: “Summarize for executives, focusing on decisions, risks, and required actions.”',
      ),
    ],
    warning: HelpText(
      'Không dùng bản tóm tắt thay cho việc đọc văn bản gốc trong các quyết định pháp lý, tài chính hoặc ký duyệt quan trọng.',
      'Do not replace the original document with its summary for important legal, financial, or approval decisions.',
    ),
  ),
  HelpSectionData(
    id: 'rag',
    icon: Icons.chat_bubble_outline,
    title: HelpText('Hỏi đáp văn bản', 'Document Q&A'),
    summary: HelpText(
      'Đặt câu hỏi dựa trên mẫu hoặc văn bản mà bạn được phép truy cập và kiểm tra nguồn tham khảo.',
      'Ask questions about accessible templates or documents and review the cited sources.',
    ),
    route: '/rag',
    videoAsset: 'assets/videos/document_qa.mp4',
    steps: [
      HelpStep(
        HelpText('Chọn phạm vi hỏi đáp', 'Choose the source mode'),
        HelpText(
          'Mở Hỏi đáp văn bản và chọn chế độ Mẫu hoặc Văn bản. Chọn Mẫu khi cần tìm biểu mẫu phù hợp; chọn Văn bản khi cần tra cứu nội dung tài liệu đã lưu.',
          'Open Document Q&A and choose Template or Document mode. Use Template to find suitable forms and Document to search saved document content.',
        ),
      ),
      HelpStep(
        HelpText('Tạo cuộc hội thoại mới hoặc mở lịch sử', 'Start or resume a conversation'),
        HelpText(
          'Bạn có thể bắt đầu câu hỏi mới hoặc chọn một phiên cũ trong danh sách lịch sử. Dùng phiên mới khi đổi chủ đề để tránh ngữ cảnh cũ làm câu trả lời khó hiểu.',
          'Start a new question or select an older session from history. Use a new session when changing topics so previous context does not confuse the answer.',
        ),
      ),
      HelpStep(
        HelpText('Viết câu hỏi cụ thể', 'Ask a specific question'),
        HelpText(
          'Nêu rõ loại thông tin cần tìm, đối tượng và mốc thời gian nếu có. Ví dụ: “Trong các văn bản tôi được xem, văn bản nào quy định thời hạn thanh toán 30 ngày?”',
          'State the needed information, subject, and date range when relevant. Example: “Among documents I can access, which one specifies a 30-day payment deadline?”',
        ),
      ),
      HelpStep(
        HelpText('Gửi câu hỏi và chờ kết quả', 'Send and wait for the answer'),
        HelpText(
          'Bấm gửi một lần và chờ hệ thống tìm kiếm. Không cần gửi lặp lại khi trạng thái đang xử lý vì có thể tạo nhiều tác vụ giống nhau.',
          'Send the question once and wait for search to complete. Do not repeatedly submit while processing, because that may create duplicate tasks.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra nguồn tham khảo', 'Review citations'),
        HelpText(
          'Mở phần nguồn bên dưới câu trả lời. Nhấp vào tài liệu liên quan để đọc nội dung gốc, đặc biệt khi câu trả lời chứa số liệu, thời hạn, tên người hoặc kết luận quan trọng.',
          'Open the sources below the answer. Review the original document whenever the response contains numbers, deadlines, names, or important conclusions.',
        ),
      ),
      HelpStep(
        HelpText('Hỏi tiếp hoặc diễn đạt lại', 'Follow up or rephrase'),
        HelpText(
          'Nếu kết quả quá rộng, hỏi tiếp với phạm vi hẹp hơn. Nếu không tìm thấy nguồn, thử dùng từ khóa xuất hiện trong tiêu đề hoặc nội dung văn bản.',
          'If the answer is too broad, narrow the scope in a follow-up. If no source is found, use keywords likely to appear in the title or document text.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Một câu hỏi nên tập trung vào một vấn đề; tách câu hỏi dài thành nhiều lượt.',
        'Keep each question focused on one issue; split long questions into separate turns.',
      ),
    ],
    warning: HelpText(
      'Câu trả lời AI có thể chưa đầy đủ. Nguồn tài liệu gốc mới là căn cứ chính thức.',
      'AI answers may be incomplete. The original source document remains authoritative.',
    ),
  ),
  HelpSectionData(
    id: 'chat',
    icon: Icons.smart_toy_outlined,
    title: HelpText('Chat AI', 'AI Chat'),
    summary: HelpText(
      'Trao đổi bằng văn bản hoặc giọng nói, hỏi tài liệu và yêu cầu tạo văn bản trong một cuộc hội thoại.',
      'Use text or voice to ask questions, search documents, and request document creation in one conversation.',
    ),
    route: '/chat',
    videoAsset: 'assets/videos/chat_ai.mp4',
    steps: [
      HelpStep(
        HelpText('Chọn hình thức tương tác', 'Choose an interaction mode'),
        HelpText(
          'Tại trang Chat AI, chọn Trò chuyện bằng chat để dễ đọc lịch sử và nguồn; chọn Giọng nói AI khi cần ra lệnh nhanh; chọn Thư viện audio để nghe lại nội dung đã lưu.',
          'On the AI Chat page, choose Text chat for history and citations, AI Voice for quick spoken commands, or Audio library for saved recordings.',
        ),
      ),
      HelpStep(
        HelpText('Bắt đầu cuộc trò chuyện', 'Start a conversation'),
        HelpText(
          'Mở chat văn bản và tạo phiên mới nếu bạn bắt đầu chủ đề khác. Nhập yêu cầu tự nhiên, nhưng nên nêu rõ mục tiêu, đối tượng và kết quả mong muốn.',
          'Open text chat and start a new session for a new topic. Write naturally, but state the goal, subject, and expected result clearly.',
        ),
      ),
      HelpStep(
        HelpText('Đính kèm tài liệu khi cần', 'Attach a document when needed'),
        HelpText(
          'Nếu giao diện cho phép đính kèm, chọn đúng tài liệu hỗ trợ cho câu hỏi. Chỉ tải nội dung cần thiết và kiểm tra rằng bạn có quyền sử dụng tài liệu đó.',
          'When attachments are available, choose the supporting document carefully. Upload only what is needed and make sure you are allowed to use it.',
        ),
      ),
      HelpStep(
        HelpText('Yêu cầu hỏi đáp tài liệu', 'Request document Q&A'),
        HelpText(
          'Nói rõ bạn muốn AI tìm trong mẫu hay văn bản. Sau khi có kết quả, mở danh sách nguồn và đối chiếu thông tin quan trọng với tài liệu gốc.',
          'Specify whether AI should search templates or documents. After receiving an answer, open the citations and verify important details against the source.',
        ),
      ),
      HelpStep(
        HelpText('Yêu cầu tạo văn bản', 'Request document creation'),
        HelpText(
          'Mô tả loại văn bản, mục đích, người nhận và dữ liệu cần điền. Khi AI tạo xong, mở liên kết văn bản để kiểm tra và chỉnh sửa; không xem nội dung AI tạo là bản phát hành cuối.',
          'Describe the document type, purpose, recipient, and required information. Open the generated document to review and edit it; do not treat the first AI output as final.',
        ),
      ),
      HelpStep(
        HelpText('Dùng giọng nói', 'Use voice mode'),
        HelpText(
          'Cho phép trình duyệt dùng micro, nói rõ ràng và chờ hệ thống dừng nghe. Đọc transcript trước khi chấp nhận thao tác. Nếu transcript sai, chuyển sang chat văn bản để sửa chính xác.',
          'Allow browser microphone access, speak clearly, and wait for listening to stop. Review the transcript before accepting an action. Switch to text chat when exact correction is needed.',
        ),
      ),
      HelpStep(
        HelpText('Quản lý lịch sử', 'Manage conversation history'),
        HelpText(
          'Đặt tên hoặc mở lại phiên có nội dung liên quan. Xóa phiên không còn cần thiết, nhưng hãy chắc chắn rằng bạn không cần tra cứu lại nội dung trong phiên đó.',
          'Name or reopen relevant sessions. Delete sessions you no longer need, but first confirm that their content will not be needed later.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Hãy yêu cầu AI xác nhận lại tài liệu, người nhận và hành động trước những thao tác quan trọng.',
        'Ask AI to confirm the document, recipient, and intended action before important operations.',
      ),
    ],
    warning: HelpText(
      'Không nhập mật khẩu, khóa ký số, mã OTP hoặc bí mật truy cập vào cuộc trò chuyện.',
      'Never enter passwords, signing keys, OTP codes, or access secrets into the conversation.',
    ),
  ),
  HelpSectionData(
    id: 'signing',
    icon: Icons.workspace_premium_outlined,
    title: HelpText('Ký số', 'Digital signing'),
    summary: HelpText(
      'Theo dõi yêu cầu ký, mở tài liệu cần ký, kiểm tra PDF đã ký và xử lý hòm thư chuyển tiếp.',
      'Track signing requests, open items awaiting signature, review signed PDFs, and process forwarded mailbox items.',
    ),
    route: '/signing/tasks',
    prerequisites: [
      HelpText(
        'Khóa ký số và quyền ký phải được cấu hình cho tài khoản.',
        'A signing key and signing permission must be configured for the account.',
      ),
    ],
    steps: [
      HelpStep(
        HelpText('Mở Yêu cầu ký', 'Open signing requests'),
        HelpText(
          'Vào Ký số > Yêu cầu ký. Dùng các nhóm trạng thái để phân biệt yêu cầu sẵn sàng, đang chờ bước trước, đã ký hoặc bị từ chối.',
          'Go to Digital signing > Signing requests. Use status groups to distinguish ready, waiting, completed, and rejected requests.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra thông tin yêu cầu', 'Review request details'),
        HelpText(
          'Mở yêu cầu và đọc tên văn bản, người tạo, thứ tự ký, người nhận và ghi chú. Nếu tài liệu hoặc người ký không đúng, không tiếp tục ký.',
          'Open the request and review the document, creator, signing order, recipient, and notes. Stop if the document or signer is incorrect.',
        ),
      ),
      HelpStep(
        HelpText('Xem tài liệu trước khi ký', 'Review before signing'),
        HelpText(
          'Mở bản xem PDF và đọc các trang liên quan. Kiểm tra nội dung cuối, chữ ký trước đó và trạng thái toàn vẹn trước khi xác nhận.',
          'Open the PDF preview and review all relevant pages. Check final content, prior signatures, and integrity status before confirming.',
        ),
      ),
      HelpStep(
        HelpText('Thực hiện hoặc từ chối ký', 'Sign or reject'),
        HelpText(
          'Chỉ ký khi toàn bộ thông tin chính xác. Nếu từ chối, nhập lý do cụ thể để người gửi biết cần sửa gì. Không chia sẻ mật khẩu hoặc khóa ký cho người khác.',
          'Sign only when all information is correct. If rejecting, provide a specific reason so the sender knows what to fix. Never share signing credentials.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra PDF đã ký', 'Review signed PDFs'),
        HelpText(
          'Vào PDF đã ký để tìm bản hoàn tất. Mở chi tiết, kiểm tra người ký và trạng thái xác minh, sau đó tải file khi cần lưu hoặc gửi.',
          'Open Signed PDFs to find completed files. Review signers and verification status, then download when needed.',
        ),
      ),
      HelpStep(
        HelpText('Xử lý Hòm thư', 'Process mailbox items'),
        HelpText(
          'Mở Hòm thư để xem các luồng chuyển tiếp. Đọc timeline, mở bản PDF đúng phiên bản và chọn hoàn thành hoặc từ chối theo trách nhiệm của bạn.',
          'Open Mailbox to view forwarded workflows. Read the timeline, open the correct PDF version, and complete or reject the item according to your responsibility.',
        ),
      ),
      HelpStep(
        HelpText('Duyệt đề xuất ký', 'Review signing proposals'),
        HelpText(
          'Mở Duyệt đề xuất ký, kiểm tra người đề xuất, tài liệu, người ký và thứ tự ký. Chỉ phê duyệt khi toàn bộ thông tin phù hợp; nếu từ chối, ghi rõ nội dung cần sửa.',
          'Open Review signing proposals and verify the requester, document, signers, and signing order. Approve only when all details are correct; otherwise provide a specific rejection reason.',
        ),
        access: HelpAccess.signingProposalReviewer,
      ),
      HelpStep(
        HelpText('Dùng ủy quyền khi được phép', 'Use delegation when authorized'),
        HelpText(
          'Người quản lý được cấp quyền có thể tạo ủy quyền theo thời gian và phạm vi. Kiểm tra người được ủy quyền, ngày hiệu lực và bộ phận trước khi lưu.',
          'Authorized managers can create time-bound delegations. Verify the delegate, effective dates, and department before saving.',
        ),
        access: HelpAccess.signingDelegationManager,
      ),
    ],
    warning: HelpText(
      'Ký số là thao tác có giá trị nghiệp vụ. Luôn đọc tài liệu gốc và xác minh người nhận trước khi ký hoặc chuyển tiếp.',
      'Digital signing is a consequential business action. Always review the original document and verify recipients before signing or forwarding.',
    ),
  ),
  HelpSectionData(
    id: 'templates',
    icon: Icons.description_outlined,
    title: HelpText('Quản lý mẫu văn bản', 'Template management'),
    summary: HelpText(
      'Tạo, tải lên, chỉnh sửa, phân loại và chia sẻ các mẫu dùng để sinh văn bản.',
      'Create, upload, edit, categorize, and share templates used for document generation.',
    ),
    route: '/templates',
    videoAsset: 'assets/videos/template_management.mp4',
    steps: [
      HelpStep(
        HelpText('Chọn phạm vi danh sách', 'Choose a list scope'),
        HelpText(
          'Trong nhóm Quản lý mẫu văn bản, chọn Mẫu dùng chung, Mẫu phòng ban, Mẫu của tôi, Yêu thích hoặc Mẫu chia sẻ cho đồng nghiệp.',
          'Under Template management, choose Shared, Department, Private, Favorites, or Templates shared with me.',
        ),
      ),
      HelpStep(
        HelpText('Xem toàn bộ mẫu trong công ty', 'View all company templates'),
        HelpText(
          'Mở Tất cả (Admin) khi cần kiểm tra mẫu thuộc mọi người dùng và phòng ban. Dùng bộ lọc trước khi chỉnh sửa hoặc xóa để tránh tác động nhầm dữ liệu của đơn vị khác.',
          'Open All (Admin) to review templates across users and departments. Filter the list before editing or deleting to avoid affecting another team’s data.',
        ),
        access: HelpAccess.companyAdmin,
      ),
      HelpStep(
        HelpText('Tạo mẫu mới', 'Create a template'),
        HelpText(
          'Chọn Tạo mẫu văn bản. Bạn có thể bắt đầu nhanh, tải file Word, tạo thủ công hoặc tải nhiều mẫu tùy các lựa chọn đang hiển thị.',
          'Choose Create template. Depending on the available options, start quickly, upload a Word file, create manually, or upload multiple templates.',
        ),
      ),
      HelpStep(
        HelpText('Chuẩn bị biến trong mẫu', 'Prepare template variables'),
        HelpText(
          'Đánh dấu các vị trí cần điền bằng tên biến rõ nghĩa, ví dụ `ho_ten`, `ngay_ban_hanh`, `don_vi`. Tránh hai biến khác nghĩa nhưng có tên quá giống nhau.',
          'Mark fillable positions with clear variables such as `full_name`, `issue_date`, or `organization`. Avoid nearly identical names for fields with different meanings.',
        ),
      ),
      HelpStep(
        HelpText('Nhập thông tin mô tả', 'Add descriptive information'),
        HelpText(
          'Đặt tên mẫu dễ tìm, thêm mô tả, danh mục và tag. Những thông tin này giúp người dùng khác hiểu mẫu dùng cho việc gì trước khi mở.',
          'Use a searchable name and add a description, category, and tags. This helps other users understand the template before opening it.',
        ),
      ),
      HelpStep(
        HelpText('Chọn phạm vi chia sẻ', 'Choose visibility'),
        HelpText(
          'Chọn Riêng tư nếu chỉ bạn dùng, Phòng ban nếu dùng trong một nhóm, hoặc Công khai nếu dùng chung trong công ty. Một số lựa chọn có thể cần người có thẩm quyền duyệt.',
          'Choose Private for personal use, Department for a group, or Public for company-wide access. Some visibility choices may require approval.',
        ),
      ),
      HelpStep(
        HelpText('Xem trước và thử mẫu', 'Preview and test'),
        HelpText(
          'Mở chi tiết mẫu, xem trước bố cục và thử sinh một văn bản với dữ liệu mẫu. Kiểm tra các biến có được thay đúng vị trí và định dạng Word có được giữ lại.',
          'Open template details, preview the layout, and generate a test document. Confirm variables are replaced correctly and Word formatting is preserved.',
        ),
      ),
      HelpStep(
        HelpText('Chỉnh sửa hoặc chia sẻ', 'Edit or share'),
        HelpText(
          'Dùng Chỉnh sửa cho thông tin và nội dung hỗ trợ; dùng chỉnh sửa thủ công khi cần thay đổi trực tiếp file Word. Chỉ chia sẻ cho đúng người hoặc nhóm cần sử dụng.',
          'Use Edit for metadata and supported content changes; use manual editing for direct Word changes. Share only with the people or groups that need access.',
        ),
      ),
      HelpStep(
        HelpText('Xóa hoặc khôi phục', 'Delete or restore'),
        HelpText(
          'Xóa mẫu sẽ đưa mẫu vào Thùng rác nếu luồng hỗ trợ xóa mềm. Có thể khôi phục từ Thùng rác; xóa vĩnh viễn thì không thể hoàn tác.',
          'Deleting a template sends it to Trash when soft deletion is supported. Restore it from Trash if needed; permanent deletion cannot be undone.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Luôn tạo một văn bản thử trước khi đưa mẫu cho nhiều người sử dụng.',
        'Always generate a test document before releasing a template to many users.',
      ),
    ],
  ),
  HelpSectionData(
    id: 'documents',
    icon: Icons.folder_outlined,
    title: HelpText('Quản lý văn bản', 'Document management'),
    summary: HelpText(
      'Tìm kiếm, tải lên, xem, chỉnh sửa, chia sẻ, lưu trữ và xóa văn bản.',
      'Search, upload, review, edit, share, archive, and delete documents.',
    ),
    route: '/documents',
    videoAsset: 'assets/videos/document_management.mp4',
    steps: [
      HelpStep(
        HelpText('Chọn đúng danh sách', 'Choose the correct list'),
        HelpText(
          'Mở Văn bản của tôi, Văn bản trong nhóm, Văn bản công khai, Yêu thích, Văn bản được chia sẻ hoặc Đã lưu trữ. Mỗi mục chỉ hiển thị dữ liệu đúng phạm vi tương ứng.',
          'Open My documents, Group, Public, Favorites, Shared with me, or Archived. Each view shows only documents in that scope.',
        ),
      ),
      HelpStep(
        HelpText('Xem toàn bộ văn bản trong công ty', 'View all company documents'),
        HelpText(
          'Mở Tất cả (Admin) khi cần kiểm tra văn bản thuộc mọi người dùng và phòng ban. Lọc theo chủ sở hữu, trạng thái và phạm vi trước khi thực hiện thao tác quản trị.',
          'Open All (Admin) to review documents across users and departments. Filter by owner, status, and visibility before performing an administrative action.',
        ),
        access: HelpAccess.companyAdmin,
      ),
      HelpStep(
        HelpText('Tìm kiếm và lọc', 'Search and filter'),
        HelpText(
          'Nhập từ khóa theo tiêu đề hoặc nội dung. Dùng bộ lọc trạng thái, nguồn gốc, mức chia sẻ, chủ sở hữu và phòng ban để thu hẹp kết quả.',
          'Search by title or content. Use status, source, visibility, owner, and department filters to narrow the results.',
        ),
      ),
      HelpStep(
        HelpText('Tải văn bản Word lên', 'Upload a Word document'),
        HelpText(
          'Bấm Tải lên Word, chọn file và nhập tiêu đề bắt buộc. Chờ upload hoàn tất rồi mở văn bản để kiểm tra hệ thống đã đọc đúng nội dung.',
          'Click Upload Word, select a file, and enter the required title. Wait for upload to finish, then open the document to confirm its content was read correctly.',
        ),
      ),
      HelpStep(
        HelpText('Mở chi tiết', 'Open details'),
        HelpText(
          'Chọn một văn bản để xem nội dung, file, phiên bản, quyền chia sẻ và các thao tác liên quan. Luôn kiểm tra đúng phiên bản trước khi tải hoặc gửi ký.',
          'Open a document to review content, files, versions, sharing permissions, and related actions. Verify the correct version before downloading or signing.',
        ),
      ),
      HelpStep(
        HelpText('Chỉnh sửa văn bản', 'Edit a document'),
        HelpText(
          'Dùng trình chỉnh sửa thủ công khi cần thay đổi trực tiếp. Nếu dùng Word AI, nhập yêu cầu rõ ràng, bấm Check prompt, chạy tác vụ và kiểm tra lại kết quả trước khi chấp nhận phiên bản mới.',
          'Use manual editing for direct changes. For Word AI, enter a clear instruction, run Check prompt, execute the job, and review the result before accepting a new version.',
        ),
      ),
      HelpStep(
        HelpText('Chia sẻ đúng phạm vi', 'Share with the correct audience'),
        HelpText(
          'Mở bảng chia sẻ, chọn người hoặc nhóm và mức quyền phù hợp. Chỉ cấp quyền sửa khi người nhận thực sự cần thay đổi nội dung.',
          'Open the sharing panel, select people or groups, and assign the appropriate permission. Grant edit access only when the recipient must modify content.',
        ),
      ),
      HelpStep(
        HelpText('Đánh dấu yêu thích hoặc lưu trữ', 'Favorite or archive'),
        HelpText(
          'Dùng Yêu thích cho tài liệu thường xuyên sử dụng. Dùng Lưu trữ khi văn bản không còn hoạt động nhưng vẫn cần giữ để tra cứu.',
          'Favorite frequently used documents. Archive inactive documents that must remain available for reference.',
        ),
      ),
      HelpStep(
        HelpText('Xóa một hoặc nhiều văn bản', 'Delete one or multiple documents'),
        HelpText(
          'Chọn từng văn bản hoặc Chọn tất cả các mục đang hiển thị, sau đó bấm Xóa. Đọc kỹ số lượng trong hộp xác nhận để tránh xóa nhầm.',
          'Select individual documents or all visible items, then click Delete. Check the item count in the confirmation dialog to avoid deleting the wrong documents.',
        ),
      ),
    ],
    warning: HelpText(
      'Trước khi xóa hoặc thay thế file, hãy kiểm tra văn bản có đang nằm trong quy trình ký hoặc chia sẻ hay không.',
      'Before deleting or replacing a file, check whether it is involved in a signing or sharing workflow.',
    ),
  ),
  HelpSectionData(
    id: 'prompts',
    icon: Icons.bolt_outlined,
    title: HelpText('Quản lý prompt', 'Prompt management'),
    summary: HelpText(
      'Tạo, kiểm tra, phân loại, chia sẻ và quản lý các chỉ dẫn tái sử dụng cho AI.',
      'Create, validate, categorize, share, and manage reusable AI instructions.',
    ),
    route: '/prompts',
    videoAsset: 'assets/videos/prompt_management.mp4',
    steps: [
      HelpStep(
        HelpText('Chọn phạm vi prompt', 'Choose a prompt scope'),
        HelpText(
          'Dùng các mục Tất cả của tôi, Riêng tư, Phòng ban, Công khai hoặc Được chia sẻ để tìm prompt.',
          'Use All accessible, Private, Department, Public, or Shared with me to find prompts.',
        ),
      ),
      HelpStep(
        HelpText('Xem toàn bộ prompt trong công ty', 'View all company prompts'),
        HelpText(
          'Mở Tất cả (Admin) để kiểm tra prompt của mọi phạm vi. Xác nhận chủ sở hữu, trạng thái duyệt và chức năng sử dụng trước khi chỉnh sửa hoặc xóa.',
          'Open All (Admin) to review prompts from every scope. Verify the owner, approval status, and usage scope before editing or deleting.',
        ),
        access: HelpAccess.companyAdmin,
      ),
      HelpStep(
        HelpText('Tạo prompt mới', 'Create a prompt'),
        HelpText(
          'Bấm Tạo prompt mới và nhập tên dễ hiểu. Trong phần quy tắc, mô tả hành động AI phải thực hiện, đối tượng xử lý, yêu cầu đầu ra và điều kiện cần tránh.',
          'Click Create prompt and enter a clear name. In the rules, describe the requested action, target content, output requirements, and constraints.',
        ),
      ),
      HelpStep(
        HelpText('Viết prompt rõ ràng', 'Write a clear prompt'),
        HelpText(
          'Dùng câu mệnh lệnh cụ thể, ví dụ: “Viết lại đoạn được chọn theo văn phong trang trọng, giữ nguyên số liệu và tên riêng”. Tránh chuỗi ký tự vô nghĩa hoặc yêu cầu quá chung như “làm tốt hơn”.',
          'Use a specific instruction such as: “Rewrite the selected paragraph in a formal tone while preserving numbers and proper names.” Avoid random text or vague requests like “make it better.”',
        ),
      ),
      HelpStep(
        HelpText('Bấm Check prompt', 'Run Check prompt'),
        HelpText(
          'Bấm Check prompt trước khi lưu. Hệ thống kiểm tra nội dung vô nghĩa, mức liên quan và dấu hiệu prompt injection. Nếu không đạt, đọc lý do, sửa nội dung và kiểm tra lại.',
          'Click Check prompt before saving. The system checks meaning, relevance, and prompt-injection indicators. If blocked, read the reason, revise the content, and check again.',
        ),
      ),
      HelpStep(
        HelpText('Chọn phạm vi sử dụng', 'Choose usage scopes'),
        HelpText(
          'Đánh dấu đúng tính năng sẽ dùng prompt, chẳng hạn sinh văn bản, tóm tắt, Word AI hoặc compliance. Chọn sai phạm vi có thể khiến prompt không xuất hiện tại nơi bạn cần.',
          'Select the features where the prompt will be used, such as document generation, summaries, Word AI, or compliance. Incorrect scopes may hide the prompt from the intended feature.',
        ),
      ),
      HelpStep(
        HelpText('Chọn phạm vi chia sẻ', 'Choose visibility'),
        HelpText(
          'Dùng Riêng tư cho cá nhân, Phòng ban cho nhóm hoặc Công khai cho toàn công ty. Prompt được chia sẻ có thể phải qua quy trình duyệt trước khi người khác sử dụng.',
          'Use Private for yourself, Department for a group, or Public for the company. Shared prompts may require approval before others can use them.',
        ),
      ),
      HelpStep(
        HelpText('Theo dõi trạng thái', 'Track status'),
        HelpText(
          'Dùng bộ lọc trạng thái để xem prompt đã duyệt, đang chờ hoặc bị từ chối. Nếu bị từ chối, mở sửa, đọc lý do và gửi duyệt lại sau khi điều chỉnh.',
          'Filter by approved, pending, or rejected status. For rejected prompts, edit them according to the reason and submit again.',
        ),
      ),
      HelpStep(
        HelpText('Sửa hoặc xóa', 'Edit or delete'),
        HelpText(
          'Sau khi sửa nội dung, bạn bắt buộc Check prompt lại vì token cũ không còn khớp. Khi xóa, kiểm tra tên prompt trong hộp xác nhận; xóa hàng loạt cần kiểm tra số lượng đã chọn.',
          'After editing content, run Check prompt again because the previous token no longer matches. Before deleting, verify the prompt name and selected count.',
        ),
      ),
    ],
    tips: [
      HelpText(
        'Một prompt tốt thường gồm: hành động, nội dung mục tiêu, phong cách, định dạng đầu ra và điều không được thay đổi.',
        'A strong prompt usually includes the action, target content, style, output format, and elements that must remain unchanged.',
      ),
    ],
    warning: HelpText(
      'Không đưa mật khẩu, token truy cập, khóa bí mật hoặc dữ liệu cá nhân không cần thiết vào prompt dùng chung.',
      'Do not place passwords, access tokens, secrets, or unnecessary personal data in shared prompts.',
    ),
  ),
  HelpSectionData(
    id: 'trash',
    icon: Icons.delete_outline,
    title: HelpText('Thùng rác', 'Trash'),
    summary: HelpText(
      'Khôi phục mục đã xóa hoặc xóa vĩnh viễn khi chắc chắn không còn cần dữ liệu.',
      'Restore deleted items or permanently remove data only when it is no longer needed.',
    ),
    route: '/trash',
    steps: [
      HelpStep(
        HelpText('Chọn loại dữ liệu', 'Choose a category'),
        HelpText(
          'Mở Thùng rác và chọn loại dữ liệu như văn bản, mẫu, prompt hoặc mục khác đang hiển thị. Số cạnh mỗi loại cho biết số mục đã xóa.',
          'Open Trash and select a category such as documents, templates, prompts, or another displayed type. The count shows how many deleted items it contains.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra mục cần xử lý', 'Review the item'),
        HelpText(
          'Đọc tên, người tạo và thời gian xóa. Với tên gần giống nhau, kiểm tra thêm thông tin trước khi chọn.',
          'Review the name, creator, and deletion time. Check extra details when multiple items have similar names.',
        ),
      ),
      HelpStep(
        HelpText('Khôi phục', 'Restore'),
        HelpText(
          'Bấm Khôi phục tại một mục hoặc chọn nhiều mục rồi dùng nút khôi phục hàng loạt. Sau đó quay lại danh sách tương ứng để xác nhận dữ liệu đã xuất hiện.',
          'Restore a single item or select multiple items for bulk restoration. Return to the relevant list afterward to confirm the data is available.',
        ),
      ),
      HelpStep(
        HelpText('Xóa vĩnh viễn', 'Delete permanently'),
        HelpText(
          'Chỉ dùng khi chắc chắn dữ liệu không còn giá trị. Đọc kỹ hộp xác nhận vì thao tác xóa vĩnh viễn không thể hoàn tác.',
          'Use permanent deletion only when the data has no remaining value. Read the confirmation carefully because the action cannot be undone.',
        ),
      ),
    ],
    warning: HelpText(
      'Không xóa vĩnh viễn tài liệu đang liên quan đến ký số, kiểm toán, khiếu nại hoặc nghĩa vụ lưu trữ.',
      'Do not permanently delete records related to signing, audits, disputes, or retention obligations.',
    ),
  ),
  HelpSectionData(
    id: 'profile',
    icon: Icons.manage_accounts_outlined,
    title: HelpText('Hồ sơ cá nhân', 'Profile'),
    summary: HelpText(
      'Cập nhật thông tin cá nhân, chức danh, liên hệ, alias người nhận và mật khẩu.',
      'Update personal information, job details, contact data, recipient aliases, and password.',
    ),
    route: '/profile',
    steps: [
      HelpStep(
        HelpText('Mở chế độ chỉnh sửa', 'Open edit mode'),
        HelpText(
          'Mở Hồ sơ cá nhân, kiểm tra thông tin hiện tại rồi bấm Chỉnh sửa. Một số tài khoản có thể được yêu cầu đổi mật khẩu ngay sau lần đăng nhập đầu.',
          'Open Profile, review the current information, and click Edit. Some accounts may be required to change their password after first sign-in.',
        ),
      ),
      HelpStep(
        HelpText('Cập nhật thông tin', 'Update information'),
        HelpText(
          'Nhập họ tên, email, chức danh, mã nhân viên, số điện thoại, địa chỉ và ngày sinh theo dữ liệu chính xác. Các trường này có thể được dùng để tự động điền văn bản.',
          'Enter accurate name, email, title, employee number, phone, address, and birth date. These fields may be used for automatic document filling.',
        ),
      ),
      HelpStep(
        HelpText('Quản lý alias người nhận', 'Manage recipient aliases'),
        HelpText(
          'Thêm các cách gọi mà Chat AI có thể dùng để tìm bạn, ví dụ tên thường gọi hoặc chức danh. Chỉ đặt một alias chính và tránh alias quá chung.',
          'Add names that AI Chat may use to find you, such as a common name or title. Keep one primary alias and avoid overly generic aliases.',
        ),
      ),
      HelpStep(
        HelpText('Đổi mật khẩu', 'Change password'),
        HelpText(
          'Nhập mật khẩu mới và nhập lại chính xác. Dùng mật khẩu riêng cho hệ thống này, không gửi mật khẩu qua chat hoặc email.',
          'Enter and confirm the new password. Use a unique password for this system and never send it through chat or email.',
        ),
      ),
      HelpStep(
        HelpText('Lưu và kiểm tra', 'Save and verify'),
        HelpText(
          'Bấm Lưu, chờ thông báo thành công rồi mở lại hồ sơ để kiểm tra. Sau đó có thể thử Điền từ hồ sơ trong chức năng Sinh văn bản từ mẫu.',
          'Click Save, wait for confirmation, and reopen the profile to verify. You can then test Fill from profile in document generation.',
        ),
      ),
    ],
  ),
  HelpSectionData(
    id: 'approvals',
    icon: Icons.share_outlined,
    title: HelpText('Phê duyệt chia sẻ', 'Share approvals'),
    summary: HelpText(
      'Xem và quyết định các yêu cầu chia sẻ đang chờ tài khoản của bạn phê duyệt.',
      'Review and decide sharing requests awaiting your approval.',
    ),
    route: '/sharing/pending',
    access: HelpAccess.shareApprover,
    steps: [
      HelpStep(
        HelpText('Mở danh sách chờ duyệt', 'Open pending approvals'),
        HelpText(
          'Mở Chia sẻ chờ duyệt. Badge trên thanh điều hướng cho biết số yêu cầu chưa được xử lý hoặc chưa được bạn đọc.',
          'Open Share approvals. The navigation badge shows requests that remain unread or unprocessed.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra người gửi và đối tượng', 'Review requester and item'),
        HelpText(
          'Đọc người yêu cầu, loại dữ liệu, phạm vi chia sẻ, người nhận và mức quyền. Mở đối tượng gốc nếu cần xác minh nội dung.',
          'Review the requester, item type, visibility, recipients, and requested permission. Open the original item when verification is needed.',
        ),
      ),
      HelpStep(
        HelpText('Phê duyệt hoặc từ chối', 'Approve or reject'),
        HelpText(
          'Phê duyệt khi phạm vi và quyền phù hợp. Nếu từ chối, nhập lý do cụ thể để người gửi có thể sửa và gửi lại.',
          'Approve only when visibility and permission are appropriate. Provide a specific reason when rejecting so the requester can correct and resubmit.',
        ),
      ),
    ],
  ),
  HelpSectionData(
    id: 'ai-settings',
    icon: Icons.psychology_outlined,
    title: HelpText('Cấu hình AI', 'AI settings'),
    summary: HelpText(
      'Cấu hình model, tham số tìm kiếm và ngữ cảnh công ty. Chỉ quản trị viên được phép thay đổi.',
      'Configure models, retrieval parameters, and company context. Only administrators may change these settings.',
    ),
    route: '/admin/ai-config',
    access: HelpAccess.companyAdmin,
    steps: [
      HelpStep(
        HelpText('Đọc cấu hình hiện tại', 'Review current settings'),
        HelpText(
          'Mở Cấu hình AI và ghi lại model, nhiệt độ, số kết quả RAG và nguồn Internet đang dùng trước khi thay đổi.',
          'Open AI settings and note the current model, temperature, RAG result count, and Internet source before making changes.',
        ),
      ),
      HelpStep(
        HelpText('Chỉnh sửa có kiểm soát', 'Edit carefully'),
        HelpText(
          'Bấm Chỉnh sửa, chỉ thay đổi tham số đã hiểu rõ. Nhiệt độ cao làm câu trả lời đa dạng hơn nhưng khó lặp lại; số kết quả lớn có thể tăng thời gian và chi phí.',
          'Click Edit and change only settings you understand. Higher temperature increases variation but reduces repeatability; more results may increase latency and cost.',
        ),
      ),
      HelpStep(
        HelpText('Cấu hình model Chat AI', 'Configure the AI Chat model'),
        HelpText(
          'Chọn model phù hợp trong danh sách và lưu riêng phần Chat AI nếu giao diện yêu cầu. Thử một câu hỏi không nhạy cảm sau khi đổi model.',
          'Select an appropriate model and save the AI Chat section separately when required. Test it with a non-sensitive question afterward.',
        ),
      ),
      HelpStep(
        HelpText('Cập nhật ngữ cảnh công ty', 'Update company context'),
        HelpText(
          'Nhập thông tin ổn định như tên công ty, đơn vị, quy ước và cách xưng hô. Không nhập mật khẩu, khóa API hoặc bí mật kỹ thuật.',
          'Enter stable information such as company name, departments, conventions, and preferred terminology. Never enter passwords, API keys, or technical secrets.',
        ),
      ),
      HelpStep(
        HelpText('Lưu và kiểm thử', 'Save and test'),
        HelpText(
          'Lưu từng phần, sau đó kiểm tra Chat AI, hỏi đáp và sinh văn bản với dữ liệu thử. Nếu kết quả bất thường, khôi phục giá trị trước đó.',
          'Save each section, then test AI Chat, Q&A, and document generation with sample data. Restore previous values if behavior becomes abnormal.',
        ),
      ),
    ],
    warning: HelpText(
      'Thay đổi model hoặc ngữ cảnh công ty ảnh hưởng nhiều người dùng. Nên ghi lại cấu hình trước và sau khi thay đổi.',
      'Model and company-context changes affect many users. Record configuration values before and after each change.',
    ),
  ),
  HelpSectionData(
    id: 'accounts',
    icon: Icons.admin_panel_settings_outlined,
    title: HelpText('Tài khoản, phòng ban và nhóm', 'Accounts and departments'),
    summary: HelpText(
      'Quản lý người dùng, vai trò, phòng ban, nhóm và phạm vi quyền trong công ty.',
      'Manage users, roles, departments, groups, and company permissions.',
    ),
    route: '/admin',
    access: HelpAccess.companyAdmin,
    steps: [
      HelpStep(
        HelpText('Chọn loại dữ liệu quản trị', 'Choose an administration area'),
        HelpText(
          'Mở trang quản trị và chọn tab người dùng, phòng ban hoặc nhóm phù hợp. Tìm kiếm trước khi tạo mới để tránh bản ghi trùng.',
          'Open administration and select the users, departments, or groups area. Search before creating a new record to avoid duplicates.',
        ),
      ),
      HelpStep(
        HelpText('Tạo hoặc sửa người dùng', 'Create or edit a user'),
        HelpText(
          'Nhập tài khoản, email và thông tin bắt buộc. Chỉ bật quyền Staff hoặc Superuser cho người thực sự chịu trách nhiệm quản trị.',
          'Enter the username, email, and required information. Grant Staff or Superuser only to users responsible for administration.',
        ),
      ),
      HelpStep(
        HelpText('Tạo phòng ban hoặc nhóm', 'Create a department or group'),
        HelpText(
          'Đặt tên rõ ràng, thêm mô tả và chọn thành viên. Kiểm tra nhóm có đang được dùng để chia sẻ mẫu, văn bản hoặc prompt trước khi sửa lớn.',
          'Use a clear name, add a description, and select members. Check whether the group is used for templates, documents, or prompt sharing before major changes.',
        ),
      ),
      HelpStep(
        HelpText('Xóa có kiểm tra', 'Delete carefully'),
        HelpText(
          'Trước khi xóa người dùng hoặc nhóm, chuyển giao dữ liệu và trách nhiệm liên quan. Đọc thông báo lỗi nếu hệ thống chặn do còn quan hệ dữ liệu.',
          'Before deleting a user or group, transfer related data and responsibilities. Read any blocking message when dependencies still exist.',
        ),
      ),
    ],
    warning: HelpText(
      'Không cấp quyền quản trị chỉ để giải quyết tạm thời một lỗi truy cập. Hãy cấp đúng quyền nghiệp vụ cần thiết.',
      'Do not grant administrator access as a temporary workaround for access problems. Assign only the required business permission.',
    ),
  ),
  HelpSectionData(
    id: 'backup',
    icon: Icons.cloud_download_outlined,
    title: HelpText('Sao lưu dữ liệu', 'Data backup'),
    summary: HelpText(
      'Tạo, tải, kiểm tra chữ ký, khôi phục và cấu hình sao lưu tự động cho dữ liệu công ty.',
      'Create, download, verify, restore, and schedule company backups.',
    ),
    route: '/admin/backups',
    access: HelpAccess.companyAdmin,
    steps: [
      HelpStep(
        HelpText('Thiết lập mật khẩu backup', 'Set the backup password'),
        HelpText(
          'Nếu hệ thống yêu cầu, đặt mật khẩu backup đủ mạnh và lưu ở nơi quản lý bí mật của công ty. Mật khẩu này dùng để xác nhận các thao tác quan trọng.',
          'When required, set a strong backup password and store it in the company password manager. It confirms sensitive backup actions.',
        ),
      ),
      HelpStep(
        HelpText('Chọn thành phần sao lưu', 'Select components'),
        HelpText(
          'Ở tab Tạo backup, chọn các thành phần cần lưu hoặc Chọn tất cả. Với bản sao lưu định kỳ quan trọng, nên sao lưu toàn bộ để giữ quan hệ dữ liệu.',
          'On Create backup, select the required components or choose all. For important scheduled backups, include everything to preserve data relationships.',
        ),
      ),
      HelpStep(
        HelpText('Tạo và tải bản backup', 'Create and download'),
        HelpText(
          'Bấm Tạo backup và chờ trạng thái hoàn tất. Sau đó tải file về nơi lưu trữ an toàn, có kiểm soát quyền truy cập và có bản sao dự phòng.',
          'Create the backup and wait until it completes. Download it to secure storage with controlled access and redundancy.',
        ),
      ),
      HelpStep(
        HelpText('Kiểm tra chữ ký', 'Verify the signature'),
        HelpText(
          'Dùng Kiểm tra chữ ký trước khi khôi phục hoặc chuyển file. Nếu chữ ký không hợp lệ, không sử dụng bản backup đó và điều tra nguồn file.',
          'Verify the signature before restoring or transferring a file. Do not use a backup with an invalid signature; investigate its source.',
        ),
      ),
      HelpStep(
        HelpText('Khôi phục dữ liệu', 'Restore data'),
        HelpText(
          'Chỉ khôi phục khi đã hiểu dữ liệu nào sẽ bị ảnh hưởng. Đọc cảnh báo, nhập mật khẩu xác nhận và thực hiện trong thời gian bảo trì nếu dữ liệu đang được nhiều người sử dụng.',
          'Restore only after understanding affected data. Read warnings, enter the confirmation password, and use a maintenance window when users are active.',
        ),
      ),
      HelpStep(
        HelpText('Cấu hình backup tự động', 'Configure automatic backups'),
        HelpText(
          'Bật backup tự động, chọn chu kỳ và số bản giữ lại. Lưu cấu hình rồi kiểm tra thời gian chạy gần nhất để chắc chắn lịch đang hoạt động.',
          'Enable automatic backups, choose the interval and retention count, save, and verify the latest run time.',
        ),
      ),
    ],
    warning: HelpText(
      'Khôi phục backup có thể thay đổi lượng lớn dữ liệu. Luôn tạo một bản backup mới trước khi restore và giới hạn quyền thao tác.',
      'A restore can change large amounts of data. Create a fresh backup first and restrict restore permission.',
    ),
  ),
];
