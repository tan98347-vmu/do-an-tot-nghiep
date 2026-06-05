import 'dart:html' as html;

html.EventListener? _beforeUnloadListener;

/// Khi `enabled = true`, dang ky listener `beforeunload` de trinh duyet hien
/// hop thoai canh bao truoc khi dong tab / reload. Khi `false`, go listener.
void setBeforeUnloadGuard(bool enabled) {
  if (enabled) {
    if (_beforeUnloadListener != null) {
      return;
    }
    _beforeUnloadListener = (html.Event event) {
      if (event is html.BeforeUnloadEvent) {
        // Chuoi tra ve khong duoc cac trinh duyet hien dai hien thi, nhung
        // viec set returnValue se kich hoat hop thoai canh bao mac dinh.
        event.returnValue = 'Ban co thay doi chua luu.';
      }
    };
    html.window.addEventListener('beforeunload', _beforeUnloadListener!);
  } else {
    if (_beforeUnloadListener == null) {
      return;
    }
    html.window.removeEventListener('beforeunload', _beforeUnloadListener!);
    _beforeUnloadListener = null;
  }
}
