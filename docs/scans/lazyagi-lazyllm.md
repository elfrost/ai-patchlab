---
layout: default
title: "LazyAGI/LazyLLM: security scan"
date: 2026-06-06
---

# LazyAGI/LazyLLM — security scan

**Repository:** [LazyAGI/LazyLLM](https://github.com/LazyAGI/LazyLLM) — 3.8k★, Apache-2.0, a multi-agent LLM application framework backed by SenseTime (top-committer emails on `sensetime.com`) with a distributed deploy-relay server, fine-tuning components, RAG tooling, and an HPC launcher layer.
**Commit scanned:** `b11fa4c12b1b` (HEAD of `main` at scan time)
**Scan date:** 2026-06-06
**Disclosure status:** **Post-only public + private email to maintainer.** No `SECURITY.md` or PVR is published, but the project is corporate-backed (SenseTime); the two highest-severity items surfaced by curation warranted private disclosure rather than a public courtesy issue. Disclosure email sent to `wangzhihong@sensetime.com` (top-committer corporate address) covering the two severe items. This post discusses the broader patterns and the items that can be discussed publicly without enabling exploitation.

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 73 |
| Medium | 48 |
| Low | 0 |
| Info | 0 (filtered) |

**121 total findings. After curation: two items reported privately to the maintainer; a series-record **16-site `pull_request_target` workflow cluster** in a single workflow file; a six-CVE dependency tail dominated by Gradio (×3) and DeepSpeed (RCE class); the recurring SQL-identifier and agent-shell-tool classes; and a classic `eval()`-based calculator agent tool pattern. The 17 gitleaks generic-api-key hits are entirely in test fixtures (a file literally named `test_validate_api_key.py` and Feishu-URL test data).**

## Top findings (curated)

### 1. `.github/workflows/main.yml` — 16-site `pull_request_target` + checkout PR head cluster

**Tool:** Semgrep (`yaml.github-actions.security.pull-request-target-code-checkout`)
**Verdict:** **Real — series record for this class. Every job in `main.yml` (16 sites: lines 36, 74, 116, 177, 232, 282, 329, 408, 462, 500, 548, 593, 673, 722, 803, 870) checks out the PR head SHA under `pull_request_target`.**

The repeating pattern at every job:

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}
    fetch-depth: 2
```

`pull_request_target` is the privileged variant of the PR trigger — it runs with the *base* repo's `GITHUB_TOKEN` write scopes and (depending on the workflow) access to repository secrets. Combining it with `actions/checkout@v4` at `ref: ${{ github.event.pull_request.head.sha }}` deliberately checks out the *attacker-controlled* PR head into the privileged context. Any job step that runs code from the checked-out tree (`make lint-only-diff`, `make doccheck`, the test runners, etc.) executes attacker code with the privileged token.

The same class has appeared on [airweave](airweave-ai-airweave.html) (single-site, since fixed) and on [Giskard](giskard-ai-giskard-oss.html) (clean teardown of how to use `pull_request_target` correctly). 16 sites in one workflow is the series record by an order of magnitude.

**Architectural fix shape** (per the [Giskard teardown](giskard-ai-giskard-oss.html)): split into two workflows. One uses `pull_request_target` for trusted, code-free steps (label management, comments, secret-gated reporting); the other uses plain `pull_request` for code-running steps (lint, tests, doc checks) without secrets. The `pull_request_target` jobs never check out the PR head.

### 2. `requirements.txt` — Gradio 5.49.1 carries three named CVEs

**Tool:** Trivy
**Verdict:** **Real — single pin bump clears all three.**

| CVE | Class |
|---|---|
| Path Traversal (absolute path, Windows) | High |
| Server-Side Request Forgery (SSRF, internal access) | High |
| Open Redirect | Medium |

Plus the alpaca-LoRA fine-tuning component's `requirements.txt` carries **`DeepSpeed` Remote Code Execution Vulnerability** and a `sentencepiece` invalid-memory-access advisory. Two `lxml_html_clean` advisories round out the dep tail. No Dependabot is configured on the repo, consistent with the pattern across the recent series ([MemoryBear](suanmosuanyangtechnology-memorybear.html), [agency-swarm](vrsen-agency-swarm.html), [ouroboros](q00-ouroboros.html)).

### 3. `lazyllm/tools/tools/calculator.py:9` — `Calculator` agent tool uses `eval()` over LLM-controlled expression

```python
from math import *  # noqa. import math functions for expressions

class Calculator(ModuleBase):
    def __init__(self):
        super().__init__()

    def forward(self, exp: str, *args, **kwargs):
        return eval(exp)
```

**Tool:** Semgrep (`eval-detected`)
**Verdict:** **Real — the classic agent-tool eval-sandbox-escape pattern.**

The `Calculator` tool is registered as something an agent can call (`forward(exp)` is the tool-call entrypoint). `exp` comes from the LLM. `eval(exp)` with `from math import *` in scope gives the LLM full Python access — calling `__import__('os').system('...')`, reading the file system, exfiltrating env vars, etc. The "calc tool" → "RCE" pivot is documented in every LLM-agent-security overview from the last two years.

The safer shapes are well-known:
- `ast.literal_eval(exp)` — only handles literals; rejects function calls
- `simpleeval` or `numexpr` — purpose-built safe-math evaluators
- A regex-validated allowlist of operators + `eval` only after validation

### 4. 25× SQL identifier interpolation (`text(f"…")` / formatted-SQL / asyncpg-sqli) — the recurring class

**Tool:** Semgrep (`avoid-sqlalchemy-text` + `sqlalchemy-execute-raw-query` + `formatted-sql-query`)
**Verdict:** **Same class as on nine prior scans — gated by configuration-controlled identifiers today, brittle to future input-source changes.**

The pattern keeps repeating: identifiers (table names, collection names) come from validated config, no real injection vector with the current input sources, but the defensible long-term shape is SQLAlchemy's `quoted_name()` / `Identifier()`. Cross-scan link discipline applies: [Upsonic](upsonic-upsonic.html), [PraisonAI](mervinpraison-praisonai.html), [airweave](airweave-ai-airweave.html), [honcho](plastic-labs-honcho.html), [dstack](dstackai-dstack.html), [pixeltable](pixeltable-pixeltable.html), [semantic-router](aurelio-labs-semantic-router.html), [ReMe](agentscope-ai-reme.html), and now LazyLLM.

### 5. `lazyllm/tools/agent/shell_tool.py:74` + 3× HPC launcher `shell=True` — the recurring by-design class

**Verdict:** **By-design.**

`shell_tool.py:74` is the agent's shell tool — same pattern as [fast-agent](evalstate-fast-agent.html)'s `interactive_shell.py`, [agency-swarm](vrsen-agency-swarm.html)'s `PersistentShellTool.py`, [ReMe](agentscope-ai-reme.html)'s `tools/shell.py`. The agent operator opts in; the LLM controls the command on purpose.

The 3× `subprocess shell=True` in `lazyllm/launcher/{base,sco,slurm}.py` are HPC job launchers (SLURM / SenseTime SCO cluster). They build cluster-job command strings programmatically and shell them out. By-design for the launcher use case.

### 6-N. Standard noise / by-design

| Finding | Files | Verdict |
|---|---|---|
| 17× gitleaks `generic-api-key` | `tests/charge_tests/Models/test_validate_api_key.py` (11×), `tests/basic_tests/Tools/test_feishu_fs_url.py` (6×) | **FP** — the first file is *literally* `test_validate_api_key` (test fixtures for an API-key validator), the second is Feishu (Lark) test URLs. Both are textbook curation-only-knows fixture-FP shape. |
| 17× `pickle.load`/`dump` | Across `module/module.py`, `module/servermodule.py`, `tools/rag/migrate_collections.py`, `components/finetune/easy_r1/model_merger.py`, etc. | **Mixed — most are local-file model serialization (by-design); one specific call site sits behind an HTTP endpoint and was disclosed privately.** |
| 13× `non-literal-import` | Plugin / module-loader discovery | **By-design** |
| 4× `pickles-in-pytorch` | PyTorch model checkpoint loads | **By-design** — standard PyTorch ckpt path |
| 4× `run-shell-injection` | `.github/actions/{load_cache,run_tests}/action.yml`, `.github/workflows/publish_release.yml` ×2 | Real best-practice — the recurring `${{ }}`-into-`run:` class. Standard `env:`-indirection fix. |
| 1× SSRF in `lazyllm/tools/train_service/serve.py:752` | `requests.get(data_path)` where `data_path = job.training_dataset[0].dataset_download_uri` | Real if the train-job submission is exposed to untrusted users; gated to operator-submitted job configs today. |
| 3× `dangerous-globals-use` | Dispatch / plugin patterns | **By-design** |
| 2× `dynamic-urllib`, 2× `insecure-hash` | URL-builder / non-crypto digest patterns | Typically the safe case |

## Patterns observed

**A 16-site `pull_request_target` cluster is the cleanest single-finding example yet for "this is one architectural pattern, not 16 separate things."** Across the series the worst-case raw count for any one class on one repo had been the SQL-identifier cluster at 139 sites in three files on [ReMe](agentscope-ai-reme.html). The workflow cluster here is concentrated even more — all 16 are in one file, every job uses the same dangerous shape. A two-workflow split fixes all 16 at once. The class itself isn't novel (we've covered it three times already) but the concentration is.

**Corporate backing changes the disclosure calculus more than a published SECURITY.md does.** LazyLLM has no `SECURITY.md` and no PVR enabled; the strict-norm heuristic (presence of `SECURITY.md`) would have routed today's curation toward a single public courtesy issue. The dispositive signal turned out to be the top-committer email (`@sensetime.com`) — a clear corporate disclosure target — together with the severity of two specific findings. The methodology lesson worth adding: *severity overrides the heuristic when no formal channel exists*. Two findings warranted private disclosure regardless of whether the repo had advertised a channel; the existence of a corporate address made it concretely possible.

**The "calculator tool that `eval`s" finding is a teaching moment.** Among the LLM-agent-security articles that get cited most often, the example pattern is exactly `def forward(exp): return eval(exp)`. That pattern shipping in a 3.8k-star framework as a registered agent tool is what people mean when they say "the well-known classes show up in real codebases continuously." Filed in the public post because the pattern is widely-documented; the actionable shape (`simpleeval` / `ast.literal_eval`) is one line of code per call site.

## Notes on the tool

- The `--ignore-samples` default kept the FP pile at the 17 gitleaks test-fixture hits and the standard `python36/37-compatibility-*` lint. None of the new defaults shipped 2026-05-28 would have suppressed the test-fixture gitleaks bunch; an additional default-ignore for `tests/**/test_*api_key*.py` shape paths would (it's the explicit-fixture-name pattern that the curator notices instantly).
- This is the **fourth scan** where the cross-scan link discipline (`see [other-scan]`) carries the curation story. The series-narrative density is now load-bearing for the posts; future tool-side work to auto-link recurring classes against prior reports would compress curation time materially.

## Disclosure timeline

- **2026-06-06** — Scan run at commit `b11fa4c12b1b`; findings curated.
- **2026-06-06** — Two highest-severity items disclosed privately by email to `wangzhihong@sensetime.com` (top-committer corporate address — no `SECURITY.md` or PVR is published, so the corporate-address path is the appropriate channel). No public courtesy issue filed; the items that can be discussed publicly without enabling exploitation are covered in this write-up.

## Reproduce

```bash
git clone https://github.com/elfrost/ai-patchlab
cd ai-patchlab
pip install -e ".[dev]"
python scanner/run_scan.py \
  --from-git-url "https://github.com/LazyAGI/LazyLLM" \
  --reports-dir reports/lazyagi-lazyllm \
  --min-severity medium \
  --ignore-samples
```

External tools (Semgrep, Gitleaks, Trivy, pip-audit) need to be installed separately — see the [project README](https://github.com/elfrost/ai-patchlab#readme).
