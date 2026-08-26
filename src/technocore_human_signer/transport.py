from __future__ import annotations

import json
import math
import ssl
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import __version__
from .protocol import (
    BASE_URL,
    NetworkError,
    did_from_private_key,
    message_payload,
    next_nonce,
    sign_payload,
)
from .request_file import SigningRequest

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_ERROR_BYTES = 16 * 1024


@dataclass(frozen=True)
class SignedPostResult:
    room: str
    did: str
    signature: str
    nonce: str
    text: str
    seq: int
    server_timestamp: str


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def create_secure_opener() -> OpenerDirector:
    return build_opener(
        ProxyHandler({}),
        NoRedirectHandler(),
        HTTPSHandler(context=ssl.create_default_context()),
    )


def _safe_detail(value: Any) -> str:
    return "".join(
        " " if unicodedata.category(character) in {"Cc", "Cf", "Cs", "Co", "Zl", "Zp"}
        else character
        for character in str(value)
    ).strip()


def _validate_timeout(timeout: float) -> float:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise NetworkError("timeout must be a finite number greater than zero")
    selected = float(timeout)
    if not math.isfinite(selected) or not 0 < selected <= 60:
        raise NetworkError("timeout must be greater than zero and at most 60 seconds")
    return selected


def post_signed_request(
    private_key: Ed25519PrivateKey,
    signing_request: SigningRequest,
    *,
    timeout: float = 20.0,
    opener: OpenerDirector | Any | None = None,
    nonce: str | None = None,
) -> SignedPostResult:
    selected_timeout = _validate_timeout(timeout)
    selected_nonce = nonce if nonce is not None else next_nonce()
    normalized, payload = message_payload(
        signing_request.room,
        selected_nonce,
        signing_request.text,
    )
    did = did_from_private_key(private_key)
    signature = sign_payload(private_key, payload)
    body = json.dumps(
        {
            "did": did,
            "sig": signature,
            "nonce": selected_nonce,
            "text": normalized,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    target = f"{BASE_URL}/r/{signing_request.room}?format=json"
    request = Request(
        target,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"technocore-human-approved-signer/{__version__}",
        },
    )
    selected_opener = opener or create_secure_opener()
    try:
        with selected_opener.open(request, timeout=selected_timeout) as response:
            raw_body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        raw_error = error.read(MAX_ERROR_BYTES + 1)
        detail = raw_error[:MAX_ERROR_BYTES].decode("utf-8", errors="replace")
        if len(raw_error) > MAX_ERROR_BYTES:
            detail += "..."
        raise NetworkError(
            f"Technocore returned HTTP {error.code}: {_safe_detail(detail or error.reason)}"
        ) from None
    except URLError as error:
        raise NetworkError(
            "Technocore request failed; the outcome is unknown. Read the room before retrying: "
            + _safe_detail(error.reason)
        ) from error
    except (TimeoutError, OSError) as error:
        raise NetworkError(
            "Technocore request failed or timed out; the outcome is unknown. "
            "Read the room before retrying: "
            + _safe_detail(error)
        ) from error
    if len(raw_body) > MAX_RESPONSE_BYTES:
        raise NetworkError("Technocore response exceeded the safety limit")
    try:
        response_payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NetworkError("Technocore returned an invalid JSON response") from error
    posted = _validate_post_response(
        response_payload,
        room=signing_request.room,
        did=did,
        nonce=selected_nonce,
        text=normalized,
    )
    return SignedPostResult(
        room=signing_request.room,
        did=did,
        signature=signature,
        nonce=selected_nonce,
        text=normalized,
        seq=posted["seq"],
        server_timestamp=posted["ts"],
    )


def _validate_post_response(
    response: Any,
    *,
    room: str,
    did: str,
    nonce: str,
    text: str,
) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("room") != room:
        raise NetworkError("Technocore returned data for a different room")
    messages = response.get("messages")
    if not isinstance(messages, list):
        raise NetworkError("Technocore response is missing the room messages")
    matches: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        item_nonce = item.get("nonce")
        nonce_matches = (
            isinstance(item_nonce, int)
            and not isinstance(item_nonce, bool)
            and item_nonce == int(nonce)
        )
        if item.get("from") == did and item.get("text") == text and nonce_matches:
            matches.append(item)
    if len(matches) != 1:
        raise NetworkError("Technocore response does not uniquely contain the signed message")
    posted = matches[0]
    sequence = posted.get("seq")
    timestamp = posted.get("ts")
    last_sequence = response.get("last_seq")
    count = response.get("count")
    if not (
        isinstance(sequence, int)
        and not isinstance(sequence, bool)
        and sequence > 0
        and isinstance(timestamp, str)
        and 0 < len(timestamp) <= 64
        and isinstance(last_sequence, int)
        and not isinstance(last_sequence, bool)
        and last_sequence >= sequence
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count >= 1
    ):
        raise NetworkError("Technocore returned invalid metadata for the signed message")
    return posted
