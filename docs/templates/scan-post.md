---
layout: default
title: "owner/repo: security scan"
date: YYYY-MM-DD
---

# owner/repo - security scan

**Repository:** [owner/repo](https://github.com/owner/repo)
**Commit scanned:** `<sha>`
**Scan date:** YYYY-MM-DD
**Disclosure status:** draft / disclosed / public after 90-day window

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |

**Total findings:** N (M of interest after curation)

## Top findings

### 1. <short title>

- **File:** `path/to/file.py:42`
- **Tool:** semgrep
- **Confidence:** high
- **Why it matters:** <one sentence>
- **Recommendation:** <one sentence>

<repeat for top 3-7 findings; redact details if pre-disclosure>

## Patterns observed

<2-4 paragraphs about what was common, what surprised you, what the
maintainers appear to do well. This section is what builds the writer's
reputation - show insight, not just a finding list.>

## Notes on the tool

<Anything AI PatchLab missed, false-positived on, or could improve.
Each item here should map to a backlog entry in the AI PatchLab repo.>

## Disclosure timeline

- YYYY-MM-DD - scan run
- YYYY-MM-DD - maintainers notified privately
- YYYY-MM-DD - public post (this page)

## Reproduce

```bash
git clone https://github.com/owner/repo /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/owner-repo
```
