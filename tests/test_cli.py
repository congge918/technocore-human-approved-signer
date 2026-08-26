import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from technocore_human_signer.cli import main
from technocore_human_signer.protocol import did_from_private_key, message_payload, sign_payload
from technocore_human_signer.receipt import create_receipt, write_receipt
from technocore_human_signer.request_file import create_request, load_request


class CliTests(unittest.TestCase):
    def test_agent_safe_prepare_works_without_tty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "request.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["prepare", "lobby", "hello", "--output", str(output)])

            self.assertEqual(code, 0)
            self.assertEqual(load_request(output).text, "hello")

    def test_send_refuses_noninteractive_input_before_reading_secrets(self) -> None:
        stderr = io.StringIO()
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stderr.isatty", return_value=False),
            redirect_stderr(stderr),
        ):
            code = main(["send", "missing.request.json", "--key", "missing.pem"])

        self.assertEqual(code, 2)
        self.assertIn("human-operated interactive terminal", stderr.getvalue())

    def test_public_receipt_verification_works_without_tty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            key = Ed25519PrivateKey.generate()
            request = create_request("technocore", "hello")
            _, payload = message_payload(request.room, "123", request.text)
            receipt = create_receipt(
                request,
                did=did_from_private_key(key),
                signature=sign_payload(key, payload),
                nonce="123",
                seq=42,
                server_timestamp="2026-08-25T01:02:03.000000Z",
            )
            path = Path(temp_dir) / "message.receipt.json"
            write_receipt(path, receipt)
            stdout = io.StringIO()
            with (
                patch("sys.stdin.isatty", return_value=False),
                patch("sys.stderr.isatty", return_value=False),
                redirect_stdout(stdout),
            ):
                code = main(["verify-receipt", str(path)])

            self.assertEqual(code, 0)
            self.assertIn("Valid Ed25519 signature", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
