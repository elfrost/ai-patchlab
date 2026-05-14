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
