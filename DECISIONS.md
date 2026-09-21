# Architecture Decision Records â€” ai-patchlab

> Log chronologique des dÃ©cisions architecturales du projet.
> Format: ADR (Architecture Decision Record) simplifiÃ©.

## Comment utiliser

Quand une dÃ©cision architecturale est prise (choix de tech, design de module, pattern adoptÃ©), ajouter une entrÃ©e ici. Ceci permet de comprendre POURQUOI le code est structurÃ© comme il l'est.

**Quand Ã©crire un ADR ?**

| Ã‰crire un ADR | Sauter |
|---------------|--------|
| Adoption d'un nouveau framework | Bump de version mineure |
| Choix de DB ou de stockage | Bug fix |
| Pattern d'API ou d'auth | DÃ©tail d'implÃ©mentation |
| Architecture sÃ©curitÃ© | Maintenance de routine |
| Pattern d'intÃ©gration externe | Changement de config |

**Cycle de vie:** `Proposed â†’ Accepted â†’ Deprecated â†’ Superseded` (ou `Rejected`)

---

## Templates

Choisir le format selon le poids de la dÃ©cision. Le format **Lite** suffit pour 80% des cas â€” ne sortir le **Standard** que pour les dÃ©cisions structurantes.

### Lite (par dÃ©faut)

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted | superseded | deprecated
**Decision:** [La dÃ©cision en une phrase]
**Context:** [Pourquoi cette dÃ©cision Ã©tait nÃ©cessaire]
**Consequences:** [Ce que Ã§a implique pour la suite]
```

### Standard (dÃ©cisions structurantes)

InspirÃ© du format MADR. Utiliser quand le choix engage la stack, la sÃ©curitÃ©, ou est difficilement rÃ©versible.

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted

**Context:** [ProblÃ¨me, contraintes, drivers â€” 3-5 lignes]

**Decision Drivers:**
- [Driver 1 â€” must-have]
- [Driver 2 â€” should-have]

**Considered Options:**
- Option A â€” [pros / cons]
- Option B â€” [pros / cons]
- Option C â€” [pros / cons]

**Decision:** [Option retenue + 1 phrase de raisonnement]

**Consequences:**
- Positive: [ce que Ã§a dÃ©bloque]
- Negative: [ce que Ã§a coÃ»te]
- Risks: [mitigations]
```

### Y-Statement (dÃ©cision rapide Ã  formaliser)

Une seule phrase structurÃ©e. Utile pour capturer une dÃ©cision dÃ©jÃ  prise sans rÃ©Ã©crire un ADR complet.

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted

In the context of **[contexte]**, facing **[problÃ¨me]**, we decided for **[option]** and against **[alternatives]**, to achieve **[bÃ©nÃ©fice]**, accepting that **[trade-off]**.
```

### Superseding (dÃ©prÃ©cier un ADR existant)

```
### ADR-XXX: [Titre â€” supersedes ADR-YYY]
**Date:** YYYY-MM-DD
**Status:** accepted (supersedes ADR-YYY)

**Context:** ADR-YYY a choisi [X] pour [raison]. Depuis, [ce qui a changÃ©].

**Decision:** Remplacer [X] par [Y].

**Migration:**
- Phase 1: [Ã©tape]
- Phase 2: [Ã©tape]

**Consequences:** [coÃ»ts de migration + bÃ©nÃ©fices long terme]

**Lessons learned from ADR-YYY:** [ce qu'on retient pour les futurs ADRs]
```

### RFC (proposition Ã  dÃ©battre)

Pour les dÃ©cisions qui requiÃ¨rent un round de discussion avant `accepted`. Status reste `Proposed` pendant la review.

```
### ADR-XXX: [Titre â€” RFC]
**Date:** YYYY-MM-DD
**Status:** Proposed

**Summary:** [2 phrases]

**Motivation:** [pourquoi maintenant]

**Detailed Design:** [code, schÃ©mas, contracts]

**Drawbacks:** [coÃ»ts honnÃªtes]

**Alternatives considered:** [au moins 2]

**Unresolved questions:**
- [ ] Question 1
- [ ] Question 2
```

### Bonnes pratiques

- **Ã‰crire l'ADR AVANT l'implÃ©mentation** (pas aprÃ¨s comme excuse)
- **1-2 pages max** â€” un ADR long indique un manque de clartÃ©
- **HonnÃªte sur les trade-offs** â€” inclure les vrais cons, pas juste les pros
- **Linker les ADRs liÃ©s** â€” construire un graphe de dÃ©cisions
- **Ne jamais modifier un ADR `accepted`** â€” crÃ©er un nouveau qui supersede

---

## Decisions

<!-- Ajouter les nouvelles dÃ©cisions en haut (plus rÃ©cent en premier) -->

### ADR-016: Dismissals are recorded as counted rule families, not discarded

**Date:** 2026-09-21
**Status:** accepted

**Context:** A scan produces on the order of 77 findings of which roughly one is real. The other 76 dismissals are argued once, compressed into a paragraph of post prose, and then gone. The same rule families are re-triaged on the next repository, by hand, from zero. ADR-014 showed what the recorded version is worth: mining 87 archived reports turned informal votes ("13th appearance of the SQL-identifier FP") into 1,802 hits across 26 repositories and justified two mechanized confidence tiers. The raw findings were already archived under `reports/<slug>/raw/`; what was missing was the **verdicts**. Separately, `--ignore-file`, `--ignore-samples` and `--min-severity` drop findings silently, which is the same dishonesty ADR-015 removed for coverage.

**Decision Drivers:**
- Must produce a corpus that can be counted, because counting is what converted judgement into rules in ADR-014 (must-have)
- Must not become per-finding bureaucracy that nobody fills in or reads (must-have)
- Must not land in `reports/.daily_state.json`, already a flat bag of ~100 ad-hoc keys where one mis-keyed entry evaded a guardrail for about 20 runs (must-have)
- Should use one schema for both producers so the corpus is unified (should-have)

**Considered Options:**
- **A - Scanner-emitted only.** Record what the scanner itself suppressed. Pros: deterministic, testable, ships immediately. Cons: path patterns and severity floors are not the 76 judgements; it would miss the whole point.
- **B - Curation-emitted only.** Persist the `/daily` Phase 4 verdicts. Pros: captures the valuable half. Cons: leaves mechanical suppression silent, and an LLM-filled file with no deterministic sibling has nothing holding its shape.
- **C - One schema, two producers, rows counted per rule family.** **Selected.**
- **D - Per-finding verdict rows.** Rejected: a severity floor can drop hundreds of findings in one scan, and Phase 4 already groups by rule family, so per-finding rows would be both enormous and a worse fit for the workflow that produces them.

**Decision:** Take option C. `reports/<slug>/verdicts.json` holds rows of `{source, reason_code, tool, rule, count, verdict, detail}`. The scanner writes its own rows on every scan by diffing the finding list across each suppression step, grouped by `(tool, rule)` with a count. `/daily` Phase 4 appends judgement rows in the same shape, one per rule family it triaged, drawn from a closed `reason_code` vocabulary so the corpus stays countable. The Markdown report renders a Dismissed section only when rows exist. `verdicts.json` is never written into `.daily_state.json`.

**Consequences:**
- Positive: the corpus that ADR-014 had to reconstruct by hand is now produced as a by-product of the work that generates it. A future mechanization measurement becomes a `sum()` over the closed vocabulary rather than an archaeology project.
- Positive: `--ignore-samples` and `--min-severity` stop removing findings silently, which closes the last place where the report hides its own edits.
- Negative: the closed vocabulary is a guess made from the curation memory and will be wrong in places. Adding a code is cheap; the risk is drift into a long tail of one-off codes that cannot be counted, which defeats the purpose.
- Negative: the curation half depends on `/daily` filling it in. If the rows go stale or empty, the file is worse than nothing because it looks authoritative. The scanner rows are the deterministic floor that keeps the file honest even when the judgement rows are missing.
- Risks: scope creep into a query CLI or a dashboard. The MVP ships a loader and a counter, nothing else; anything more needs its own decision.
- Builds on ADR-015 (coverage as an artifact) and ADR-014 (measure before mechanizing).

### ADR-015: Coverage is a report artifact, not a finding

**Date:** 2026-09-17
**Status:** accepted

**Context:** `cloudflare/security-audit-skill` (MIT, published 2026-06-18) is an agent skill, not a scanner - 220 KB of methodology plus two zero-dependency JSON validators, with no analysis code of its own. It orchestrates isolated sub-agents through six phases and is the seed of Cloudflare's internal vulnerability harness. Its published design principles converge almost exactly on the curation doctrine this project derived independently from 105 public scans: adversarial validation by a fresh agent, "defense-in-depth gaps are not vulnerabilities", "severity requires impact", and an explicit `needs_validation` verdict for facts that are not visible in source. That convergence is evidence the doctrine is right; it is not a reason to adopt the mechanism, which is non-deterministic, un-CI-able, priced per run, and refuses to execute target code without an OS-enforced sandbox. Two of its structural ideas do not exist here and are cheap to port.

**Decision Drivers:**
- Must not weaken determinism or reproducibility - they are the only properties this project has that an LLM auditor cannot copy (must-have)
- Must address a failure mode already observed in the field, not a hypothetical one (must-have)
- Must fit MVP discipline: no new dependencies, no agent orchestration, files under 300 lines (must-have)
- Should convert per-scan curation judgement into an accumulating asset instead of discarding it (should-have)

**Considered Options:**
- **A - Adopt the skill as the pipeline.** Pros: far deeper reasoning than any SAST, free, strong brand. Cons: not reproducible, cannot gate CI, needs a sandbox most environments lack, no published precision data at three months old. Rejected as a replacement; retained as a complementary point-in-time tool.
- **B - Ignore it.** Pros: zero cost. Cons: forfeits two structural ideas that answer a documented recurring failure. Rejected.
- **C - Adapt two ideas, drop the rest.** Port (1) coverage as a first-class artifact and (2) deterministic rejection records with a retained reason. Discard the six phases, sub-agent isolation, the artifact-promotion procedure, `coverage_id` encoding, and agent budgets - none apply to a synchronous subprocess pipeline. **Selected.**
- **D - Build a competing agent skill.** Pros: plays to the curated FP corpus. Cons: head-on competition with a Cloudflare-branded 10k-star MIT skill on distribution, and it abandons determinism to fight on their ground. Rejected now; revisit only as a *curation* layer over any scanner's output once the rejection corpus from (2) exists.

**Decision:** Take option C. Coverage stops being inferred from `info`-severity meta findings scattered through the findings list and becomes `reports/coverage.json` plus a coverage block rendered **before** the findings in `security_report.md`, carrying an explicit `complete: bool`. Rejection records follow as a separate change: anything the scanner suppresses itself (ignore patterns, secrets baselines, a framework rule fired against a project that does not declare the framework) is retained with a machine-readable reason instead of being deleted.

**Consequences:**
- Positive: the honesty that ADR-013 bought at the `Finding` level is promoted to the report level. `is_meta` already marks every ingredient and every adapter already emits them, so this is a rendering and reconciliation change, not new detection. A reader can no longer mistake "nothing was looked at" for "nothing was found" - the exact confusion behind the three field incidents: Semgrep silently losing 52% of coverage after an unrelated pydantic downgrade, tracecat's two core files drawing zero rules with `paths.skipped` empty, and `scan_dependency` reading root-only so a monorepo with no top-level manifest rendered as clean.
- Positive: it is a real product differentiator. Scanners report findings; almost none report what they failed to examine.
- Negative: reports get longer and some will now open by announcing they are incomplete. That is the intended cost.
- Negative: rejection records grow the report surface and need their own suppression discipline, or they become the noise they were meant to remove.
- Risks: scope creep toward porting more of the skill. The mitigation is this ADR - anything beyond the two named ports needs its own decision. Per-tool unit counts (files scanned, manifests audited) are deliberately excluded from v1 because they would couple the coverage module to runner internals; they are a follow-up once the artifact exists.
- Relates to ADR-013 (meta findings exempt from severity filtering) and ADR-014 (field-derived confidence tiers); both are prerequisites that made this cheap.

### ADR-014: Field-derived confidence tiers, measured not guessed
**Date:** 2026-08-21
**Status:** accepted
**Decision:** Rules that downgrade a finding's confidence must be justified by a measurement over the published scan corpus in `reports/`, and the measured count must be written into the comment next to the rule. Two tiers were added on this basis. Semgrep: the SQL-identifier cluster (`sqlalchemy-execute-raw-query`, `formatted-sql-query`, `avoid-sqlalchemy-text`, `asyncpg-sqli`) and `github-actions-mutable-action-tag` join `logger-credential-leak` in `_HIGH_FALSE_POSITIVE_SEMGREP_RULES`. Gitleaks: `confidence_for_gitleaks_finding` now takes `(rule_id, secret)` - a provider-specific rule stays `high`, `generic-api-key` drops to `medium`, and a placeholder-shaped match drops to `low` regardless of rule. The matched secret is read only to grade the hit and is never written into a `Finding`.
**Context:** Three months of public scans produced a curation backlog with informal vote counts ("13th appearance of the SQL-identifier FP"), all of it living in `reports/.daily_state.json` and none of it in the scanner. Mining the 87 archived reports turned those votes into numbers: the SQL-identifier cluster is 1,802 hits across 26 repositories (26.5% of all Semgrep output), `github-actions-mutable-action-tag` is 1,341 hits (20% on its own), and `generic-api-key` is 1,126 of 1,326 Gitleaks hits (85%). Retro-applying the new rules to that history moves 49% of Semgrep findings and 93% of Gitleaks hits out of the top tier.
**Consequences:** A downgraded finding is still reported - `low` confidence removes it from the "Top Findings" block (which ranks on severity then confidence) but never from the report, so a low-signal rule that is right in a given repo is still visible. Adding a rule to either set requires re-running the measurement; a rule added without a count is a guess wearing a number. The docstring of `_HIGH_FALSE_POSITIVE_SEMGREP_RULES` deliberately covers two distinct cases - outright false positives, and true-but-never-actionable posture nits - because collapsing them into one honest sentence beats two frozensets with identical behaviour. Known gap, logged in the roadmap: `sqlalchemy-execute-raw-query` fired 157 times on a project with no SQLAlchemy dependency, which is a rule-applicability problem that a confidence tier only partly mitigates.

### ADR-013: Scanner-infrastructure findings are exempt from severity filtering
**Date:** 2026-08-21
**Status:** accepted
**Decision:** Add `is_meta: bool = False` to `Finding` and to `FINDING_FIELDS`. Every finding that describes the state of the scan rather than a defect in the scanned code sets `is_meta=True`: tool not installed, tool disabled, scan error, JSON parse error, command error, no supported manifest, placeholder adapter, and the two new partial-coverage findings. `filter_by_min_severity` keeps every `is_meta` finding regardless of the floor; `select_top_findings` continues to exclude them, so they are never promoted into the headline block. `partial-coverage` joins `META_FINDING_KINDS` as a certain-state kind.
**Context:** Meta findings are emitted at `info` severity, so any run with `--min-severity medium` - which is what the public scan series uses - silently dropped them. A crashed Semgrep, a missing pip-audit and a scan that produced nothing all rendered as an identical clean-looking report. The failure mode was recorded twice in the field before it was fixed: once when a 0-byte Semgrep report was filtered out of the run that produced it, and again when pip-audit produced no output at all and its `info` meta finding never reached the report.
**Consequences:** Reports gain an `is_meta` field, which is additive and defaults to `False`, so existing consumers are unaffected. New scanner adapters must set `is_meta=True` on any finding built with `confidence_for_meta_finding(...)` - the two always travel together, and the pairing is the convention to follow rather than a mechanism that enforces itself. `--ignore-file` suppression does **not** yet honour the exemption; that is logged in the roadmap as a follow-up, since a path pattern can still hide a coverage warning.

### ADR-012: Probabilistic web template fingerprinting boundary
**Date:** 2026-05-14
**Status:** accepted
**Decision:** Add a `fingerprint/` module that indexes a curated, committed list of open-source template repositories into deterministic `RepoFingerprint` records (favicon SHA-256, distinctive static asset hashes, HTML signatures) and then probes one user-supplied live URL per invocation, scoring each candidate repo with a bounded weighted sum. Single target, single shot. The output is a SIGNAL, never an attribution: JSON + Markdown reports must keep the canonical disclaimer block and may not use words like "confirmed", "proven", "stolen", or "copied". The web probe is the only network surface besides the seeded git remotes; it validates the scheme (`http`/`https` only), honours `robots.txt` for our configured user agent, and caps both bytes per asset and total assets per target.
**Context:** AI PatchLab needs to surface "this site looks like it was built from repo X" as a remediation hint without becoming a mass crawler, a paid AI client, or an attribution oracle. The MVP must stay local-first and stay aligned with ADR-010 (no default remote/paid call) and ADR-003 (placeholder-then-real pattern reusing existing module shapes). The future use case is cross-correlating template detection with PatchLab vulnerability scans (e.g. "this site was likely built from repo X, and repo X has CVE-Y"), so the signal needs a stable score band but does not need to be a single yes/no answer.
**Consequences:** Indexer + matcher live under `fingerprint/`. No database, no DOM parser, no scraping framework: v0.1 is built on `re` + `hashlib` + `httpx`. Match results are ranked but never confirmed; the disclaimer block and the absence of attribution words are guaranteed by tests. Expanding to multi-target scanning, auto-discovery, or a DOM-based extractor requires a new ADR. The indexer clones via `scanner.git_source.cloned_repo` (no duplicated clone code); fingerprint JSON files live in `fingerprint/db/<slug>.json` (gitignored except `.gitkeep`); match reports live in `reports/fingerprint/`.

### ADR-011: Centralized scanner confidence rules
**Date:** 2026-05-14
**Status:** accepted
**Decision:** Centralize every `Finding.confidence` assignment in `scanner/confidence.py`. Each scanner adapter imports a named rule function (`confidence_for_semgrep_finding`, `confidence_for_gitleaks_finding`, `confidence_for_trivy_vulnerability`, `confidence_for_trivy_misconfiguration`, `confidence_for_dependency_vulnerability`, `confidence_for_ai_review_record`, `confidence_for_placeholder`) plus the shared `confidence_for_meta_finding(kind)` helper for cross-cutting `not-installed` / `disabled` / `not-configured` / `no-supported-manifest` / `no-findings` / `scan-error` / `json-parse-error` / `command-error` states. Magic strings (`confidence="high"`, `confidence="medium"`, `confidence="low"`) are no longer allowed inline in `scanner/scanners/*`.
**Context:** Phase 3 of the roadmap called for explicit confidence rules. The previous code assigned confidence levels as inline magic strings across five scanner adapters and `common.py`, with no shared rationale and a few mild inconsistencies between the meta-finding cases of different scanners. New scanner contributors had no documented contract for picking a level.
**Consequences:** Adding a new scanner means writing a new rule function in `scanner/confidence.py` (or reusing the meta-finding helper) instead of inventing inline strings; the rules are exercised by `tests/test_confidence.py` and behavior is unchanged for the existing scanners. The meta-finding helper rejects unknown kinds with `ValueError` so typos surface early.

### ADR-010: Disabled-by-default local AI review boundary
**Date:** 2026-05-13
**Status:** accepted
**Decision:** AI security review is disabled by default. The first implementation supports only a user-configured local command provider invoked through `subprocess.run(..., shell=False)`; no remote, hosted, or paid AI provider is contacted by default, and adding one in the future requires explicit configuration plus a new ADR.
**Context:** AI PatchLab must keep the MVP local-first, PowerShell-friendly, and free of paid API calls. The earlier AI review placeholder did not enforce a real boundary, and Phase 3 explicitly requires AI review to stay local or explicitly user-configured before any GPT-backed remediation work is reused on top of it.
**Consequences:** Default scans emit one `ai-review-disabled` info finding and never reach the network. When a user sets `AI_PATCHLAB_AI_REVIEW_ENABLED=true` with provider `local_command` and a wrapper path, AI PatchLab executes that wrapper, accepts JSON list or `{ "findings": [...] }` shapes, and normalizes results into the shared `Finding` schema. Disabled, misconfigured, command-failure, JSON-parse, and empty-result states all surface as normalized `info` findings so the security report still completes.

### ADR-009: pip-audit CLI dependency scanner integration
**Date:** 2026-05-13
**Status:** accepted
**Decision:** Integrate Python dependency scanning through local pip-audit execution and consume its JSON vulnerability output.
**Context:** AI PatchLab needs a real dependency scanner while keeping the MVP local-first, PowerShell-compatible, and free of bundled scanner binaries or paid APIs. pip-audit supports requirements files, local Python project paths, JSON output, and clear exit codes for vulnerable versus clean dependency sets.
**Consequences:** Users must install pip-audit separately or make the `pip_audit` Python module available. The scan writes `reports/raw/pip-audit.json`, normalizes supported vulnerability records into the shared finding schema, and continues with an info finding when pip-audit is missing, unsupported manifests are absent, or scanner setup fails.

### ADR-008: Trivy CLI filesystem scanner integration
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Integrate Trivy through the local CLI in filesystem mode and consume its JSON report output for vulnerabilities and misconfigurations.
**Context:** AI PatchLab needs real repository dependency and configuration scanning while preserving the local-first, PowerShell-compatible MVP and avoiding bundled scanner binaries or paid APIs.
**Consequences:** Users must install Trivy separately and ensure it is available on `PATH`. The scan writes `reports/raw/trivy.json`, normalizes supported findings into the shared schema, and continues with an info finding when Trivy is missing or cannot produce usable results.

### ADR-007: Rule-based patch suggestion fields
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Add deterministic patch suggestion fields to normalized findings and render them in Markdown reports.
**Context:** AI PatchLab needs concise before/after remediation examples for common vulnerability patterns without calling paid APIs.
**Consequences:** Reports can show actionable patch guidance for known patterns today, and future GPT-backed remediation can reuse the same `patch_before`, `patch_after`, and `remediation_explanation` schema.

### ADR-006: Deterministic recommendation enrichment
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Enrich normalized finding recommendations with local rule-based keyword matching.
**Context:** Remediation guidance needs to be specific and actionable for common security findings while preserving raw scanner output and avoiding paid APIs in the MVP.
**Consequences:** Recommendation quality improves for known patterns, but coverage depends on maintaining deterministic keyword rules until a later configurable AI review layer is introduced.

### ADR-005: Semgrep CLI as static analysis scanner integration
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Integrate Semgrep through the local CLI and consume its JSON report output.
**Context:** AI PatchLab needs a real static analysis scanner while preserving the local CLI MVP and PowerShell-compatible workflow.
**Consequences:** Users must install Semgrep separately or have it available at the supported Python user Scripts fallback path. If Semgrep is missing, the scan continues with an info finding instead of failing the full report.

### ADR-004: Gitleaks CLI as first real scanner integration
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Integrate Gitleaks through the local CLI and consume its JSON report output.
**Context:** AI PatchLab needs real secret scanning while staying PowerShell-friendly and avoiding bundled scanner binaries or paid APIs.
**Consequences:** Users must install Gitleaks separately and ensure it is available on `PATH`. If it is missing, the scan continues with an info finding instead of failing the full report.

### ADR-003: Placeholder scanner adapters before real tool execution
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Start with modular placeholder adapters for Semgrep, Gitleaks, Trivy, dependency scanning, and AI security review.
**Context:** The immediate goal is to lock the normalized finding schema, report generation, and PowerShell-friendly CLI before integrating external scanner binaries.
**Consequences:** v0.1 reports contain info-level placeholder findings. Real scanners can replace each module independently while preserving the report contract.

### ADR-002: Data stack for local scanner MVP
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Use the EzProject `data` stack as the primary stack for AI PatchLab MVP v0.1.
**Context:** The MVP reads a local repository path, normalizes scanner outputs, and writes JSON and Markdown reports. It does not expose a REST API, ship a web app, or call paid AI APIs.
**Consequences:** Keep the scanner as a local Python CLI first. Future AI-agent patterns may be added after the scanner workflow and remediation report format are stable.

### ADR-001: Initial project scaffold
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Use EzProject v4 template as project foundation.
**Context:** Need a standardized project structure with built-in quality gates, slash commands, subagents, and reference patterns.
**Consequences:** All code follows CLAUDE.md coding standards. Use examples/ patterns as reference. Use PRP workflow for features.
