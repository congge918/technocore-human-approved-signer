from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .protocol import (
    BASE_URL,
    SIGNATURE_PATTERN,
    ValidationError,
    message_payload,
    verify_payload,
)
from .request_file import SigningRequest, create_request

RECEIPT_SCHEMA = "technocore-human-approved-receipt-v1"
TOOL_NAME = "technocore-human-approved-signer"
TOOL_REPOSITORY = "https://github.com/congge918/technocore-human-approved-signer"
MAX_RECEIPT_BYTES = 32 * 1024
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "service",
        "room",
        "did",
        "signature",
        "nonce",
        "text",
        "seq",
        "server_timestamp",
        "permalink",
        "request_sha256",
        "tool",
    }
)
TOOL_FIELDS = frozenset({"name", "version", "repository"})


@dataclass(frozen=True)
class SignedReceipt:
    room: str
    did: str
    signature: str
    nonce: str
    text: str
    seq: int
    server_timestamp: str
    permalink: str
    request_sha256: str
    tool_version: str


def receipt_permalink(room: str, seq: int) -> str:
    return f"{BASE_URL}/humans#r/{room}/{seq}"


def create_receipt(
    signing_request: SigningRequest,
    *,
    did: str,
    signature: str,
    nonce: str,
    seq: int,
    server_timestamp: str,
) -> SignedReceipt:
    receipt = SignedReceipt(
        room=signing_request.room,
        did=did,
        signature=signature,
        nonce=nonce,
        text=signing_request.text,
        seq=seq,
        server_timestamp=server_timestamp,
        permalink=receipt_permalink(signing_request.room, seq),
        request_sha256=signing_request.request_sha256,
        tool_version=__version__,
    )
    validate_receipt(receipt)
    return receipt


def receipt_to_dict(receipt: SignedReceipt) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "service": BASE_URL,
        "room": receipt.room,
        "did": receipt.did,
        "signature": receipt.signature,
        "nonce": receipt.nonce,
        "text": receipt.text,
        "seq": receipt.seq,
        "server_timestamp": receipt.server_timestamp,
        "permalink": receipt.permalink,
        "request_sha256": receipt.request_sha256,
        "tool": {
            "name": TOOL_NAME,
            "version": receipt.tool_version,
            "repository": TOOL_REPOSITORY,
        },
    }


def validate_receipt(receipt: SignedReceipt) -> SignedReceipt:
    if isinstance(receipt.seq, bool) or not isinstance(receipt.seq, int) or receipt.seq <= 0:
        raise ValidationError("receipt sequence must be a positive integer")
    if (
        not isinstance(receipt.server_timestamp, str)
        or not receipt.server_timestamp
        or len(receipt.server_timestamp) > 64
    ):
        raise ValidationError("receipt server timestamp is invalid")
    if not isinstance(receipt.tool_version, str) or not receipt.tool_version:
        raise ValidationError("receipt tool version is invalid")
    normalized, payload = message_payload(receipt.room, receipt.nonce, receipt.text)
    if normalized != receipt.text:
        raise ValidationError("receipt text is not in canonical single-line form")
    if SIGNATURE_PATTERN.fullmatch(receipt.signature or "") is None:
        raise ValidationError("receipt signature has an invalid format")
    verify_payload(receipt.did, receipt.signature, payload)
    expected_request = create_request(receipt.room, receipt.text)
    if (
        SHA256_PATTERN.fullmatch(receipt.request_sha256 or "") is None
        or receipt.request_sha256 != expected_request.request_sha256
    ):
        raise ValidationError("receipt request digest does not match its room and text")
    if receipt.permalink != receipt_permalink(receipt.room, receipt.seq):
        raise ValidationError("receipt permalink does not match its room and sequence")
    return receipt


def write_receipt(path: Path, receipt: SignedReceipt) -> Path:
    validate_receipt(receipt)
    resolved = path.expanduser().resolve()
    serialized = (
        json.dumps(receipt_to_dict(receipt), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(resolved, flags, 0o644)
        created = True
        with os.fdopen(descriptor, "wb") as receipt_file:
            descriptor = None
            receipt_file.write(serialized)
            receipt_file.flush()
            os.fsync(receipt_file.fileno())
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                resolved.unlink(missing_ok=True)
            except OSError:
                pass
        raise ValidationError(f"cannot create receipt file: {error}") from error
    return resolved


def load_receipt(path: Path) -> SignedReceipt:
    resolved = path.expanduser().resolve()
    try:
        size = resolved.stat().st_size
        if size <= 0 or size > MAX_RECEIPT_BYTES:
            raise ValidationError("receipt file has an unsafe size")
        raw = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("receipt file must be valid UTF-8") from error
    except OSError as error:
        raise ValidationError(f"cannot read receipt file: {error}") from error
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValidationError("receipt file must contain valid JSON") from error
    if not isinstance(payload, dict) or frozenset(payload) != RECEIPT_FIELDS:
        raise ValidationError("receipt file has missing or unexpected fields")
    tool = payload.get("tool")
    if not isinstance(tool, dict) or frozenset(tool) != TOOL_FIELDS:
        raise ValidationError("receipt tool metadata has missing or unexpected fields")
    if payload["schema"] != RECEIPT_SCHEMA or payload["service"] != BASE_URL:
        raise ValidationError("receipt schema or service is unsupported")
    if tool["name"] != TOOL_NAME or tool["repository"] != TOOL_REPOSITORY:
        raise ValidationError("receipt tool metadata is not recognized")
    string_fields = (
        "room",
        "did",
        "signature",
        "nonce",
        "text",
        "server_timestamp",
        "permalink",
        "request_sha256",
    )
    if any(not isinstance(payload[field], str) for field in string_fields):
        raise ValidationError("receipt contains a field with the wrong type")
    if not isinstance(tool["version"], str):
        raise ValidationError("receipt tool version must be a string")
    receipt = SignedReceipt(
        room=payload["room"],
        did=payload["did"],
        signature=payload["signature"],
        nonce=payload["nonce"],
        text=payload["text"],
        seq=payload["seq"],
        server_timestamp=payload["server_timestamp"],
        permalink=payload["permalink"],
        request_sha256=payload["request_sha256"],
        tool_version=tool["version"],
    )
    return validate_receipt(receipt)
