import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Counter theo doi so popup/dialog dang mo can iframe phai an tam.
///
/// Flutter Web: HtmlElementView (iframe PDF/noi dung) chiem stacking context rieng,
/// se de LEN overlay/dialog cua Flutter -> nguoi dung khong tuong tac duoc voi
/// dialog/popup. Giai phap: khi co popup mo thi TAM AN iframe (thay bang placeholder),
/// dong popup thi hien lai. Counter ho tro nhieu popup long nhau.
final ValueNotifier<int> iframeBlockerCount = ValueNotifier<int>(0);

void pushIframeBlocker() {
  iframeBlockerCount.value = iframeBlockerCount.value + 1;
}

void popIframeBlocker() {
  final v = iframeBlockerCount.value;
  iframeBlockerCount.value = v > 0 ? v - 1 : 0;
}

/// Bao quanh mot iframe/HtmlElementView: tu dong an (thay bang placeholder) khi
/// co popup/dialog dang mo (iframeBlockerCount > 0). Dung chung cho moi noi
/// hien Noi dung mau / noi dung van ban / PDF preview.
class IframeBlocker extends StatelessWidget {
  final Widget child;
  final double placeholderHeight;
  final String message;

  const IframeBlocker({
    super.key,
    required this.child,
    this.placeholderHeight = 240,
    this.message =
        'Xem trước tạm ẩn để hộp thoại hiển thị đầy đủ.\nĐóng hộp thoại để xem lại.',
  });

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: iframeBlockerCount,
      builder: (_, count, __) {
        if (count > 0) {
          return Container(
            height: placeholderHeight,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.visibility_off_outlined,
                    size: 36, color: Colors.blueGrey),
                const SizedBox(height: 8),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: Colors.blueGrey),
                ),
              ],
            ),
          );
        }
        return child;
      },
    );
  }
}

/// NavigatorObserver tu dong tam an iframe khi BAT KY popup/dialog nao mo
/// (DialogRoute, ModalBottomSheetRoute, PopupMenuRoute, DropdownRoute... deu la
/// PopupRoute) va hien lai khi popup dong. Dang ky cho ca root navigator (GoRouter)
/// lan cac ShellRoute navigator.
class IframeBlockerObserver extends NavigatorObserver {
  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route is PopupRoute) pushIframeBlocker();
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route is PopupRoute) popIframeBlocker();
  }

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (route is PopupRoute) popIframeBlocker();
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    if (oldRoute is PopupRoute) popIframeBlocker();
    if (newRoute is PopupRoute) pushIframeBlocker();
  }
}
