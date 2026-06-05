import 'package:shared_preferences/shared_preferences.dart';

class PreferencesHelper {
  const PreferencesHelper._();

  static bool getBool(
    SharedPreferences preferences,
    String key, {
    bool defaultValue = false,
  }) {
    return preferences.getBool(key) ?? defaultValue;
  }

  static Future<void> setBool(
    SharedPreferences preferences,
    String key,
    bool value,
  ) {
    return preferences.setBool(key, value);
  }
}
