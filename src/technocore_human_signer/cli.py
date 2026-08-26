from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from . import __version__
from .identity import MIN_PASSPHRASE_CHARS, create_identity, load_identity
from .protocol import BASE_URL, SignerError, ValidationError, did_from_private_key
from .receipt import create_receipt, load_receipt, write_receipt
from .request_file import create_request, load_request, write_request
from .transport import post_signed_request

DEFAULT_KEY_PATH = Path("identity.pem")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="technocore-safe",
        description="Prepare and manually approve signed Technocore messages.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init", help="manually create an encrypted DID identity")
    init_parser.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)

    did_parser = commands.add_parser("did", help="manually display the public DID")
    did_parser.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)

    prepare_parser = commands.add_parser(
        "prepare",
        help="create an unsigned request that an agent may safely prepare",
    )
    prepare_parser.add_argument("room")
    prepare_parser.add_argument("text")
    prepare_parser.add_argument("--output", type=Path, required=True)

    inspect_parser = commands.add_parser("inspect", help="validate and display an unsigned request")
    inspect_parser.add_argument("request_file", type=Path)

    verify_parser = commands.add_parser(
        "verify-receipt",
        help="verify a public receipt and its Ed25519 signature offline",
    )
    verify_parser.add_argument("receipt_file", type=Path)

    send_parser = commands.add_parser(
        "send",
        help="manually review, unlock, sign, and send one request",
    )
    send_parser.add_argument("request_file", type=Path)
    send_parser.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)
    send_parser.add_argument(
        "--receipt",
        type=Path,
        help="public receipt path (default: replace .request.json with .receipt.json)",
    )
    send_parser.add_argument("--timeout", type=float, default=20.0)
    return parser


def _print_request(request_file: Path) -> None:
    request = load_request(request_file)
    print(f"Destination: {BASE_URL}")
    print(f"Room:        {request.room}")
    print(f"SHA-256:     {request.request_sha256}")
    print("Message:")
    print(request.text)


def _require_interactive_terminal() -> None:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise SignerError(
            "send requires a human-operated interactive terminal; agents must stop after prepare"
        )


def _prompt_existing_passphrase(key_path: Path) -> str:
    return getpass.getpass(f"Passphrase for {key_path.expanduser().resolve()}: ")


def _default_receipt_path(request_file: Path) -> Path:
    name = request_file.name
    if name.endswith(".request.json"):
        name = name[: -len(".request.json")] + ".receipt.json"
    else:
        name += ".receipt.json"
    return request_file.with_name(name)


def run_command(args: argparse.Namespace) -> int:
    if args.command == "prepare":
        request = create_request(args.room, args.text)
        output = write_request(args.output, request)
        print(output)
        print(request.request_sha256)
        return 0

    if args.command == "inspect":
        _print_request(args.request_file)
        return 0

    if args.command == "verify-receipt":
        receipt = load_receipt(args.receipt_file)
        print("Valid Ed25519 signature and canonical receipt.")
        print(f"DID:       {receipt.did}")
        print(f"Room:      {receipt.room}")
        print(f"Sequence:  {receipt.seq}")
        print(f"Permalink: {receipt.permalink}")
        print("Note: seq and timestamp are server assertions and are not covered by the signature.")
        return 0

    _require_interactive_terminal()

    if args.command == "init":
        first = getpass.getpass(
            f"New identity passphrase ({MIN_PASSPHRASE_CHARS}+ characters): "
        )
        second = getpass.getpass("Confirm identity passphrase: ")
        if first != second:
            raise SignerError("passphrases do not match")
        did = create_identity(args.key, first)
        print(f"Created encrypted identity: {args.key.expanduser().resolve()}")
        print(f"Public DID: {did}")
        return 0

    if args.command == "did":
        private_key = load_identity(args.key, _prompt_existing_passphrase(args.key))
        print(did_from_private_key(private_key))
        return 0

    if args.command == "send":
        signing_request = load_request(args.request_file)
        receipt_path = args.receipt or _default_receipt_path(args.request_file)
        resolved_receipt = receipt_path.expanduser().resolve()
        if resolved_receipt.exists():
            raise ValidationError(f"refusing to overwrite existing receipt: {resolved_receipt}")
        _print_request(args.request_file)
        print(f"Receipt:     {resolved_receipt}")
        private_key = load_identity(args.key, _prompt_existing_passphrase(args.key))
        did = did_from_private_key(private_key)
        print(f"Signing DID: {did}")
        challenge = f"SEND {signing_request.request_sha256[:12]}"
        print("This action publishes the message publicly and cannot be recalled.")
        entered = input(f"Type {challenge} to sign and send: ")
        if entered != challenge:
            raise SignerError("confirmation did not match; nothing was sent")
        result = post_signed_request(
            private_key,
            signing_request,
            timeout=args.timeout,
        )
        receipt = create_receipt(
            signing_request,
            did=result.did,
            signature=result.signature,
            nonce=result.nonce,
            seq=result.seq,
            server_timestamp=result.server_timestamp,
        )
        try:
            written = write_receipt(resolved_receipt, receipt)
        except ValidationError as error:
            raise SignerError(
                f"message was published at {receipt.permalink}, but its receipt could not be saved: "
                f"{error}"
            ) from error
        print(f"Published: {receipt.permalink}")
        print(f"Receipt:   {written}")
        print(f"DID:       {receipt.did}")
        print(f"Nonce:     {receipt.nonce}")
        return 0
    raise SignerError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    try:
        return run_command(build_parser().parse_args(argv))
    except KeyboardInterrupt:
        print("Cancelled; nothing further was sent.", file=sys.stderr)
        return 130
    except SignerError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
