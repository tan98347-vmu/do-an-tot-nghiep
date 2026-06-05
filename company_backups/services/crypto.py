"""Backup ZIP encryption module — AES-256-GCM streaming.

Pipeline cuc bo r5/M10:
1. `build_company_zip` tao file plaintext ZIP trong thu muc tmp.
2. `sign_generic_file` ky so file plaintext, sinh `.sig`.
3. `encrypt_file_stream` ma hoa file plaintext sang ciphertext luu disk.
4. Plaintext bi xoa; chi giu ciphertext + sig.

Format file ciphertext:
    [MAGIC 6 bytes][salt 16 bytes][nonce_prefix 8 bytes][n x (len_be32 + ciphertext)]

Moi chunk co counter rieng (nonce = nonce_prefix + counter_be32) dam bao
nonce unique cho AES-GCM. AAD = str(company_id).encode() chong cross-tenant.
"""

import base64
import os
from typing import Iterator, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
MAGIC = b'CBKv1\x00'  # 6 bytes
MAGIC_LEN = len(MAGIC)
SALT_LEN = 16
NONCE_PREFIX_LEN = 8
KEY_VERSION = 1
KDF_N = 2 ** 14
KDF_R = 8
KDF_P = 1

# Password-derived master key (admin password → 32 bytes)
PWD_KDF_N = 2 ** 15
PWD_KDF_R = 8
PWD_KDF_P = 1


def derive_master_from_password(password: str, pwd_salt: bytes) -> bytes:
    """Scrypt KDF: admin password -> 32-byte master_key."""
    if not password:
        raise ValueError('password rong.')
    if len(pwd_salt) != SALT_LEN:
        raise ValueError(f'pwd_salt phai {SALT_LEN} bytes.')
    return Scrypt(
        salt=pwd_salt, length=32,
        n=PWD_KDF_N, r=PWD_KDF_R, p=PWD_KDF_P,
    ).derive(password.encode('utf-8'))


def _derive_key(master_key: bytes, salt: bytes, company_id: int) -> bytes:
    """Dan xuat khoa AES tu master + salt + company_id (scrypt)."""
    if not master_key or len(master_key) != 32:
        raise ValueError('master_key phai la 32 bytes.')
    info = salt + int(company_id).to_bytes(4, 'big', signed=False)
    return Scrypt(salt=info, length=32, n=KDF_N, r=KDF_R, p=KDF_P).derive(master_key)


def encrypt_file_stream(in_path: str, out_path: str,
                        master_key: Optional[bytes] = None,
                        *, company_id: int,
                        password: Optional[str] = None) -> dict:
    """Encrypt file streaming. Tra ve encryption_meta dict (JSON-safe).

    Cau hinh khoa:
    - Truyen `master_key` (32 bytes): che do env-master-key truyen thong.
    - Truyen `password` (str): che do password admin -> Scrypt derive master_key.
      Khi decrypt phai cung password.
    """
    if password is not None and password != '':
        pwd_salt = os.urandom(SALT_LEN)
        master_key = derive_master_from_password(password, pwd_salt)
        pwd_meta = {
            'pwd_kdf': 'scrypt',
            'pwd_kdf_n': PWD_KDF_N,
            'pwd_kdf_r': PWD_KDF_R,
            'pwd_kdf_p': PWD_KDF_P,
            'pwd_salt': base64.b64encode(pwd_salt).decode('ascii'),
        }
    else:
        pwd_meta = {}
    salt = os.urandom(SALT_LEN)
    nonce_prefix = os.urandom(NONCE_PREFIX_LEN)
    key = _derive_key(master_key, salt, company_id)
    aes = AESGCM(key)
    aad = str(int(company_id)).encode('utf-8')
    counter = 0
    with open(in_path, 'rb') as fin, open(out_path, 'wb') as fout:
        fout.write(MAGIC)
        fout.write(salt)
        fout.write(nonce_prefix)
        while True:
            block = fin.read(CHUNK_SIZE)
            if not block:
                break
            nonce = nonce_prefix + counter.to_bytes(4, 'big', signed=False)
            ct = aes.encrypt(nonce, block, associated_data=aad)
            fout.write(len(ct).to_bytes(4, 'big', signed=False))
            fout.write(ct)
            counter += 1
    out = {
        'alg': 'AESGCM',
        'kdf': 'scrypt',
        'kdf_n': KDF_N,
        'kdf_r': KDF_R,
        'kdf_p': KDF_P,
        'salt': base64.b64encode(salt).decode('ascii'),
        'nonce_prefix': base64.b64encode(nonce_prefix).decode('ascii'),
        'key_version': KEY_VERSION,
        'chunk_size': CHUNK_SIZE,
        'magic': 'CBKv1',
        'chunk_count': counter,
    }
    out.update(pwd_meta)
    return out


def resolve_master_key_for_meta(meta: dict,
                                env_master_key: Optional[bytes],
                                password: Optional[str]) -> bytes:
    """Resolve 32-byte master_key tu meta + (password hoac env_master_key).

    - Neu meta co `pwd_salt` -> bat buoc co password.
    - Neu khong -> dung env_master_key.
    """
    if meta.get('pwd_salt'):
        if not password:
            raise ValueError('Backup nay duoc ma hoa bang password admin; can mat khau de giai ma.')
        pwd_salt = base64.b64decode(meta['pwd_salt'])
        return derive_master_from_password(password, pwd_salt)
    if not env_master_key:
        raise ValueError('Backup yeu cau BACKUP_ENCRYPTION_MASTER_KEY nhung khong co.')
    return env_master_key


def _read_meta_from_dict(meta: dict) -> tuple[bytes, bytes]:
    salt = base64.b64decode(meta['salt'])
    nonce_prefix = base64.b64decode(meta['nonce_prefix'])
    if len(salt) != SALT_LEN or len(nonce_prefix) != NONCE_PREFIX_LEN:
        raise ValueError('encryption_meta khong hop le (salt/nonce_prefix sai do dai).')
    return salt, nonce_prefix


def decrypt_file_stream(in_path: str, out_path: str, master_key: bytes, meta: dict,
                        *, company_id: int) -> None:
    """Decrypt file streaming vao out_path. Raise InvalidTag neu ciphertext bi sua."""
    salt, nonce_prefix = _read_meta_from_dict(meta)
    key = _derive_key(master_key, salt, company_id)
    aes = AESGCM(key)
    aad = str(int(company_id)).encode('utf-8')
    with open(in_path, 'rb') as fin, open(out_path, 'wb') as fout:
        magic = fin.read(MAGIC_LEN)
        if magic != MAGIC:
            raise ValueError('File khong phai backup ciphertext hop le (MAGIC mismatch).')
        # bo qua salt + nonce_prefix da co trong meta
        fin.read(SALT_LEN)
        fin.read(NONCE_PREFIX_LEN)
        counter = 0
        while True:
            length_bytes = fin.read(4)
            if not length_bytes:
                break
            if len(length_bytes) != 4:
                raise ValueError('File ciphertext bi truncate (chunk header).')
            length = int.from_bytes(length_bytes, 'big', signed=False)
            ct = fin.read(length)
            if len(ct) != length:
                raise ValueError('File ciphertext bi truncate (chunk body).')
            nonce = nonce_prefix + counter.to_bytes(4, 'big', signed=False)
            pt = aes.decrypt(nonce, ct, associated_data=aad)
            fout.write(pt)
            counter += 1


def decrypt_to_response(in_path: str, master_key: bytes, meta: dict,
                        *, company_id: int) -> Iterator[bytes]:
    """Generator yield bytes plaintext. Dung voi StreamingHttpResponse."""
    salt, nonce_prefix = _read_meta_from_dict(meta)
    key = _derive_key(master_key, salt, company_id)
    aes = AESGCM(key)
    aad = str(int(company_id)).encode('utf-8')
    with open(in_path, 'rb') as fin:
        magic = fin.read(MAGIC_LEN)
        if magic != MAGIC:
            raise ValueError('File khong phai backup ciphertext hop le.')
        fin.read(SALT_LEN)
        fin.read(NONCE_PREFIX_LEN)
        counter = 0
        while True:
            length_bytes = fin.read(4)
            if not length_bytes:
                break
            if len(length_bytes) != 4:
                raise ValueError('File ciphertext bi truncate.')
            length = int.from_bytes(length_bytes, 'big', signed=False)
            ct = fin.read(length)
            if len(ct) != length:
                raise ValueError('File ciphertext bi truncate.')
            nonce = nonce_prefix + counter.to_bytes(4, 'big', signed=False)
            yield aes.decrypt(nonce, ct, associated_data=aad)
            counter += 1


def looks_like_encrypted(path: str) -> bool:
    """Kiem tra header file co MAGIC khong (de phan biet legacy plaintext zip)."""
    try:
        with open(path, 'rb') as f:
            head = f.read(MAGIC_LEN)
        return head == MAGIC
    except OSError:
        return False
