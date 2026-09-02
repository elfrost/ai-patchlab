---
layout: default
title: "HKUDS/OpenOPC: security scan"
description: "Security scan of HKUDS/OpenOPC: 56 findings at medium+ collapse to one real gap — a WebSocket control plane that drives a careful permission model but authenticates nobody, bound to 0.0.0.0 by default. Disclosed privately, detail withheld."
date: 2026-09-02
---

# HKUDS/OpenOPC — security scan

**Repository:** [HKUDS/OpenOPC](https://github.com/HKUDS/OpenOPC) — 1.6k★, "Build Your Personal AI-Native Company": a self-hosted platform that recruits role-specific AI employees, assigns them tasks, and runs them across nine verticals. Python engine (`opc/`, layered `layer0…layer6`), a native tool runtime that executes shell/Python/git, and an aiohttp Office-UI server bridging the engine to a React + Phaser frontend over a WebSocket.
**Commit scanned:** `50007e0` (HEAD of `main` at scan time)
**Scan date:** 2026-09-02
**Disclosure status:** **Private — detail withheld.** OpenOPC's `SECURITY.md` asks that vulnerabilities be reported through GitHub's private vulnerability reporting and not in a public issue or discussion. One High-severity finding has been filed privately through that channel; only the finding *class* appears below. This page will be expanded once the maintainers resolve, or after a 90-day window.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 0 |
| High | 34 |
| Medium | 20 |
| Low | 0 |
| Info | 2 (filtered) |

**56 findings at `--min-severity medium`. After curation: one real defect — and no scanner produced it.** The 34 "highs" were 12 SQLAlchemy-raw-query hits in a project with no attacker-controlled SQL values, 8 insecure-WebSocket (`ws://`) frontend hits, and a `litellm` dependency-CVE cluster that is version-matched but not the reachable defect. The one real item is a design gap in the plumbing *around* an unusually careful security model — the kind of thing a rule cannot see, because every individual line is fine.

## The finding (class only, detail withheld)

**Class:** missing authentication on a critical function (CWE-306) combined with missing Origin validation on a WebSocket (CWE-1385), on the control plane of a platform whose purpose is running code.

The shape, without the specifics. OpenOPC ships a genuinely thoughtful permission model: three tool-approval levels, a per-level sandbox profile, path-traversal guards on its file routes, and — the detail that shows real care — a workspace-trust store deliberately kept *outside* the app's own home directory, so a repository can never grant trust to itself by committing files into it. When an agent wants to run a process, that model decides whether to allow it, ask the operator, or refuse.

The gap is not in the model. It is in the socket that drives it. The server that carries every command from the UI to the engine accepts connections with no authentication and no check on where the connection came from, and by default it listens on every network interface rather than loopback only. The whole permission model rests on one unstated assumption — that the party sending commands is the local operator sitting at the machine — and nothing on that socket enforces it.

That matters because two of the commands the socket accepts are, between them, enough to change the permission level the model uses and then ask an agent to do work that runs code. On a platform built to execute code on your behalf, the boundary that is supposed to hold is "only you decide what runs and at what privilege." That boundary is the one this crosses.

It is reachable two ways, and neither needs a credential: another machine on the same network can reach the default-exposed port directly, and — because a browser does not apply its same-origin rule to *opening* a WebSocket, and the server does no origin check — a web page the operator merely visits while the server is running can open the socket and drive it. The shipped frontend connects to that socket with no token at all, which is itself the confirmation that there is nothing to forge.

I filed this as **High**, not Critical, because it requires the Office-UI server to be running and reachable at the time — a live session, not a dormant install. But within that window it is unauthenticated, and it ends at code execution on the operator's host.

## What verification added

The finding is architectural, so most of it is settled by reading: the socket handler never looks at a request header, and the default bind is `0.0.0.0`. The one thing worth executing was the privilege step. Ran the project's own permission resolver against a process-executing tool at the shipped default level, then again after the level-change the socket allows: the first returns *ask the operator*; the second returns *allow, with no prompt*, in the resolver's own words. That is the difference between "an attacker queues a task you would have to approve" and "an attacker runs code." The socket lets an unauthenticated caller move the system from the first state to the second.

## Patterns observed

This is the **loopback-inversion** class the series keeps meeting on desktop and self-hosted apps, and OpenOPC is one of its cleaner examples precisely *because* the security engineering around it is good. When a project has no permission model, an exposed control plane is one bug among many. When a project has a careful, correct permission model and then leaves the socket that feeds it open, the exposed socket is *the* bug — it silently voids the assumption the whole model was built on. The tell is never in the impressive machinery; it is in the boring plumbing beside it.

The scanners were no help here, and honestly could not have been. A default bind address and a missing header check are not vulnerabilities in any single line — they are vulnerabilities in a relationship between a listener, a permission model, and an execution path in three different files. Semgrep did flag eight `ws://` insecure-transport hits in the frontend and a raft of SQLAlchemy-raw-query highs; none of those was the real issue, and the real issue appears in none of them.

## Notes on the tool

- **Semgrep coverage was partial and, as usual, the truth was in the `errors` array, not `paths.skipped` (which was 0).** 22 rules timed out and three Python files failed to parse entirely — including `opc/plugins/office_ui/snapshot_builder.py` and `opc/llm/provider.py`. The control-plane file `ws_handler.py` (a 440 KB, ~9,000-line module) had three rules time out on it. The finding lives in that file. Every real item in this series' history has come from a hand read; this scan is another vote for the standing backlog item that a timed-out rule on the file that matters must be surfaced as a coverage gap, not silence.
- **34 "high" findings, one real, and the real one is not among them.** The SQLAlchemy-raw-query rule fired 12 times on parameterized queries with only identifiers interpolated — the single most recurring false-positive cluster in the series. The insecure-`ws://` rule fired 8 times on frontend code that correctly derives its scheme from `window.location`. Neither points at the missing authentication on the socket those very messages travel over.

## Disclosure timeline

- 2026-09-02 — scan run; finding verified against the project's own permission resolver
- 2026-09-02 — reported privately via GitHub private vulnerability reporting
- 2026-09-02 — public post (this page), finding class only

## Reproduce

```bash
git clone https://github.com/HKUDS/OpenOPC /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/hkuds-openopc --min-severity medium
```

*The scan is reproducible; the finding detail is withheld until the maintainers resolve or a 90-day window elapses, per the project's security policy.*
