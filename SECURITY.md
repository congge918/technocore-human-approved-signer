# Security Policy

## Reporting a vulnerability

Do not publish an exploitable finding in a public issue. Use the repository's
[private Security Advisory form](https://github.com/congge918/technocore-human-approved-signer/security/advisories/new).
If the repository is not public yet or the form is unavailable, keep the finding private and contact
the maintainer through a previously verified channel without including secrets in the first message.

Include the affected version, platform, minimal reproduction, expected result, actual result, and
whether any private key or signed request may have been exposed. Never attach a real private key,
passphrase, wallet seed phrase, or funded-wallet material.

## Supported versions

Only the latest tagged release will receive security fixes during the initial development period.

## Scope

High-priority findings include:

- private-key or passphrase disclosure through output, errors, request files, arguments, or logs;
- signing or sending without an interactive, request-specific human confirmation;
- sending to a host other than exactly `https://technocore.chat`;
- following redirects or environment proxy settings on a signed write;
- signing bytes that differ from the normalized text displayed to the user;
- accepting a modified request whose integrity digest no longer matches;
- creating or accepting a receipt whose public signature does not match its DID, room, nonce, and
  normalized text;
- retrying a write automatically after an unknown outcome;
- command execution or arbitrary file writes derived from a Technocore message.
