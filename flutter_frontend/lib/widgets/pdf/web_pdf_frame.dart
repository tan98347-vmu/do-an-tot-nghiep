// Tệp này dùng để: đóng gói khối giao diện hoặc hành vi lặp lại trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác.

import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import '../../core/iframe_blocker.dart';

final Set<String> _registeredPdfViews = <String>{};
final Set<String> _registeredPdfDebugListeners = <String>{};
final Map<String, html.IFrameElement> _pdfFramesByViewKey = <String, html.IFrameElement>{};
final Map<String, String> _pdfUrlsByViewKey = <String, String>{};

// Mục đích: Hàm `_pdfDebugLog` triển khai phần việc `pdf Debug Log` trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

void _pdfDebugLog(String stage, {required String viewKey, required String pdfUrl, html.IFrameElement? frame}) {
  debugPrint(
    '[web_pdf_frame] $stage | view_key=$viewKey | pdf_url=$pdfUrl | frame_src=${frame?.src ?? ''}',
  );
}

// Mục đích: Hàm `_pdfViewerUrl` triển khai phần việc `pdf Viewer Url` trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

String _pdfViewerUrl(String pdfUrl) {
  return '$pdfUrl#toolbar=0&navpanes=0&view=FitH';
}

// Mục đích: Hàm `_attachPdfDebugListeners` triển khai phần việc `attach Pdf Debug Listeners` trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

void _attachPdfDebugListeners({
  required String viewKey,
  required String pdfUrl,
  required html.IFrameElement frame,
}) {
  if (!_registeredPdfDebugListeners.add(viewKey)) return;
  frame.onLoad.listen((_) {
    _pdfDebugLog('iframe_load', viewKey: viewKey, pdfUrl: pdfUrl, frame: frame);
  });
}

// Mục đích: Lớp `WebPdfFrame` triển khai phần việc `Web Pdf Frame` trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class WebPdfFrame extends StatelessWidget {
  final String viewKey;
  final String pdfUrl;
  final bool interactive;
  final ValueChanged<html.IFrameElement>? onFrameReady;

  const WebPdfFrame({
    super.key,
    required this.viewKey,
    required this.pdfUrl,
    this.interactive = true,
    this.onFrameReady,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/pdf/web_pdf_frame.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    if (_registeredPdfViews.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        final viewerUrl = _pdfViewerUrl(pdfUrl);
        final frame = html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.pointerEvents = interactive ? 'auto' : 'none'
          ..src = viewerUrl;
        _pdfDebugLog('register', viewKey: viewKey, pdfUrl: pdfUrl, frame: frame);
        _attachPdfDebugListeners(viewKey: viewKey, pdfUrl: pdfUrl, frame: frame);
        _pdfFramesByViewKey[viewKey] = frame;
        _pdfUrlsByViewKey[viewKey] = pdfUrl;
        onFrameReady?.call(frame);
        return frame;
      });
    }
    final existingFrame = _pdfFramesByViewKey[viewKey];
    if (existingFrame != null) {
      existingFrame.style.pointerEvents = interactive ? 'auto' : 'none';
      if (_pdfUrlsByViewKey[viewKey] != pdfUrl) {
        existingFrame.src = _pdfViewerUrl(pdfUrl);
        _pdfUrlsByViewKey[viewKey] = pdfUrl;
        _pdfDebugLog('update_src', viewKey: viewKey, pdfUrl: pdfUrl, frame: existingFrame);
      }
      onFrameReady?.call(existingFrame);
    }
    return IframeBlocker(child: HtmlElementView(viewType: viewKey));
  }
}
