# Visa Slot Tracker — Architecture and Setup Guide

This is the technical deep-dive. It documents the detection pipeline, calibration logic, and operational concerns that have evolved across versions. Most readers should start with `USER_GUIDE.md` (plain English) or `QUICKSTART.md` (CLI reference). Read this when you're debugging, extending, or curious about the *why*.

> **What's current as of v4.1.0:**
> - All v3.2.x detection and notification core preserved verbatim — validated against 22+ hours of real VFS Global traffic
> - v4.0.0 added: tier system (hot/warm/cold polling), Telegram setup wizard, GitHub Actions deployment, country selection, visa-free flagging
> - v4.1.0 added: US visa wait-time tracker (state.gov + CGI Federal public pages, 5 Indian consulates × 5 visa categories)
> - See `CHANGELOG.md` for the full history with reasoning per release

The sections below describe what was originally implemented in v3.2.2 and how it has held up through subsequent releases. **The architecture has not changed substantively since v3.2.2** — only the additions documented above and obvious bugfixes. The original v3.2.2 narrative is preserved below as historical record.

---

## Architecture history — v3.2.x (preserved verbatim, still current)

The original v3.2.2 release fixed three failure modes from the v3.2 production run; all three fixes remain core to the current architecture:

> **What was new in v3.2.2 (production-blocking fixes from terminal-log audit):**
> - **Delta-based page-change classifier** — the v3.2 production run logged 200 page_changed events per cycle on stable VFS content (firing 866 fake slot notifications in 2 cycles). v3.2.2 computes the diff between previous and current page text and classifies only the new content, not the whole page. Integration test verified: zero false positives on stable noise; real slot openings still detected.
> - **Persistent-noise marker** — a country firing page_changed in 2+ consecutive cycles gets flagged noisy in the DB; classifier threshold raised from 2→3 weak positives for that country until it goes clean. Auto-decay.
> - **Notification rate-limit** — max 25 alerts per cycle. Overflow becomes a single summary "X events detected, see dashboard" alert. Stops the storm.
> - **Selector phase 5x speedup** — calibration was 105s/country in Step 3 (87% of total runtime) because of Selenium's implicit_wait=5s × 21 selectors. v3.2.2 drops implicit_wait to 0.3s during Step 3 only. Total `--all` runtime: ~17 min instead of 83.
> - **JWT circuit-breaker** — after 6 consecutive harvest failures for a country, VFSJWTSession short-circuits and logs loudly. Surfaced in `status` output.
> - **Cycle/interval mismatch warning** — run_monitor logs once when cycle wall-time > 2× interval (your v3.2 run had 65–135 min cycles against a 3-min interval).
> - **`selftest` CLI** — 30-second offline integration check covering 10 critical paths. Run before every calibration to catch regressions.
> - **`run --dry-run`** — skip outbound notifications, just log what would have fired. Safe way to validate v3.2.2 in production.

> **What changed in v3.2.1:** URL audit (Portugal moved BLS→VFS, Algeria/Tunisia/Mozambique moved BLS→embassy_direct, all four were broken in v3.2). VFS lift-api JWT replay path (real-time slot data via authenticated requests, cached 25 min). Calibrator click-through phase (Step 3.5) to surface APIs gated behind buttons. Parallel calibration (`--workers N`). Per-country `confidence` (high/medium/low). New `verify-urls` preflight.

> **What changed in v3.2:** Multi-processor registry — 82 visa application centers across 7 processors covering 75+ destinations from 15 Indian cities. New `coverage` and `list-countries` CLI commands.

---

## How It Actually Works (v3.2.2)

The tracker uses a **three-layer detection strategy**, in priority order per check:

**Layer 1a — VFS JWT Replay**: For VFS countries, opens a headless browser at the country portal, harvests an `Authorization: Bearer <jwt>` from network logs or localStorage, then makes authenticated `GET https://lift-api.vfsglobal.com/appointment/slots?countryCode=ind&missionCode=<iso3>&...` requests. JWT cached 25 min. **v3.2.2 circuit-breaker**: after 6 consecutive failures for a country, JWT path short-circuits and the tracker falls through to anonymous endpoints + page-change. Surfaced loudly in `status`.

**Layer 1b — Anonymous API Interception**: For non-VFS portals or VFS endpoints discovered during calibration, replays with plain `requests.get`. Date extractor is key-aware (only emits dates from `appointment_date`-like keys, skips `created_at`/`expires`/etc.) and plausibility-filtered (`[today, today+365]`).

**Layer 3 — Page-Change Detection (DELTA-based, v3.2.2)**: After SPA hydration, hashes the visible text. On hash change:
1. Compute the textual delta between previous baseline preview and current page text using `difflib.SequenceMatcher`
2. Strip noise from the delta
3. If delta is < 30 chars or pure noise → suppress
4. Otherwise classify ONLY the delta (not the whole page) with the weighted classifier
5. Persistent-noise marker: bump `consecutive_changes`; if ≥ 2, raise classifier threshold to 3 weak positives. Auto-decay on a clean cycle.

**Notifications (v3.2.2)**: Email (SMTP), Telegram bot, Discord webhook, desktop. Rate-limited at 25 alerts per send. Overflow → one summary alert with country breakdown. `--dry-run` flag skips outbound entirely.

The calibration step visits each country's portal once, waits for hydration, clicks through Book/Continue buttons (Step 3.5) to surface gated APIs, tests selectors with **0.3s implicit_wait** instead of 5s (the v3.2.2 speedup), discovers structure, saves to SQLite with `confidence` field.

---

## Prerequisites

| Tool | Required | Purpose |
|------|----------|---------|
| Python 3.10+ | Yes | Runtime (3.14 tested — urllib3/charset_normalizer pin warnings silenced) |
| Google Chrome or Chromium | Yes | Headless browsing |
| Gmail account | For email alerts | SMTP sender |
| Telegram account | For Telegram alerts | Bot API |
| Discord server | For Discord alerts | Webhooks |

---

## Step 1: Install System Dependencies

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip -y

wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install google-chrome-stable -y
```

### macOS
```bash
brew install python3
brew install --cask google-chrome
```

### Windows
Install Python from python.org and Chrome from google.com/chrome. Tested against Python 3.14 + Chrome 147+.

---

## Step 2: Install Python Dependencies

```bash
pip install "selenium>=4.15" requests beautifulsoup4 \
            aiohttp websockets fake-useragent \
            webdriver-manager
```

---

## Step 3: Set Up Notification Channels (optional)

### Gmail App Password
1. https://myaccount.google.com/security → enable 2-Step Verification
2. Go to App passwords → generate one for "Mail"
3. Copy the 16-character password into `config.json`

### Telegram Bot
1. Message `@BotFather`, send `/newbot`, save the token
2. Message `@userinfobot` for your numeric chat ID
3. Send your bot any message first

### Discord Webhook
Server Settings → Integrations → Webhooks → New Webhook → copy URL into `config.json`

---

## Step 4: Selftest (NEW in v3.2.2 — RUN THIS FIRST)

Before anything else, run the offline integration check:

```bash
python visa_tracker_v3.py selftest
```

Takes 30 seconds. No network, no Selenium. Validates 10 critical paths:
1. Registry loads + processor metadata
2. URL routing for v3.2.1 corrected countries (Portugal/Algeria/Tunisia/Mozambique)
3. Page-change classifier (weighted + strict mode)
4. Delta computation (difflib)
5. Noise pattern stripping
6. VFSJWTSession circuit-breaker
7. DB schema + migrations
8. Click-through XPath syntax
9. Notifier (empty / dry-run / rate-limited paths)
10. Default targets seed honors v3.2.1 corrections

Should output `Passed: 10 / Failed: 0`. If any fail, **don't proceed to calibration** — the wiring is broken.

---

## Step 5: Configure

The first run writes a `config.json` seeded from the registry's `priority: high` and `priority: medium` enabled centers (about 42 countries). Edit to enable/disable countries, add credentials, tune the interval.

```json
{
  "check_interval_seconds": 1800,
  "max_concurrent": 2,
  "desktop_alerts": true,
  "notification_dry_run": false,
  "browser": { "headless": true, "page_timeout": 30, "proxies": [] },
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com", "smtp_port": 587,
    "sender": "you@gmail.com", "password": "xxxx xxxx xxxx xxxx",
    "recipients": ["you@gmail.com"]
  },
  "telegram": { "bot_token": "", "chat_ids": [] },
  "discord": { "webhook_url": "" },
  "targets": [ ... seeded from centers.json ... ]
}
```

> **Recommendation v3.2.2:** Default `check_interval_seconds: 180` (3 min) is too aggressive — even with 42 targets and `max_concurrent: 2`, the v3.2 production run took **65-135 minutes per cycle**. The loop runs back-to-back instead of polling. Either bump interval to 1800s (30 min) which matches reality, OR reduce target count to ~10 high-priority countries. The interval-mismatch warning will tell you once when you're running back-to-back.

---

## Step 6: Preflight URLs

```bash
python visa_tracker_v3.py verify-urls
```

~30 seconds. Groups every enabled URL into ✓ reachable / 🛡 Cloudflare / ❌ DNS fail / ❌ 4xx / ⚠ 5xx / ⏱ timeout. Should report 70 reachable VFS + 2 BLS + a few Cloudflare walls. **Zero DNS fails** if the v3.2.1 URL audit is intact.

---

## Step 7: Calibrate

```bash
# Sequential (default, ~17 min for 42 countries thanks to v3.2.2 selector speedup)
python visa_tracker_v3.py calibrate --all

# Parallel — 3-4 workers cuts wall time further
python visa_tracker_v3.py calibrate --all --workers 3

# One country (smoke test)
python visa_tracker_v3.py calibrate "Czech Republic"
```

Phases per country (v3.2.2 timing):
1. **Page load + SPA hydration** (~8s)
2. **Cloudflare check** (~0s if clean, +10s if challenged)
3. **CSS selector test** (~5s — was 105s in v3.2)
4. **Click-through Step 3.5** (~10-30s — clicks Book/Continue/Available buttons)
5. **Network capture** (~0s — replays buffered logs)
6. **Strategy + confidence** assignment

Calibration writes per-country PNG/HTML to `calibration_output/`, results to SQLite `calibration` table, summary to `calibration_report.json` with confidence buckets.

---

## Step 8: Inspect Coverage

```bash
python visa_tracker_v3.py coverage
```

Shows the loaded registry: 82 centers across 7 processors, 72 enabled, confidence distribution, Indian cities covered.

```bash
python visa_tracker_v3.py list-countries   # dump every supported country
```

---

## Step 9: First Run — DRY-RUN MODE FIRST

```bash
python visa_tracker_v3.py run --once --dry-run
```

`--dry-run` skips outbound notifications and logs what *would* have been sent. Run this first cycle in dry-run to validate the new delta classifier against your actual portal text. If you see `[DRY-RUN] Would have sent N slot alert(s)` with N > 5, something's still misfiring — check the dashboard before unleashing real notifications.

After confirming dry-run is clean:

```bash
python visa_tracker_v3.py run                # Background tracker
python visa_tracker_v3.py run --once         # Single cycle (real notifications)
python visa_tracker_v3.py run --server       # Tracker + dashboard
python visa_tracker_v3.py server             # Server-only (read-only DB)
python visa_tracker_v3.py status             # Health/diagnostics
```

`status` now also surfaces JWT circuit-breaker state (which countries are short-circuited).

---

## Step 10: Open the Dashboard

```
http://localhost:8080      # HTTP API
ws://localhost:8081        # WebSocket
```

`visa-dashboard.jsx` (v3.2.1 — unchanged in v3.2.2) renders:
- Confidence-aware slot list (high/medium/low visually distinct)
- Live demo mode when no backend reachable
- Pause/Resume, Check now (POST /api/run-now), per-processor health bars
- ArrowLeft/Right tab keyboard navigation, ARIA roles
- Sound toggle without WebSocket churn

---

## Troubleshooting

### `RequestsDependencyWarning: urllib3 (2.6.3) doesn't match...`
Silenced in v3.2.1+. Was a noisy warning from `requests` complaining about Python 3.14's bundled deps; no functional impact.

### `selftest` reports failures
Stop. Don't run calibration. Some part of the wiring is broken. Most common causes:
- `centers.json` doesn't have `vfs_global.known_api_endpoints` → re-copy `centers.json` from this drop
- Old DB schema with stale `calibration` rows → `sqlite3 visa_slots.db "DROP TABLE calibration;"` and let the migration recreate
- Module import error → check Python version is 3.10+

### `verify-urls` reports DNS fails
A URL in `centers.json` is broken. Fix it there before calibrating. v3.2.1 fixed Portugal + 3 BLS — if you see DNS fails on those, you're running an older `centers.json`.

### Calibration reports "Page-change detection (fallback)" for most countries
Expected. Most VFS portals don't expose appointment data without login — the calibrator can't see them by design. v3.2.1's JWT replay path picks up slot data during runtime (not calibration). Calibration confidence will be `medium` (registry default) for most VFS countries.

### Notification rate-limit fires every cycle
The delta classifier should prevent this, but if it persists for a country it means that country's portal genuinely changes content significantly between every load. Options:
1. Re-calibrate that country specifically — its baseline may have been captured during a CDN flap
2. Disable that country in `config.json` (remove from `targets`)
3. Set `notification_dry_run: true` and review logs to see what's actually being detected

### `status` shows `⚠ JWT circuit breakers open`
Means VFS lift-api isn't responding to our JWT for those countries. Common causes:
1. Country requires login first — JWT only minted post-auth → expected, falls through to page-change
2. VFS deployed Bot Management on lift-api → JWT path is dead → page-change is your only signal
3. Your IP got rate-limited → wait 1 hour, then `python -c "from visa_tracker_v3 import VFSJWTSession; ..."` to manually reset

In all cases, page-change layer continues to function. The breaker just stops the JWT retries from wasting cycles.

### `INTERVAL MISMATCH` warning
Expected with default 3-min interval and 42 targets. Either bump `check_interval_seconds` or reduce `targets` count. The warning fires once per process to alert you, not per cycle.

### Dashboard shows "Disconnected"
Demo mode. Run `python visa_tracker_v3.py run --server` and reload.

### Notifications not firing (after dry-run validation)
- Email: Gmail blocks regular passwords, you need an App Password
- Telegram: send `/start` to your bot once before the tracker runs
- Discord: regenerate the webhook if it 404s
- Desktop: on macOS allow notifications for your terminal app

---

## Architecture Notes

### Why the delta classifier exists (v3.2.2 root cause)

The v3.2 production run log showed 200 page_changed events per cycle on VFS countries with stable content. Three compounding bugs:
1. **Insufficient noise stripping** — Nuxt `__nuxt-XXX` IDs, Vue `data-v-XXX` scoped CSS, dynamic ARIA controls survived the v3.2 patterns; hash differed every load
2. **Lax classifier** — single weak positive ("available" anywhere on page) flipped to slots_likely
3. **Whole-page classification** — even after hash change, classifier read the entire post-noise text, so static "Book your appointment" UI copy fired slots_likely on any cosmetic mutation

v3.2.1 fixed (2) with weighted signals. v3.2.2 fixes (3) with the delta classifier and tightens (1) with Nuxt/Vue noise patterns. Integration test confirms: 8 cycles × 20 country-city pairs of stable+noisy content produces **zero** page_changed events.

### Why VFS lift-api needs JWT replay (not anonymous fetch)
Direct `requests.get` returns 403. Reference Bangladesh impl uses Selenium to harvest a JWT first. v3.2.1's `VFSJWTSession`:
1. `get(country, portal_url)` — return cached JWT if <25 min old, else `_harvest`
2. `_harvest` — open Chrome at portal, scan network log for `Authorization: Bearer ...` headers on `lift-api.vfsglobal.com` requests, fall back to `localStorage` / `sessionStorage` keys containing `token`/`auth`/`jwt`
3. `replay(endpoint, jwt, params)` — `GET` with `Authorization: Bearer <jwt>` and country-specific params (`countryCode=ind`, `missionCode=<iso3>`, `languageCode=en-US`, `applicantsCount=1`, `days=90`, `slotType=2`)
4. **v3.2.2 circuit-breaker**: after 6 consecutive failures, country is short-circuited until reset

### The interval/throughput reality

With 42 targets averaging 5 cities each (210 city-checks) at ~25-30s per check (Selenium driver init + page load + hydration wait + page hash + driver close), even with `max_concurrent: 2` the cycle takes ~50-100 minutes wall time. The v3.2 production log confirmed 65-135 min cycles. v3.2.2 doesn't change this — it just warns you once. Either reduce target scope or accept continuous-mode operation.

---

## Migration

### v3.2.1 → v3.2.2 (recommended)

The DB migration is **idempotent and automatic** — no manual schema changes needed.

1. Drop in the new files
2. `python visa_tracker_v3.py selftest` (validates wiring; should pass 10/10)
3. **You don't need to wipe `page_hashes`** — the migration adds `consecutive_changes` and `last_change_at` columns; existing rows just have NULL values which the new code treats as 0
4. **You SHOULD wipe page_hashes anyway** if you're upgrading from a session that produced false positives, because the stored content_preview is only 500 chars (v3.2.1 default) and the delta classifier wants more:
   ```bash
   sqlite3 visa_slots.db "DELETE FROM page_hashes;"
   ```
   Slot history and check log are preserved. Baselines re-establish on the next cycle.
5. `python visa_tracker_v3.py verify-urls` to confirm URLs are clean
6. Optionally `python visa_tracker_v3.py calibrate --all --workers 3` (~17 min thanks to selector speedup)
7. **First run with dry-run**: `python visa_tracker_v3.py run --once --dry-run` — should show 0 slot alerts on a stable cycle
8. Then go live: `python visa_tracker_v3.py run --server`

### v3.2 → v3.2.2 (jumping versions)

Combines v3.2.1 corrections + v3.2.2 fixes:
1. **Delete v3.2 calibration data** (the four broken-URL countries are reclassified):
   ```bash
   sqlite3 visa_slots.db "DELETE FROM calibration; DELETE FROM page_hashes;"
   rm calibration_report.json
   ```
   The DB migrations add `confidence` (v3.2.1) and `consecutive_changes` (v3.2.2) columns automatically. Slot history and check log preserved.
2. `python visa_tracker_v3.py selftest`
3. `python visa_tracker_v3.py verify-urls`
4. `python visa_tracker_v3.py calibrate --all --workers 3` (~17 min)
5. `python visa_tracker_v3.py run --once --dry-run` (validate)
6. `python visa_tracker_v3.py run --server` (live)

### v3.0/v3.1 → v3.2.2

v3.0 and v3.1 used a wrong VFS URL pattern. Then do the v3.2 → v3.2.2 migration above.

---

## Files (v3.2.2)

| File | Purpose | Lines |
|------|---------|-------|
| `visa_tracker_v3.py` | Tracker + JWT replay + delta classifier + selftest | ~3500 |
| `centers.json` | Multi-processor centers registry, 82 entries | — |
| `visa-dashboard.jsx` | React dashboard with confidence filtering | ~1300 |
| `config.json` | Notification channels + active targets list | — |
| `PROCESSORS.md` | Visa processor landscape doc | — |
| `SETUP_GUIDE.md` | This file | — |
| `calibration_report.json` | Generated by calibrator | — |
| `visa_slots.db` | SQLite — slots, checks, baselines (with v3.2.2 noise tracking) | — |
| `visa_tracker.log` | Rolling log file | — |
