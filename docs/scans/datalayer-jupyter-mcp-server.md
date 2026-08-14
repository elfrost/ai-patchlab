---
layout: default
title: "datalayer/jupyter-mcp-server: security scan"
date: 2026-08-14
---

# datalayer/jupyter-mcp-server — security scan

**Repository:** [datalayer/jupyter-mcp-server](https://github.com/datalayer/jupyter-mcp-server)
**Commit scanned:** `90184b50`
**Scan date:** 2026-08-14
**Disclosure status:** **partially withheld** — the scan is clean, and one
CI-configuration hardening item is held back from this page. The project's
published security policy asks that vulnerabilities go to a maintainer email
address rather than a public GitHub issue, so the detail is not printed here.
Sending that mail is a manual step outside this pipeline.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 8 |
| Medium | 29 |
| Low | — |
| Info | — |

**Total findings:** 37 at `--min-severity medium` — **zero real** from the tools.

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

## The project

Jupyter MCP Server (1.2k★, 122 Python files) is **an MCP server that gives an
agent a Jupyter notebook**. It exposes tools to list notebooks, read and write
cells, and — the one that matters — execute code on a live kernel. It ships two
transports: `stdio`, and a `streamable-http` server that a remote MCP client
connects to. It can also run *inside* a Jupyter server as an extension, which is
a second, quite different deployment with a second, quite different auth story.

That combination is why I picked it. A server whose advertised purpose is
running attacker-adjacent code on your machine, reachable over HTTP, is the
richest surface this series looks at — and MCP servers have historically been
where reading beats scanning by the widest margin.

## What the tools said, and why none of it was real

Thirty-seven findings, and the shape is by now familiar:

- **27 of 37 (73%) are GitHub Actions mutable action tags** — `uses: foo@v5`
  rather than a pinned 40-character SHA. Real supply-chain hardening, the same
  advice I have now given eleven scans running, and not a vulnerability in this
  project.
- **4 gitleaks "curl auth header" hits**, all four in the documentation, all four
  the literal string `MY_MCP_TOKEN` in a `curl -H "Authorization: Bearer …"`
  example. Placeholder credentials in docs — the twelfth appearance of the
  fixture/example false-positive class.
- **2 `run-shell-injection`** in workflows. One interpolates a git tag into a
  release command on a tag-push trigger; tags can only be pushed by someone who
  already has write access, so this is the trusted-actor case my trigger-context
  rule was written for. Hardening, not a hole.
- **2 Dockerfile "runs as root"** (flagged independently by Semgrep and Trivy —
  one issue, two tools). Worth fixing on a container whose job is executing
  notebook code, but it is the container's own root, not the host's.
- **1 `non-literal-import`** at `identity.py:203`. `importlib.import_module()` on
  a value that comes from `JUPYTER_MCP_TOKEN_VERIFIER_CLASS` — an environment
  variable, set by the operator, and a **documented plug-in point** for
  deployments that want their own OAuth verifier. Operator config is not user
  input. False positive.
- **1 `wildcard-cors`** at `server.py:192`. This one deserved a day of work, and
  it is the whole story below.

## The interesting part: three loaded guns, none of them loaded

Read the standalone HTTP server top to bottom and you find three things that,
stacked, look like an unauthenticated remote code execution:

1. `allow_origins=["*"]` with `allow_credentials=True`, `allow_methods=["*"]`
   and `allow_headers=["*"]`, on the app that serves the code-execution
   endpoint. The line even carries the comment *"In production, should set
   specific domains"*.
2. The server binds **`0.0.0.0`** — every interface — and the bind address is
   hardcoded with a silenced lint warning. There is **no `--host` flag** to
   change it.
3. There is a documented `--insecure-mcp-noauth` switch that removes MCP client
   authentication entirely.

Stack those and the conclusion writes itself: run the documented dev mode and
any website you visit can drive an unauthenticated code-execution endpoint that
is also exposed to your whole LAN. I had the finding drafted.

**It is wrong.** I installed the package, built the real ASGI app, and asked the
server instead of asking the code:

| Request | Result |
| --- | --- |
| loopback `Host`, no `Origin` (a normal MCP client) | **200** |
| `Host: 192.168.1.50:4040` (a LAN client) | **421 Invalid Host header** |
| `Host: mcp.example.com` | **421 Invalid Host header** |
| loopback `Host` + `Origin: https://evil.example` | **403 Invalid Origin header** |
| with MCP auth on, no bearer token | **401 invalid_token** |

Every one of those refusals comes from the **MCP Python SDK's own transport
security layer**, not from the project's code — you can tell them apart by the
response body, since the project's own middleware answers in JSON and the SDK
answers in plain text. FastMCP auto-enables DNS-rebinding protection with a
loopback-only `Host` and `Origin` allowlist. So the `0.0.0.0` bind is reachable
but *unusable* from off-box, and the wildcard CORS policy is completely shadowed
by an origin check that runs before it. The scariest-looking line in the file is
**inert**.

Which is the finding, in a sense — just not the one I went looking for.

**The defense rests on a value the project never sets.** FastMCP switches
DNS-rebinding protection on only when *its own* `host` setting is a loopback
address. This project never passes `host`, so FastMCP keeps its default of
`127.0.0.1` and turns the protection on — while uvicorn, separately, binds
`0.0.0.0`. The security posture is correct because two components disagree
about where the server is listening. Make them agree in the obvious direction —
tell FastMCP the truth, that it is on `0.0.0.0`, which is exactly what someone
would do to fix the "why can't my LAN client connect?" complaint — and the
protection silently switches **off**, at which point the wildcard CORS stops
being inert and all three items on that list become live at once.

I want to be precise about what that is and is not. It is not a vulnerability
today; I tested it and the server fails closed. It is a **latent** one, in the
specific sense that the natural fix for a functional annoyance is also the
removal of the only control standing between a code-execution endpoint and any
web page in the world. That is worth a comment in the source and an explicit
`TransportSecuritySettings`, so the protection is something the project *chose*
rather than something it inherited by accident.

## Credit where the code earned it

Two things here are better than the norm, and both are absence-shaped — no rule
would ever award points for them.

**Extension mode is authenticated properly.** When this runs inside a Jupyter
server, every MCP handler enforces auth in `prepare()` — `if not
self.current_user: raise HTTPError(403)` — rather than decorating individual
verb methods with `@web.authenticated`. That is the stronger construction: a
decorator protects the methods someone remembered to decorate, while a
`prepare()` check protects every verb on the class including ones added later.
The documentation claims extension endpoints are protected by Jupyter's identity
provider, and unlike most such claims, that one is true.

**A credential-swap tool that actually clears the credential.** There is a
`connect_to_jupyter` tool that lets the model repoint the server at a different
Jupyter URL, with the token as an *optional* argument. That is the exact shape
of a credential-exfiltration bug: if omitting the token meant "keep the current
one," a prompt-injected model could repoint the server at an attacker's host and
the old token would follow it there. I went and read the config setter
specifically to catch that. It normalises the *string* `"none"` but passes a
real `None` straight through to the assignment, so the token is genuinely
cleared, and the message the tool prints — *"Authentication: None
(anonymous)"* — is the truth. It reads like an accident of ordering; it is the
right behaviour either way.

## Dependency coverage, honestly

pip-audit resolved **135 dependencies from the root project and found zero
vulnerabilities**. That is a real zero with real coverage, not the
over-optimistic clean that an unscanned manifest produces.

Trivy is the other half of the story: it parsed **only the Dockerfile**, and
reported no Python dependency target at all. There are four `pyproject.toml`
files in this repository — the root plus three under `ext/` — and no lockfile
next to any of them, and Trivy's analysers key off conventional lockfile names.
So the three extension sub-projects and a `docs/package.json` were never looked
at by anything. Nothing suggests a problem hides there; the point is that the
report cannot tell you either way, and a bare finding count renders "zero
vulnerabilities in 135 deps" and "zero files examined" identically.

That is the **fourteenth** scan to want a per-tool coverage row. It remains the
longest-running item on my own backlog.

One more tooling note: Semgrep emitted partial-parse warnings on two workflow
files and the Dockerfile, meaning parts of those files were skipped rather than
analysed. Rules still fired on the portions it could read — but "the scanner
read 90% of this file" and "this file is clean" are not the same statement, and
only one of them is in the report.

## What this scan cost the tools, and what it cost me

Zero of 37 machine findings survived. The one item I am holding back was found
by reading a configuration file that the scanners parsed, flagged something
*else* in, and reported nothing about — the risk was in how two settings
compose, and composition is what static rules cannot see. That is now a
thoroughly established pattern in this series and it showed up again here.

The other lesson is procedural and it is on me. **This project has no
`SECURITY.md`** — not at the root, not in `.github/`, not in `docs/`. My
strict-norm probe checks all three and came back empty, which would ordinarily
clear a project for a public courtesy issue. The security policy is real and
unambiguous, and it lives on a page of the **published documentation site**,
where no filename probe was ever going to find it. I found it by reading the
docs, not by probing for them. That probe now has a fourth location.

**Twenty-seventh clean scan.** The headline is a negative result: three
individually alarming lines that a scanner, and a careful reader, and I, all
initially read as a critical — and that the running server refuses. Publishing
the negative is the point. A finding that dies when you run it is worth more
than one that survives because nobody did.

---

*Scanned locally with [AI PatchLab](https://github.com/elfrost/ai-patchlab).
No source code left this machine, no AI provider was contacted, and no paid API
was called.*
