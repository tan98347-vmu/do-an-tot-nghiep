from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from accounts.identity_normalization import normalize_lookup_value
from accounts.models import CompanyUserMembership, UserAlias, UserGroupMembership, UserProfile
from accounts.tenancy import get_user_company, get_user_membership, is_company_admin, is_platform_admin
from signing.models import UserSigningCredential


class UserAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAlias
        fields = (
            'id',
            'alias',
            'is_primary_hint',
        )
        read_only_fields = ('id',)


class UserProfileSerializer(serializers.ModelSerializer):
    aliases = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            'avatar',
            'bio',
            'chuc_danh',
            'cccd',
            'ngay_sinh',
            'age_years',
            'ma_nhan_vien',
            'so_dien_thoai',
            'dia_chi',
            'so_yeu_ly_lich',
            'aliases',
        )

    def get_aliases(self, obj):
        aliases = obj.user.aliases.order_by('-is_primary_hint', 'alias', 'id')
        return UserAliasSerializer(aliases, many=True).data


class UserSigningCredentialSerializer(serializers.ModelSerializer):
    fingerprint_sha256 = serializers.SerializerMethodField()

    class Meta:
        model = UserSigningCredential
        fields = (
            'id',
            'provider',
            'key_alias',
            'key_id',
            'subject_dn',
            'serial_number',
            'issuer_dn',
            'valid_from',
            'valid_to',
            'status',
            'fingerprint_sha256',
        )

    def get_fingerprint_sha256(self, obj):
        try:
            from signing.pki import certificate_fingerprint_sha256

            return certificate_fingerprint_sha256(obj.certificate_pem)
        except Exception:
            return ''


class UserSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    technical_username = serializers.CharField(source='username', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)
    groups = serializers.SerializerMethodField()
    signing_credentials = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    company_role = serializers.SerializerMethodField()
    is_platform_admin = serializers.SerializerMethodField()
    must_change_password = serializers.SerializerMethodField()
    is_company_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'technical_username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_staff',
            'is_superuser',
            'is_platform_admin',
            'is_company_admin',
            'company_role',
            'must_change_password',
            'company',
            'profile',
            'groups',
            'signing_credentials',
            'date_joined',
        )
        read_only_fields = fields

    def get_username(self, obj):
        membership = get_user_membership(obj)
        return membership.local_username if membership else obj.username

    def get_full_name(self, obj):
        return obj.get_full_name() or self.get_username(obj)

    def get_groups(self, obj):
        memberships = obj.group_memberships.select_related('group').all()
        company = get_user_company(obj)
        if company is not None:
            memberships = memberships.filter(group__company=company)
        return [
            {
                'id': membership.group_id,
                'name': membership.group.name,
                'role': membership.role,
            }
            for membership in memberships
        ]

    def get_signing_credentials(self, obj):
        credentials = obj.signing_credentials.order_by('-updated_at')
        return UserSigningCredentialSerializer(credentials, many=True).data

    def get_company(self, obj):
        company = get_user_company(obj)
        if company is None:
            return None
        return {
            'id': company.id,
            'code': company.code,
            'slug': company.slug,
            'name': company.name,
            'status': company.status,
        }

    def get_company_role(self, obj):
        membership = get_user_membership(obj)
        return membership.role if membership else None

    def get_is_platform_admin(self, obj):
        return is_platform_admin(obj)

    def get_must_change_password(self, obj):
        membership = get_user_membership(obj)
        return bool(membership and membership.must_change_password)

    def get_is_company_admin(self, obj):
        return is_company_admin(obj)


class UserMeUpdateSerializer(serializers.Serializer):
    class UserAliasInputSerializer(serializers.Serializer):
        alias = serializers.CharField(max_length=150, allow_blank=False)
        is_primary_hint = serializers.BooleanField(required=False, default=False)

        def validate_alias(self, value):
            cleaned = ' '.join(str(value or '').split()).strip()
            if not normalize_lookup_value(cleaned):
                raise serializers.ValidationError('Bi danh khong duoc de trong.')
            return cleaned

    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    chuc_danh = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    cccd = serializers.CharField(required=False, allow_blank=True)
    ngay_sinh = serializers.DateField(required=False, allow_null=True)
    age_years = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=120)
    ma_nhan_vien = serializers.CharField(required=False, allow_blank=True)
    so_dien_thoai = serializers.CharField(required=False, allow_blank=True)
    dia_chi = serializers.CharField(required=False, allow_blank=True)
    so_yeu_ly_lich = serializers.CharField(required=False, allow_blank=True)
    aliases = UserAliasInputSerializer(many=True, required=False)
    password = serializers.CharField(required=False, write_only=True, min_length=8, trim_whitespace=False)

    def validate_email(self, value):
        return str(value or '').strip()

    def validate_cccd(self, value):
        value = str(value or '').strip()
        if not value:
            return ''
        digits = ''.join(ch for ch in value if ch.isdigit())
        if digits != value or len(digits) not in {9, 12}:
            raise serializers.ValidationError('CCCD/CMND chi duoc gom 9 hoac 12 chu so.')
        return digits

    def validate_ma_nhan_vien(self, value):
        import re

        value = str(value or '').strip()
        if not value:
            return ''
        if not re.fullmatch(r'[A-Za-z0-9._\-/ ]{1,50}', value):
            raise serializers.ValidationError('Ma nhan vien chi duoc gom chu, so va . _ - /.')
        request = self.context.get('request')
        instance = request.user if request else None
        company = get_user_company(instance)
        qs = UserProfile.objects.filter(ma_nhan_vien__iexact=value)
        if company is not None:
            qs = qs.filter(company=company)
        if instance is not None:
            qs = qs.exclude(user=instance)
        if qs.exists():
            raise serializers.ValidationError('Ma nhan vien da duoc su dung boi tai khoan khac trong cong ty.')
        return value

    def validate_so_dien_thoai(self, value):
        import re

        value = str(value or '').strip()
        if not value:
            return ''
        if re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError('So dien thoai khong duoc chua chu cai.')
        digits = re.sub(r'[^0-9]', '', value)
        if len(digits) < 9 or len(digits) > 15:
            raise serializers.ValidationError('So dien thoai phai co tu 9 den 15 chu so.')
        return digits

    def validate_dia_chi(self, value):
        value = ' '.join(str(value or '').split()).strip()
        if not value:
            return ''
        if len(value) > 255:
            raise serializers.ValidationError('Dia chi khong duoc vuot qua 255 ky tu.')
        return value

    def validate_ngay_sinh(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('Ngay sinh khong duoc o tuong lai.')
        return value

    def validate_aliases(self, value):
        seen = set()
        primary_count = 0
        for item in value:
            normalized = normalize_lookup_value(item['alias'])
            if normalized in seen:
                raise serializers.ValidationError('Danh sach bi danh dang bi trung sau khi chuan hoa.')
            seen.add(normalized)
            if item.get('is_primary_hint'):
                primary_count += 1
        if primary_count > 1:
            raise serializers.ValidationError('Chi duoc danh dau mot bi danh uu tien.')
        return value

    def update(self, instance, validated_data):
        aliases_data = validated_data.pop('aliases', serializers.empty)
        password = validated_data.pop('password', None)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['first_name', 'last_name', 'email', 'password'])
        else:
            instance.save(update_fields=['first_name', 'last_name', 'email'])

        company = get_user_company(instance)
        profile, _ = UserProfile.objects.get_or_create(
            user=instance,
            defaults={'company': company},
        )
        for field in (
            'chuc_danh',
            'bio',
            'cccd',
            'ngay_sinh',
            'age_years',
            'ma_nhan_vien',
            'so_dien_thoai',
            'dia_chi',
            'so_yeu_ly_lich',
        ):
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        if company is not None and profile.company_id != company.id:
            profile.company = company
        elif company is None and profile.company_id is not None:
            profile.company = None
        profile.save()

        if aliases_data is not serializers.empty:
            instance.aliases.all().delete()
            for item in aliases_data:
                alias_obj = UserAlias(user=instance)
                alias_obj.company = company
                alias_obj.alias = item['alias']
                alias_obj.is_primary_hint = bool(item.get('is_primary_hint', False))
                alias_obj.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    def create(self, validated_data):
        raise serializers.ValidationError('Dang ky tu do da bi tat trong phien ban multi-company.')

    def validate(self, attrs):
        raise serializers.ValidationError('Dang ky tu do da bi tat trong phien ban multi-company.')
