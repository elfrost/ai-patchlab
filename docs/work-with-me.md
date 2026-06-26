---
layout: default
title: Work with me — AI agent & LLM security review
---

# Work with me

I do **independent security review of AI agents, MCP servers, and LLM applications** — the kind of careful, curated audit the [public scan log]({{ '/' | relative_url }}) demonstrates, run privately and in depth against your codebase.

If you're shipping an agent framework, an MCP server, a RAG pipeline, or anything that brokers credentials or executes tool calls on a user's behalf, the questions that matter aren't "how many findings does a scanner produce" — they're *which findings are real, which are reachable, and which are the dangerous one hiding behind a guard that almost holds.* That's the work.

## The proof is public

Everything I'd do for you, I've done in the open — [36 curated scans]({{ '/' | relative_url }}) of well-known AI/agent projects, with **9 confirmed fixes** where maintainers acted on the findings, and a documented methodology behind each one.

- **Real findings, not scanner noise.** A typical scan starts at hundreds of raw findings and ends at a handful that matter — because the rest are false positives, by-design patterns, or vendored third-party code. The curation is the value.
- **Reachability over rule-count.** A `subprocess(shell=True)` that's safe under operator trust can become a multi-tenant sandbox escape once you trace who reaches it — and a scary-looking SQL string can be fully gated by a five-character allowlist. The verdict goes wherever the *code* goes, which means reading the code, not the rule.
- **Responsible disclosure, done right.** Severe findings go to you privately first — never a public issue before you've patched. False positives are documented so you don't waste a sprint on them. Good engineering gets credited, not nitpicked. (Maintainers have called the reports *"unusually clean,"* *"careful,"* and *"well-structured and actionable."*)

## What an engagement looks like

| | **First-look** | **Full review** | **Ongoing** |
|---|---|---|---|
| **Scope** | One service / repo, the high-risk surfaces (auth, tool execution, credential handling, ingestion trust) | The whole codebase: source, dependencies (with reachability), container/CI, the trust model | Recurring review on a cadence — pre-release, per-quarter, or per-major-feature |
| **You get** | A prioritized list of real, exploitability-shaped findings with fix guidance + the documented FPs, and a call to walk through them | The above, plus an architecture-level write-up of the trust boundaries and where they're thin | A standing relationship — your codebase reviewed as it evolves, not just once |
| **Price** | **$750** flat | scoped — *contact for a quote* | retainer, by arrangement |

*The first-look is a fixed-price entry point — one focused pass to surface what actually matters, with a call to walk through it. Anything larger is scoped per engagement: a 200-LOC MCP server and a 24-MB multi-tenant harness are not the same audit, so tell me the shape and I'll give you a real number.*

## What I'm especially good at

The current AI/agent ecosystem, specifically: **MCP servers, agent harnesses, tool-execution sandboxes, credential brokering, multi-tenant agent platforms, RAG ingestion, and the LLM-prompt-injection threat model.** These are surfaces where off-the-shelf scanners are structurally blind — they see syntax, and the risk lives in cross-process trust boundaries, absence-of-control, and "who can reach this sink with what input." That gap is the whole reason the public scans surface things scanners miss.

## ai-patchlab-pro *(coming)*

The curation engine behind the public scans — the adversarial-verification workflows, the reachability and ownership-split analysis, the call-graph-aware rule refinements — is becoming a private tool: **scan your own repo with the curation layer, not just the raw scanners.** If you'd want that as a product (self-hosted or hosted), say so when you reach out and I'll add you to the early list.

## Get in touch

Email **[dosiswow2@gmail.com](mailto:dosiswow2@gmail.com?subject=AI%20agent%20security%20review%20enquiry)** with:

- a one-line description of the project (and a repo link if it's shareable),
- the rough scope you're thinking (triage vs full review vs ongoing),
- and any timeline or trigger (a release, a SOC 2 push, an enterprise deal, a funding diligence).

I'll come back with a scoped proposal and a real number. No source code leaves your control without an arrangement you're comfortable with — the public scans are all run on public repos, and a private engagement is private.

---

*[← back to the scan log]({{ '/' | relative_url }})*
