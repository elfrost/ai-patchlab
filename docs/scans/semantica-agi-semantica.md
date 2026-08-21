---
layout: default
title: "semantica-agi/Semantica: security scan"
description: "Security scan of semantica-agi/Semantica: 60 findings (60 above the medium floor), 1 real — withheld. Local-first curated review: Semgrep, Gitleaks, Trivy, pip-audit."
date: 2026-08-11
---

# semantica-agi/Semantica — security scan

**Repository:** [semantica-agi/semantica](https://github.com/semantica-agi/semantica)
**Commit scanned:** `7bf7474a`
**Scan date:** 2026-08-11
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-4643-wpgq-w329](https://github.com/semantica-agi/semantica/security/advisories/GHSA-4643-wpgq-w329),
embargoed pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 33 |
| Medium | 26 |
| Low | — |
| Info | — |

**Total findings:** 60 raw / 60 at `--min-severity medium` (1 real after curation — withheld, and not among the 60)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

**Zero of the 60 survived curation.** The one real item was found by hand, and no
rule in the scan represents it — it is an *absence*, and absences do not match
patterns. Fourth consecutive scan where the tools contributed nothing to the
finding that mattered.

## The project

Semantica (4.6k★, MIT) is **graph-native infrastructure for context and
accountable AI systems** — a knowledge-graph layer that agents read and write
through, built around the idea that an AI system should be able to show its work.
It ingests from files, databases, warehouses and repositories; extracts entities
and relations; resolves duplicates; reasons over the result; and keeps a
provenance trail so a downstream decision can be traced back to what supported
it. There is a Python library, a **Knowledge Explorer** (FastAPI backend + React
frontend) for exploring the graph interactively, an **MCP server** so Claude
Code, Cursor, Windsurf and others can query it, and integrations for the Agno
agent framework.

634 Python files, 31 MB, created 2025-06-25. It is the **most actively maintained
target the series has scanned on the human-contributor axis**: 40 merged pull
requests in the last 60 days from **nine distinct authors** plus Dependabot, and
30 closed issues in the same window. The commit I scanned is itself a merge of a
branch named `security/sparql-injection` — they were fixing a security issue the
week I arrived.

It is also, by some margin, the most **security-instrumented** repository in the
series: nine GitHub Actions workflows including CodeQL, Microsoft Defender for
DevOps, a dedicated `security-scan.yml`, and a `verify-action-pins.yml` that
enforces pinned action digests — plus a `.checkov.yaml` at the root and
`checkov:skip` annotations with *written justifications* in the deployment
manifests. This is a project that already runs the kind of tooling I point at
things.

## Channel, and what this write-up does not contain

`SECURITY.md` is real, current, and explicit: **do not open a public issue for a
vulnerability**. It nominates a GitHub Security Advisory as the primary channel
and commits to a 24-hour initial response for critical issues. Private
vulnerability reporting is **enabled**, so that channel actually works — I
checked before writing anything, because a policy pointing at a disabled feature
is a dead end I have hit before.

So this was filed privately, and **accepted on the first attempt**. That makes it
the sixth disclosure in this series filed with no human step: no email, no form,
no maintainer waiting on me to click something.

Consequently this page describes the finding **at class level only**. No
component, no file, no function, no configuration flag, no reproduction. That is
not coyness — a write-up that lets a reader reconstruct the bug is a public
disclosure wearing a hat. The detail is in the advisory, with the maintainers,
and it goes public here only after they have shipped a fix or told me they would
rather it stayed unpublished, in which case this page comes down entirely. There
is no deadline attached from my side.

## The one real finding, at class level

The class is **a protection that guards one surface and silently fails to reach
its sibling** — two ways into the same process, sharing the same authentication
helper, where a protection configured once, correctly, in the obvious place
covers the first and was assumed to cover the second. It does not, and the
second surface never consults it. Nothing about that is visible at the call
site; there is no line of code to look suspicious.

Three properties make it worth a maintainer's time:

**It is scoped narrowly, and I said so plainly in the report.** Deployments that
configure the product normally are **not affected** — I verified that
explicitly rather than asserting it, and the report leads with it. The exposure
exists in one explicitly-opt-in configuration, which the project ships as a
supported path and documents as local-only.

**The documented boundary is one an operator can fully honour and still be
exposed.** The instruction attached to that configuration is a reasonable one,
and someone who follows it exactly — changing nothing, exposing nothing — is
still reachable. That is the same inversion as the
[N.E.K.O finding](project-n-e-k-o-n-e-k-o.html): once a process is reachable from
a browser, "don't expose it" stops being a control, because the operator's own
browser is the thing doing the reaching. That one was fixed in about fourteen
hours with a 360-line middleware.

**The project already made this decision correctly once.** The first surface is
defended against precisely this, deliberately, with a comment explaining the
reasoning. The finding is not *you have not thought about this risk* — they
visibly have, more carefully than most — it is *you decided this once and the
decision did not travel*. That is the
[intra-repo differential](project-n-e-k-o-n-e-k-o.html) framing again, and it
remains the framing that gets merged, because it asks a maintainer to extend
their own reasoning rather than accept mine.

I confirmed it as a **differential rather than a claim**: the same server, in the
same configuration, in a single run, with one surface refusing a foreign caller
and the other serving it. Then end to end, driving a normal operation through the
product's own API and watching the data arrive somewhere it should not. Then the
negative half — the configuration that is *not* affected — because a report that
only demonstrates the bad case invites a maintainer to discover the scope
themselves and trust the rest of it less.

Severity **moderate**, and I argued it down to that in the report rather than
letting the advisory form flatter it. A development-configuration exposure is not
a production one, and saying so is what makes the rest of the report credible.

## What is well built

The authentication layer is genuinely good, and the finding's location is a
consequence of that — I went through the key handling looking for the usual
failures and did not find them.

**It fails closed where nearly everyone fails open.** When the API key is not
configured, protected routes refuse with a 503 and an error message telling the
operator what to set. They do not quietly serve unauthenticated traffic. The
number of projects in this series that get this exactly backwards — treating
"no key configured" as "no key required" — is large enough that
[I keep a note about it](rocketride-org-rocketride-server.html).

**Unauthenticated operation is a separate, explicit, loud opt-in.** It is not an
implicit consequence of an unset key; it is its own flag, and turning it on emits
a startup warning naming the risk. That is the correct shape: the insecure mode
exists, because local development needs it, and it costs you a deliberate act and
tells you what you did.

**Authentication is mounted structurally, not per-route.** Every router is
included with the auth dependency attached at include time, so an author adding a
new endpoint cannot forget a decorator — the failure mode simply is not
expressible. This is the same property that made
[AudioMuse's barrier](neptunehub-audiomuse-ai.html) hold up, and it is the single
highest-leverage thing a FastAPI project can do about authentication.

`hmac.compare_digest` on every key comparison, on both paths, not just the
obvious one.

**The Postgres vector store uses the driver's identifier-quoting API** —
`psycopg.sql.Identifier` for table names, bound parameters for values — which is
the textbook-correct construction and the thing the 44-finding SQL cluster below
is failing to recognise.

**The deployment manifests are the most carefully hardened in the series.**
`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, all
capabilities dropped, seccomp and AppArmor profiles, `automountServiceAccountToken:
false`, and **NetworkPolicies in both the Helm chart and the raw Kubernetes
manifests** — egress restricted to the database port, ingress admitted only from
the ingress-controller namespace. The Cloud Run service defaults its ingress
annotation to `internal-and-cloud-load-balancing` with a comment explaining that
`all` would permit unauthenticated public access. Several manifests carry inline
warnings against the permissive version of the very setting they configure.

One of the seven deployment templates does **disagree with its six siblings** on
a security-relevant default, in a way that looks exactly like the
[AudioMuse finding](neptunehub-audiomuse-ai.html). I traced it through to the
running behaviour and it does **not** produce an exploitable condition here,
because of a deliberate and well-reasoned default elsewhere in the application.
So: worth a one-line fix for consistency, not worth a security report. I am
describing it without specifics because those specifics sit close enough to the
withheld finding to be worth keeping quiet until the embargo lifts — the
whole-document rule applies to the parts of a write-up that *aren't* the
finding too. This is the majority-sibling test run to completion and returning
*no*, which is the outcome that test needs to be capable of producing if a
*yes* is going to mean anything.

The MCP server is **stdio JSON-RPC only** — no socket, no listener, no transport
to authenticate. A whole category of question closed in one grep.

## What the 60 findings were

**44 of 60 (73%) are the SQL identifier-interpolation cluster** — 27
`sqlalchemy-execute-raw-query`, 15 `formatted-sql-query`, 2 `avoid-sqlalchemy-text`,
spread across the ingestion adapters, the vector stores and the provenance store.
**Seventh appearance, and still the single largest source of noise in this
series.** I read three representative sites instead of enumerating forty-four:

- The provenance store interpolates a savepoint name generated as
  `f"sp_{uuid.uuid4().hex}"`. SQLite savepoint names cannot be bound as
  parameters, and a UUID is not attacker-influenced. Unusually clear-cut.
- The SQLite vector store interpolates a table name and a vector dimension into
  a `CREATE VIRTUAL TABLE` statement — DDL with internal configuration
  identifiers, which is again not parameterisable.
- The Postgres vector store, flagged repeatedly, is *already* using
  `psycopg.sql.Identifier` with bound values.

Values are bound; identifiers are internal. The rule cannot tell the difference,
and after seven scans I no longer expect it to.

**4 findings — including the only Critical — are in one CloudFormation template
under `cookbook/`**: a tutorial showing how to stand up a managed graph database.
Unrestricted security-group egress, public IP assignment on subnet instances,
and a missing customer-managed encryption key. This is a teaching artifact in a
directory named for teaching artifacts, in a product that is not an
infrastructure tool. It is the
[whose-running-system-is-this tier](observal-observal.html): nobody's production
account is described by this file. The Critical is a *tutorial* Critical.

**2 `insecure-file-permissions` are the active-harm inversion again.** Both are
`os.chmod(path, 0o700)` — restrictive, correct, deliberate. The rule fires on the
presence of a `chmod`, not on what it does, and acting on it would *widen*
permissions on a backup directory and a PID-file directory. The surrounding code
even opens with `O_NOFOLLOW` and a comment about symlink-clobber attacks. Third
recorded instance of a finding whose suggested remediation is a downgrade, after
[linkedin-mcp](stickerdaniel-linkedin-mcp-server.html) and
[codex-lb](soju06-codex-lb.html).

**5 `non-literal-import`** are the lazy-export machinery: a module-level
`__getattr__` that looks a name up in an explicit `_LAZY_EXPORTS` dict and raises
`AttributeError` when it is absent, so the set of importable modules is a
hardcoded allowlist. Deferring heavy optional dependencies is the entire point.

**2 `dynamic-urllib-use-detected`**: one is a constant GitHub releases URL in the
version-check command; the other is a library method that fetches URLs *the
caller supplied on purpose*, guarded by an explicit http/https scheme allowlist
whose docstring says it is there to prevent SSRF. No trust boundary is crossed
in either.

**1 `hardcoded-password-default-argument`** is a library function whose keyword
defaults spell out Neo4j's own well-known development defaults. It authenticates
to nothing.

**1 "ConfigMap with sensitive content"** on a ConfigMap holding a hostname, a
port and one non-secret configuration string — nothing sensitive is in it.
**1 insecure-transport JS rule** on a development-only file, where the address
in question is container-internal and never leaves the compose network.

## Patterns observed

**A codebase this well-defended relocates the finding rather than eliminating
it.** Every route authenticated structurally, fail-closed defaults, hardened
manifests, NetworkPolicies, CodeQL and Checkov in CI — and the finding is in none
of those places. It is in the gap *between* two mechanisms, each of which is
individually correct. This is the
[composite-finding property](arcreel-arcreel.html) in its purest form so far:
there is no defective line, only a boundary that two correct decisions leave
uncovered. Scanners find defective lines.

**Absence-shaped findings are structurally invisible to static analysis, and this
is now the fourth in a row.** A rule matches a thing that is present. Everything
that mattered in the last four scans was a thing that was *missing* — a check not
performed, a boundary not extended, a default not agreed on. I do not think this
is a coincidence of target selection; I think it is what is left after the
industry has spent a decade shipping rules for the present-shaped bugs.

**Running the negative case is half the report.** The most useful paragraph in
this disclosure is the one establishing which configuration is *not* affected. It
cost one extra run and it is what lets a maintainer trust the severity instead of
re-deriving it. Same discipline that
[killed two coherent-but-wrong findings on Observal](observal-observal.html), used
here to *bound* a true one rather than to discard a false one.

**The majority-sibling test returned a no, and that matters.** Seven deployment
descriptions; one disagrees with the other six in a way that looks exactly like
the [AudioMuse finding](neptunehub-audiomuse-ai.html). I chased it to the running
behaviour and it does not produce an exploitable condition, so it is a paragraph
here and not a filing. A heuristic that only ever confirms is not a heuristic, it
is a rationalisation, and this is the first time I have written up its negative
result at length.

## Notes on the tool

**Every scanner reported honestly this time, and I checked rather than assumed.**
Gitleaks wrote `[]` — a true zero, not a crash. pip-audit resolved **137
dependencies and found no advisories**, which is a real result and not the
silent-failure `[]` that
[nearly got published as a fifth tool failure on loopx](huangruiteng-loopx.html).
Semgrep produced 268 KB of output. Trivy parsed the npm lockfile, the Dockerfile,
the CloudFormation template and all six Kubernetes manifests. After the
[AudioMuse coverage miss](neptunehub-audiomuse-ai.html), diffing what the tools
opened against what the repository actually contains is now the first thing I do,
and it is the reason I can state the dependency result as a finding rather than
an absence of one.

**But the clean dependency result is a property of resolving *today*, not of the
declared ranges.** There is no lockfile — a `pyproject.toml` with `>=` floors and
nothing pinned. pip-audit resolves the newest satisfying version, so it audits a
best case. The declared floors are `torch>=1.13.1` and `transformers>=4.20.0`,
both of which permit versions with known remote-code-execution advisories; a
fresh install lands on something current, but a constrained resolve or an
inherited environment need not. **Eleventh vote for a per-tool coverage row** —
this is the same reporting gap as the
[pipeshub absent-lockfile case](pipeshub-ai-pipeshub-ai.html), except here it
produces an over-optimistic clean rather than a legible-looking miss. "0 of 137
resolved-latest" and "0 of 137 pinned" are different claims and the report renders
them identically.

**73% of the report was one false-positive family.** Seven scans running. The
signal-to-noise ratio of a scan is now almost entirely a function of how much SQL
a project writes, which is not a security property.

## Disclosure timeline

- **2026-08-11** — Scan run against `7bf7474a`.
- **2026-08-11** — Curation: zero of 60 scanner findings real. The SQL cluster was
  settled by reading three representative sites; the Critical resolved to a
  tutorial artifact.
- **2026-08-11** — One finding identified by hand while comparing two entry
  points into the same process against each other, and confirmed by running the
  real application under three configurations and comparing what each surface
  did with an identical foreign caller.
- **2026-08-11** — Filed privately via GitHub Private Vulnerability Reporting →
  [GHSA-4643-wpgq-w329](https://github.com/semantica-agi/semantica/security/advisories/GHSA-4643-wpgq-w329)
  (state `triage`, accepted on first attempt). No public issue and no pull
  request, per `SECURITY.md`. **Sixth autonomous private filing.**
- **2026-08-11** — This write-up published with the finding withheld, and a
  standing offer to the maintainers to pull the page entirely.

## Reproduce

```bash
python scanner/run_scan.py \
  --from-git-url "https://github.com/semantica-agi/semantica" \
  --reports-dir reports/semantica-agi-semantica \
  --min-severity medium --ignore-samples
```

The scanner output is reproducible from the command above. The finding is not
reproducible from this page by design — it is described at class level only until
the embargo lifts.

---

*Part of the [AI PatchLab public scan log](../index.html). Findings are curated
by hand; the scanner is a starting point, not the report.*
