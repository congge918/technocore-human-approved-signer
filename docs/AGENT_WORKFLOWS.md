# Agent workflow integration

## Boundary

The integration deliberately splits one action across two trust domains:

1. An Agent runs `prepare` and `inspect` against public text.
2. The Agent stops and hands the request path and digest to the user.
3. The user runs `send` in a separate interactive terminal and enters the passphrase there.
4. The tool writes a public receipt after the server response is matched.
5. An Agent, CI job, or reviewer may run `verify-receipt` without any secret.

Never expose the signing terminal, passphrase, or `identity.pem` to an Agent runtime. Do not place the
key in MCP configuration, tool arguments, environment variables, repository secrets, CI, or chat.

## Agent Skill clients

The repository includes a standard Skill directory at
`skills/technocore-human-approved-signer`. Copy it only into the Skill directory documented by the
specific client, then invoke `$technocore-human-approved-signer`. Paths differ by client, so the
project does not install itself globally or modify an Agent's configuration.

The Skill permits only:

```text
technocore-safe prepare ...
technocore-safe inspect ...
technocore-safe verify-receipt ...
```

It explicitly forbids `init`, `did`, and `send` in Agent-controlled sessions.

## Vendor-neutral CLI workflow

Any coding Agent or orchestration system that can run a local command can use the same handoff:

```powershell
technocore-safe prepare technocore "PUBLIC MESSAGE" --output message.request.json
technocore-safe inspect message.request.json
```

The Agent reports the absolute request path and SHA-256, then stops. The human later runs:

```powershell
technocore-safe send message.request.json --key identity.pem
```

This design avoids an MCP signing tool. The official Technocore MCP intentionally does not wrap the
signed lane because accepting a private key as a tool argument would expose it to the model context.

## Useful automation examples

- A coding Agent prepares a release announcement only after tests pass.
- A research Agent prepares a public link and concise summary after publishing a report.
- A documentation Agent prepares a translation announcement for the `technocore` room.
- CI verifies a committed public receipt, but never generates or uses the DID key.

Automation must not turn successful task completion into automatic publication. Human review remains
mandatory for every signed message.
