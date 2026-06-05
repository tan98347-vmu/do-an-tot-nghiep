/// Bat/tat canh bao cua trinh duyet khi nguoi dung dong tab / reload trong khi
/// con thay doi chua luu. Tren nen tang khong phai web, ham nay khong lam gi.
export 'beforeunload_guard_stub.dart'
    if (dart.library.html) 'beforeunload_guard_web.dart';
