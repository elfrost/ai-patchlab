---
layout: default
title: "the-momentum/open-wearables: security scan"
description: "Security scan of the-momentum/open-wearables: 145 findings (134 above the medium floor), 2 real. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-03
---

# the-momentum/open-wearables — security scan

**Repository:** [the-momentum/open-wearables](https://github.com/the-momentum/open-wearables)
**Commit scanned:** `87f589316f26`
**Scan date:** 2026-08-03
**Disclosure status:** disclosed — [issue #1380](https://github.com/the-momentum/open-wearables/issues/1380)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 76 |
| Medium | 56 |
| Low | 0 |
| Info | 0 |

**Total findings:** 145 raw / 134 above the medium floor (2 real after curation)

Open Wearables (2.3k★, MIT) is a **self-hosted platform that unifies wearable
health data** — Garmin, Whoop, Oura, Strava, Suunto, Apple Health, Google Health
— behind one normalized API, with a developer dashboard, a mobile SDK, outgoing
webhooks via svix, Celery workers, and an MCP server for asking questions about
the data in natural language. It is the first scan in this series where the
asset at risk is **someone's heart rate, sleep, and body composition**, and the
README is explicit that the intended users include healthcare platforms
aggregating patient data and individuals self-hosting for privacy.

It is also, and I want to lead with this because it shapes everything below, a
**well-built codebase**. The two real findings are not the result of a team that
doesn't think about security. They are both cases of a boundary that is correct
in five places and absent in the sixth.

## Top findings

### 1. The Garmin webhook authenticates on the *presence* of a header, not its value

- **File:** `backend/app/services/providers/garmin/webhook_handler.py:95`
- **Tool:** none — no rule fired on this
- **Confidence:** high (empirically confirmed against the shipped method)

```python
def verify_signature(self, request: Request, body: bytes) -> bool:
    client_id = request.headers.get("garmin-client-id")
    if not client_id:
        ...
        return False
    return True
```

`settings.garmin_client_id` exists in config and is never consulted. Any
non-empty string authenticates. I ran the shipped method against a stub request
rather than trusting the read:

| `garmin-client-id` | `verify_signature()` |
| --- | --- |
| *(absent)* | `False` → 401 |
| `x` | **`True`** |
| `0` | **`True`** |
| `attacker-invented` | **`True`** |

The project's own test suite demonstrates it from the outside without meaning
to: `tests/api/v1/test_garmin_webhooks.py` — in a class named
`TestGarminWebhookAuth` — posts with `"test-client-id"` and `"x"`, neither of
which is configured anywhere, and asserts a 200.

`BaseWebhookHandler.handle()` makes `verify_signature` the *only* gate before
`parse_payload` → `dispatch`. Neither the unified route nor the deprecated
compat routes carry an auth dependency, and there is no router-level
`dependencies=`. Past it, for any user whose Garmin-side `userId` is known, sit
`process_deregistrations` (revokes the connection, fires an outgoing
`connection.revoked` event), `process_user_permissions` (overwrites the stored
OAuth scope), and the wellness/activity writers.

**Recommendation:** compare the value with `self._verify_token(...)` and fail
closed when unset — the shape `oura/` and `google/` already use. And because a
client ID is an identifier rather than a secret, the durable fix is a
high-entropy path segment on the registered callback URL, or IP allowlisting.

### 2. `docker-compose.prod.yml` publishes Postgres and Redis on `0.0.0.0`

- **File:** `docker-compose.prod.yml`
- **Tool:** none — Trivy flagged the Dockerfiles for running as root, not this
- **Confidence:** high

Postgres is published with `POSTGRES_PASSWORD: open-wearables` written as a
literal, and Redis is published with no `--requirepass` at all. Docker's short
`ports` syntax binds all interfaces, so on a host without a separate firewall
both are internet-reachable. Postgres holds the health data and the stored
provider OAuth tokens; Redis is the Celery broker, and write access to a broker
means queueing tasks for the workers to run.

There is a sharper edge on the Postgres half. The `db` service hardcodes
`POSTGRES_PASSWORD`, while `svix-server` in the same file reads
`${DB_PASSWORD:-open-wearables}`. An operator who sets `DB_PASSWORD` changes
svix's DSN and *not* the password the database actually boots with — the
documented-looking knob moves one of the two things it appears to move.

**Recommendation:** bind to `127.0.0.1:`, take the password from a required
variable, and turn on `--requirepass`. The app side already supports it —
`settings.redis_url` builds `rediss://` with URL-encoded credentials and has
tests.

## Patterns observed

**Both findings are the sixth instance of something done right five times.**
This is the shape I keep meeting and it deserves a name. The webhook framework
here is genuinely good: `verify_signature` is an `@abstractmethod`, so a
provider cannot silently inherit a permissive default; `handle()` is
verify → parse → dispatch with a hard 401 and no branch that skips the first
step; the shared helpers use `hmac.compare_digest`; and both Oura and Google
**fail closed when their secret is unconfigured**, which is precisely the
fail-open pattern I found on another project three days ago. Garmin is the one
provider whose scheme isn't HMAC — Garmin doesn't sign bodies — and it is exactly
there, at the seam where the framework's assumption stops holding, that the
check degraded into a presence test. The compose file is the same story: it uses
`expose:` for svix-server and the `:?` required-variable form for
`VITE_API_URL`, then uses plain `ports:` for the two datastores. The authors
demonstrably know both distinctions. Uniformity is the thing that failed, not
knowledge.

**A "presence check" is the tautological guard again.** On a desktop AI
companion last week the useless guard was a router-wide dependency asserting
`request.client.host` is loopback on a socket already bound to loopback. Here it
is `if not client_id: return False; return True`. Both read like security code,
both appear in the right place in the call graph, and neither constrains
anything an attacker controls. When a guard's failure mode is "the attacker
omits a header they could just as easily send", it is decoration. The
distinguishing question is cheap: *what value would fail this check, and can the
caller simply choose a different one?*

**The MCP subproject inverts the dependency numbers completely.** All 2
Criticals and ~33 of the Highs are dependency CVEs in `mcp/uv.lock` — Authlib
auth-bypass, FastMCP OAuthProxy consent, MCP SDK HTTP-transport and WebSocket
Host/Origin issues, PyJWT forgery, a Lua sandbox escape. Grouping by lockfile
first, as the [Kiln](kiln-ai-kiln.html) scan taught, changes the picture: `mcp/`
is not in either compose file. It's a **stdio** MCP server (`mcp.run()` with no
transport argument) that Claude Desktop or Cursor launches locally. The
server-transport CVEs describe HTTP and WebSocket transports it never starts;
the OAuthProxy CVE describes a component it never constructs; `lupa` and
`diskcache` are transitive dependencies of FastMCP that nothing imports. The
shipped `backend/uv.lock` produced exactly **one** advisory (a timing
side-channel in `ecdsa`, pulled in transitively by `python-jose`). The honest
version of this cluster is one sentence — *refresh `mcp/uv.lock`* — not
thirty-five findings. Same lesson as before, arriving from a new direction:
version-match is not reachability, and *which* lockfile a hit came from is often
the whole story.

**Credit where the scanners were loudest and most wrong.** The SNS handler
(`apple_xml/sns_service.py`) got flagged for SHA-1, and it is the *third*
confirmed instance of protocol-mandated SHA-1 in this series after the Chromium
cookie KDF and the RFC 6455 WebSocket handshake: AWS `SignatureVersion 1`
specifies SHA-1, the code selects SHA-256 whenever the version says 2, and — the
part that matters more — it regex-allowlists the signing-certificate URL
*before* fetching it, which is the SSRF defense that surface actually needs. The
`secret_key` setting has no default, so the app refuses to boot unconfigured
rather than shipping a guessable one. API keys are 128-bit random. And the
unscoped `get_user` I spent a while on turns out to be an
[advertised boundary](agentera-agently.html): the model's docstring says
*"Global API key for external service access"*, which is a defensible design for
a single-org self-hosted deployment and honestly labelled. The docstring settled
it in both directions this scan — it convicted the Garmin handler and it
acquitted the API key.

## Notes on the tool

1. **`pip-audit` produced no output file at all, and its meta finding was
   filtered out by `--min-severity medium`.** This is the *third* consecutive
   scan hitting this and it is now the top backlog item: scanner-infrastructure
   meta findings (`not-installed`, `scan-error`) must be exempt from the
   severity floor, because "the tool didn't run" and "the tool found nothing"
   currently render identically. Semgrep (244 KB), Gitleaks (25 KB) and Trivy
   (426 KB) were verified non-zero-byte per the
   [Clawith lesson](dataelement-clawith.html); pip-audit had nothing to verify.
2. **Group dependency findings by lockfile in the report itself.** The single
   most useful curation move here was noticing that 35 of 46 dependency hits
   came from a subproject that no compose file deploys. The report should print
   a per-lockfile breakdown, and flag lockfiles with no deployment reference.
3. **A "presence check" rule is worth writing.** `if not x: return False` /
   `return True` inside a function named `verify_*` / `authenticate_*` /
   `check_*` is a greppable shape, and it caught nothing here. Related: a rule
   for *a configured setting that exists and is never read by the function whose
   name matches it* — `settings.garmin_client_id` sitting unused two files from
   `verify_signature` is a strong signal.
4. **Compose port-binding needs a rule.** `ports: "N:N"` (no interface prefix)
   on a datastore image — postgres, redis, mongo, elasticsearch — is
   mechanically detectable, and the `expose:`-elsewhere-in-the-same-file
   contrast makes it a high-confidence call rather than a style nag.
5. **The `.mdx` / docs candidate-FP tier held again**: 21 of 31 Gitleaks hits
   were `curl -H "Authorization: Bearer ..."` examples in `docs/**/*.mdx`, and
   most of the rest were test fixtures and `.ai/specs/`. Zero real secrets.
6. **The SQL cluster was the [#1 recurring FP](mnemosyne-oss-mnemosyne.html)
   once more** — 14 hits, of which 9 are one-off migration scripts and the rest
   bind every value as a parameter, f-stringing only the *placeholder names*
   (`:record_id_{i}`) into a `VALUES` list. Still no rule that checks whether
   what's interpolated is a value or an identifier.
7. **36 `github-actions-mutable-action-tag` findings** dominated the medium
   band. Real supply-chain hardening, but at 36 instances of one rule in one
   file it drowns the band; these want collapsing into a single finding with a
   count.

## Disclosure timeline

- 2026-08-03 — scan run
- 2026-08-03 — [issue #1380](https://github.com/the-momentum/open-wearables/issues/1380) filed publicly (private vulnerability reporting is disabled on the repo and there is no `SECURITY.md` in the root, `.github/`, or `docs/` — a public issue was the only channel available)
- 2026-08-03 — public post (this page)

## Reproduce

```bash
git clone https://github.com/the-momentum/open-wearables /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target \
  --reports-dir ./reports/the-momentum-open-wearables --min-severity medium
```
