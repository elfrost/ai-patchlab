---
layout: default
title: "bubbuild/bub: security scan"
description: "Security scan of bubbuild/bub, a hook-first Python runtime for agents in shared chats: 72 findings, 1 real. The Telegram allowlist is the runtime's only remote trust boundary, and four operator-facing docs teach filling it with a Telegram username — an identifier its owner can release and a stranger can claim."
date: 2026-09-13
---

# bubbuild/bub — security scan

**Repository:** [bubbuild/bub](https://github.com/bubbuild/bub) — 1.6k★, Apache-2.0, a hook-first Python runtime for agents that "live alongside people." Every turn stage is a [pluggy](https://pluggy.readthedocs.io/) hook; the same runtime drives a CLI, a Telegram bot, and any channel you write. 53 Python files, 10.8k lines. Unusually well-tended: **eight distinct authors merged PRs in the last 60 days and the issue tracker was at zero open issues** on the day of the scan.
**Commit scanned:** `eccbf7c` (HEAD of `main` at scan time)
**Scan date:** 2026-09-13
**Disclosure status:** One real finding, reported in full in a public issue on the day of the scan. No `SECURITY.md` exists at the repository root, in `.github/`, in `docs/`, or on the published docs site, and private vulnerability reporting is disabled — so no private channel exists to use. Everything below is published in full, and every fact it rests on was already public in the project's own documentation.

## Summary

| Severity | Count (medium+) |
| --- | ---: |
| Critical | 1 |
| High | 27 |
| Medium | 41 |
| Low | 0 |
| Info | 3 (scanner meta) |

**Total findings:** 72 (69 above the `medium` floor) — **1 real after curation**, plus two small siblings in the same twenty lines.

Coverage note, because it changes how to read the zeros. Semgrep reported **2 errors and zero rule timeouts** — both `PartialParsing`, on `Dockerfile` and `website/src/data/userwall.yml`. Neither is Python, so the `src/` tree genuinely was covered and Semgrep's silence on it is real silence rather than a gap. Gitleaks returned `[]` against a repository that ships an `env.example` full of placeholders: a true zero, not a crash. And the dependency picture came back clean on **both** install paths — Trivy read `uv.lock` (0 advisories), pip-audit resolved the `pyproject.toml` floors (0 advisories across ~30 packages). All 57 dependency findings in the table above come from one file, `website/pnpm-lock.yaml`, which is the marketing and docs site, not the runtime anyone installs.

## Why this target

Two reasons, and the second is the one that made it worth the day.

The responsiveness pre-check this series runs came back stronger here than on any candidate in weeks: eight distinct humans merged pull requests in 60 days, five issues were closed, and the open-issue count was **zero**. That is a project that answers. The alternative candidate with more stars — a commercially-backed LLM gateway at 4.7k★ — had 70 open issues sitting at zero comments amid a billing dispute, and was dropped on exactly this criterion.

The second reason is the shape of the product. Bub is an agent runtime whose whole premise is that agents and humans share one conversation, reachable from a Telegram group. That means it has something most of the local-first agent projects in this series do not: **a genuine remote trust boundary**. A CLI agent's threat model is "you already have the shell." A Telegram-connected agent's threat model is "who on the internet may drive this?" — and the answer lives in about twenty lines of one file.

## The finding: the allowlist is checked against a handle its owner can give away

Bub's Telegram channel is gated by two settings, `BUB_TELEGRAM_ALLOW_USERS` and `BUB_TELEGRAM_ALLOW_CHATS`. The enforcement is in `src/bub/channels/telegram.py:226`:

```python
async def _on_message(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    ...
    user = update.effective_user
    sender_tokens = {str(user.id)}
    if user.username:
        sender_tokens.add(user.username)
    if self._allow_users and sender_tokens.isdisjoint(self._allow_users):
        await update.message.reply_text("Access denied.")
        return
    await self._on_receive(await self._build_message(update.message))
```

The caller is admitted if **either** their numeric Telegram user ID **or** their current `@username` appears in the allowlist. Those two identifiers have very different properties. A Telegram user ID is immutable and permanently bound to one account. A username is a handle the account *rents*: its owner can change it at any time, and once released it returns to the pool and can be registered by anyone — Telegram even runs an official marketplace for trading them.

So an allowlist entry that is a username is an authentication check against a transferable credential. The project's own field description and its reference documentation both say the setting holds **user IDs**:

> `BUB_TELEGRAM_ALLOW_USERS` | unset | `allow_users` | Comma-separated allowlist of Telegram user IDs. Empty means no restriction.
> — `website/src/content/docs/docs/reference/settings.mdx:136`

But the documents an operator actually copies say something else. **Four of them** — five counting the Chinese translations — put a username in the example:

| File | Line | Example given |
| --- | --- | --- |
| `env.example` | — | `BUB_TELEGRAM_ALLOW_USERS=123456789,my_username` |
| `docs/operate/channels/telegram.mdx` | 29 | `BUB_TELEGRAM_ALLOW_USERS=123456789,your_username` |
| `docs/operate/configure.mdx` | 47, 75 | `allow_users: "123456789,your_username"` |
| `AGENTS.md` | "Security & Configuration Tips" | names the setting, does not say IDs |
| `docs/reference/settings.mdx` | 136 | **"user IDs"** |
| `docs/operate/deploy.mdx` | 30 | `BUB_TELEGRAM_ALLOW_USERS=123456789` ← numeric only |

This is the [contract-versus-artifact split](ginlix-ai-langalpha.html) this series keeps finding, in an unusually clean form: the *reference* is correct, the *tutorials* are not, and the code implements the tutorials. An operator has no way to discover the difference, because the permissive path works perfectly right up until it doesn't.

### What it reaches

An admitted Telegram message becomes a turn, and the default toolset is not a subset. `resolve_tool_names(names=None)` returns `set(REGISTRY)` — **every registered tool, including `bash`** (`src/bub/builtin/tools.py:142`), which passes its `cmd` string straight to `asyncio.create_subprocess_shell`. There is no approval prompt, no command allowlist, and no sandbox anywhere in the tree — a grep for `approval`/`confirm`/`sandbox` across `src/` finds only an installer prompt and an unrelated `PermissionError` handler. The sibling `fs.read`/`fs.write`/`fs.edit` tools resolve absolute paths without confinement (`_resolve_path` returns `path` unchanged when `path.is_absolute()`).

None of that is a defect. For a project whose stated purpose is running an agent that does real work on your machine, a shell tool is the product — this series has a [standing rule](agentera-agently.html) against filing a code-executor's executor. It matters here only because it sets the stakes for the one boundary that *is* a boundary: whoever passes `_on_message` gets a shell.

And the shipped container makes that a root shell. `docker-compose.yml` mounts the workspace and `~/.agents` from the host, `restart: unless-stopped`, and the `Dockerfile` declares no `USER` — Trivy's DS-0002, the one genuinely relevant misconfiguration in the run.

### The differential

Running the shipped `_on_message` against synthetic updates, with the allowlist set to the exact string from `env.example`:

```
BUB_TELEGRAM_ALLOW_USERS = '123456789,your_username'

_on_message (src/bub/channels/telegram.py:226):
  operator, by numeric ID                       id=123456789  username=operator_handle -> ADMITTED -> reaches the default bash tool
  operator, by username                         id=555000111  username=your_username   -> ADMITTED -> reaches the default bash tool
  DIFFERENT ACCOUNT that acquired the handle    id=999999999  username=your_username   -> ADMITTED -> reaches the default bash tool
  unrelated stranger                            id=424242424  username=someone_else    -> denied  ['Access denied.']
  case-mismatched legitimate operator           id=555000111  username=Your_Username   -> denied  ['Access denied.']

_on_start (src/bub/channels/telegram.py:218) — same allowlist set:
  unrelated stranger hits /start                id=424242424  username=someone_else    -> ANSWERED ('Bub is online. Send text to start.')
```

Row three is the finding. Account `999999999` shares nothing with the operator — different ID, different account, no prior contact — and is admitted because it holds a string. Rows five and six are the two siblings that fell out of the same twenty lines:

**The comparison is case-sensitive, and Telegram usernames are not.** `sender_tokens` receives `user.username` in whatever case the account stores; the allowlist is compared verbatim. An operator who writes `Your_Username` while their account stores `your_username` is locked out of their own bot. This fails closed, so it is a correctness bug rather than a security one — and it slightly narrows the finding above, since an attacker must match the operator's chosen casing.

**`/start` never checks the user allowlist.** `_on_start` (`:218`) applies `_allow_chats` and stops; its sibling `_on_message` (`:226`) applies both. So with `ALLOW_USERS` set and `ALLOW_CHATS` unset — precisely the configuration `deploy.mdx:30` demonstrates — any Telegram user who finds the bot gets a friendly "Bub is online," confirming a live deployment. That contradicts the project's own documented rule ("If `BUB_TELEGRAM_ALLOW_USERS` is set, messages from any other user receive `Access denied.`"), and it is the [intra-repo differential](ascending-llc-jarvis-registry.html) in its cheapest form: one handler is the specification for the other.

Worth stating plainly, because it bounds the severity: **this is not a live compromise of every Bub deployment.** It requires an operator who enabled Telegram, who put a username rather than an ID in the allowlist, and who later let that username go. What it *is* is a documented configuration path that silently converts a permanent credential into a temporary one, on the only boundary the runtime has. There is also no test covering it — `tests/test_configure.py` exercises `allow_users: "1,2"`, numeric only, so the branch four documents teach has never been executed by CI.

### The fix is a product decision, so it was posed rather than patched

The obvious repair — reject non-numeric allowlist entries — is correct and **breaks every operator who followed `env.example`**. Their bot would stop answering them, with no migration path, because the Telegram Bot API offers no username-to-ID lookup for an account that has not yet written to the bot. So the issue names the tradeoff and leaves the call to the maintainers:

- **Strict:** reject non-numeric entries at startup with an explanatory error, and fix the four documents. Secure, breaking.
- **Compatible:** keep accepting usernames, log a startup warning naming each non-numeric entry as reassignable, and change the examples to lead with IDs. Non-breaking, relies on the operator reading a log line.

The `/start` alignment and the case-insensitive comparison are unambiguous and were offered as a one-line PR either way. This series has learned repeatedly — on [tabbyAPI](theroyallab-tabbyapi.html), on [davinci-resolve-mcp](samuelgursky-davinci-resolve-mcp.html), on [Zleap-AI](zleap-ai-sag.html) — that when a fix has a compatibility cost, posing the question outperforms shipping the patch, because only the maintainer can price the breakage.

## What the other 71 findings were

**57 npm advisories, all from `website/pnpm-lock.yaml`** — including the report's only Critical (Astro RCE via AVIF image optimization, GHSA-26w7-cxv4-gfx2) and a reflected-XSS (CVE-2026-50146). These are the Astro docs site at `bub.build`, not the Python runtime. Two gates apply. First, [whose running system is this](observal-observal.html): the website is *the maintainers' own* deployment, not something an adopter inherits — `pip install bub` pulls none of it. Second, reachability: the AVIF RCE needs Astro to process an attacker-supplied image, and a docs site accepts no uploads. The XSS is the closer call — `astro.config.mjs` is SSG by default but `website/src/pages/[...locale]/index.astro` opts into SSR with `prerender = false`, so one real server-rendered page exists. Worth a `pnpm update` on their own site; not an adopter-facing vulnerability, and not what the issue was filed about.

**11 `github-actions-mutable-action-tag`** — `actions/checkout@v6` and friends pinned by tag. Severity here is a function of the trigger, and both workflows are safe ones: `main.yml` fires on `push` and plain `pull_request` (not `pull_request_target`), `on-release-main.yml` on `release: published`. Supply-chain hygiene, not a vulnerability, and the same rule fires on most of GitHub.

**1 `detect-non-literal-regexp`** in `website/src/i18n/utils.ts:124` — a locale string interpolated into a `RegExp`. The locale set is a compile-time constant. Not attacker-controlled.

**2 Dockerfile misconfigurations** — DS-0002 (runs as root), discussed above and folded into the main finding as hardening; DS-0026 (no `HEALTHCHECK`), which is not a security issue.

**3 info-level meta findings** from the scanner itself, one of which was wrong. See below.

## The one that didn't survive: a conditional state check, defeated by PKCE

`bub login openai` runs an OAuth flow against `auth.openai.com` with a loopback callback on `localhost:1455`. The state validation reads (`src/bub/builtin/auth.py:215`):

```python
if returned_state and returned_state != state:
    raise CodexOAuthStateMismatchError
```

That is the [conditional-verification shape](sentelabsai-openexecutive.html) this series files regularly: the check is skipped, not failed, when the attacker supplies no `state` at all. And the loopback callback is reachable in the way loopback servers always are — not from the internet, but from **a web page in the victim's browser**, which can issue `GET http://localhost:1455/auth/callback?code=…` as a bare navigation or image load, no CORS required. The 300-second window is open precisely while the victim is at their browser, because the flow just opened it for them.

The classic attack from here is authorization-code injection: the attacker obtains a code for *their* OpenAI account and gets the victim's client to redeem it, silently binding the victim's agent to the attacker's account. It does not work here, and the reason is that **PKCE is implemented correctly**. `_build_pkce_verifier()` generates 32 random bytes per flow, `code_challenge_method="S256"` is set on both the authorization URL and the token exchange, and the verifier never leaves the process. An injected code was minted against the *attacker's* challenge, so the victim's verifier will not match it and the token endpoint rejects the exchange. RFC 9700 assigns exactly this division of labour — PKCE stops code injection, `state` stops CSRF — and the PKCE half is intact.

What remains is a login denial-of-service: an injected request sets the callback result and stops the server, so the genuine code is dropped and the login fails with an exchange error. That is not worth a maintainer's time, and the conditional itself is *deliberate* — it exists so the `--manual` flow can accept a bare pasted code, which legitimately carries no state. The honest note is a narrow one: the automatic loopback path always sends a state and could require one, without touching the manual path. It is defence in depth on a door PKCE already locks, and it was not filed.

This is the [mitigation gate](aurelio-labs-semantic-router.html) doing the job it exists for. The finding was coherent, matched a pattern with a good hit rate in this series, and was wrong — and the only thing that established that was reading the PKCE implementation instead of assuming it was decorative.

## Patterns observed

**A trust boundary can be undermined by a tutorial.** Nothing in `telegram.py` is badly written. The allowlist is enforced before dispatch, it fails closed on an empty intersection, and it is checked in exactly one place — the sweep for a second, weaker gate found nothing, which on this kind of code is rarer than it should be. The defect is entirely in the seam between that code and the six documents describing it, where the reference says "user IDs," the tutorials show a username, and the implementation accommodates both. Neither artifact is wrong alone. This is the [composite class](langflow-ai-openrag.html): two individually-defensible decisions in different files that compose into a weakened control, and no static rule can see it, because no rule reads `env.example` next to `_on_message`.

**The zero-open-issues signal was worth more than the star count.** The pre-check that selected this repository over a target three times its size was not stars, licence, or recency — all three favoured the other one. It was that eight different people had merged work here in two months and nobody's question was sitting unanswered. That is also the strongest predictor in this series' resolution record: the fast fixes have come from projects that were already answering, and the silent ones from projects with full trackers. Responsiveness is a security property, because a vulnerability report is only worth what the project does with it.

**Both dependency install paths came back clean, which is unusual enough to name.** This series keeps finding projects where `uv.lock` and `pyproject.toml` disagree — [83 advisories against 1](langroid-langroid.html) on langroid, [63 against zero](whiteguo233-openbiliclaw.html) on OpenBiliClaw — because the two files describe different install paths and a project ships both. Bub ships both too, and they agree at zero. The lock is current, the floors resolve to the same clean set, and the Dockerfile uses `uv sync --no-dev` so the published image gets the audited pins. Credit where it is due: this is the state every one of those other reports was asking for.

**Everything interesting was absence-shaped.** 72 findings from four tools, and the one that mattered was a property of an identifier's *lifecycle* — that a Telegram username can change hands — which is not visible in any file. Semgrep found a regex in a TypeScript i18n helper. Trivy found a docs site's npm tree. The real finding needed a human to ask what kind of thing `your_username` is. That gap is the standing justification for the hand sweep, and it has not narrowed in 103 scans.

## Notes on the tool

- **The unaudited-lockfile meta finding fired when the lockfile had in fact been audited.** `dependency-scan` emitted "A shipped lockfile was not covered by the dependency scan," reasoning that pip-audit read `pyproject.toml` and does not read `uv.lock` — true in isolation, and its recommendation even says "audit the lockfile with a tool that reads it (e.g. Trivy)." Trivy had already read it, in the same run, as a `lang-pkgs`/`uv` target returning zero. The scanner has both tools' target lists in hand and does not cross-check them. **This is the second run in a row where this warning overstated the gap** ([langroid](langroid-langroid.html) logged the same complaint), which promotes it from a note to a backlog item: the check should reconcile the two tools' targets and stay silent when one of them covered the file, or better, report where their versions disagree.
- **`PartialParsing` still gets the timeout recommendation.** Both Semgrep errors here were parse failures, on `Dockerfile` and a YAML data file, and the advice was again "re-run with a higher `--timeout`" — which will never help a parse error. Same backlog item as last scan; flagging it twice because the text is actively misleading about what the operator should do.
- **Dependency findings need an ownership column more than a severity one.** 57 of this report's 72 findings, including its only Critical, are a documentation website's npm tree. They are not wrong, and they dominate the summary table so thoroughly that the actual finding does not appear in it at all. The scanner knows each finding's path; a first-party/vendored/ancillary split — `src/` versus `website/` versus `tests/` — would have put the 57 in their own bucket without discarding them. This is the [monorepo ownership split](klavis-ai-klavis.html) the series has asked for before, and bub is the cleanest demonstration yet of why: the severity ranking and the interest ranking were perfectly inverted.
- **No tool in the stack can read a settings table.** The finding rests on comparing six documents against twenty lines of code. Four tools, 72 findings, zero signal on it.

## Disclosure timeline

- 2026-09-13 — scan run at `eccbf7c`
- 2026-09-13 — curation complete: 1 real finding, quality gate met
- 2026-09-13 — reported publicly ([bubbuild/bub#305](https://github.com/bubbuild/bub/issues/305)) — no `SECURITY.md` at root, in `.github/`, in `docs/` or on the docs site, and private vulnerability reporting is disabled, so no private channel exists
- 2026-09-13 — public post (this page)
- 2026-09-15 — **closed by the maintainer as won't-fix** (maintainer `frostming`), 2 days after filing:

> Accepting usernames is mainly for convenience, and it is also used in other agents. Agent administrators are responsible for assessing security risks and handling them properly.
>
> Therefore, we will not make this fix.

**The question was answered, and the answer is the maintainer's to give.** The report deliberately did not propose a patch — it argued that dropping `@username` support would break a documented convenience feature, and that *which* of ergonomics or identifier stability the project wants is a product call, not a security bug with an obvious fix. The maintainer made that call: usernames stay, and the operator owns the risk. That is a coherent position, and it is the same one several other agent frameworks have taken.

What remains unresolved is narrower than the issue, and worth stating plainly: the project's reference table still documents the setting as holding "user IDs" while `env.example` and three operator-facing docs show `your_username`. If operators are the ones assessing this risk, the documentation is what they will assess it from, and it currently teaches the permissive form without naming the trade-off. That is a docs question rather than a code one, and it was not what the issue asked, so it is recorded here rather than re-litigated upstream.

Reported in the open because there was nowhere private to report it, and because every fact it rests on — the code, `env.example`, and four published documents — was already public. Nothing in the issue tells an attacker anything the project's own documentation does not.

## Reproduce

```bash
git clone https://github.com/bubbuild/bub /tmp/scan-target
.venv/Scripts/python.exe scanner/run_scan.py \
  --repo /tmp/scan-target \
  --reports-dir ./reports/bubbuild-bub \
  --min-severity medium
```
