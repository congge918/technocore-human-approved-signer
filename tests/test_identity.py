import tempfile
import unittest
from pathlib import Path

from technocore_human_signer.identity import create_identity, load_identity
from technocore_human_signer.protocol import IdentityError, did_from_private_key


class IdentityTests(unittest.TestCase):
    def test_encrypted_identity_round_trip_and_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "identity.pem"
            passphrase = "correct horse battery staple"
            did = create_identity(path, passphrase)

            self.assertIn(b"ENCRYPTED PRIVATE KEY", path.read_bytes())
            self.assertEqual(did_from_private_key(load_identity(path, passphrase)), did)
            with self.assertRaises(IdentityError):
                create_identity(path, passphrase)

    def test_wrong_passphrase_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "identity.pem"
            create_identity(path, "correct horse battery staple")
            with self.assertRaises(IdentityError):
                load_identity(path, "incorrect passphrase")


if __name__ == "__main__":
    unittest.main()
