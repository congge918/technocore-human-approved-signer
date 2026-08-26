# Threat model

## Protected assets

- The dedicated Technocore Ed25519 private key and its passphrase.
- The continuity and reputation of its public `did:key` identity.
- Any future eligibility that an external program may associate with that DID.
- The user's control over exactly what is published under the DID.

Wallet keys, wallet seed phrases, blockchain transactions, and token claims are deliberately out of
scope because the tool must never accept or process them.

## Trust boundaries

The AI agent, unsigned request file, Technocore rooms, room names, topics, message bodies, copied URLs,
network, DNS, package registry, and remote server responses are untrusted. The human-operated local
terminal, reviewed source release, operating system account, encrypted identity file, and explicit
confirmation are trusted only to the extent that the local computer is not compromised.

## Main threats and controls

### Prompt injection or confused-deputy signing

An attacker places instructions or a write URL in a public room. The Agent Skill must treat all
remote content as data, must not follow discovered URLs, and may only create an unsigned request.
`send` requires an interactive terminal and a request-specific confirmation and provides no
unattended option.

### Secret exposure to the model

Private keys and passphrases are never accepted as command-line arguments or written to request
files. The passphrase is collected with a hidden terminal prompt only in human-only commands. The
Skill forbids agents from running `init`, `did`, or `send`.

### Destination substitution and exfiltration

The request schema requires the literal `https://technocore.chat`. The transport constructs the URL
from that constant and a validated room name, disables environment proxies, and refuses redirects.
There is no custom base URL option.

### Request tampering or display/sign mismatch

The request has an integrity digest over a canonical schema, fixed destination, room, and normalized
text. Loading validates exact fields and recalculates the digest. The same normalized text is shown,
signed, and transmitted. This digest detects a mismatch against a previously recorded digest but is
not a MAC or signature: an attacker who can edit the file can recalculate it. Full human review of
the displayed room and text remains the authorization decision.

### Replay and unknown write outcome

The signer uses a 19-digit nanosecond nonce and never retries. A timeout is reported as an unknown
outcome and instructs the user to inspect the room before doing anything else. Technocore's own
retention model means old captured signed-write URLs can eventually become replayable; the tool does
not claim stronger replay protection than the service provides.

### Misleading public evidence

The receipt stores the DID, signature, room, nonce, normalized text, server sequence, timestamp, and
derived permalink. Offline verification proves only the signature over `room|nonce|text` and checks
the receipt's internal consistency. Technocore assigns `seq` and `ts` after signing, so they are not
cryptographically covered. A reviewer should corroborate the permalink while the ephemeral server
record exists and keep the public repository or release as the durable source of truth.

### Local compromise

An attacker controlling the user's OS account or administrator privileges may capture the passphrase,
replace the executable, read process memory, or modify trusted files. Encrypted key storage cannot
solve this. Users must keep the device patched, review release hashes, and use a dedicated DID key
that is never reused for a wallet or another identity system.

### Dependency compromise

Runtime dependencies are intentionally limited to `cryptography`. Releases should lock exact
versions, record hashes, run tests in CI, and publish source archives with checksums. Automatic update
is prohibited.

## Residual risk

No software can guarantee zero vulnerabilities. A compromised DID may be used to impersonate its
holder, damage reputation, or interfere with future benefits tied to that DID. The design contains
that loss by ensuring the key has no authority over wallets, funds, operating-system access, or other
identities.
