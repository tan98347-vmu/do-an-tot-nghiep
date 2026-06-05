"""Tests for sign_generic_file / verify_generic_file (RSA-PSS SHA256)."""

import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import SimpleTestCase

from signing.services import sign_generic_file, verify_generic_file


def _gen_rsa_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem, pub_pem


class GenericSigningTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.priv_pem, cls.pub_pem = _gen_rsa_keypair()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='sig_test_'))
        self.file = self.tmp / 'payload.bin'
        self.file.write_bytes(os.urandom(4096))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sign_and_verify_ok(self):
        sig = self.tmp / 'payload.bin.sig'
        sign_generic_file(str(self.file), self.priv_pem, str(sig))
        self.assertTrue(sig.exists())
        self.assertGreater(sig.stat().st_size, 100)  # signature ~256 bytes
        self.assertTrue(verify_generic_file(str(self.file), str(sig), self.pub_pem))

    def test_verify_returns_false_when_file_tampered(self):
        sig = self.tmp / 'payload.bin.sig'
        sign_generic_file(str(self.file), self.priv_pem, str(sig))
        # Flip 1 byte
        data = bytearray(self.file.read_bytes())
        data[10] = (data[10] + 1) & 0xFF
        self.file.write_bytes(bytes(data))
        self.assertFalse(verify_generic_file(str(self.file), str(sig), self.pub_pem))

    def test_verify_returns_false_with_wrong_pubkey(self):
        sig = self.tmp / 'payload.bin.sig'
        sign_generic_file(str(self.file), self.priv_pem, str(sig))
        _, other_pub = _gen_rsa_keypair()
        self.assertFalse(verify_generic_file(str(self.file), str(sig), other_pub))

    def test_verify_returns_false_with_missing_sig(self):
        # sig khong ton tai
        self.assertFalse(verify_generic_file(str(self.file), str(self.tmp / 'nope.sig'), self.pub_pem))
