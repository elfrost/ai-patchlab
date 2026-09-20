---
layout: default
title: "TencentCloud/Octop: security scan"
date: 2026-09-20
---

# TencentCloud/Octop — security scan

**Repository:** [TencentCloud/Octop](https://github.com/TencentCloud/Octop)
**Commit scanned:** `757fd12e`
**Scan date:** 2026-09-20
**Disclosure status:** withheld — reported privately by email (the repo's GitHub private vulnerability reporting is disabled, and its SECURITY.md forbids public issues). The finding is described here at class level only; the exact route set and the reachability chain stay withheld until the maintainer has had a chance to fix it.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 112 |
| Medium | 184 |
| Low | 0 |
| Info | 3 |

**Total findings:** 300 above the medium floor (3 are scan-coverage meta findings). One real issue, reported privately — and it is **not** one of the 297 tool findings. Of those 297, none survived curation as an exploitable vulnerability (the lone Critical is a valid dependency bump, covered below).

## Scan coverage

| Tool | Status | Detail |
| --- | --- | --- |
| `semgrep` | `partial` | Semgrep did not cover every file it was pointed at |
| `gitleaks` | `ran` | Ran without reporting a coverage problem. |
| `trivy` | `ran` | Ran without reporting a coverage problem. |
| `dependency-scan` | `error` | pip-audit scan did not complete successfully |
| `ai-security-review` | `not_run` | AI security review is disabled (ADR-010) |

**Coverage complete:** no, and this one needs two sentences before the findings.
**pip-audit timed out at 300 seconds** and produced nothing — but the Python
dependency surface was **not** left unexamined: Trivy read `uv.lock` and produced
the dependency CVEs discussed below (including the lone Critical), so the gap is a
redundant second opinion, not a blind spot. **Semgrep reported 50 errors, 0 of
them rule timeouts** — every one is a syntax / partial-parse error on a *non-Python*
file (three benchmark/skill YAML data files, five GitHub Actions workflows, seven
dashboard `.test.tsx` files, two Dockerfiles, several shell scripts, a Go `main`).
No first-party Python module was skipped, which matters because the real finding
lives in the Python API layer and that layer was fully read.

## The finding (class only)

The one real issue is **not** in any tool's output. It is an **authorization** gap,
and it is worth reading precisely because Octop's permission model is otherwise one
of the more carefully built in this series.

Octop is a **multi-user** self-hosted control plane. It ships a real permission
system: a catalogue of module keys (`backup`, `channels`, `connectors`,
`terminal`, `browser`, `desktop`, `storage_backends`, and two dozen more), a
`require_permission(key)` dependency factory, and a default-deny rule where a
non-admin user only reaches a module if that key is in their granted set. Admin
bypasses; everyone else is checked. New users onboarded through the invite flow are
created with the `USER` role and an **empty** permission set, so by construction they
can reach almost nothing. That is the right shape, and it is enforced consistently
across the API — with one exception.

The class, stated without a recipe: **one sensitive control-plane surface is gated
by authentication alone, not by any permission key — and no permission key for it
exists in the catalogue at all.** Every other module that touches something
dangerous sits behind `require_permission(...)`. This one sits behind "are you
logged in?", which for a multi-user box is a much weaker statement. A user who holds
*zero* permissions — the invite-onboarding default — still reaches it. The
confinement that *should* contain the blast radius is a per-user policy that is
**unset by default** (so it does not restrict), and the shipped container image
broadens that default scope well beyond any single user's own workspace.

This is the [inert-security-flag](mnemosyne-oss-mnemosyne.html) family turned
inside out. There the enforcing symbol existed but was never called; here the
enforcement pattern is applied *everywhere but one place*, and the one place has no
key to apply. It is also the [scan-the-seam](mljar-mercury.html) shape: the
project's own permission catalogue is the contract, and the finding is the single
route-group the catalogue forgot to include. When a codebase gates 27 surfaces one
way and 1 surface another way, the odd one out is almost always an oversight rather
than a decision — and reading the two against each other is what surfaces it, not
any single-file rule.

It is **post-authentication** — the attacker needs a valid account, which on a
multi-user instance is exactly what the invite flow hands out. I am withholding the
route set, the reachability chain, and the container-deployment specifics until the
maintainer has fixed it. The fix is small and does not require any new machinery:
the project already applies a control-tier permission to its other sensitive
features (`terminal`, `browser`, `desktop` are each gated), so closing the gap means
extending the model the project already follows to the one surface that skipped it —
not imposing a new one.

## Patterns observed

**Octop is well-built, and the finding is a single gap in an otherwise coherent
authorization model — not sloppiness.** The evidence is everywhere around it. The
JWT layer is default-deny at the middleware: every `/api/*` path requires a valid
token unless it is on a small, explicit exempt allowlist (setup wizard, health,
login, OAuth callbacks), and the exempt entries that *process* input carry their
own credential — the internal-MCP endpoints, for instance, verify a per-instance
secret token even though they sit outside the JWT gate. The setup wizard, the
classic takeover surface on a self-hosted app, is genuinely hardened: it requires a
CLI-generated one-time password by default (`require_setup_password=True`), binds
`127.0.0.1` by default, closes itself once a single user exists (a second lockdown
middleware returns `503 {"setup_required": true}` until an admin is created), and
the shipped Docker entrypoint **creates the admin before the server ever starts
listening** — so the window a "setup race" would need does not exist in the default
image, and the generated password is a random 16-character strong one written to a
`chmod 600` credential file.

Two findings I chased hard and then discarded are worth naming, because they show
what "well-built" looks like under a microscope. The tar-extraction hits
(`tarfile.extractall` in the backup module) both pass `filter=tarfile.data_filter`
— the modern Python defense against extraction path traversal — so they are
[credited false positives](fast-agent.html). And the setup-takeover chain that
looked so promising collapsed the moment I [ran the remedy against the real
deployment](roflcoopter-viseron.html): the entrypoint pre-provisions the admin, and
every setup route re-checks `user_count == 0` server-side, so there is no reachable
state where an attacker completes the wizard. The finding that survived is the one
that *no* amount of reading the setup or backup code would have found — it lives in
the gap between the permission catalogue and one router that forgot to use it.

## Notes on the tool

**Zero of the 297 tool findings were an exploitable vulnerability, and the curation
is the usual catalogue.** The single Critical is Trivy's flag on `anyio 4.14.1`
([CVE-2026-63374](https://avd.aquasec.com/nvd/cve-2026-63374)) — a real, valid
dependency bump to `4.14.2`, but its own impact statement is narrow: TLS
certificate spoofing *only* for internationalized (non-ASCII) domain names *and*
only on a connection already redirected to a malicious server by other means. It is
worth applying as hygiene; it is not a hole in Octop's own code. The 112 Highs are
the recurring cast: **61 `sqlalchemy-execute-raw-query` + 31 `formatted-sql-query`**
are the [SQL-identifier false positive](mnemosyne-oss-mnemosyne.html) at series-record
volume — `migrate.py` is static DDL, and the repository layer builds every
`UPDATE … SET {', '.join(fields)}` from hardcoded `"col = ?"` literals with all
values bound as `?` (I read `_scope_filter` in the usage repo specifically: it
assembles `"ts >= ?"`, `"user_id = ?"`, `"agent_id = ?"` and returns the values in a
separate params list — no user data touches the SQL string). **Three
`run-shell-injection`** are `${{ github.ref_name }}` on a `push: tags` /
`workflow_dispatch` trigger — creating a tag needs push access, so the
[trigger decides the severity](lightseekorg-tokenspeed.html) and this is a CI
hardening nit, not an external vector. The `detected-ssh-password` and
`generic-api-key` hits are a doc placeholder (`sshpass -p '<password>'` in a deploy
guide), a `_SIGN_SECRET` the code explicitly comments as *public* signing material
required by a third-party MCP API, and a test fixture. Six `logger-credential-leak`
hits are the [domain-noun collision](superlinked-sie.html) — the functions are
*about* credentials but log only `.kind` and exception strings, never the secret.
The 184 mediums are the same texture: 54 mutable-action-tag rows (CI hygiene), 22
`dynamic-urllib-use`, 15 `use-defused-xml` on config parsing, and client-side
prototype-pollution on the dashboard's own state store.

The tool's real limitation here is the one it hits every time the finding is
architectural: **no rule can represent "one router uses `current_user` where its 27
siblings use `require_permission`."** The gap is an *absence* of an authorization
tier, spread across a router file, a permissions catalogue, and a default-policy
value that are each individually valid. That is — by my count — the seventeenth time
in this series the real finding was invisible to the scanners and visible only by
reading one surface against the project's own stated contract.

## Disclosure timeline

- 2026-09-20 — scan run; finding identified and verified against the source at `757fd12e`
- 2026-09-20 — reported privately by email to the address in SECURITY.md (GitHub private vulnerability reporting is disabled on the repo); detail withheld here pending a fix

## Reproduce

```bash
git clone https://github.com/TencentCloud/Octop /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/tencentcloud-octop --min-severity medium --ignore-samples
```

---

## More from this series

- **Previous scan:** [hydropix/TranslateBooksWithLLMs](hydropix-translatebookswithllms.html) — 2026-09-19, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 107 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
