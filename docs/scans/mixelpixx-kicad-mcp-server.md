---
layout: default
title: "mixelpixx/KiCAD-MCP-Server: security scan"
description: "Security scan of mixelpixx/KiCAD-MCP-Server: 29 findings, 0 real — 20th clean scan: an MCP server (1.6k★, MIT) that drives KiCAD for AI-assisted PCB design"
date: 2026-07-22
---

# mixelpixx/KiCAD-MCP-Server - security scan

**Repository:** [mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)
**Commit scanned:** `2f05a725f9ac`
**Scan date:** 2026-07-22
**Disclosure status:** public (clean scan — no maintainer contact required)

## Summary

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | 9 |
| Medium | 20 |
| Low | 0 |
| Info | 0 |

**Total findings:** 29 (0 real after curation — 20th clean scan)

## The shape of the target

KiCAD MCP Server (1.6k★, MIT) is a [Model Context Protocol](https://modelcontextprotocol.io)
server that lets an AI assistant drive **KiCAD** for PCB design — place components,
create symbols and footprints, route, run DRC/ERC, export production files. It's a
two-language bridge: a **TypeScript MCP server** (`src/`) that speaks the protocol and
spawns a long-lived **Python backend** (`python/kicad_interface.py`) which talks to KiCAD
through the bundled `pcbnew` SWIG bindings. The AI's tool calls become JSON commands piped
over stdin to that Python process.

For an MCP server the curation question is narrow and specific: **can a tool argument
reach a dangerous sink** — a shell, a network egress it shouldn't make, a file write
outside its lane? The tool surface here is unusually wide (schematic editing, footprint
generation, an autorouter shell-out, an LCSC datasheet helper, a JLCPCB parts-database
downloader, Eagle/SVG import), so there were plenty of places to look. Every one of them
comes back clean or by-design.

## Top findings — and why each is not real

### 1. Six `use-defused-xml-parse` "highs" — the one genuine residual, and it's DoS-only

The import features parse untrusted XML with the standard library:
`python/commands/eagle.py:578` (Eagle `.sch`), `python/commands/svg_import.py:543`
(SVG logos), `python/commands/schematic_handlers.py:2843/3068`, and
`python/kicad_interface.py:4142` (kicad-cli netlist) all call
`xml.etree.ElementTree.parse()` on a caller-supplied file, with no `defusedxml` in either
`requirements.txt`.

This is the only finding that describes a real class — you *are* parsing files a user
may have received from someone else — but the impact is bounded and worth stating
precisely. CPython's `ElementTree` (expat) **does not resolve external general entities**;
a `SYSTEM "file:///etc/passwd"` or `http://…` entity is not fetched, it raises. So the
classic XXE outcomes — arbitrary **file read** and **SSRF** — are off the table here. What
remains is **entity-expansion DoS** (billion-laughs / quadratic blowup): a maliciously
nested design file could exhaust memory and hang the local process. That's real, but it's
**self-inflicted and local** — the user asked to import the file, and the blast radius is
their own KiCAD MCP process. A one-line-per-file hardening (`import defusedxml.ElementTree
as ET`) closes it; it does not clear the "exploitability-shaped, high-confidence" bar that
gates a courtesy issue.

### 2. Four JLCPCB SQL "highs" — the identifier-interpolation false positive

`python/commands/jlcpcb_downloader.py:166` and `:237` trip both
`sqlalchemy-execute-raw-query` and `formatted-sql-query`:

```python
count = src.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
...
for row in src.execute(f"SELECT * FROM [{relation}]"):
```

This is the [single most recurring false positive in the series](scans/mnemosyne-oss-mnemosyne.html):
the f-string interpolates an **identifier**, never a value. `name`/`relation` come from the
source SQLite's own schema (`_relation_names()` → `sqlite_master`), are bracket-quoted, and
every data column on the write side is a bound `?` parameter
(`INSERT … VALUES (?, ?, ?, …)`). No user value reaches the query text.

### 3. Two `detect-child-process` "highs" — operator-gated, and the real path is argv

`src/server.ts:365` and `:420` build a shell string:

```javascript
exec(`"${pythonExe}" --version`, …);
const testCommand = `"${pythonExe}" -c "import pcbnew; print('OK')"`;
```

`pythonExe` comes from `findPythonExecutable()` — a project `venv`/`.venv`, then the
`KICAD_PYTHON` **environment variable**, then the KiCAD-bundled interpreter. It is
operator configuration, not an MCP-client input; an operator who sets `KICAD_PYTHON` to a
malicious string is injecting into their own machine. And the path that actually runs the
backend (`src/server.ts:516`) already uses `spawn(pythonExe, [scriptPath], …)` with an
**argv array** — no shell. Swapping the two validation `exec()`s to `execFile` is a clean
defense-in-depth nit, not a remote-reachable bug.

### 4. Four `path-join-resolve-traversal` medium — constant segments

`src/server.ts:95–117` flags `join(binDir, "Lib", "site-packages")`,
`join(projectRoot, "venv", …)` and friends. The variable roots are `__dirname`-derived or
platform-detected; the appended segments are **string constants**. There is no
user-controlled path component to traverse with.

## What the scanner can't see — the sweep

Static rules under-count MCP servers (the [zotero-mcp](scans/54yyyu-zotero-mcp.html)
lesson), so the network/subprocess/egress surfaces got a hand sweep. All three held:

- **Autorouter shell-out.** `freerouting.autoroute` takes AI-supplied `boardPath`,
  `outputPath`, and `jarPath` and runs `java -jar …` (or a Docker variant). The command is
  assembled as a **`List[str]` argv** in `_build_freerouting_cmd()` and handed to
  `subprocess.run([...])` — no `shell=True`, no interpolation into a shell. The tool inputs
  are argv elements, so there's no command injection despite the wide-open path arguments.
  Well-built; **credit the defense.**
- **Datasheet "fetch."** `get_datasheet_url` / the LCSC enricher only *construct* a URL
  string (`https://www.lcsc.com/datasheet/<LCSC#>.pdf`) and write it into the schematic —
  the code and its docstring are explicit that **no network request is made**. No SSRF.
- **The `express` import.** `src/server.ts` imports `express` but never calls `.listen()`
  or mounts a route — the transport is `StdioServerTransport` only. There is **no network
  listener** and therefore no unauthenticated HTTP surface to protect.

## Patterns observed

The interesting thing about this repo is how *little* attack surface a capable MCP server
can have when it commits to the local, STDIO-only transport. Every dangerous-looking
primitive here — a `child_process` spawn, an autorouter subprocess, an XML importer, a SQL
loader — is real, but each is either driven by argv (freerouting, the backend spawn),
gated behind operator config (`KICAD_PYTHON`), or parsing files on the user's own disk at
the user's own request. There's no remote principal in the threat model, which collapses
the interesting classes (RCE, SSRF, arbitrary write) before they start.

The freerouting handler is the highlight: it's exactly the pattern that usually *is* the
finding — take a filename from an untrusted-ish caller, shell out to a JAR — done right,
as an argv list, with a Docker-isolated variant beside it. The datasheet helper is a nice
inversion too: the "URL fetch" a scanner would want to flag is a string built from a part
number and never dereferenced.

The genuine residual — stdlib `ElementTree` on the import paths — is worth a maintainer's
five minutes precisely because the impact is *smaller* than a scanner implies. It is not
XXE-as-file-read (CPython won't fetch external entities); it is entity-expansion DoS, and
naming that distinction is the useful part of the write-up. The `defusedxml` swap is the
right hardening; the "arbitrary file disclosure" reading is not.

Housekeeping-tier residuals round it out: twelve `github-actions-mutable-action-tag`
mediums in `.github/workflows/ci.yml` (pin third-party actions to a commit SHA, not a
mutable `@v4`) and two `curl … | bash` lines in `scripts/install-linux.sh` (a common
installer convenience, operator-run). Both are supply-chain hygiene, not vulnerabilities.

Secrets, dependencies, and containers were fully clean: Gitleaks `[]`, Trivy `[]`,
pip-audit 0 vulnerable dependencies.

## Notes on the tool

- The **XXE / `use-defused-xml-parse` rule needs an impact split.** On CPython's
  `ElementTree` the rule fires at `high` for a class whose *reachable* impact is
  entity-expansion DoS, not file read / SSRF (external entities aren't resolved). A
  parser-family-aware severity — `lxml`/`pulldom` (external-entity-capable) at high,
  stdlib `etree` at medium/DoS — would rank this residual honestly instead of implying
  file disclosure. Backlog candidate.
- The **parameterized-SQL identifier false positive struck again** (4 of 29 findings). The
  standing backlog item — verify `execute()`'s parameter tuple and check whether the
  f-string tokens are identifiers vs data before flagging — would have collapsed these.
- **`detect-child-process` / `path-join` want a taint source.** Both fired on
  operator-config and constant-segment paths with no user-controlled input reaching the
  sink; a reachability pass (is the interpolated value MCP-client-derived?) separates the
  `execFile` nit from a real injection.

## Disclosure timeline

- 2026-07-22 — scan run; curation found 0 real, exploitability-shaped items
- 2026-07-22 — public post (this page). No maintainer contact required for a clean scan.

## Reproduce

```bash
git clone https://github.com/mixelpixx/KiCAD-MCP-Server /tmp/scan-target
python scanner/run_scan.py --repo /tmp/scan-target --reports-dir ./reports/mixelpixx-kicad-mcp-server --min-severity medium
```
