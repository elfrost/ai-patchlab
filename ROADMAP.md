# ROADMAP - ai-patchlab

## Conventions
- `[ ]` = Todo
- `[-]` = In Progress (YYYY/MM/DD)
- `[x]` = Completed (YYYY/MM/DD)

---

## Phase 0 - Bootstrap
- [x] Project scaffolded from EzProject v4 template - Project mode (2026-05-12)
- [x] Stack finalized as `data` (2026-05-12)
- [ ] Virtual environment + dependencies installed
- [ ] `.env` configured
- [x] `/kickoff` interview completed (2026-05-12)
- [x] `INITIAL.md` populated with MVP v0.1 scanner foundation spec (2026-05-12)

## Phase 1 - Scanner Foundation
- [x] CLI accepts a local repository path (2026-05-12)
- [x] `reports/` is created automatically when missing (2026-05-12)
- [x] JSON and Markdown reports are generated (2026-05-12)
- [x] Normalized finding schema implemented (2026-05-12)
- [x] Placeholder scanner modules added for Semgrep, Gitleaks, Trivy, dependency scan, and AI review (2026-05-12)

## Phase 2 - Real Scanner Integrations
- [x] Add Semgrep execution and result parsing (2026-05-12)
- [x] Add Gitleaks execution and result parsing (2026-05-12)
- [x] Add Trivy execution and result parsing (2026-05-12)
- [x] Add dependency scan execution and result parsing (2026-05-13)

## Phase 3 - Remediation Planning
- [x] Generate actionable remediation recommendations from findings (2026-05-12)
- [x] Add confidence rules for scanner outputs (2026-05-14)
- [x] Add patch-plan Markdown section (2026-05-12)
- [x] Keep AI review local or explicitly user-configured (2026/05/13)

## Phase 3.5 - Public scans & reputation
- [-] Set up GitHub Pages scan log under `docs/` (2026/05/14)
- [x] Add `--from-git-url` to scan a public repo with one command (2026-05-14)
- [ ] Add `--min-severity` filter to keep public reports focused
- [ ] Add a "Top findings" summary block at the top of `security_report.md`
- [ ] First public scan published

## Phase 4 - Polish & Stabilize
- [ ] Add integration tests with sample vulnerable repositories
- [ ] Add clear scanner failure handling and partial-report behavior
- [ ] Add release checklist

## Phase 5 - Scaling & CI/CD
- [ ] CI/CD pipeline - GitHub Actions for lint and tests
- [ ] Performance profiling - Identify slow scanner steps
- [ ] Optional cache strategy for repeated scans

## Phase 6 - Monitoring & Observability
- [ ] Structured scan logs
- [ ] Optional alerting for scheduled scans
- [ ] Metrics for scan duration and finding counts

## Backlog
- [ ] Patch-ready output generation
- [ ] SARIF export
- [ ] Repository baseline comparison
- [ ] Web UI, after CLI workflow is stable

---

## Completed
<!-- Items completed are moved here with their date -->
- [x] AI-Trader fork scan validated end-to-end with Semgrep/Gitleaks environment fixes and actionable recommendations for observed findings (2026-05-12)
