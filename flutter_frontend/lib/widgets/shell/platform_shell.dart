import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../platform/platform_admin_password_dialog.dart';

class PlatformShell extends ConsumerWidget {
  final Widget child;

  const PlatformShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isWide = MediaQuery.of(context).size.width >= 1000;
    final nav = const _PlatformNav();

    if (isWide) {
      return Scaffold(
        body: Row(
          children: [
            SizedBox(width: 288, child: nav),
            Expanded(child: child),
          ],
        ),
      );
    }

    return Scaffold(
      drawer: Drawer(child: nav),
      appBar: AppBar(
      ),
      body: child,
    );
  }
}

class _PlatformNav extends ConsumerWidget {
  const _PlatformNav();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final strings = AppStrings.of(context);
    final location = GoRouterState.of(context).matchedLocation;

    Widget navTile(
      String label,
      IconData icon,
      String route,
    ) {
      final active = route == '/platform/companies'
          ? location == route
          : location == route || location.startsWith('$route/');
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        child: Material(
          color: active
              ? Colors.white.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => context.go(route),
            hoverColor: Colors.white.withValues(alpha: 0.08),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  Icon(icon,
                      size: 18, color: active ? Colors.white : Colors.white54),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight:
                            active ? FontWeight.w700 : FontWeight.normal,
                        color: active ? Colors.white : Colors.white70,
                      ),
                    ),
                  ),
                  if (active)
                    Container(
                      width: 4,
                      height: 4,
                      decoration: const BoxDecoration(
                        color: Color(0xFF60A5FA),
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    // Tile chay mot hanh dong (vd: mo hop thoai) thay vi dieu huong route.
    Widget actionTile(String label, IconData icon, VoidCallback onTap) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: onTap,
            hoverColor: Colors.white.withValues(alpha: 0.08),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  Icon(icon, size: 18, color: Colors.white54),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      label,
                      style: const TextStyle(
                        fontSize: 13.5,
                        color: Colors.white70,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    Widget sectionLabel(String text) => Padding(
          padding: const EdgeInsets.only(left: 16, top: 14, bottom: 2),
          child: Text(
            text.toUpperCase(),
            style: const TextStyle(
              color: Colors.white30,
              fontSize: 9.5,
              letterSpacing: 1.3,
              fontWeight: FontWeight.w700,
            ),
          ),
        );

    Future<void> logout() async {
      final ok = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(strings.pick('Đăng xuất', 'Sign out')),
          content: Text(
            strings.pick(
              'Bạn có muốn đăng xuất khỏi khu quản trị công ty không?',
              'Do you want to sign out of company administration?',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(strings.pick('Hủy', 'Cancel')),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(strings.pick('Đăng xuất', 'Sign out')),
            ),
          ],
        ),
      );
      if (ok == true) {
        await ref.read(authProvider.notifier).logout();
      }
    }

    return Material(
      color: const Color(0xFF0F172A),
      child: Column(
        children: [
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                sectionLabel(strings.pick('Nen tang', 'Platform')),
                navTile(
                  strings.pick('Quan ly cong ty', 'Manage companies'),
                  Icons.business_outlined,
                  '/platform/companies',
                ),
                navTile(
                  strings.pick('Thung rac cong ty', 'Company trash'),
                  Icons.delete_outline,
                  '/platform/companies/trash',
                ),
                sectionLabel(strings.pick('Tai khoan', 'Account')),
                actionTile(
                  strings.pick('Doi mat khau', 'Change password'),
                  Icons.lock_outline,
                  () => showPlatformAdminChangePasswordDialog(context),
                ),
              ],
            ),
          ),
          if (user != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Colors.white12)),
                color: Color(0xFF0A0F1E),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 17,
                    backgroundColor: const Color(0xFF3B82F6),
                    child: Text(
                      (user.fullName.isNotEmpty
                              ? user.fullName[0]
                              : user.username[0])
                          .toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          user.fullName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          user.roleLabel,
                          style: const TextStyle(
                              color: Colors.white38, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.logout,
                        color: Colors.white38, size: 18),
                    onPressed: logout,
                    tooltip: strings.pick('Đăng xuất', 'Sign out'),
                    splashRadius: 18,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
