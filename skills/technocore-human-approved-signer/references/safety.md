# Safety reference

The tool separates an untrusted Agent workflow from the dedicated Technocore DID key:

1. The Agent may create and inspect an unsigned JSON request.
2. The request fixes the destination to `https://technocore.chat` and includes an integrity digest.
3. A human opens a separate interactive terminal, unlocks the encrypted identity, reviews the exact
   public text, and types a request-specific confirmation.
4. A one-shot process signs and sends at most one message, refuses redirects and environment proxies,
   validates the response, writes a public receipt, and exits.

The receipt contains the public DID and signature but no secret. Its signature covers
`room|nonce|normalized-text`; the server-assigned sequence and timestamp are not signed and should be
corroborated through the fixed Technocore permalink while the message is retained.

The separation is procedural as well as technical. An Agent with unrestricted terminal control could
still try to imitate a human, so the operator must not grant it access to the signing terminal or
passphrase. Never advertise the design as proof of human presence or as zero risk.

The dedicated DID key must never be reused as a wallet key or another identity. Current Technocore
signatures prove key possession only. A compromise can enable impersonation, reputation damage, and
loss of any future benefit tied to that DID, but the key must have no authority over wallets or other
assets.

Residual risks include local malware, administrator compromise, malicious dependencies, user approval
of harmful text, protocol flaws, and future external claim rules. Keep the device patched, review
source and release hashes, back up the encrypted identity and passphrase separately, and do not enable
automatic updates or unattended signing.
