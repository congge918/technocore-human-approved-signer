import json
import tempfile
import unittest
from pathlib import Path

from technocore_human_signer.protocol import ValidationError
from technocore_human_signer.request_file import (
    create_request,
    load_request,
    request_to_dict,
    write_request,
)


class RequestFileTests(unittest.TestCase):
    def test_round_trip_and_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "message.request.json"
            request = create_request("lobby", "hello\nworld")
            write_request(path, request)

            self.assertEqual(load_request(path), request)
            with self.assertRaises(ValidationError):
                write_request(path, request)

    def test_destination_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "message.request.json"
            payload = request_to_dict(create_request("lobby", "hello"))
            payload["base_url"] = "https://attacker.example"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_request(path)

    def test_extra_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "message.request.json"
            payload = request_to_dict(create_request("lobby", "hello"))
            payload["command"] = "run-me"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_request(path)

    def test_text_tampering_without_new_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "message.request.json"
            payload = request_to_dict(create_request("lobby", "hello"))
            payload["text"] = "changed"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_request(path)


if __name__ == "__main__":
    unittest.main()
