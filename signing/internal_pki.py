"""
internal_pki.py
  = kho và nhà cấp phát khóa/certificate nội bộ
"""

import base64
import hashlib
import uuid
from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import (
    CREDENTIAL_PROVIDER_INTERNAL_PKI,
    CREDENTIAL_STATUS_ACTIVE,
    InternalPkiConfig,
    UserSigningCredential,
    UserSigningKeySecret,
)
from .pki import certificate_metadata_from_pem

class InternalPkiError(Exception):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `InternalPkiError` gom mot loai loi backend co chu dich de service hoac endpoint trong file `signing/internal_pki.py` co the phan nhanh ro rang.
    Vai tro cua no trong frontend: Frontend khong nhin thay lop loi nay truc tiep; no chi nhan HTTP status, toast hoac thong diep da duoc endpoint quy doi tu loi do.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Tach rieng loi `InternalPkiError` de luong xu ly khong phai dung exception chung chung kho chan doan.
    """
    pass

def _crypto_modules():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_crypto_modules` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        from cryptography import x509
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as exc:
        raise InternalPkiError('cryptography is required for internal PKI provisioning.') from exc
    return {
        'x509': x509,
        'Fernet': Fernet,
        'hashes': hashes,
        'serialization': serialization,
        'rsa': rsa,
        'NameOID': NameOID,
    }

def _fernet():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_fernet` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    raw_secret = (
        getattr(settings, 'SIGNING_INTERNAL_PKI_MASTER_KEY', None)
        or getattr(settings, 'SECRET_KEY', '')
        or 'internal-pki'
    )
    digest = hashlib.sha256(str(raw_secret).encode('utf-8')).digest()
    return deps['Fernet'](base64.urlsafe_b64encode(digest))

def encrypt_secret(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `encrypt_secret` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `decrypt_secret` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return _fernet().encrypt((value or '').encode('utf-8')).decode('utf-8')

def decrypt_secret(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `decrypt_secret` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `encrypt_secret` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not value:
        return ''
    return _fernet().decrypt(value.encode('utf-8')).decode('utf-8')

def _serialize_private_key(private_key):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_serialize_private_key` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    return private_key.private_bytes(
        encoding=deps['serialization'].Encoding.PEM,
        format=deps['serialization'].PrivateFormat.PKCS8,
        encryption_algorithm=deps['serialization'].NoEncryption(),
    ).decode('utf-8')

def _serialize_certificate(certificate):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_serialize_certificate` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    return certificate.public_bytes(deps['serialization'].Encoding.PEM).decode('utf-8')

def _load_private_key(private_key_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_load_private_key` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    return deps['serialization'].load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
    )

def ensure_internal_ca():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `ensure_internal_ca` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `encrypt_secret` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    x509 = deps['x509']
    rsa = deps['rsa']
    hashes = deps['hashes']
    NameOID = deps['NameOID']

    config = InternalPkiConfig.get_config()
    if config.ca_certificate_pem and config.encrypted_private_key_pem:
        return config

    now = timezone.now()
    cert_now = now.astimezone(dt_timezone.utc).replace(tzinfo=None)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'VN'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'AI Van Ban'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'AI Van Ban Internal Signing CA'),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(cert_now - timedelta(days=1))
        .not_valid_after(cert_now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
        .sign(private_key=private_key, algorithm=hashes.SHA256())
    )
    config.ca_certificate_pem = _serialize_certificate(cert)
    config.encrypted_private_key_pem = encrypt_secret(_serialize_private_key(private_key))
    config.valid_from = now - timedelta(days=1)
    config.valid_to = now + timedelta(days=3650)
    config.save()
    return config

def _issue_user_certificate(user, ca_config):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_issue_user_certificate` la helper noi bo trong file `signing/internal_pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `encrypt_secret`, `decrypt_secret`, `ensure_internal_ca` goi lai.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _crypto_modules()
    x509 = deps['x509']
    rsa = deps['rsa']
    hashes = deps['hashes']
    NameOID = deps['NameOID']

    ca_private_key = _load_private_key(decrypt_secret(ca_config.encrypted_private_key_pem))
    ca_certificate = x509.load_pem_x509_certificate(ca_config.ca_certificate_pem.encode('utf-8'))
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    display_name = user.get_full_name().strip() or user.username
    subject_parts = [
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'VN'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'AI Van Ban'),
        x509.NameAttribute(NameOID.COMMON_NAME, display_name),
        x509.NameAttribute(NameOID.USER_ID, str(user.id)),
    ]
    if user.email:
        subject_parts.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, user.email))
    subject = x509.Name(subject_parts)
    now = timezone.now()
    cert_now = now.astimezone(dt_timezone.utc).replace(tzinfo=None)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_certificate.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(cert_now - timedelta(minutes=5))
        .not_valid_after(cert_now + timedelta(days=730))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private_key.public_key()),
            critical=False,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
        .sign(private_key=ca_private_key, algorithm=hashes.SHA256())
    )
    return _serialize_certificate(cert), _serialize_private_key(private_key)

@transaction.atomic
def ensure_user_signing_credential(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `ensure_user_signing_credential` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `encrypt_secret` trong module nay.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if user is None or not isinstance(user, User):
        return None
    active = UserSigningCredential.objects.filter(
        user=user,
        status=CREDENTIAL_STATUS_ACTIVE,
        valid_to__gte=timezone.now(),
    ).order_by('-updated_at').first()
    if active:
        if active.provider != CREDENTIAL_PROVIDER_INTERNAL_PKI:
            return active
        if hasattr(active, 'key_secret'):
            return active

    ca_config = ensure_internal_ca()
    certificate_pem, private_key_pem = _issue_user_certificate(user, ca_config)
    metadata = certificate_metadata_from_pem(certificate_pem)

    if active and active.provider == CREDENTIAL_PROVIDER_INTERNAL_PKI and not hasattr(active, 'key_secret'):
        credential = active
        credential.provider = CREDENTIAL_PROVIDER_INTERNAL_PKI
        credential.key_alias = credential.key_alias or f'user-{user.id}-main'
        credential.key_id = credential.key_id or uuid.uuid4().hex
        credential.certificate_pem = certificate_pem
        credential.subject_dn = metadata['subject_dn']
        credential.serial_number = metadata['serial_number']
        credential.issuer_dn = metadata['issuer_dn']
        credential.valid_from = metadata['valid_from']
        credential.valid_to = metadata['valid_to']
        credential.status = CREDENTIAL_STATUS_ACTIVE
        credential.save()
    else:
        credential = UserSigningCredential.objects.create(
            user=user,
            provider=CREDENTIAL_PROVIDER_INTERNAL_PKI,
            key_alias=f'user-{user.id}-main',
            key_id=uuid.uuid4().hex,
            certificate_pem=certificate_pem,
            subject_dn=metadata['subject_dn'],
            serial_number=metadata['serial_number'],
            issuer_dn=metadata['issuer_dn'],
            valid_from=metadata['valid_from'],
            valid_to=metadata['valid_to'],
            status=CREDENTIAL_STATUS_ACTIVE,
        )
    UserSigningKeySecret.objects.update_or_create(
        credential=credential,
        defaults={'encrypted_private_key_pem': encrypt_secret(private_key_pem)},
    )
    return credential

def get_private_key_pem_for_credential(credential):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_private_key_pem_for_credential` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `encrypt_secret` trong module nay.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if credential is None or not hasattr(credential, 'key_secret'):
        return ''
    return decrypt_secret(credential.key_secret.encrypted_private_key_pem)

def ensure_all_active_users_have_signing_credentials():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `ensure_all_active_users_have_signing_credentials` la ham nghiep vu chinh trong file `signing/internal_pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_crypto_modules`, `_fernet`, `encrypt_secret` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    for user in User.objects.filter(is_active=True).order_by('id'):
        ensure_user_signing_credential(user)
