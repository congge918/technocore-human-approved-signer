from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .protocol import BASE_URL, ValidationError, normalize_message, validate_room

REQUEST_SCHEMA = "technocore-human-approved-request-v1"
MAX_REQUEST_BYTES = 32 * 1024
REQUEST_FIELDS = frozenset({"schema", "base_url", "room", "text", "request_sha256"})


@dataclass(frozen=True)
class SigningRequest:
    room: str
    text: str
    request_sha256: str


def _canonical_payload(room: str, text: str) -> bytes:
    payload = {
        "base_url": BASE_URL,
        "room": room,
        "schema": REQUEST_SCHEMA,
        "text": text,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def create_request(room: str, text: str) -> SigningRequest:
    valid_room = validate_room(room)
    normalized = normalize_message(text)
    digest = hashlib.sha256(_canonical_payload(valid_room, normalized)).hexdigest()
    return SigningRequest(valid_room, normalized, digest)


def request_to_dict(request: SigningRequest) -> dict[str, str]:
    return {
        "schema": REQUEST_SCHEMA,
        "base_url": BASE_URL,
        "room": request.room,
        "text": request.text,
        "request_sha256": request.request_sha256,
    }


def write_request(path: Path, request: SigningRequest) -> Path:
    resolved = path.expanduser().resolve()
    serialized = (
        json.dumps(request_to_dict(request), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(resolved, flags, 0o644)
        created = True
        with os.fdopen(descriptor, "wb") as request_file:
            descriptor = None
            request_file.write(serialized)
            request_file.flush()
            os.fsync(request_file.fileno())
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                resolved.unlink(missing_ok=True)
            except OSError:
                pass
        raise ValidationError(f"cannot create request file: {error}") from error
    return resolved


def load_request(path: Path) -> SigningRequest:
    resolved = path.expanduser().resolve()
    try:
        size = resolved.stat().st_size
        if size <= 0 or size > MAX_REQUEST_BYTES:
            raise ValidationError("request file has an unsafe size")
        raw = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("request file must be valid UTF-8") from error
    except OSError as error:
        raise ValidationError(f"cannot read request file: {error}") from error
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValidationError("request file must contain valid JSON") from error
    if not isinstance(payload, dict) or frozenset(payload) != REQUEST_FIELDS:
        raise ValidationError("request file has missing or unexpected fields")
    if any(not isinstance(value, str) for value in payload.values()):
        raise ValidationError("all request fields must be strings")
    if payload["schema"] != REQUEST_SCHEMA:
        raise ValidationError("unsupported request schema")
    if payload["base_url"] != BASE_URL:
        raise ValidationError("request destination must be exactly https://technocore.chat")
    request = create_request(payload["room"], payload["text"])
    if payload["request_sha256"] != request.request_sha256:
        raise ValidationError("request integrity check failed")
    return request
