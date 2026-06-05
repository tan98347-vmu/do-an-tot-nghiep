"""Tests for company_backups.services.crypto — encrypt/decrypt roundtrip + tamper detection."""

import hashlib
import os
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from django.test import SimpleTestCase

from company_backups.services.crypto import (
    CHUNK_SIZE, MAGIC,
    decrypt_file_stream, encrypt_file_stream, looks_like_encrypted,
)


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class CryptoRoundTripTests(SimpleTestCase):

    def setUp(self):
        self.master_key = os.urandom(32)
        self.tmp = Path(tempfile.mkdtemp(prefix='cbk_test_'))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_random_plaintext(self, size: int) -> Path:
        path = self.tmp / 'plain.zip'
        with open(path, 'wb') as f:
            remaining = size
            while remaining > 0:
                chunk = os.urandom(min(remaining, 1 << 20))
                f.write(chunk)
                remaining -= len(chunk)
        return path

    def test_roundtrip_small_file(self):
        plain = self._make_random_plaintext(1024)
        cipher = self.tmp / 'cipher.bin'
        restored = self.tmp / 'restored.zip'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=42)
        decrypt_file_stream(str(cipher), str(restored), self.master_key, meta, company_id=42)
        self.assertEqual(_sha256(plain), _sha256(restored))

    def test_roundtrip_multi_chunk(self):
        plain = self._make_random_plaintext(CHUNK_SIZE * 2 + 1234)
        cipher = self.tmp / 'cipher.bin'
        restored = self.tmp / 'restored.zip'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=42)
        self.assertEqual(meta['chunk_count'], 3)
        decrypt_file_stream(str(cipher), str(restored), self.master_key, meta, company_id=42)
        self.assertEqual(_sha256(plain), _sha256(restored))

    def test_cipher_starts_with_magic(self):
        plain = self._make_random_plaintext(128)
        cipher = self.tmp / 'cipher.bin'
        encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=1)
        with open(cipher, 'rb') as f:
            head = f.read(6)
        self.assertEqual(head, MAGIC)
        # khong giong zip
        self.assertNotEqual(head[:4], b'PK\x03\x04')

    def test_looks_like_encrypted(self):
        plain = self._make_random_plaintext(64)
        cipher = self.tmp / 'cipher.bin'
        encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=1)
        self.assertTrue(looks_like_encrypted(str(cipher)))
        self.assertFalse(looks_like_encrypted(str(plain)))

    def test_flip_bit_in_ciphertext_raises_invalid_tag(self):
        plain = self._make_random_plaintext(2048)
        cipher = self.tmp / 'cipher.bin'
        restored = self.tmp / 'restored.zip'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=42)
        # Flip 1 byte trong vung chunk body (sau header 30 bytes)
        data = bytearray(Path(cipher).read_bytes())
        flip_at = 50
        data[flip_at] = (data[flip_at] + 1) & 0xFF
        Path(cipher).write_bytes(bytes(data))
        with self.assertRaises(InvalidTag):
            decrypt_file_stream(str(cipher), str(restored), self.master_key, meta, company_id=42)

    def test_wrong_master_key_raises_invalid_tag(self):
        plain = self._make_random_plaintext(2048)
        cipher = self.tmp / 'cipher.bin'
        restored = self.tmp / 'restored.zip'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=42)
        wrong_key = os.urandom(32)
        with self.assertRaises(InvalidTag):
            decrypt_file_stream(str(cipher), str(restored), wrong_key, meta, company_id=42)

    def test_wrong_company_id_raises_invalid_tag(self):
        plain = self._make_random_plaintext(2048)
        cipher = self.tmp / 'cipher.bin'
        restored = self.tmp / 'restored.zip'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=42)
        with self.assertRaises(InvalidTag):
            decrypt_file_stream(str(cipher), str(restored), self.master_key, meta, company_id=99)

    def test_unique_salt_nonce_per_encrypt(self):
        plain = self._make_random_plaintext(64)
        metas = []
        for i in range(10):
            cipher = self.tmp / f'c{i}.bin'
            metas.append(encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=1))
        salts = {m['salt'] for m in metas}
        nonces = {m['nonce_prefix'] for m in metas}
        self.assertEqual(len(salts), 10)
        self.assertEqual(len(nonces), 10)

    def test_meta_has_required_fields(self):
        plain = self._make_random_plaintext(64)
        cipher = self.tmp / 'cipher.bin'
        meta = encrypt_file_stream(str(plain), str(cipher), self.master_key, company_id=1)
        for key in ('alg', 'kdf', 'salt', 'nonce_prefix', 'key_version', 'chunk_size'):
            self.assertIn(key, meta)
        self.assertEqual(meta['alg'], 'AESGCM')
        self.assertEqual(meta['kdf'], 'scrypt')
        self.assertEqual(meta['key_version'], 1)

    def test_master_key_wrong_length_raises(self):
        plain = self._make_random_plaintext(64)
        cipher = self.tmp / 'cipher.bin'
        with self.assertRaises(ValueError):
            encrypt_file_stream(str(plain), str(cipher), os.urandom(16), company_id=1)
