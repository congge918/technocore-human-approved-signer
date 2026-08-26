from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .protocol import IdentityError, did_from_private_key

MIN_PASSPHRASE_CHARS = 16
MAX_IDENTITY_BYTES = 64 * 1024


def create_identity(path: Path, passphrase: str) -> str:
    resolved = path.expanduser().resolve()
    if resolved.exists():
        raise IdentityError(f"refusing to overwrite existing identity: {resolved}")
    if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE_CHARS:
        raise IdentityError(
            f"identity passphrase must contain at least {MIN_PASSPHRASE_CHARS} characters"
        )

    private_key = Ed25519PrivateKey.generate()
    try:
        private_bytes = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(passphrase.encode("utf-8")),
        )
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as error:
        raise IdentityError(f"cannot prepare encrypted identity: {error}") from error

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(resolved, flags, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as identity_file:
            descriptor = None
            identity_file.write(private_bytes)
            identity_file.flush()
            os.fsync(identity_file.fileno())
        os.chmod(resolved, 0o600)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                resolved.unlink(missing_ok=True)
            except OSError:
                pass
        raise IdentityError(f"cannot create encrypted identity: {error}") from error
    return did_from_private_key(private_key)


def load_identity(path: Path, passphrase: str) -> Ed25519PrivateKey:
    resolved = path.expanduser().resolve()
    try:
        size = resolved.stat().st_size
        if size <= 0 or size > MAX_IDENTITY_BYTES:
            raise IdentityError("identity file has an unsafe size")
        private_bytes = resolved.read_bytes()
    except OSError as error:
        raise IdentityError(f"cannot read identity {resolved}: {error}") from error

    try:
        loaded = serialization.load_pem_private_key(
            private_bytes,
            password=passphrase.encode("utf-8"),
        )
    except (TypeError, ValueError) as error:
        raise IdentityError("incorrect passphrase or invalid encrypted identity") from error
    if not isinstance(loaded, Ed25519PrivateKey):
        raise IdentityError("identity must contain an encrypted Ed25519 private key")
    return loaded
