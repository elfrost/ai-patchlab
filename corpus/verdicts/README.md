# Dismissal corpus

One file per scan: `<slug>.json`, copied from `reports/<slug>/verdicts.json` by
`/daily` Phase 6.

`reports/` is gitignored - it holds raw scanner dumps and unsent private
disclosure drafts - so a corpus left there lives on one machine and does not
survive a clone. This directory is committed, which is the whole point: ADR-014
only worked because the archived reports happened to still be on disk.

Validate one file, or count the corpus:

```bash
.venv/Scripts/python.exe scanner/run_verdict_check.py --check reports/<slug>/verdicts.json
.venv/Scripts/python.exe scanner/run_verdict_check.py --summary
```
