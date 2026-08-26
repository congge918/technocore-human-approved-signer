import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from technocore_human_signer.protocol import NetworkError, did_from_private_key
from technocore_human_signer.request_file import create_request
from technocore_human_signer.transport import NoRedirectHandler, post_signed_request


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.payload[:size]


class FakeOpener:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.request = None
        self.timeout = None

    def open(self, request, timeout: float):
        self.request = request
        self.timeout = timeout
        return FakeResponse(self.response)


class TransportTests(unittest.TestCase):
    def test_signed_post_is_fixed_to_official_origin_and_matches_response(self) -> None:
        key = Ed25519PrivateKey.generate()
        did = did_from_private_key(key)
        request = create_request("lobby", "hello")
        response = {
            "room": "lobby",
            "count": 1,
            "last_seq": 42,
            "messages": [
                {
                    "seq": 42,
                    "ts": "2026-08-25T01:02:03.000000Z",
                    "from": did,
                    "nonce": 123,
                    "text": "hello",
                }
            ],
        }
        opener = FakeOpener(response)

        result = post_signed_request(key, request, opener=opener, nonce="123")

        self.assertEqual(result.did, did)
        self.assertEqual(result.seq, 42)
        self.assertEqual(result.nonce, "123")
        self.assertEqual(result.text, "hello")
        self.assertEqual(opener.request.full_url, "https://technocore.chat/r/lobby?format=json")
        self.assertEqual(opener.request.method, "POST")
        body = json.loads(opener.request.data.decode("utf-8"))
        self.assertEqual(set(body), {"did", "sig", "nonce", "text"})
        self.assertNotIn("private", opener.request.data.decode("utf-8").lower())

    def test_redirect_handler_refuses_redirects(self) -> None:
        handler = NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://evil"))

    def test_mismatched_server_record_is_rejected(self) -> None:
        key = Ed25519PrivateKey.generate()
        response = {
            "room": "lobby",
            "count": 1,
            "last_seq": 42,
            "messages": [
                {
                    "seq": 42,
                    "ts": "2026-08-25T01:02:03.000000Z",
                    "from": did_from_private_key(key),
                    "nonce": 123,
                    "text": "different text",
                }
            ],
        }
        with self.assertRaises(NetworkError):
            post_signed_request(
                key,
                create_request("lobby", "hello"),
                opener=FakeOpener(response),
                nonce="123",
            )


if __name__ == "__main__":
    unittest.main()
