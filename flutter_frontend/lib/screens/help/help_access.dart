// === CHÍNH SÁCH QUYỀN XEM TRỢ GIÚP ===
// HelpAccessPolicy.allows(...) quyết định một user có được xem một mục Trợ giúp hay không (theo vai trò/tính năng được bật).
// Dùng bởi help_screen để ẩn/chuyển hướng các mục mà user không có quyền.

import '../../models/signing.dart';
import '../../models/user.dart';

enum HelpAccess {
  standard,
  shareApprover,
  companyAdmin,
  signingProposalReviewer,
  signingDelegationManager,
}

class HelpAccessPolicy {
  final AppUser? user;
  final SigningSummary? signingSummary;

  const HelpAccessPolicy({
    required this.user,
    required this.signingSummary,
  });

  bool allows(HelpAccess access) {
    return switch (access) {
      HelpAccess.standard => user != null,
      HelpAccess.shareApprover => user?.canApprovePending == true,
      HelpAccess.companyAdmin => user?.canAccessAdminArea == true,
      HelpAccess.signingProposalReviewer =>
        signingSummary?.canReviewProposals == true,
      HelpAccess.signingDelegationManager =>
        signingSummary?.canManageHrDelegations == true ||
            signingSummary?.canManageAccountingDelegations == true,
    };
  }
}
