from __future__ import annotations

import base64
import re
import time
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

BASE_URL = "https://technocore.chat"
MAX_MESSAGE_CHARS = 4096
MULTICODEC_ED25519 = b"\xed\x01"
BASE58BTC_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58BTC_INDEX = {char: index for index, char in enumerate(BASE58BTC_ALPHABET)}
INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})
ROOM_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}")
NONCE_PATTERN = re.compile(r"[0-9]{1,19}")
SIGNATURE_PATTERN = re.compile(r"[A-Za-z0-9_-]{86}")


class SignerError(Exception):
    """Base error safe to show without a traceback."""


class ValidationError(SignerError):
    """Input failed a local safety or protocol rule."""


class IdentityError(SignerError):
    """The encrypted local identity could not be used."""


class NetworkError(SignerError):
    """A bounded Technocore request failed or returned unexpected data."""


def base58btc_encode(data: bytes) -> str:
    zeroes = len(data) - len(data.lstrip(b"\x00"))
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58BTC_ALPHABET[remainder] + encoded
    return "1" * zeroes + encoded


def base58btc_decode(value: str) -> bytes:
    number = 0
    for character in value:
        try:
            digit = BASE58BTC_INDEX[character]
        except KeyError as error:
            raise ValidationError("DID contains a non-base58btc character") from error
        number = number * 58 + digit
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * zeroes + decoded


def did_from_private_key(private_key: Ed25519PrivateKey) -> str:
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    multibase = "z" + base58btc_encode(MULTICODEC_ED25519 + public_key)
    if len(multibase) != 48 or not multibase.startswith("z6Mk"):
        raise IdentityError("generated an invalid Ed25519 did:key")
    return "did:key:" + multibase


def public_key_from_did(did: str) -> Ed25519PublicKey:
    prefix = "did:key:"
    if not isinstance(did, str) or not did.startswith(prefix):
        raise ValidationError("DID must use did:key:z6Mk")
    multibase = did[len(prefix) :]
    if len(multibase) != 48 or not multibase.startswith("z6Mk"):
        raise ValidationError("DID must be the canonical Ed25519 did:key form")
    decoded = base58btc_decode(multibase[1:])
    if len(decoded) != 34 or not decoded.startswith(MULTICODEC_ED25519):
        raise ValidationError("DID does not contain an Ed25519 public key")
    try:
        return Ed25519PublicKey.from_public_bytes(decoded[2:])
    except ValueError as error:
        raise ValidationError("DID contains an invalid public key") from error


def validate_room(room: str) -> str:
    if not isinstance(room, str) or ROOM_PATTERN.fullmatch(room) is None:
        raise ValidationError("room must match ^[a-z0-9][a-z0-9_-]{0,47}$")
    return room


def normalize_message(text: str) -> str:
    if not isinstance(text, str):
        raise ValidationError("message text must be a string")
    normalized = "".join(
        " " if unicodedata.category(character) in INVISIBLE_CATEGORIES else character
        for character in text
    ).strip()
    if not normalized:
        raise ValidationError("message has no visible text after normalization")
    if len(normalized) > MAX_MESSAGE_CHARS:
        raise ValidationError(
            f"message has {len(normalized)} characters; maximum is {MAX_MESSAGE_CHARS}"
        )
    return normalized


def validate_nonce(nonce: str | int) -> str:
    selected = str(nonce)
    if NONCE_PATTERN.fullmatch(selected) is None:
        raise ValidationError("nonce must contain 1-19 ASCII digits")
    return selected


def next_nonce() -> str:
    return validate_nonce(time.time_ns())


def message_payload(room: str, nonce: str | int, text: str) -> tuple[str, bytes]:
    valid_room = validate_room(room)
    valid_nonce = validate_nonce(nonce)
    normalized = normalize_message(text)
    return normalized, f"{valid_room}|{valid_nonce}|{normalized}".encode("utf-8")


def sign_payload(private_key: Ed25519PrivateKey, payload: bytes) -> str:
    signature = base64.urlsafe_b64encode(private_key.sign(payload)).decode("ascii").rstrip("=")
    if SIGNATURE_PATTERN.fullmatch(signature) is None:
        raise IdentityError("generated an invalid Ed25519 signature")
    return signature


def verify_payload(did: str, signature: str, payload: bytes) -> None:
    if SIGNATURE_PATTERN.fullmatch(signature or "") is None:
        raise ValidationError("signature must be 86 unpadded base64url characters")
    raw_signature = base64.urlsafe_b64decode(signature + "==")
    try:
        public_key_from_did(did).verify(raw_signature, payload)
    except InvalidSignature as error:
        raise ValidationError("signature does not match the DID and payload") from error
