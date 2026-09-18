---
layout: default
title: "langroid/langroid: security scan"
description: "Security scan of langroid/langroid, a multi-agent LLM programming framework: 132 findings, zero real, thirty-third clean scan. The repository ships a SECURITY.md that names its own boundaries and declares what is out of scope — this scan tested the document against the code, in-scope item by in-scope item, and it held."
date: 2026-09-12
---

# langroid/langroid — security scan

**Repository:** [langroid/langroid](https://github.com/langroid/langroid) — 4.1k★, MIT, a multi-agent LLM programming framework: agents that chat, call tools, query SQL and graph databases, run pandas expressions, ingest repositories and documents, and route messages between each other. 459 Python files. Actively maintained — three distinct authors merged PRs in the last 60 days and issues are closed within days.
**Commit scanned:** `053dbfe` (HEAD of `main` at scan time — pushed the morning of the scan)
**Scan date:** 2026-09-12
**Disclosure status:** Nothing to disclose. Strict-norm repository (substantial `SECURITY.md`, private vulnerability reporting enabled, 16 published advisories) — the quality gate was not met, so nothing was filed, publicly or privately. Everything below is published in full.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 6 |
| High | 51 |
| Medium | 70 |
| Low | 0 |
| Info | 3 (scanner meta) |

**Total findings:** 132 (130 above the `medium` floor) — **zero real after curation. Thirty-third clean scan.**

Coverage note: Semgrep scanned 585 files, skipped 0, and reported **3 errors** — all `PartialParsing`, on `Dockerfile` and `.github/workflows/docker-publish.yml`. Those two files were hand-reviewed below, because a parse error means the rules did not run and their absence from the results is not evidence of anything. Gitleaks returned zero. Trivy read `uv.lock` (83 advisories); pip-audit resolved the `pyproject.toml` floors (181 packages, 1 advisory). The two dependency tools disagree by a factor of 83, and that disagreement is the most useful thing in the report — see below.

## Why this target

Most repositories in this series have no security policy, or a copy of GitHub's default. Langroid has something rarer: a `SECURITY.md` that states a threat model, names which of its own functions are **not** security boundaries, lists what is in scope, and pre-declares what will be closed without a fix.

It says, in effect: *this framework's purpose is executing model-generated code and queries against your data. That is the feature. An LLM is not a trust boundary.* It then names its own `sanitize_command()`, its SQL/Cypher/AQL denylists and its AST checks as **best-effort hardening, not security boundaries** — "they exist to stop an *unlucky* LLM, not a *determined attacker*" — and points at the real boundaries: the database role you hand the agent, the container it runs in, the egress rules.

That is an *advertised boundary*, and this series has a standing test for one: does the code match the document? A declaration of scope is only worth anything if the things declared **in** scope are actually defended. The policy makes that testable, because it enumerates them:

> - Trust boundary, message routing, sender verification.
> - Parsing and deserialization flaws (XXE, unsafe deserialization, decompression bombs) in the document and message parsers.
> - Path traversal in the file tools (`ReadFileTool`, `WriteFileTool`, `ListDirTool`) and in repository / folder ingestion.
> - Credential or secret leakage in a default configuration.
> - **A code path that skips a documented safety gate entirely** — that is, a *missing call* to a validator, not a *bypass* of one.
> - **A statement the `allowed_statement_types` allowlist misclassifies.**
> - Vulnerable dependencies with a demonstrated impact on Langroid.

So this scan is not a hunt for a denylist bypass — the maintainer has already said those get closed, and he is right to: a denylist over four SQL dialects cannot be completed. It is a check of the seven claims above, one at a time. The interesting property of that framing is that it can come back **no**. It came back no. That is the point of running it.

## What the 132 findings actually were

- **83 Trivy advisories, every one of them from `uv.lock`** — and none from the `Dockerfile` target. Discussed in its own section below, because the version numbers are the story.
- **27 `github-actions-mutable-action-tag`** hits — `actions/checkout@v4`, `docker/login-action@v3`, and friends, pinned by tag rather than SHA. Supply-chain hygiene worth doing; not a vulnerability, and the same 27 would fire on most repositories on GitHub.
- **8 SQL and eval hits** — 4 `avoid-sqlalchemy-text`, 2 `sqlalchemy-execute-raw-query`, 2 `formatted-sql-query`, plus 3 `eval-detected`. Every one lands on `SQLChatAgent` or the pandas paths. These are the *product*. A framework whose documented purpose is running LLM-generated SQL will light up every raw-SQL rule in the ruleset, and that is not a finding, it is a category error — the [code-executor inversion](agentera-agently.html) this series has hit repeatedly. Out of scope by the policy, and correctly so.
- **4 `non-literal-import`** in `logging.py` and `system.py` — dynamic imports of optional dependencies, the standard pattern for a framework with 30 extras.
- **1 `run-shell-injection`**, the report's only novel High, on `.github/workflows/pytest-subset.yml:105`. Resolved below.
- **3 info-level meta findings** — the Semgrep partial-coverage warning, the unaudited-lockfile note, and the disabled-by-default AI review.

## The seven in-scope claims, checked

**1. Path traversal in the file tools — guarded, and guarded in the harder direction.** All three tools (`ReadFileTool`, `WriteFileTool`, `ListDirTool`) route through `safe_resolve_path(base, user_path)` in `langroid/utils/system.py:213`. The first thing worth noting is an anti-pattern that *isn't* one: all three discard the return value and then operate on the raw `self.file_path` inside a `chdir`. That is normally the bug — validate the canonical path, use the raw one. Here the docstring gets there first:

> A `~` path is checked under *both* interpretations — expanded (as `read_file` reads it) and literal (as `create_file` and `list_dir` write/list it, since those do not expand) — and rejected if either one escapes. **Callers validate with this function but then operate on the raw path, so validating only one interpretation would leave the other unguarded.**

The code does exactly that: it resolves the user path twice, once expanded and once literal, and rejects if *either* lands outside the base. The asymmetry it is defending against is real — `read_file` calls `expand_user_path`, `create_file` and `list_dir` do not — and it is the kind of divergence between siblings this series usually finds *unhandled*. Closes [GHSA-fg23-3346-88f5](https://github.com/langroid/langroid/security/advisories/GHSA-fg23-3346-88f5).

**2. Repository and folder ingestion — guarded.** `langroid/parsing/repo_loader.py` resolves each candidate path and checks containment against the resolved root, with the failure modes written down: unreadable paths, permission errors, symlink loops, and dangling symlinks that `os.walk` lists anyway. The root is resolved once rather than per entry, with a comment explaining that `Path.resolve()` costs syscalls. Closes [GHSA-99m6-3pvg-q66h](https://github.com/langroid/langroid/security/advisories/GHSA-99m6-3pvg-q66h).

**3. XXE and deserialization in the message parsers — guarded.** `XMLToolMessage` parses with `lxml`, which is the parser family where XXE is *real* rather than [DoS-only](ucbepic-docetl.html) — and it is configured `resolve_entities=False, load_dtd=False, no_network=True`, with the reasoning in a comment above it. A grep of the whole package finds no `pickle.load`, no `yaml.load`, no `marshal`, and no archive extraction at all — no `extractall`, no `tarfile`, no `ZipFile`. There is no decompression-bomb surface because there is no decompression. Closes [GHSA-pw95-88fg-3j6f](https://github.com/langroid/langroid/security/advisories/GHSA-pw95-88fg-3j6f).

**4. Credential leakage in a default configuration — clean.** `.env-template` holds 40-odd placeholders (`your-key-here-without-quotes`) and nothing else. Gitleaks returned zero on the full history-less tree. The shipped `.chainlit/config.toml` enables multi-modal and file upload and disables speech-to-text; it does not enable the MCP feature, which matters for the dependency section below.

**5. A missing call to a documented safety gate — none found, and finding that out took three passes.** This is the in-scope item that best rewards a sweep, so it got one. Both `eval()` sinks in the package — `table_chat_agent.py:242` and `vector_store/base.py:307` — are structurally identical: `if not self.config.full_eval: expr = sanitize_command(expr)`, then `eval(code, safe_eval_globals(vars), {})`. The globals restriction is applied *unconditionally*, including when `full_eval=True` disables the AST validator, so even the explicitly-out-of-scope path cannot reach `__import__`/`eval`/`exec` through implicit builtin injection. Two sinks, one shape, no drift.

The sender-verification surface took longer and is the methodological find of this scan. It is documented below.

**6. `allowed_statement_types` misclassification — guarded, including the nested case.** The policy specifically invites reports where the allowlist classifies a statement as one kind while the engine performs another, and calls that "a bounded, fixable defect." The validator already handles it: after checking the top-level node kind, `_nested_write_kinds()` walks the AST for embedded writes, with the reasoning inline — a data-modifying CTE (`WITH x AS (DELETE ... RETURNING *) SELECT ...`) and `SELECT ... INTO tbl` both parse with a `Select` top node while the database still performs the write. A query that trips it gets rejected with the embedded kind named in the error. Closes [GHSA-3gpx-vwr3-xvwx](https://github.com/langroid/langroid/security/advisories/GHSA-3gpx-vwr3-xvwx). An unparseable query is rejected rather than passed, which is the right direction to fail.

**7. Vulnerable dependencies with demonstrated impact — none reachable.** Three candidates, all resolved against the code rather than the version number. Below.

## The methodological find: three correct ways to say the same thing

Langroid has been hit three times by one bug class, and the third instance is what makes the pattern legible.

The seed was [GHSA-gjgq-w2m6-wr5q](https://github.com/langroid/langroid/security/advisories/GHSA-gjgq-w2m6-wr5q) (CVE-2026-54771): a tool registered `use=False, handle=True` — meaning *the LLM may not call this, but the agent will handle it* — could be invoked anyway by a chat user pasting raw tool JSON, because the dispatch path never checked whether the message came from `Entity.USER` or `Entity.LLM`. The fix added a `tainted` mark on USER-derived documents and a filter that drops handle-only tools out of tainted messages.

Then it happened twice more, in the same shape: [GHSA-2j3c-5vm9-xppx](https://github.com/langroid/langroid/security/advisories/GHSA-2j3c-5vm9-xppx) (`RecipientTool`) and [GHSA-4fpx-72j9-gwg3](https://github.com/langroid/langroid/security/advisories/GHSA-4fpx-72j9-gwg3) (`RewindTool`). Both are *relabelling* bugs: a tool handler takes attacker-influenceable content out of its own field and re-emits it as a **new document labelled `sender=Entity.LLM`**, which arrives untainted and therefore trusted. The first fix had been scoped to `DonePassTool`/`AgentDoneTool` only, so both siblings were left unpatched. Each advisory says the same thing about why: *the handler has no `chat_doc` argument, so taint is structurally invisible to it.*

That yields an obvious sweep — find every tool handler that lacks a `chat_doc` parameter — and the obvious sweep is **wrong**. Run it and 16 of 24 handlers come back "unguarded," including `SendTool` and `AgentSendTool`, which re-emit a `content` field verbatim and are exactly the shape of the two patched bugs.

They are fine. There are three different correct idioms in this codebase, and only the first needs `chat_doc`:

1. **Document-derived** — `tainted=chat_doc is not None and chat_doc.metadata.tainted`. Used by `RecipientTool`, `AddRecipientTool`, `RewindTool`, `PassTool`, `DonePassTool`, `ForwardTool`.
2. **Tool-level mark** — `tainted=self._tainted`, where `_tainted` was stamped onto the tool object by `_tainted_copy()` when it was parsed out of a tainted document. Used by `SendTool` and `AgentSendTool`. No `chat_doc` needed, because the taint rides the tool rather than the message.
3. **Implicit, via the tool list** — `AgentDoneTool` and `DoneTool` pass no `tainted=` argument at all, and are still correct, because `response_template()` computes `tainted=tainted or any(getattr(t, "_tainted", False) for t in tool_messages)` and both put `self` in `tool_messages`. The mark propagates without anyone naming it.

A name-matched sweep sees idiom 1 and reports the other two as missing. This series has the inverse lesson on file — [a sweep that under-reports because it misses alias spellings](mai-with-u-maibot.html) — and this is the same failure in the other direction: **on default-deny code, a single-idiom sweep over-reports, and every false positive it generates looks exactly like the two real CVEs that preceded it.** The only way through is to enumerate the propagation idioms *before* counting violations. Eight handlers take `chat_doc`; the other sixteen either re-emit nothing attacker-controlled (the seven web-search tools return search results, not user fields) or carry taint by idiom 2 or 3. Zero gaps.

Worth naming the one that could have been a finding and isn't: `arangodb_agent.py:140` and `:149` call `create_llm_response()` with no `tainted=` argument — the literal `RewindTool` defect signature. Both emit a fixed string (`"I give up, since I have exceeded the maximum number of tries"`). Nothing attacker-influenceable passes through them, so there is nothing to taint.

## The dependency disagreement, which is the useful part

The two dependency tools produced 83 advisories and 1 advisory against the same repository. They are both right, and the reason is the cleanest demonstration of this the series has recorded:

| | pip-audit | Trivy |
| --- | --- | --- |
| Read | `pyproject.toml` floors | `uv.lock` |
| Packages | 181 | — |
| **nltk version seen** | **3.10.3** | **3.10.0** |
| nltk advisories | 1 | 17 |

Same package, same repository, same scan, two versions. `pyproject.toml` declares `nltk<4.0.0,>=3.8.2` — an open floor, so a fresh resolve picks up 3.10.3 and sixteen of the seventeen advisories evaporate. `uv.lock` pins 3.10.0. Neither tool is wrong; they described **different install paths**, and a report that "reconciled" them into one number would have destroyed the only information that mattered.

So the question becomes: who actually runs the lockfile?

- **PyPI consumers** — `pip install langroid` — resolve from the floors. Not the lock.
- **The published Docker image** — the `Dockerfile` runs `uv pip install --no-cache-dir .`, which resolves from the floors. **Not** `uv sync`. Trivy scanned the `Dockerfile` target separately and returned **zero**.
- **CI and contributors** — `.github/workflows/pytest.yml` and `validate.yml` run `uv sync --dev`, and the `Makefile` drives everything through `uv run`. These get the lock.

The 83 advisories therefore describe the **contributor and CI environment**, not any shipped artifact and not a single user of the library. That is a real de-rating — it moves the cluster from "users are exposed" to "the test suite runs on old pins" — but it is not zero, and one entry in it is worth a maintainer's minute. It is the only thing in this report that is:

> **`gitpython` is pinned at 3.1.56 in `uv.lock`. [CVE-2026-78676](https://nvd.nist.gov/vuln/detail/CVE-2026-78676) is a critical RCE fixed in 3.1.59**: GitPython before 3.1.59 fails to safely re-serialize multi-line git-config values, so a crafted config with embedded newlines becomes a live directive — `core.hooksPath` — after any unrelated config write, giving arbitrary code execution via hook invocation. Twelve further gitpython advisories sit alongside it.

What makes this one different from the other 82 is that **langroid imports gitpython in its own code** — `agent/tools/file_tools.py` (the `WriteFileTool` git-commit path) and `parsing/repo_loader.py`. It is not a transitive leaf that happens to be in the tree. `pyproject.toml` declares `gitpython<4.0.0,>=3.1.43`, so every consumer install already resolves past it; only the environment CI runs in, and that contributors get from `uv sync`, is pinned behind. The fix is `uv lock --upgrade-package gitpython` and costs nothing.

Adjacent and structural: **there is no `.github/dependabot.yml`.** With no bot watching `uv.lock` and consumers resolving from floors that always look current, a stale lock is close to invisible — nothing in the project's own feedback loop reports it. That is the [lockfile-coverage gap](whiteguo233-openbiliclaw.html) this series keeps finding, in its quietest form: not a wrong pin, just nothing configured to notice.

The three remaining critical-severity entries all fail the reachability gate, and each fails it for a different reason worth recording:

- **`unstructured` 0.18.32, CVE-2026-71428 (critical SSRF)** — the CVE is specific to the `url` argument of `partition`, `partition_html` and `partition_md`, fetched without host validation. Langroid calls `partition_pdf`, `partition_docx` and `partition_doc` — the **file**-based entry points — and never passes a URL to any of them. Affected surface, not reachable surface: the same split that retired the [LiteLLM-proxy CVEs](klavis-ai-klavis.html).
- **`chainlit` 2.11.1, CVE-2026-45018 (critical command injection via the MCP stdio transport)** — requires `features.mcp.enabled = true` in `.chainlit/config.toml`. Langroid ships that file and does not enable MCP. Fixed in 2.12.0, and the floor (`>=2.0.1,<3.0.0`) already admits it.
- **`chromadb` 0.4.23, CVE-2026-45833 (critical code injection)** — the odd one out, because it is **not** lock-only: `pyproject.toml` ceiling-pins `chromadb<=0.4.23`, so anyone installing `langroid[chromadb]` gets this version by construction, and Trivy reports **no fixed version at all**. It survives anyway, on surface: both chromadb CVEs describe the ChromaDB **server** — `/api/v2/tenants/{...}/collections/{id}` endpoints, an "authenticated attacker", `trust_remote_code` on a server-side model repository. Langroid uses chromadb as an embedded client library and stands up no such endpoint. A ceiling pin with no patched version above it is worth knowing about; it is not a vulnerability in langroid.

## What Semgrep could not parse, read by hand

Three Semgrep errors, all `PartialParsing`, meaning the rules for those two files did not run. Absence of findings there is absence of evidence, so:

**`.github/workflows/docker-publish.yml`** interpolates `${{ env.DOCKER_TAG }}` — derived from `${GITHUB_REF#refs/tags/}` — directly into `run:` blocks that call `docker manifest`. A tag name containing shell metacharacters would inject. The trigger is `push` to `main` and to tags, so creating that tag requires write access to the repository, and `run-shell-injection` severity is a function of the trigger: an injection reachable only by someone who can already push is not a boundary crossing. Same conclusion for `${{ github.ref_type }}`, which is `branch` or `tag` and nothing else.

**`Dockerfile`** clones langroid over HTTPS from its canonical URL, renames `.env-template` to `.env` (placeholders only), and installs with `uv pip install .`. The one line worth a raised eyebrow is `sh -c "$(wget https://raw.githubusercontent.com/.../oh-my-zsh/master/tools/install.sh -O -)"` — piping a remote script from a `master` branch into a shell, unpinned. In a developer convenience image whose `CMD` is `zsh`, with a `|| true` after it, this is a documented-anywhere-else-too pattern and not something to file; it is recorded here because it is exactly what the Dockerfile rules would have flagged had they run.

The one novel High, **`pytest-subset.yml:105**, resolves the same way — and the maintainer got there first. The workflow interpolates `${{ inputs.pytest_args }}` straight into a `run:` block, above a comment reading: *"input is substituted directly; workflow_dispatch is restricted to users with write access, so this is not an injection vector."* The trigger really is `workflow_dispatch` only. That is an accepted risk with the correct reasoning attached, which is a different object from an oversight, and it deserves to be credited as one.

## Patterns observed

**A security policy that names its non-boundaries is worth more than one that promises safety.** The most useful sentence in langroid's `SECURITY.md` is the admission that `sanitize_command()` and the SQL denylists are *not* security boundaries — that they stop an unlucky LLM, not a determined attacker. Most projects in this position claim the opposite, and their users deploy accordingly. By refusing the claim and naming the real boundaries — database role, container, egress — the document moves the defence to where it can actually hold, and simultaneously makes the project *auditable*: it converts "is this safe?" into seven checkable propositions. This scan exists because those propositions were checkable.

**Sixteen advisories is not a smell; it is a shape.** It would be easy to read langroid's advisory list as a bad sign. The opposite reading fits the code better: nearly every one of those advisories has left a comment behind at the site it fixed, naming the GHSA and explaining the reasoning. `safe_resolve_path` carries the both-interpretations argument. The nested-write check carries the CTE example. The eval sites carry the builtins-injection note. `RecipientTool` carries "do not let that relabel launder untrusted content." The code has accumulated its own security history in the places where that history is load-bearing, which is why a reviewer arriving cold can check seven claims in an afternoon instead of reconstructing the threat model from scratch.

**The repeated bug class is the one to watch, and the repetition is informative.** Three advisories, one mechanism: relabel USER content as LLM content and the trust filter stops applying. The first fix was scoped to two tools; two siblings were found later. The response was not a third point-fix but a *generalisation* — a tool-level `_tainted` mark plus implicit propagation through `tool_messages` — which is why `SendTool` and `AgentSendTool` are already correct without ever having been the subject of an advisory. The lesson for a reviewer is the one in the section above: when a project fixes a class by generalising, single-idiom sweeps stop working, and the reviewer's job shifts from *counting violations* to *enumerating the idioms first*.

**Zero real findings, and the interesting part is which question failed.** The tools produced 132 findings and none of them pointed at anything. That is now routine — it has happened 33 times. What is not routine is that the hand sweep also came back empty *against a checklist the maintainer wrote himself*. The advertised-boundary test is only meaningful if it can fail, and this series has published it failing: a boundary [advertised but not implemented](mims-harvard-tooluniverse.html), a guard [wired to the wrong route set](liaohch3-claude-tap.html), a [deny-list that confessed](mljar-mercury.html) what its `@authenticated` decorator did not cover. Here it passed, seven for seven. Publishing the pass is the only thing that makes the failures worth reading.

## Notes on the tool

- **The unaudited-lockfile meta finding did its job, and should say more.** It correctly flagged that pip-audit read `pyproject.toml` while `uv.lock` went unread — but Trivy *had* already covered the lock in the same run, so the warning as phrased ("not covered by the dependency scan") overstates the gap. The scanner knows both tools' targets; it could reconcile them and say the more useful thing: *two install paths were audited by two different tools, and here is where their package versions disagree.* The nltk 3.10.0-vs-3.10.3 split is exactly the output a user wants and the scanner currently makes them derive by hand. Backlog item.
- **`PartialParsing` errors need the same treatment `timeout` errors already get.** `scan_semgrep` emits `semgrep-partial-coverage` naming the `rule -> file` pairs that did not run, which is right, but it phrases the recommendation around raising `--timeout` — useless advice for a parse failure, which will never succeed on retry. A parse error on a `Dockerfile` or a workflow means *those rule families produced nothing for this file*; the recommendation should say "hand-review, these rules did not run" rather than suggest a re-run.
- **A `--dep-surface` column is the recurring ask.** Three of the six criticals in this report were retired by asking "which API does the CVE actually name, and does this repository call it?" That question is mechanical enough to assist: Trivy's advisory text usually names the affected function (`partition(url=...)`, the `/api/v2` endpoints, `features.mcp.enabled`), and the scanner already has the repository on disk to grep. Not automatic triage — just surfacing the affected symbol next to a yes/no on whether it appears in the tree would cut the manual pass substantially.
- **No tool in the stack can see any of the seven in-scope questions.** Taint propagation across three idioms, a `~`-expansion asymmetry between sibling helpers, a nested-write classifier, an lxml parser's entity flags — Semgrep found the `eval()` calls and the raw SQL, which are the parts that are *supposed* to be there, and found nothing about the machinery that makes them safe. This is the standing gap the series keeps recording, and it is why the hand sweep is not optional.

## Disclosure timeline

- 2026-09-12 — scan run at `053dbfe`
- 2026-09-12 — curation complete: zero real findings, quality gate not met, nothing filed
- 2026-09-12 — public post (this page)

Nothing was reported to the maintainers, because nothing met the bar. The `gitpython` lock pin and the absent `dependabot.yml` are published here in full rather than sent privately: they are hygiene items affecting the contributor environment, visible to anyone reading `uv.lock`, and not a vulnerability in the shipped library.

## Reproduce

```bash
git clone https://github.com/langroid/langroid /tmp/scan-target
.venv/Scripts/python.exe scanner/run_scan.py \
  --repo /tmp/scan-target \
  --reports-dir ./reports/langroid-langroid \
  --min-severity medium
```

---

## More from this series

- **Next scan:** [bubbuild/bub](bubbuild-bub.html) — 2026-09-13, 1 real
- **Previous scan:** [mljar/mercury](mljar-mercury.html) — 2026-09-11, 1 real — withheld
- [Every scan in the series]({{ '/' | relative_url }}) — 105 repositories, newest first
- [Where a maintainer shipped a fix]({{ '/fixed' | relative_url }}) — the 24 that resolved
- [Scans that found nothing]({{ '/clean' | relative_url }}) — 40 of them, published as they were
