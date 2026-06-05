class UserAlias {
  final int id;
  final String alias;
  final bool isPrimaryHint;

  const UserAlias({
    required this.id,
    required this.alias,
    required this.isPrimaryHint,
  });

  factory UserAlias.fromJson(Map<String, dynamic> json) => UserAlias(
        id: json['id'] as int? ?? 0,
        alias: json['alias'] as String? ?? '',
        isPrimaryHint: json['is_primary_hint'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'alias': alias,
        'is_primary_hint': isPrimaryHint,
      };
}

class UserProfile {
  final String? bio;
  final String? chucDanh;
  final String? cccd;
  final String? ngaySinh;
  final int? ageYears;
  final String? maNhanVien;
  final String? soDienThoai;
  final String? diaChi;
  final String? soYeuLyLich;
  final List<UserAlias> aliases;

  const UserProfile({
    this.bio,
    this.chucDanh,
    this.cccd,
    this.ngaySinh,
    this.ageYears,
    this.maNhanVien,
    this.soDienThoai,
    this.diaChi,
    this.soYeuLyLich,
    this.aliases = const [],
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        bio: json['bio'] as String?,
        chucDanh: json['chuc_danh'] as String?,
        cccd: json['cccd'] as String?,
        ngaySinh: json['ngay_sinh'] as String?,
        ageYears: json['age_years'] as int?,
        maNhanVien: json['ma_nhan_vien'] as String?,
        soDienThoai: json['so_dien_thoai'] as String?,
        diaChi: json['dia_chi'] as String?,
        soYeuLyLich: json['so_yeu_ly_lich'] as String?,
        aliases: (json['aliases'] as List<dynamic>? ?? const [])
            .map((item) =>
                UserAlias.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList(),
      );
}

class UserSigningCredential {
  final int id;
  final String provider;
  final String keyAlias;
  final String keyId;
  final String subjectDn;
  final String serialNumber;
  final String issuerDn;
  final String validFrom;
  final String validTo;
  final String status;
  final String fingerprintSha256;

  const UserSigningCredential({
    required this.id,
    required this.provider,
    required this.keyAlias,
    required this.keyId,
    required this.subjectDn,
    required this.serialNumber,
    required this.issuerDn,
    required this.validFrom,
    required this.validTo,
    required this.status,
    required this.fingerprintSha256,
  });

  factory UserSigningCredential.fromJson(Map<String, dynamic> json) =>
      UserSigningCredential(
        id: json['id'] as int? ?? 0,
        provider: json['provider'] as String? ?? '',
        keyAlias: json['key_alias'] as String? ?? '',
        keyId: json['key_id'] as String? ?? '',
        subjectDn: json['subject_dn'] as String? ?? '',
        serialNumber: json['serial_number'] as String? ?? '',
        issuerDn: json['issuer_dn'] as String? ?? '',
        validFrom: json['valid_from'] as String? ?? '',
        validTo: json['valid_to'] as String? ?? '',
        status: json['status'] as String? ?? '',
        fingerprintSha256: json['fingerprint_sha256'] as String? ?? '',
      );
}

class UserGroupMembership {
  final int id;
  final String name;
  final String role;

  const UserGroupMembership({
    required this.id,
    required this.name,
    required this.role,
  });

  bool get isLeader => role == 'leader';

  factory UserGroupMembership.fromJson(Map<String, dynamic> json) =>
      UserGroupMembership(
        id: json['id'] as int? ?? 0,
        name: json['name'] as String? ?? '',
        role: json['role'] as String? ?? 'member',
      );
}

class CompanySummary {
  final int id;
  final String code;
  final String slug;
  final String name;
  final String status;

  const CompanySummary({
    required this.id,
    required this.code,
    required this.slug,
    required this.name,
    required this.status,
  });

  factory CompanySummary.fromJson(Map<String, dynamic> json) => CompanySummary(
        id: json['id'] as int? ?? 0,
        code: json['code'] as String? ?? '',
        slug: json['slug'] as String? ?? '',
        name: json['name'] as String? ?? '',
        status: json['status'] as String? ?? '',
      );
}

class AppUser {
  final int id;
  final String username;
  final String technicalUsername;
  final String email;
  final String firstName;
  final String lastName;
  final String fullName;
  final bool isStaff;
  final bool isSuperuser;
  final bool isPlatformAdmin;
  final bool isCompanyAdmin;
  final String? companyRole;
  final bool mustChangePassword;
  final CompanySummary? company;
  final UserProfile? profile;
  final List<UserGroupMembership> groups;
  final List<UserSigningCredential> signingCredentials;

  const AppUser({
    required this.id,
    required this.username,
    required this.technicalUsername,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.isStaff,
    required this.isSuperuser,
    required this.isPlatformAdmin,
    required this.isCompanyAdmin,
    required this.companyRole,
    required this.mustChangePassword,
    required this.company,
    required this.profile,
    this.groups = const [],
    this.signingCredentials = const [],
  });

  bool get isLeaderOfAny => groups.any((group) => group.isLeader);
  bool isLeaderOf(int groupId) =>
      groups.any((group) => group.id == groupId && group.isLeader);
  bool get canApprovePending => isCompanyAdmin || isLeaderOfAny;
  bool get canAccessAdminArea => isCompanyAdmin;
  bool get canAccessPlatformArea => isPlatformAdmin;

  String get roleLabel {
    if (isPlatformAdmin) return 'Quan tri nen tang';
    if (isCompanyAdmin) return 'Admin cong ty';
    if (isLeaderOfAny) return 'Truong nhom';
    if (isStaff) return 'Nhan vien QT';
    return 'Nguoi dung';
  }

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int? ?? 0,
        username: json['username'] as String? ?? '',
        technicalUsername: json['technical_username'] as String? ??
            json['username'] as String? ??
            '',
        email: json['email'] as String? ?? '',
        firstName: json['first_name'] as String? ?? '',
        lastName: json['last_name'] as String? ?? '',
        fullName:
            json['full_name'] as String? ?? json['username'] as String? ?? '',
        isStaff: json['is_staff'] as bool? ?? false,
        isSuperuser: json['is_superuser'] as bool? ?? false,
        isPlatformAdmin: json['is_platform_admin'] as bool? ?? false,
        isCompanyAdmin: json['is_company_admin'] as bool? ?? false,
        companyRole: json['company_role'] as String?,
        mustChangePassword: json['must_change_password'] as bool? ?? false,
        company: json['company'] is Map<String, dynamic>
            ? CompanySummary.fromJson(
                Map<String, dynamic>.from(json['company'] as Map))
            : null,
        profile: json['profile'] is Map<String, dynamic>
            ? UserProfile.fromJson(
                Map<String, dynamic>.from(json['profile'] as Map))
            : null,
        groups: (json['groups'] as List<dynamic>? ?? const [])
            .map((item) => UserGroupMembership.fromJson(
                Map<String, dynamic>.from(item as Map)))
            .toList(),
        signingCredentials:
            (json['signing_credentials'] as List<dynamic>? ?? const [])
                .map((item) => UserSigningCredential.fromJson(
                    Map<String, dynamic>.from(item as Map)))
                .toList(),
      );
}
