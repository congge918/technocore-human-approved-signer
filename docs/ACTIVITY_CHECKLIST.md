# FLOP / Technocore activity evidence checklist

This checklist documents a useful Technocore integration and a public evidence trail. It does not
guarantee eligibility or a reward; FLOP Labs controls any final rules, snapshot, and allocation.

## 1. Publish useful work

- Publish this repository at `https://github.com/congge918/technocore-human-approved-signer`.
- Keep it public, include the security policy and tests, and record the exact release tag or full
  commit hash you are announcing.
- Demonstrate one real Agent workflow: Agent prepares a request, human approves it, and a second
  process verifies the public receipt.

## 2. Create one dedicated DID

Run `technocore-safe init --key identity.pem` yourself. Use a unique passphrase and never reuse a
wallet key, seed phrase, or identity key. Back up the encrypted file and passphrase separately.

## 3. Publish a signed introduction

Prepare a short public introduction in `lobby`, then send it from the human terminal. Keep the text
factual and avoid promises about an airdrop.

Suggested structure:

```text
Hello from a human-approved Agent workflow. This dedicated DID will publish reviewed Technocore integration updates; its private key never enters an Agent or wallet workflow.
```

## 4. Sign the contribution link

After the repository and commit are public, prepare one message in the `technocore` room. Include:

- the public repository URL;
- the exact release tag or full commit URL;
- what Agent workflows the tool integrates with;
- the concrete security boundary: Agent prepares, human signs, anyone verifies;
- a note that it is an independent community tool.

Example structure, to be edited after publication:

```text
I published an independent human-approved Technocore signing integration for Agent workflows: REPOSITORY_URL at COMMIT_URL. Agents prepare strict unsigned requests, a human approves each send in a local terminal, and anyone can verify the public Ed25519 receipt offline. No wallet keys or unattended signing.
```

## 5. Keep verifiable evidence

- Save the generated `.receipt.json` file.
- Run `technocore-safe verify-receipt FILE` and capture the successful output.
- Open the receipt permalink and confirm the room, DID, text, nonce, and sequence while the message
  remains available.
- Commit the receipt in a follow-up commit if you want a durable copy. The original signed message
  should point to the already-public code commit, avoiding a circular hash claim.
- Save screenshots only as supplementary evidence; the repository, signed text, signature, and
  permalink are the stronger machine-readable trail.

## 6. Share the integration

Publish an X post or thread that explains the real utility, links the repository, names the public
DID, and links the signed Technocore record. Tag the official account only where relevant and avoid
spam or repeated self-messages. A real integration and demonstration are stronger evidence than
high-volume posting.

Before any future token claim, verify the announcement and claim domain through official FLOP Labs
channels. Never enter this DID passphrase, a wallet seed phrase, or a wallet private key into a claim
site.
