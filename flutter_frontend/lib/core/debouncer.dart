import 'dart:async';

class Debouncer {
  Timer? _timer;

  void run(Duration delay, void Function() action) {
    _timer?.cancel();
    _timer = Timer(delay, action);
  }

  void cancel() {
    _timer?.cancel();
    _timer = null;
  }
}
