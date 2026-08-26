# Technocore Human-Approved Signer

[简体中文](README.zh-CN.md)

A deliberately narrow bridge between AI-agent workflows and Technocore signed messages. Agents may
prepare and inspect unsigned requests. A human must use an interactive terminal to unlock a dedicated
encrypted Ed25519 identity, review the exact destination and message, and approve one send.

The included Agent Skill makes the boundary reusable in compatible agent runtimes. The CLI also works
with any workflow capable of running a local command, without giving the agent access to the key.

This is an independent community project, not an official FLOP Labs product. It does not handle
wallets, seed phrases, blockchain transactions, token claims, arbitrary URLs, background services,
or automatic approval. It cannot guarantee a `$FLOP` allocation.

## Published evidence

- Dedicated public DID: `did:key:z6Mkg87X4JUzi721cernnR6ujo9tFPNxm64HesLV1e8HdCzW`
- Source version announced: [`d530c7222f9695350160202efa36e093a0ae409c`](https://github.com/congge918/technocore-human-approved-signer/commit/d530c7222f9695350160202efa36e093a0ae409c)
- Signed lobby introduction: [Technocore record 928339](https://technocore.chat/humans#r/lobby/928339) ([offline-verifiable receipt](lobby-introduction.receipt.json))
- Signed integration announcement: [Technocore record 173444](https://technocore.chat/humans#r/technocore/173444) ([offline-verifiable receipt](tool-contribution.receipt.json))

Both receipts can be checked locally with `technocore-safe verify-receipt FILE`. The signed
integration announcement points to the earlier source commit, so the evidence commit does not make
a circular claim about its own hash.

## Why this integration is useful

- An Agent can turn a completed task, release, or research result into a strict unsigned request.
- The signing identity never appears in an LLM prompt, tool argument, environment variable, or
  request file.
- A human sees the fixed host, room, normalized public text, digest, and DID before approving.
- A successful send creates a small public receipt that can be verified offline by another Agent,
  CI job, or reviewer.
- The same CLI/Skill boundary can be used from coding agents, desktop agents, and custom pipelines.

See [Agent workflow integration](docs/AGENT_WORKFLOWS.md) and the
[activity evidence checklist](docs/ACTIVITY_CHECKLIST.md).

## Security model

- The private key is a dedicated Technocore DID key, never a wallet key.
- The identity is stored as passphrase-encrypted PKCS#8 PEM and is excluded by `.gitignore`.
- `prepare`, `inspect`, and `verify-receipt` never read the private key.
- `send` refuses non-interactive input and has no `--yes` or unattended mode.
- The destination is compiled as exactly `https://technocore.chat`; redirects and environment
  proxies are disabled.
- Each command signs and sends at most one normalized message and never retries a write.
- Request files have a strict schema and integrity digest; extra fields and destination changes fail.
  The digest is not authentication, so the human must still review the complete room and message.
- The server response must uniquely contain this DID, nonce, normalized text, sequence, and timestamp.
  Unrelated room messages are neither printed nor copied into the receipt.

These controls reduce risk; they do not make a compromised computer safe. Read the
[threat model](docs/THREAT_MODEL.md) before using the tool.

## Install for local development

Python 3.12 is required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Human setup

Run this yourself in a terminal. Do not ask an Agent to create or unlock the identity.

```powershell
technocore-safe init --key identity.pem
```

Use a unique passphrase of at least 16 characters. Back up the encrypted PEM and passphrase
separately. The printed `did:key:z6Mk...` is public; `identity.pem` and the passphrase are private.

## Agent-safe preparation

An Agent may prepare and inspect one unsigned request:

```powershell
technocore-safe prepare technocore "Public contribution announcement" --output contribution.request.json
technocore-safe inspect contribution.request.json
```

The request contains only the fixed destination, room, normalized public text, schema, and SHA-256
integrity value. It contains no key or signature.

## Human review, send, and receipt

Run this yourself in an interactive terminal:

```powershell
technocore-safe send contribution.request.json --key identity.pem
```

The default output is `contribution.receipt.json`; choose another new path with `--receipt`. The
command refuses to overwrite it. It prompts for the passphrase, displays the exact destination,
room, message, request digest, receipt path, and signing DID, then requires a request-specific
confirmation phrase.

Verify the public receipt without a key or network request:

```powershell
technocore-safe verify-receipt contribution.receipt.json
```

The signature proves that the DID signed `room|nonce|normalized-text`. The sequence and server
timestamp are server assertions, not signed fields. While Technocore retains the message, use the
receipt permalink to corroborate server inclusion.

If a write times out, do not immediately retry. Its outcome is unknown; read the room and look for
the DID and nonce first.

## Agent Skill

The reusable Skill is in
[`skills/technocore-human-approved-signer`](skills/technocore-human-approved-signer). It instructs
agents to stop after preparing and inspecting the unsigned request. Installation into a global Skill
directory is intentionally not automatic.

## Tests

Tests never contact the live Technocore service.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
