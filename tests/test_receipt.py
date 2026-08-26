import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from technocore_human_signer.protocol import (
    ValidationError,
    did_from_private_key,
    message_payload,
    sign_payload,
)
from technocore_human_signer.receipt import (
    create_receipt,
    load_receipt,
    receipt_to_dict,
    write_receipt,
)
from technocore_human_signer.request_file import create_request


class ReceiptTests(unittest.TestCase):
    def _receipt(self):
        key = Ed25519PrivateKey.generate()
        request = create_request("technocore", "Published a safe Agent Skill")
        _, payload = message_payload(request.room, "123", request.text)
        return create_receipt(
            request,
            did=did_from_private_key(key),
            signature=sign_payload(key, payload),
            nonce="123",
            seq=42,
            server_timestamp="2026-08-25T01:02:03.000000Z",
        )

    def test_round_trip_verifies_signature_and_refuses_overwrite(self) -> None:
        receipt = self._receipt()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contribution.receipt.json"
            write_receipt(path, receipt)

            self.assertEqual(load_receipt(path), receipt)
            with self.assertRaises(ValidationError):
                write_receipt(path, receipt)

    def test_text_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contribution.receipt.json"
            payload = receipt_to_dict(self._receipt())
            payload["text"] = "tampered"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_receipt(path)

    def test_permalink_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contribution.receipt.json"
            payload = receipt_to_dict(self._receipt())
            payload["permalink"] = "https://attacker.example/"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_receipt(path)

    def test_receipt_contains_no_private_key_material(self) -> None:
        serialized = json.dumps(receipt_to_dict(self._receipt())).lower()
        self.assertNotIn("private", serialized)
        self.assertNotIn("passphrase", serialized)
        self.assertNotIn("seed", serialized)


if __name__ == "__main__":
    unittest.main()
