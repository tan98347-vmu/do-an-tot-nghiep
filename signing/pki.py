"""
Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
Vai tro backend: File `signing/pki.py` giu hoac ho tro luong backend cho de xuat ky, packet ky, nhiem vu ky, xac minh PDF, PKI noi bo va quyen uy quyen.
Vai tro cua no trong frontend: Cac man `/signing/tasks`, `/signed-pdfs`, `/signing/access` va mot phan thao tac o `/mailbox` phu thuoc truc tiep hoac gian tiep vao file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`.
Tac dung: Giu cho quy trinh ky nhieu buoc, trang thai chu ky va kiem tra toan ven PDF nhat quan giua nguoi de xuat, nguoi ky va man tra cuu.
"""

import base64
import hashlib
import json
import shutil
import ssl
import tempfile
import urllib.error
import urllib.request
from datetime import timezone as dt_timezone
from dataclasses import dataclass
from pathlib import Path

import fitz
from django.conf import settings
from django.utils import timezone

class PkiDependencyError(Exception):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `PkiDependencyError` gom mot loai loi backend co chu dich de service hoac endpoint trong file `signing/pki.py` co the phan nhanh ro rang.
    Vai tro cua no trong frontend: Frontend khong nhin thay lop loi nay truc tiep; no chi nhan HTTP status, toast hoac thong diep da duoc endpoint quy doi tu loi do.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Tach rieng loi `PkiDependencyError` de luong xu ly khong phai dung exception chung chung kho chan doan.
    """
    pass

class RemoteHsmError(Exception):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `RemoteHsmError` gom mot loai loi backend co chu dich de service hoac endpoint trong file `signing/pki.py` co the phan nhanh ro rang.
    Vai tro cua no trong frontend: Frontend khong nhin thay lop loi nay truc tiep; no chi nhan HTTP status, toast hoac thong diep da duoc endpoint quy doi tu loi do.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Tach rieng loi `RemoteHsmError` de luong xu ly khong phai dung exception chung chung kho chan doan.
    """
    pass

@dataclass
class HsmSignatureResponse:
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `HsmSignatureResponse` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/pki.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: To chuc logic lien quan toi `HsmSignatureResponse` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
    """
    signature: bytes
    provider_transaction_id: str

@dataclass
class PreparedSignatureField:
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `PreparedSignatureField` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/pki.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: To chuc logic lien quan toi `PreparedSignatureField` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
    """
    field_name: str
    signer_name: str
    display_role: str
    step_no: int

def _ensure_pki_dependencies():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_ensure_pki_dependencies` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, utils as asym_utils
        from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
    except ImportError as exc:
        raise PkiDependencyError('cryptography is required for PKI PDF signing.') from exc
    return {
        'x509': x509,
        'hashes': hashes,
        'serialization': serialization,
        'padding': padding,
        'asym_utils': asym_utils,
        'ec': ec,
        'ed25519': ed25519,
        'rsa': rsa,
    }

def _load_pyhanko_modules():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_load_pyhanko_modules` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        from asn1crypto import algos, x509 as asn1_x509
        from pyhanko import stamp
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign import fields, signers
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko_certvalidator import ValidationContext
        try:
            from pyhanko.sign.general import SimpleCertificateStore
        except ImportError:
            from pyhanko_certvalidator.registry import SimpleCertificateStore
    except ImportError as exc:
        raise PkiDependencyError('pyHanko and pyhanko-certvalidator are required for PDF CMS signing.') from exc
    return {
        'algos': algos,
        'asn1_x509': asn1_x509,
        'stamp': stamp,
        'IncrementalPdfFileWriter': IncrementalPdfFileWriter,
        'PdfFileReader': PdfFileReader,
        'fields': fields,
        'signers': signers,
        'validate_pdf_signature': validate_pdf_signature,
        'ValidationContext': ValidationContext,
        'SimpleCertificateStore': SimpleCertificateStore,
    }

def _ensure_aware_utc(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_ensure_aware_utc` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value.astimezone(dt_timezone.utc)

def load_crypto_certificate(certificate_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `load_crypto_certificate` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    x509 = deps['x509']
    pem_bytes = certificate_pem.encode('utf-8') if isinstance(certificate_pem, str) else certificate_pem
    return x509.load_pem_x509_certificate(pem_bytes)

def certificate_fingerprint_sha256(certificate_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `certificate_fingerprint_sha256` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    hashes = deps['hashes']
    cert = load_crypto_certificate(certificate_pem)
    return cert.fingerprint(hashes.SHA256()).hex()

def certificate_metadata_from_pem(certificate_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `certificate_metadata_from_pem` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem xu ly chung thu, khoa hoac ngu canh ky so trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly chung thu, khoa hoac ngu canh ky so roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc xu ly chung thu, khoa hoac ngu canh ky so xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    cert = load_crypto_certificate(certificate_pem)
    return {
        'subject_dn': cert.subject.rfc4514_string(),
        'issuer_dn': cert.issuer.rfc4514_string(),
        'serial_number': format(cert.serial_number, 'X'),
        'valid_from': _ensure_aware_utc(getattr(cert, 'not_valid_before_utc', cert.not_valid_before)),
        'valid_to': _ensure_aware_utc(getattr(cert, 'not_valid_after_utc', cert.not_valid_after)),
        'fingerprint_sha256': certificate_fingerprint_sha256(certificate_pem),
    }

def _signature_mechanism_name(certificate_pem, digest_algorithm='sha256'):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signature_mechanism_name` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    rsa = deps['rsa']
    padding = deps['padding']
    ec = deps['ec']
    ed25519 = deps['ed25519']
    cert = load_crypto_certificate(certificate_pem)
    public_key = cert.public_key()
    normalized_digest = (digest_algorithm or 'sha256').replace('-', '').lower()
    if isinstance(public_key, rsa.RSAPublicKey):
        return f'{normalized_digest}_rsa'
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        return f'{normalized_digest}_ecdsa'
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return 'ed25519'
    raise RemoteHsmError('Unsupported certificate public key type for PDF signing.')

def _estimated_signature_size(certificate_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_estimated_signature_size` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    rsa = deps['rsa']
    ec = deps['ec']
    ed25519 = deps['ed25519']
    cert = load_crypto_certificate(certificate_pem)
    public_key = cert.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        return max(public_key.key_size // 8, 256)
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        coord_size = (public_key.curve.key_size + 7) // 8
        return (coord_size * 2) + 24
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return 64
    return 512

def _asn1_cert_from_pem(certificate_pem):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_asn1_cert_from_pem` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    serialization = deps['serialization']
    libs = _load_pyhanko_modules()
    cert = load_crypto_certificate(certificate_pem)
    der_bytes = cert.public_bytes(serialization.Encoding.DER)
    return libs['asn1_x509'].Certificate.load(der_bytes)

def _load_pem_blobs(paths, inline_pems):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_load_pem_blobs` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    blobs = []
    for pem_text in inline_pems or []:
        if pem_text:
            blobs.append(pem_text)
    for path_value in paths or []:
        if not path_value:
            continue
        pem_path = Path(path_value)
        if not pem_path.exists():
            continue
        blobs.append(pem_path.read_text(encoding='utf-8'))
    return blobs

def load_trust_store_certs():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `load_trust_store_certs` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    trusted_paths = getattr(settings, 'SIGNING_PKI_TRUSTED_CA_FILES', []) or []
    trusted_pems = getattr(settings, 'SIGNING_PKI_TRUSTED_CA_PEMS', []) or []
    intermediate_paths = getattr(settings, 'SIGNING_PKI_INTERMEDIATE_CA_FILES', []) or []
    intermediate_pems = getattr(settings, 'SIGNING_PKI_INTERMEDIATE_CA_PEMS', []) or []
    trusted_blobs = _load_pem_blobs(trusted_paths, trusted_pems)
    intermediate_blobs = _load_pem_blobs(intermediate_paths, intermediate_pems)
    try:
        from .models import InternalPkiConfig

        internal_config = InternalPkiConfig.get_config()
        if getattr(internal_config, 'ca_certificate_pem', ''):
            trusted_blobs.append(internal_config.ca_certificate_pem)
    except Exception:
        pass
    return {
        'trusted': trusted_blobs,
        'intermediate': intermediate_blobs,
    }

def build_validation_context():
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `build_validation_context` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem dung payload hoac cau truc du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can dung payload hoac cau truc du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc dung payload hoac cau truc du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    libs = _load_pyhanko_modules()
    trust_store = load_trust_store_certs()
    trust_roots = [_asn1_cert_from_pem(pem_text) for pem_text in trust_store['trusted']]
    other_certs = [_asn1_cert_from_pem(pem_text) for pem_text in trust_store['intermediate']]
    return libs['ValidationContext'](
        trust_roots=trust_roots,
        other_certs=other_certs,
        allow_fetching=False,
    )

class RemoteHsmSigner:
    

    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `RemoteHsmSigner` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/pki.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: To chuc logic lien quan toi `RemoteHsmSigner` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
    """
    def __init__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__init__` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem khoi tao trang thai can thiet cho doi tuong hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khoi tao trang thai can thiet cho doi tuong hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `_base_url`, `_endpoint`, `_headers` trong cung lop.
        Tac dung: Don buoc khoi tao trang thai can thiet cho doi tuong hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        self.config = getattr(settings, 'SIGNING_REMOTE_HSM', {}) or {}

    

    def _base_url(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_base_url` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_endpoint`, `_headers` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        return str(self.config.get('base_url') or '').rstrip('/')

    

    def _endpoint(self, key, default_path):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_endpoint` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_headers` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        value = self.config.get(key)
        if value:
            return str(value)
        base_url = self._base_url()
        if not base_url:
            return ''
        return f'{base_url}{default_path}'

    

    def _headers(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_headers` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        headers = {'Content-Type': 'application/json'}
        headers.update(self.config.get('extra_headers') or {})
        api_key = self.config.get('api_key')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        return headers

    

    def _timeout(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_timeout` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        try:
            return float(self.config.get('timeout_seconds') or 15)
        except (TypeError, ValueError):
            return 15.0

    

    def _ssl_context(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_ssl_context` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem chuan bi ngu canh cho buoc xu ly phia sau trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can chuan bi ngu canh cho buoc xu ly phia sau roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc chuan bi ngu canh cho buoc xu ly phia sau xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        context = ssl.create_default_context()
        verify_ssl = bool(self.config.get('verify_ssl', True))
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    

    def _request_json(self, method, url, payload=None):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `_request_json` la helper noi bo trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        if not url:
            raise RemoteHsmError('Remote HSM endpoint is not configured.')
        request_data = None
        if payload is not None:
            request_data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            url,
            data=request_data,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout(),
                context=self._ssl_context(),
            ) as response:
                raw = response.read().decode('utf-8') if response else ''
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='ignore')
            raise RemoteHsmError(f'Remote HSM rejected request: {detail or exc.reason}') from exc
        except urllib.error.URLError as exc:
            raise RemoteHsmError(f'Cannot reach Remote HSM: {exc.reason}') from exc
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RemoteHsmError('Remote HSM response was not valid JSON.') from exc

    

    def get_provider_readiness(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_provider_readiness` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        health_url = self._endpoint('healthcheck_url', '/health')
        if not health_url:
            if self._endpoint('sign_url', '/sign'):
                return True, 'Remote HSM healthcheck is not configured; assuming provider availability.'
            return False, 'Remote HSM base URL is not configured.'
        try:
            response = self._request_json('GET', health_url)
        except RemoteHsmError as exc:
            return False, str(exc)
        ready = response.get('ready')
        if ready is None:
            return True, response.get('message') or 'Remote HSM responded successfully.'
        return bool(ready), response.get('message') or ('Remote HSM is ready.' if ready else 'Remote HSM is not ready.')

    

    def sign_digest(self, credential, digest_bytes, digest_algorithm, audit_payload=None):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `sign_digest` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        sign_url = self._endpoint('sign_url', '/sign')
        payload = {
            'user_id': credential.user_id,
            'provider': credential.provider,
            'key_alias': credential.key_alias,
            'key_id': credential.key_id,
            'digest_algorithm': digest_algorithm,
            'digest_b64': base64.b64encode(digest_bytes).decode('ascii'),
            'signature_algorithm': _signature_mechanism_name(credential.certificate_pem, digest_algorithm),
            'audit': audit_payload or {},
        }
        response = self._request_json('POST', sign_url, payload)
        signature_b64 = response.get('signature_b64') or response.get('signature')
        if not signature_b64:
            raise RemoteHsmError('Remote HSM response did not contain a signature.')
        provider_transaction_id = (
            response.get('provider_transaction_id')
            or response.get('transaction_id')
            or response.get('request_id')
            or ''
        )
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as exc:
            raise RemoteHsmError('Remote HSM signature payload was not valid base64.') from exc
        return HsmSignatureResponse(
            signature=signature_bytes,
            provider_transaction_id=provider_transaction_id,
        )

    

    def sign_payload(self, credential, payload_bytes, digest_algorithm, audit_payload=None):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `sign_payload` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `RemoteHsmSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
        Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `_base_url`, `_endpoint` trong cung lop.
        Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
        """
        normalized_digest = (digest_algorithm or 'sha256').replace('-', '').lower()
        digest_bytes = hashlib.new(normalized_digest, payload_bytes).digest()
        return self.sign_digest(credential, digest_bytes, normalized_digest, audit_payload=audit_payload)

def prepare_pdf_signature_fields(source_pdf_path, output_pdf_path, signature_fields):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `prepare_pdf_signature_fields` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if not signature_fields:
        shutil.copy2(source_pdf_path, output_pdf_path)
        return

    libs = _load_pyhanko_modules()
    fields = libs['fields']
    writer_cls = libs['IncrementalPdfFileWriter']

    temp_dir = Path(tempfile.mkdtemp(prefix='pdf-sign-fields-'))
    try:
        staged_pdf = temp_dir / 'staged_appendix.pdf'
        fielded_pdf = temp_dir / 'fielded_appendix.pdf'

        pdf_doc = fitz.open(str(source_pdf_path))
        page_width = pdf_doc[-1].rect.width if pdf_doc.page_count else 595
        page_height = pdf_doc[-1].rect.height if pdf_doc.page_count else 842
        slots_per_page = 4
        field_specs = []

        for index, field_def in enumerate(signature_fields):
            slot = index % slots_per_page
            if slot == 0:
                page = pdf_doc.new_page(width=page_width, height=page_height)
                page.insert_text(
                    fitz.Point(36, 42),
                    'DIGITAL SIGNATURE APPENDIX',
                    fontsize=16,
                    color=(0.1, 0.2, 0.45),
                )
                page.insert_text(
                    fitz.Point(36, 64),
                    'Only incremental signature updates are allowed after activation.',
                    fontsize=9,
                    color=(0.35, 0.35, 0.35),
                )
            else:
                page = pdf_doc[-1]

            top = 96 + (slot * 165)
            rect = fitz.Rect(36, top, page_width - 36, top + 78)
            page.draw_rect(rect, color=(0.15, 0.35, 0.75), width=1.0)
            page.insert_textbox(
                fitz.Rect(rect.x0 + 10, rect.y0 + 8, rect.x1 - 10, rect.y1 - 8),
                '\n'.join([
                    f'Signer: {field_def.signer_name}',
                    f'Role: {field_def.display_role}',
                    f'Step: {field_def.step_no}',
                    'Visible signature field reserved for PKI signing.',
                ]),
                fontsize=10,
                color=(0.05, 0.1, 0.2),
            )
            page_index = pdf_doc.page_count - 1
            field_specs.append(
                fields.SigFieldSpec(
                    sig_field_name=field_def.field_name,
                    on_page=page_index,
                    box=(
                        rect.x0,
                        page_height - rect.y1,
                        rect.x1,
                        page_height - rect.y0,
                    ),
                )
            )

        pdf_doc.save(str(staged_pdf))
        pdf_doc.close()

        with staged_pdf.open('rb') as input_handle, fielded_pdf.open('wb') as output_handle:
            writer = writer_cls(input_handle)
            for field_spec in field_specs:
                fields.append_signature_field(writer, field_spec)
            writer.write(output_handle)

        shutil.copy2(fielded_pdf, output_pdf_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def _build_remote_pyhanko_signer(credential, remote_signer, digest_algorithm='sha256'):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_build_remote_pyhanko_signer` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem dung payload hoac cau truc du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can dung payload hoac cau truc du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc dung payload hoac cau truc du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    libs = _load_pyhanko_modules()
    algos = libs['algos']
    signers = libs['signers']
    store_cls = libs['SimpleCertificateStore']

    signing_cert = _asn1_cert_from_pem(credential.certificate_pem)
    certificate_store = store_cls()
    trust_store = load_trust_store_certs()
    for pem_text in trust_store['intermediate'] + trust_store['trusted']:
        try:
            certificate_store.register(_asn1_cert_from_pem(pem_text))
        except Exception:
            continue

    mechanism = algos.SignedDigestAlgorithm({
        'algorithm': _signature_mechanism_name(credential.certificate_pem, digest_algorithm),
    })
    estimated_size = _estimated_signature_size(credential.certificate_pem)

    

    class _RemotePdfSigner(signers.Signer):
        

        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `_RemotePdfSigner` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/pki.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `_build_remote_pyhanko_signer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `_RemotePdfSigner` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        def __init__(self):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `__init__` la helper noi bo trong file `signing/pki.py` trong lop `_RemotePdfSigner`, chiu trach nhiem khoi tao trang thai can thiet cho doi tuong hien tai trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khoi tao trang thai can thiet cho doi tuong hien tai roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `sign_raw`, `async_sign_raw` trong cung lop.
            Tac dung: Don buoc khoi tao trang thai can thiet cho doi tuong hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            try:
                super().__init__(
                    signing_cert=signing_cert,
                    cert_registry=certificate_store,
                    signature_mechanism=mechanism,
                    prefer_pss=False,
                    embed_roots=True,
                )
            except TypeError:
                super().__init__()
                self.signing_cert = signing_cert
                self.cert_registry = certificate_store
                self.signature_mechanism = mechanism
                self.embed_roots = True
            self.last_provider_transaction_id = ''

        

        def sign_raw(self, data, digest_algorithm, dry_run=False):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `sign_raw` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `_RemotePdfSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `async_sign_raw` trong cung lop.
            Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            if dry_run:
                return bytes(estimated_size)
            response = remote_signer.sign_payload(
                credential,
                data,
                digest_algorithm,
                audit_payload={
                    'user_id': credential.user_id,
                    'key_alias': credential.key_alias,
                    'key_id': credential.key_id,
                },
            )
            self.last_provider_transaction_id = response.provider_transaction_id
            return response.signature

        

        async def async_sign_raw(self, data, digest_algorithm, dry_run=False):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `async_sign_raw` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `_RemotePdfSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `sign_raw` trong cung lop.
            Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            return self.sign_raw(data, digest_algorithm, dry_run=dry_run)

    signer_instance = _RemotePdfSigner()
    signer_instance.mechanism_label = _signature_mechanism_name(credential.certificate_pem, digest_algorithm)
    return signer_instance

def _sign_digest_locally(private_key_pem, certificate_pem, digest_bytes, digest_algorithm):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_sign_digest_locally` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    hashes = deps['hashes']
    rsa = deps['rsa']
    ec = deps['ec']
    ed25519 = deps['ed25519']
    padding = deps['padding']
    asym_utils = deps['asym_utils']
    serialization = deps['serialization']

    algorithm_name = (digest_algorithm or 'sha256').replace('-', '').lower()
    private_key = serialization.load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
    hash_algorithm = getattr(hashes, algorithm_name.upper())()
    cert = load_crypto_certificate(certificate_pem)
    public_key = cert.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        return private_key.sign(
            digest_bytes,
            padding.PKCS1v15(),
            asym_utils.Prehashed(hash_algorithm),
        )
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        return private_key.sign(
            digest_bytes,
            ec.ECDSA(asym_utils.Prehashed(hash_algorithm)),
        )
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return private_key.sign(digest_bytes)
    raise RemoteHsmError('Unsupported local private key type for PDF signing.')

def _build_local_pyhanko_signer(credential, private_key_pem, digest_algorithm='sha256'):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_build_local_pyhanko_signer` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem dung payload hoac cau truc du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can dung payload hoac cau truc du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc dung payload hoac cau truc du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    libs = _load_pyhanko_modules()
    algos = libs['algos']
    signers = libs['signers']
    store_cls = libs['SimpleCertificateStore']

    signing_cert = _asn1_cert_from_pem(credential.certificate_pem)
    certificate_store = store_cls()
    trust_store = load_trust_store_certs()
    for pem_text in trust_store['intermediate'] + trust_store['trusted']:
        try:
            certificate_store.register(_asn1_cert_from_pem(pem_text))
        except Exception:
            continue

    mechanism = algos.SignedDigestAlgorithm({
        'algorithm': _signature_mechanism_name(credential.certificate_pem, digest_algorithm),
    })
    estimated_size = _estimated_signature_size(credential.certificate_pem)

    

    class _LocalPdfSigner(signers.Signer):
        

        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `_LocalPdfSigner` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/pki.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `_build_local_pyhanko_signer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `_LocalPdfSigner` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        def __init__(self):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `__init__` la helper noi bo trong file `signing/pki.py` trong lop `_LocalPdfSigner`, chiu trach nhiem khoi tao trang thai can thiet cho doi tuong hien tai trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can khoi tao trang thai can thiet cho doi tuong hien tai roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `sign_raw`, `async_sign_raw` trong cung lop.
            Tac dung: Don buoc khoi tao trang thai can thiet cho doi tuong hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            try:
                super().__init__(
                    signing_cert=signing_cert,
                    cert_registry=certificate_store,
                    signature_mechanism=mechanism,
                    prefer_pss=False,
                    embed_roots=True,
                )
            except TypeError:
                super().__init__()
                self.signing_cert = signing_cert
                self.cert_registry = certificate_store
                self.signature_mechanism = mechanism
                self.embed_roots = True
            self.last_provider_transaction_id = ''

        

        def sign_raw(self, data, digest_algorithm, dry_run=False):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `sign_raw` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `_LocalPdfSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `async_sign_raw` trong cung lop.
            Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            if dry_run:
                return bytes(estimated_size)
            normalized_digest = (digest_algorithm or 'sha256').replace('-', '').lower()
            digest_bytes = hashlib.new(normalized_digest, data).digest()
            return _sign_digest_locally(
                private_key_pem,
                credential.certificate_pem,
                digest_bytes,
                normalized_digest,
            )

        

        async def async_sign_raw(self, data, digest_algorithm, dry_run=False):
            """
            Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
            Vai tro backend: Ham `async_sign_raw` la ham nghiep vu chinh trong file `signing/pki.py` trong lop `_LocalPdfSigner`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
            Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
            Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__init__`, `sign_raw` trong cung lop.
            Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
            """
            return self.sign_raw(data, digest_algorithm, dry_run=dry_run)

    signer_instance = _LocalPdfSigner()
    signer_instance.mechanism_label = _signature_mechanism_name(credential.certificate_pem, digest_algorithm)
    return signer_instance

def sign_pdf_incremental(source_pdf_path, output_pdf_path, field_name, credential, signer_display_name, reason_text):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `sign_pdf_incremental` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem thuc hien buoc ky so hoac ghi nhan chu ky trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien buoc ky so hoac ghi nhan chu ky roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc thuc hien buoc ky so hoac ghi nhan chu ky xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    libs = _load_pyhanko_modules()
    signers = libs['signers']
    fields = libs['fields']
    stamp = libs['stamp']
    writer_cls = libs['IncrementalPdfFileWriter']

    provider_transaction_id = ''
    if str(getattr(credential, 'provider', '') or '').strip().lower() == 'internal_pki':
        from .internal_pki import get_private_key_pem_for_credential

        private_key_pem = get_private_key_pem_for_credential(credential)
        if not private_key_pem:
            raise RemoteHsmError('Internal PKI credential is missing its private key secret.')
        pdf_signer = _build_local_pyhanko_signer(credential, private_key_pem)
    else:
        remote_signer = RemoteHsmSigner()
        pdf_signer = _build_remote_pyhanko_signer(credential, remote_signer)
    subfilter = getattr(getattr(fields, 'SigSeedSubFilter', object), 'PADES', None)
    if subfilter is None:
        subfilter = getattr(getattr(fields, 'SigSeedSubFilter', object), 'ADOBE_PKCS7_DETACHED', None)
    metadata_kwargs = {
        'field_name': field_name,
        'md_algorithm': 'sha256',
        'reason': reason_text or '',
        'name': signer_display_name or '',
    }
    if subfilter is not None:
        metadata_kwargs['subfilter'] = subfilter
    signature_meta = signers.PdfSignatureMetadata(**metadata_kwargs)
    stamp_style = stamp.TextStampStyle(
        stamp_text='Digitally signed by %(signer)s\nDate: %(ts)s',
    )
    try:
        pdf_signer_obj = signers.PdfSigner(
            signature_meta=signature_meta,
            signer=pdf_signer,
            stamp_style=stamp_style,
            existing_fields_only=True,
        )
    except TypeError:
        pdf_signer_obj = signers.PdfSigner(
            signature_meta=signature_meta,
            signer=pdf_signer,
            stamp_style=stamp_style,
        )

    with Path(source_pdf_path).open('rb') as input_handle, Path(output_pdf_path).open('wb') as output_handle:
        writer = writer_cls(input_handle)
        pdf_signer_obj.sign_pdf(writer, output=output_handle)

    metadata = certificate_metadata_from_pem(credential.certificate_pem)
    provider_transaction_id = getattr(pdf_signer, 'last_provider_transaction_id', '')
    return {
        'provider_transaction_id': provider_transaction_id,
        'digest_algorithm': 'sha256',
        'signature_algorithm': getattr(pdf_signer, 'mechanism_label', ''),
        'certificate_fingerprint': metadata['fingerprint_sha256'],
        'certificate_subject_dn': metadata['subject_dn'],
        'certificate_serial_number': metadata['serial_number'],
        'certificate_issuer_dn': metadata['issuer_dn'],
    }

def _cert_summary_from_asn1(cert_obj):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_cert_summary_from_asn1` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem tong hop so lieu tom tat trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tong hop so lieu tom tat roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc tong hop so lieu tom tat xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    deps = _ensure_pki_dependencies()
    x509 = deps['x509']
    der_bytes = cert_obj.dump()
    crypto_cert = x509.load_der_x509_certificate(der_bytes)
    return {
        'subject_dn': crypto_cert.subject.rfc4514_string(),
        'issuer_dn': crypto_cert.issuer.rfc4514_string(),
        'serial_number': format(crypto_cert.serial_number, 'X'),
        'fingerprint_sha256': crypto_cert.fingerprint(deps['hashes'].SHA256()).hex(),
    }

def _enum_name(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_enum_name` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if value is None:
        return ''
    return getattr(value, 'name', str(value))

def _per_signature_status(validation_status):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_per_signature_status` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    intact = bool(getattr(validation_status, 'intact', False))
    cryptographically_valid = bool(getattr(validation_status, 'valid', False))
    bottom_line = bool(getattr(validation_status, 'bottom_line', False))
    trusted = getattr(validation_status, 'trusted', None)
    if trusted is None:
        trusted = bottom_line
    trusted = bool(trusted)
    if bottom_line:
        return 'safe', 'Embedded PDF signature is valid and trusted.'
    if not intact:
        return 'tampered', 'The signed PDF content was modified after signing.'
    if not cryptographically_valid:
        return 'invalid', 'The embedded digital signature is cryptographically invalid.'
    return 'untrusted', 'The embedded digital signature is not trusted by the configured PKI store.'

def _summary_for_status(status_code):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_summary_for_status` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem tong hop so lieu tom tat trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tong hop so lieu tom tat roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc tong hop so lieu tom tat xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return {
        'safe': 'Van ban an toan. Tat ca chu ky so deu hop le.',
        'invalid': 'Chu ky so khong hop le.',
        'untrusted': 'Chu ky so ton tai nhung CA khong duoc trust hoac chung thu khong hop le.',
        'tampered': 'File PDF da bi thay doi sau khi ky.',
        'internal_approval': 'Ban ghi nay duoc tao bang co che xac nhan noi bo.',
    }.get(status_code, 'Khong the xac minh van ban.')

def _validate_pdf_signature_compat(validate_pdf_signature, embedded_sig, validation_context):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_validate_pdf_signature_compat` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        return validate_pdf_signature(
            embedded_sig,
            signer_validation_context=validation_context,
        )
    except TypeError as exc:
        if 'signer_validation_context' not in str(exc):
            raise
    try:
        return validate_pdf_signature(
            embedded_sig,
            validation_context=validation_context,
        )
    except TypeError as exc:
        if 'validation_context' not in str(exc):
            raise
    return validate_pdf_signature(embedded_sig, validation_context)

def _validate_pdf_signature_from_file(pdf_path, field_name, reader_cls, validate_pdf_signature, validation_context):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_validate_pdf_signature_from_file` la helper noi bo trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `load_crypto_certificate`, `certificate_fingerprint_sha256`, `certificate_metadata_from_pem` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    with open(pdf_path, 'rb') as input_handle:
        reader = reader_cls(input_handle)
        for embedded_sig in reader.embedded_signatures:
            if embedded_sig.field_name == field_name:
                return _validate_pdf_signature_compat(
                    validate_pdf_signature,
                    embedded_sig,
                    validation_context,
                )
    raise RemoteHsmError(f'Unable to locate embedded signature field "{field_name}" in signed PDF.')

def validate_pdf_signatures(pdf_path, task_by_field_name=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `validate_pdf_signatures` la ham nghiep vu chinh trong file `signing/pki.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_ensure_pki_dependencies`, `_load_pyhanko_modules`, `_ensure_aware_utc` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    libs = _load_pyhanko_modules()
    PdfFileReader = libs['PdfFileReader']
    reader_cls = libs['PdfFileReader']
    validate_pdf_signature = libs['validate_pdf_signature']
    report_items = []
    steps = []
    checked_at = timezone.now().isoformat()
    trusted_certs = load_trust_store_certs()['trusted']

    if not Path(pdf_path).exists():
        return {
            'status': 'tampered',
            'is_safe': False,
            'is_access_allowed': False,
            'summary': 'Khong tim thay tep PDF da ky.',
            'checked_at': checked_at,
            'signature_mode': 'pdf_pkcs7',
            'signature_count': 0,
            'signer_reports': [],
            'steps': [
                {
                    'code': 'file_reference',
                    'label': 'Kiem tra tep PDF da ky',
                    'status': 'failed',
                    'detail': 'Khong tim thay tep PDF tren he thong luu tru.',
                },
            ],
        }

    steps.append({
        'code': 'file_reference',
        'label': 'Kiem tra tep PDF da ky',
        'status': 'passed',
        'detail': 'Da tim thay tep PDF tren he thong luu tru.',
    })

    with Path(pdf_path).open('rb') as input_handle:
        reader = reader_cls(input_handle)
        embedded_signatures = list(getattr(reader, 'embedded_signatures', []) or [])

    if not embedded_signatures:
        return {
            'status': 'invalid',
            'is_safe': False,
            'is_access_allowed': False,
            'summary': 'Tep PDF khong chua chu ky so nhung.',
            'checked_at': checked_at,
            'signature_mode': 'pdf_pkcs7',
            'signature_count': 0,
            'signer_reports': [],
            'steps': steps + [
                {
                    'code': 'signature_presence',
                    'label': 'Phat hien chu ky nhung trong PDF',
                    'status': 'failed',
                    'detail': 'Khong tim thay bat ky chu ky CMS/PKCS#7 nao trong file PDF.',
                },
            ],
        }

    steps.append({
        'code': 'signature_presence',
        'label': 'Phat hien chu ky nhung trong PDF',
        'status': 'passed',
        'detail': f'Tim thay {len(embedded_signatures)} chu ky nhung trong file PDF.',
    })

    if trusted_certs:
        steps.append({
            'code': 'trust_store',
            'label': 'Nap trust store PKI noi bo',
            'status': 'passed',
            'detail': f'Da nap {len(trusted_certs)} root CA hoac issuing CA duoc trust.',
        })
    else:
        steps.append({
            'code': 'trust_store',
            'label': 'Nap trust store PKI noi bo',
            'status': 'warning',
            'detail': 'Khong co root CA nao duoc cau hinh. Ket qua verify se bi danh dau untrusted.',
        })

    validation_context = build_validation_context()
    task_by_field_name = task_by_field_name or {}
    severity_order = {'safe': 0, 'untrusted': 1, 'invalid': 2, 'tampered': 3}
    overall_status = 'safe'

    for embedded_sig in embedded_signatures:
        validation = _validate_pdf_signature_from_file(
            pdf_path,
            getattr(embedded_sig, 'field_name', ''),
            PdfFileReader,
            validate_pdf_signature,
            validation_context,
        )
        signature_status, detail = _per_signature_status(validation)
        if severity_order[signature_status] > severity_order[overall_status]:
            overall_status = signature_status

        signer_cert = getattr(embedded_sig, 'signer_cert', None) or getattr(validation, 'signing_cert', None)
        cert_summary = _cert_summary_from_asn1(signer_cert) if signer_cert is not None else {
            'subject_dn': '',
            'issuer_dn': '',
            'serial_number': '',
            'fingerprint_sha256': '',
        }
        field_name = getattr(embedded_sig, 'field_name', '') or ''
        matched_task = task_by_field_name.get(field_name)
        validation_path = []
        for path_cert in getattr(validation, 'validation_path', []) or []:
            try:
                validation_path.append(_cert_summary_from_asn1(path_cert))
            except Exception:
                continue
        signed_at = getattr(embedded_sig, 'self_reported_timestamp', None) or getattr(validation, 'timestamp', None)
        report_items.append({
            'field_name': field_name,
            'task_id': getattr(matched_task, 'id', None),
            'signer_user_id': getattr(getattr(matched_task, 'signer_user', None), 'id', None),
            'signer_name': getattr(getattr(matched_task, 'signer_user', None), 'get_full_name', lambda: '')() or getattr(getattr(matched_task, 'signer_user', None), 'username', ''),
            'display_role': getattr(matched_task, 'display_role', ''),
            'step_no': getattr(matched_task, 'step_no', None),
            'status': signature_status,
            'is_valid': signature_status == 'safe',
            'detail': detail,
            'signed_at': signed_at.isoformat() if signed_at else '',
            'subject_dn': cert_summary['subject_dn'],
            'issuer_dn': cert_summary['issuer_dn'],
            'serial_number': cert_summary['serial_number'],
            'certificate_fingerprint': cert_summary['fingerprint_sha256'],
            'digest_algorithm': getattr(validation, 'md_algorithm', '') or '',
            'signature_algorithm': str(getattr(validation, 'pkcs7_signature_mechanism', '') or ''),
            'integrity': {
                'intact': bool(getattr(validation, 'intact', False)),
                'valid': bool(getattr(validation, 'valid', False)),
                'trusted': bool(getattr(validation, 'trusted', signature_status == 'safe')),
                'bottom_line': bool(getattr(validation, 'bottom_line', signature_status == 'safe')),
                'coverage': _enum_name(getattr(validation, 'coverage', None)),
                'modification_level': _enum_name(getattr(validation, 'modification_level', None)),
            },
            'chain': validation_path,
        })

    summary = _summary_for_status(overall_status)
    return {
        'status': overall_status,
        'is_safe': overall_status == 'safe',
        'is_access_allowed': overall_status in {'safe', 'untrusted'},
        'summary': summary,
        'checked_at': checked_at,
        'signature_mode': 'pdf_pkcs7',
        'signature_count': len(report_items),
        'signer_reports': report_items,
        'steps': steps,
    }
