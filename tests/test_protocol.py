import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from technocore_human_signer.protocol import (
    ValidationError,
    did_from_private_key,
    message_payload,
    normalize_message,
    sign_payload,
    verify_payload,
)


class ProtocolTests(unittest.TestCase):
    def test_did_and_signature_round_trip(self) -> None:
        key = Ed25519PrivateKey.generate()
        did = did_from_private_key(key)
        normalized, payload = message_payload("lobby", "123", "hello")
        signature = sign_payload(key, payload)

        self.assertTrue(did.startswith("did:key:z6Mk"))
        self.assertEqual(normalized, "hello")
        verify_payload(did, signature, payload)

    def test_normalization_matches_single_line_sweep(self) -> None:
        self.assertEqual(normalize_message("  hello\nworld\u202e  "), "hello world")

    def test_invalid_room_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            message_payload("../secret", "1", "hello")

    def test_empty_message_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            normalize_message("\n\u202e")


if __name__ == "__main__":
    unittest.main()
