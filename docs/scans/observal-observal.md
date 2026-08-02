---
layout: default
title: "Observal/Observal: security scan"
date: 2026-08-02
---

# Observal/Observal — security scan

**Repository:** [Observal/Observal](https://github.com/Observal/Observal)
**Commit scanned:** `18c0e4b0`
**Scan date:** 2026-08-02
**Disclosure status:** withheld — one real finding filed privately as
[GHSA-2qv6-w49j-hqmq](https://github.com/Observal/Observal/security/advisories/GHSA-2qv6-w49j-hqmq),
embargoed pending maintainer response

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 7 |
| High | 27 |
| Medium | 182 |
| Low | — |
| Info | — |

**Total findings:** 1,117 raw / 216 at `--min-severity medium` (1 real after curation — withheld)

*Scanned with `--min-severity medium`, so low and info rows are filtered rather
than empty.*

Observal (2.3k★, Apache-2.0) calls itself **the control plane and system of
record for internal AI components**. The problem it targets is real and getting
worse: organisations now generate Skills, MCP servers, hooks, prompts and agents
faster than anyone can find them, so the same component gets rebuilt five times
in five repos while nobody can tell which copy is trusted. Observal answers with
a **governed registry** — submit, review, approve, version, install — plus a
usage-telemetry layer that turns silent AI failures into feedback.

The interesting engineering is the fan-out. One approved component renders into
the correct native configuration for **nine harnesses** — Claude Code, Cursor,
Kiro, Copilot (CLI and VS Code), Codex, OpenCode, Pi, Antigravity — each with its
own config dialect, hook event names, scripts directory, and project-versus-user
install scope. It ships a Python monorepo (FastAPI server, Typer CLI, shared
packages), a Next.js dashboard, Postgres + ClickHouse + Redis, Grafana
dashboards, and Terraform for both AWS and Azure. 601 Python files.

Maintenance is unusually healthy: **~100 pull requests merged in the last 60 days
from 17 distinct human contributors**, 69 issues closed in the same window, a CLA
bot, REUSE-compliant SPDX headers on every file, and a real `SECURITY.md`.

### A note on what this write-up does not contain

Observal's `SECURITY.md` opens with *"Do not open a public GitHub issue for
security vulnerabilities"* and names GitHub's private advisory flow as the
preferred channel. Their private reporting was enabled and the submission API
accepted the report, so the finding went where they asked for it to go, and it is
**under embargo until they publish or close it**.

So this page describes what the scan found the way you would describe it at a
conference before the fix ships: the *shape* of the finding and the reasoning
that produced it, with the component, the mechanism, and the reproduction left
out. The curation analysis below — which is most of the value here anyway — is
complete and unredacted, because every item in it is a **non**-finding.

This page will be updated with the full technical detail once the advisory
resolves.

## The one real finding, at class level

**Severity: High. Class: a guard that answers the right question about the wrong
noun.**

Observal has a security-conscious codebase — it carries a numbered internal
security-item scheme, and one of its hardening modules is among the more careful
implementations of its kind I have read on this series, including the detail that
it refuses rather than allows when it cannot decide.

That module is why the finding exists.

The guard establishes that a piece of user-supplied input is **safe for the
server to act on**. Having established it, the code acts on it — and in the
course of acting, does something *additional* that the guard never had an opinion
about. The team was not inattentive to the asset at risk here; they anticipated
losing it and defended the channel they pictured losing it through. The
input-validation layer simply never asked the second question, because it is a
question about a different noun than the one that layer was written to reason
about.

The lowest authenticated role reaches it. There is no review gate in front,
because the affected path runs *before* the governance flow that a registry's
review step would cover.

I do not think this is a case of a team being careless. It is closer to the
opposite: a thorough guard creates a strong intuition that the dangerous input
has been handled, and that intuition is what stops the second question from being
asked. That is a pattern worth naming, and I will name it properly here when the
embargo lifts.

The report includes a minimal patch — roughly ten lines, one new environment
variable with a safe default, and it composes with an escape hatch the project
already ships for self-hosted deployments.

## Everything the scanner ranked above it

The single real item was **not** in the report's Critical tier, and was not in
the High tier either. It was not in the report at all — no rule fired on it. This
is now a well-established pattern in this series (see
[docetl](ucbepic-docetl.html), [zotero-mcp](54yyyu-zotero-mcp.html),
[EvoScientist](evoscientist-evoscientist.html)), but Observal is an unusually
clean demonstration, because the 216 findings above the severity floor sort into
six buckets and *all six* are dismissable with a paragraph.

### All 7 Criticals are reference Terraform (new pattern for this series)

Every Critical is a Trivy IaC misconfiguration in `infra/terraform/` — unrestricted
security-group *egress* (×4), a plain-HTTP listener, a storage-account default
network action, a key-vault network ACL. This is the first scan in the series
where the entire Critical tier is **infrastructure-as-code the project ships as a
deployment reference**, not code that runs.

That distinction matters more than the count suggests. Unrestricted egress on a
security group is a finding about *your* production VPC; in a reference module
it is a default that every adopter is expected to narrow to their own CIDRs.
Trivy cannot tell the difference between "this Terraform describes a running
system" and "this Terraform is an example another team will fork," and the
severity it assigns assumes the former. The plain-HTTP listener is the
conventional `:80` → `:443` redirect pair.

This is the [monorepo ownership-split lesson](harbor-framework-harbor.html) in a
new costume: there, the raw count misled because 81% of findings were in vendored
third-party code; here it misleads because the top tier is a *template*. Both are
the same underlying question — **whose running system does this describe?** — and
neither scanner can answer it.

### The SQL cluster is the identifier false positive, again

Five `sqlalchemy-execute-raw-query` / `avoid-sqlalchemy-text` / `formatted-sql-query`
hits. Three are Alembic migrations (`alembic/versions/**` is by now a
[reliable candidate-FP tier](soju06-codex-lb.html) — migration DDL is
schema-manipulation by definition and cannot be parameterised). The other two are
textbook identifier interpolation, and Observal helpfully documents its own
reasoning inline:

```python
rows = await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
table_names = [r[0] for r in rows.fetchall()]
for table_name in table_names:
    # Table names come from pg_tables (system catalog), not user input.
    # Use quoted identifier to handle any special characters safely.
    count_row = await db.execute(text(f'SELECT count(*) FROM "{table_name}"'))
```

The interpolated value comes from the Postgres system catalog. There is no user
input anywhere in the expression. The CLI's other hit is an integer computed
from `PRAGMA page_size` interpolated into `PRAGMA max_page_count` — SQLite does
not accept bound parameters in a PRAGMA at all.

This remains the **#1 recurring false-positive cluster** across the entire series
(mnemosyne 140, codex-lb ~14, potpie ~14, AG2 5, and now Observal 5). The
discriminator has never changed: are the *values* bound and only the *identifiers*
interpolated, and do those identifiers come from somewhere the user cannot reach?

### The workflow shell-injection pair is maintainer-triggered

Two `run-shell-injection` highs, both interpolating `${{ inputs.version }}` into a
`run:` block. `inputs.*` is populated only by `workflow_dispatch` — meaning the
injection requires permission to manually dispatch a release workflow, which is
already permission to publish a release. Per the
[trigger-context rule](maziyarpanahi-openmed.html): `workflow_dispatch` is a
privilege-holder surface (hardening), `pull_request_target` is an attacker surface
(vulnerability). These are the former. Quoting the interpolation is still worth
doing — it costs nothing and removes a footgun for whoever edits the file next.

### The tar extractions are same-origin, and the checksum gate is honest-but-soft

Three `tarfile-extractall-traversal` highs. The CLI one downloads Postgres,
ClickHouse and Redis binaries from a **hardcoded** `github.com/Observal/Observal`
release URL — not environment-overridable, so a malicious archive requires
compromising the project's own release, at which point extraction filters are not
your problem. Adding `filter="data"` is still the correct hardening (it is what
[fast-agent #811](evalstate-fast-agent.html) resolved), and on Python 3.14 the
default changes anyway.

One adjacent observation worth recording as *design*, not defect: the checksum
verification fails open in two directions — a failed checksum *fetch* returns an
empty dict, and a filename missing from that dict logs "skipping verification"
and returns `True`. Since the checksums are served from the same origin as the
binaries, they provide integrity against a truncated download but no authenticity
against a compromised release. That is a reasonable thing for a local dev-server
bootstrapper to do, and the warnings are printed rather than swallowed. It is a
note, not a finding.

### The file-permission and password rules misfire predictably

Eleven `insecure-file-permissions` and six `unvalidated-password` hits. The
`chmod` calls the rule objects to are `0o600` on a secrets file and on the local
telemetry SQLite buffer — that is *correct* practice being flagged, the
[active-harm false-positive class](stickerdaniel-linkedin-mcp-server.html) where
following the advice would make things worse. The `0o755` is a hook script that
must be executable to function. The `unvalidated-password` rule is a **Django**
rule (`python.django.security.audit.unvalidated-password`) firing on a FastAPI
codebase with no Django anywhere in it.

### Dependencies are clean, and coverage was verified

Two urllib3 advisories and one `idna` CVE in `uv.lock` — the urllib3 pair are the
cross-origin-redirect header leak and the decompression DoS, both requiring
request patterns this codebase does not exhibit. Gitleaks returned **zero**
secrets across 601 Python files and a full Next.js frontend, which after the
[IBM `.secrets.baseline` scan](ibm-mcp-context-forge.html) (521 false secrets) is
worth stating plainly as a good result.

**Coverage check, stated explicitly** because two recent scans were burned by
skipping it: Trivy parsed `uv.lock`, Semgrep produced 538 KB, Trivy 596 KB, and
pip-audit resolved the CLI's dependency set. Gitleaks' 3-byte output is a literal
`[]` — a genuine zero, not the [0-byte crash](dataelement-clawith.html) that
masked 43 findings on Clawith. No scanner silently failed on this run.

## Patterns observed

**A "governed registry" moves the security question from the artifact to the
pipeline.** My first instinct on a component registry was to hunt the obvious
supply-chain path: can a malicious published component escape its install
directory and write somewhere it shouldn't? Observal handles this well. Every
file write in the install path — MCP configs, hook scripts, steering files,
prompt files, skill files, agent profiles — funnels through a *single* resolver
that `resolve()`s the path and rejects anything not `is_relative_to` the target
directory. One chokepoint, applied uniformly, is exactly the right shape, and it
is the thing most projects get wrong by scattering the check.

**The consent boundary is the harder question, and they drew it correctly.** At
user scope a hook component legitimately writes an executable script into your
harness's hooks directory — which is *by definition* arbitrary code execution on
your machine. It would be easy to write that up as a vulnerability. It isn't one:
a hook is a thing that runs commands, and installing one is consenting to that.
This is the [advertised-boundary test](agentera-agently.html) coming out the
other way — Agently was a finding because a component **named** `PythonSandbox`
promised isolation it did not enforce; Observal's hooks promise execution and
deliver execution. An honest dangerous feature beats a dishonest safe one.

**I spent real effort on a vulnerability that does not exist, and the reason is
worth writing down.** The CLI clones skill directories from a git URL supplied by
the server. Git's `ext::` transport executes arbitrary commands, so
`ext::sh -c '...'` in that field looked like install-time RCE — a clean, serious,
publishable finding. Before writing it up I ran it:

```
$ git remote add origin 'ext::sh -c "id > PWNED"'
$ git fetch --depth=1 origin main
fatal: transport 'ext' not allowed
```

Git's default transport policy has blocked `ext` for years. Had I trusted the
reasoning instead of the terminal, I would have filed a confident, well-argued,
**wrong** advisory against a project that did nothing incorrect. I then tested
`--upload-pack=` argument injection through the ref parameter, and that is inert
too — git does not parse options in the refspec position.

The finding I *did* report survived the same treatment, which is the entire
point: it is in the write-up because a listener on localhost printed the thing I
claimed would be printed, not because the code read badly.

**Three of the six dismissal buckets came from asking "whose system is this?"**
Reference Terraform, Alembic migrations, and `workflow_dispatch` inputs are all
findings whose severity depends on context that lives outside the matched line —
in one case ([pipeshub](pipeshub-ai-pipeshub-ai.html)) outside the repository
entirely. Severity is a property of a deployment, and a rule matches a syntax
tree. That gap is where roughly 95% of a 216-finding report goes to die.

## Notes on the tool

**The GHSA submission API worked, and that is new.** Yesterday's scan
([repowise](repowise-dev-repowise.html)) found private vulnerability reporting
*enabled* while `POST /security-advisories/reports` returned HTTP 500 on four
attempts, forcing a manual hand-off. The same call against Observal succeeded on
the first try and returned a GHSA ID. So the pre-check yields three states —
disabled (email only), enabled-and-API-works (fileable end-to-end),
enabled-but-API-500s (human web form only) — and the flag alone distinguishes
none of them. **Always attempt the POST.** This is the first finding in the series
disclosed through a fully automated private channel.

Backlog items from this scan:

1. **An IaC "reference module" tier is missing.** All 7 Criticals were Terraform
   the project ships as an example. `infra/terraform/**` in a project that is not
   itself an infrastructure deployment needs the same candidate-FP treatment
   `tests/**` and `examples/**` already get — or better, a distinct *"describes a
   system you would operate, not one this repo runs"* classification. This is the
   third distinct way a raw count has misled (over-count via vendored code,
   under-count via scanner-blind sweeps, and now mis-attribution via templates).
2. **Framework-mismatched rules should be suppressed by import graph.** Six
   `python.django.*` findings fired on a codebase with zero Django. A one-line
   check — is the rule's framework in the dependency set at all? — removes an
   entire bucket. Cheap, mechanical, high yield.
3. **`--min-severity` still masks scanner-infrastructure meta findings.** Fifth
   vote. Not biting on this scan because all four tools were healthy, but the
   fix has now been deferred across five scans and the failure mode it prevents
   is the worst one available: a broken scanner rendering as a clean repo.
4. **`chmod(0o600)` should never be flagged as an insecure file permission.** The
   `insecure-file-permissions` rule needs to compare against a *maximum*
   permissiveness, not merely fire on the presence of a mode literal. Flagging
   `0o600` as insecure is not noise — it is advice that, if followed, widens the
   exposure of a secrets file.
5. **No rule family covers the real item, and none plausibly could.** The finding
   is absence-shaped in the way that keeps recurring on this series
   ([zotero-mcp](54yyyu-zotero-mcp.html),
   [EvoScientist](evoscientist-evoscientist.html)): the line is unremarkable in
   isolation and is only wrong in light of a fact established elsewhere in the
   file. What generalises is the *review question* rather than a pattern — when a
   validator clears an input, enumerate every subsequent action taken on that
   input and check each one against the validator's actual scope. That is a sweep
   prompt, not a rule.
6. **Same-origin checksum verification deserves a rule.** "Artifact and its
   checksum served from the same host" is a recognisable, greppable anti-pattern
   that provides integrity while appearing to provide authenticity.

## Disclosure timeline

- **2026-08-02** — Scan run at `18c0e4b0`; 1,117 raw findings, 216 above the
  medium floor, curated to one real item.
- **2026-08-02** — Finding reported privately via GitHub Security Advisories
  ([GHSA-2qv6-w49j-hqmq](https://github.com/Observal/Observal/security/advisories/GHSA-2qv6-w49j-hqmq)),
  the channel Observal's `SECURITY.md` names as preferred. Includes an empirical
  reproduction and a minimal suggested patch.
- **2026-08-02** — This post published with the finding withheld.
- **TBD** — This page updated with full technical detail when the advisory is
  published or closed.

## Reproduce

The curation analysis above (everything except the withheld item) is fully
reproducible:

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/Observal/Observal" \
  --reports-dir reports/observal-observal \
  --min-severity medium
```
