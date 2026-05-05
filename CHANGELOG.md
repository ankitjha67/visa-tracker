# Changelog

All notable changes to the Visa Slot Tracker.

## [4.0.0] — 2026-05-05

**Major feature release.** The detection and notification core from v3.2.x is preserved verbatim — validated against real production traffic for 22+ hours, caught real Czech Republic slots May 5, 2026, suppressed 1,968 false positives. Six new workstreams layered on top.

### Added — Tier system

- New **`tier` field** on every center in `centers.json` (`hot` / `warm` / `cold`, default `cold`).
- New **`tier_intervals`** in `config.json` (default `hot=600s, warm=1800s, cold=5400s`).
- New **`run --tiered`** flag — opt-in priority-queue scheduler. Each target carries its tier; after each check, target is rescheduled at `now + tier_interval`. Hot countries get checked every 10 min, cold every 90 min, all from a single Python process with one Chrome worker (no extra resource cost, no concurrent VFS request risk).
- Detection latency for hot-tier countries drops from ~70 min (v3.2.x average) to ~5-10 min.
- New CLI command **`set-tier`** — promote countries to hot/warm/cold via `--country` or `--preset`.
- Tier-aware logging in run loop: 🔥 hot / 🌤 warm / ❄ cold emoji per check.
- Backward compat: targets without `tier` default to `cold`; without `--tiered`, behavior is identical to v3.2.x fixed-interval cycle.
- Documentation: new `TIER_SYSTEM.md` with worked examples, resource math, and tuning guide.

### Added — Country selection

- New CLI command **`select-countries`** — interactive picker. No more auto-scaffold of all 82 entries on install. Six presets (`immigration`, `schengen`, `asia-pacific`, `gulf`, `americas`, `tier1-work-study`), `all` (everything except visa-free), `custom` (numbered list).
- Updates `centers.json` `enabled` flags AND rewrites `config.json` `targets` list in one step.
- Visa-free / e-visa entries automatically excluded from `select-countries all` (forced `enabled: false` regardless).
- DIY guide in `ADDING_COUNTRIES.md` for users who prefer manual edits.

### Added — Telegram bot scaffolding

- New CLI command **`setup-telegram`** — interactive wizard. Validates bot token via `getMe`, polls `/getUpdates` to auto-detect chat_id, sends test message, writes `config.json`. End-to-end in 60 seconds (was ~5 min of manual lookup).
- `Notifier.__init__` reads **`TELEGRAM_BOT_TOKEN`**, **`TELEGRAM_CHAT_ID`**, **`NOTIFICATION_DRY_RUN`** environment variables that override `config.json`. Required for GitHub Actions secrets injection.
- `TELEGRAM_CHAT_ID` accepts comma-separated values for multiple recipients.
- Documentation: new `TELEGRAM_SETUP.md` with wizard walkthrough, manual fallback, group chat instructions, env-var reference.

### Added — GitHub Actions deployment

- Three workflow files in **`.github/workflows/`**:
  - **`monitor.yml`** — main loop, every 30 min cron, `run --once`, persists state via Actions cache, sends failure notification to Telegram on workflow error.
  - **`calibrate.yml`** — weekly recalibration, Sunday 04:00 UTC.
  - **`healthcheck.yml`** — daily 03:00 UTC alive ping with DB stats summary to Telegram.
- All three use Telegram-as-channel (server-side runners can't show desktop toasts).
- Concurrency control: monitor + calibrate share the same `concurrency.group` so they never run simultaneously.
- Documentation: new `GITHUB_ACTIONS.md` (~300 lines) — full deployment runbook including public vs private repo cost analysis, cron jitter caveats, hybrid local/cloud setup, troubleshooting.

### Added — centers.json cleanup

- New top-level **`_indian_passport_status_legend`** field documenting the four valid status values.
- **7 visa-free entries flagged**: Sri Lanka, Thailand, Malaysia, Bhutan, Nepal, Maldives, Indonesia.
- **5 e-visa entries flagged**: Vietnam, Iran, Egypt, Kenya, Taiwan.
- Each flagged entry carries `_indian_passport_status`, `_status_note` (explanation), `_status_alternative_url` (real application path), and `enabled: false`.
- Entries are **kept in the file with metadata** (not deleted) so non-Indian-passport users can re-enable, and the data survives policy changes.
- 64 active centers monitored by default (down from 82, ~22% cycle time saved).
- Documentation: new `VISA_FREE_GUIDE.md` — explains every flag, how to re-enable, how to add new flags, validation script.

### Changed

- **Header** bumped to `v4.0.0` with consolidated release notes.
- **Selftest** output now reads `(v4.0.0)` and `v4.0.0 is wired up correctly`.
- **`centers.json`** version bumped to `4.0.0`.
- **`_default_targets_from_registry()`** now skips entries with `_indian_passport_status` in `(visa_free, evisa)` and includes `tier` field on each target.
- **`_default_config()`** includes `tier_intervals` defaults so existing installs auto-upgrade on first run.

### Preserved verbatim from v3.2.4 (no behavior change)

- Three-layer detection: VFS JWT replay, anonymous API, delta page-change classifier
- Persistent-noise marker (consecutive=N escalation, strict mode)
- Notification rate-limit (cap 25, summary on overflow)
- Selector-phase 5x speedup (implicit_wait 0.3s)
- JWT circuit breaker (skip after 6 consecutive failures)
- windows-toasts desktop notifications with PowerShell BalloonTip fallback
- UTF-8 BOM-tolerant config + centers.json loaders
- Streaming GET preflight (Cloudflare HEAD-method workaround)
- Windows UTF-8 stdout reconfigure for emoji-in-output commands
- All v3.2.x CLI commands: `selftest`, `verify-urls`, `calibrate`, `status`, `coverage`, `run`, `run --once`, `run --dry-run`

### Migration from v3.2.4

- Drop in v4.0.0 files (`visa_tracker_v3.py`, `centers.json`, `requirements.txt`, all `.md` files, `.github/`)
- Existing `visa_slots.db` works unchanged
- Existing `config.json` works unchanged (tier_intervals key auto-merged on next default-config write)
- To opt into new features: run `select-countries` (pick a preset), then `set-tier` (promote priorities), then `run --tiered`
- For 24/7 cloud: see `GITHUB_ACTIONS.md`

---

## [3.2.4] — 2026-05-05

**Polish release.** Cleanup pass after the v3.2.3 production validation. No behavior changes to the detection or notification pipeline; just fixes the bundled smoke test and adds non-technical user documentation.

### Fixed

- **`smoke_test.ps1` was broken in v3.2.3.** Two bugs: (1) PowerShell here-strings (`@"..."@`) embedded inside `Test-Stage` script blocks didn't parse because the closing `"@` had leading whitespace, which PowerShell forbids; (2) the stage-7 toast test passed `source=` and `url=` kwargs to `SlotInfo`, but the dataclass actually takes `detection_method=` and `booking_url=`. Both my errors. v3.2.4 rewrites the smoke test as a Python-first design: all 7 stages live in `smoke_test.py`, and `smoke_test.ps1` is a thin 5-line wrapper that just sets UTF-8 console encoding and invokes Python. This avoids the PowerShell↔Python quoting nightmare entirely.

- **Selftest version label** updated from stale `v3.2.2` to `v3.2.4` (purely cosmetic — the test logic itself was already current).

### Added

- **`USER_GUIDE.md`** — plain-English setup and operations guide for non-developers. Covers what the tracker does, prerequisites in lay terms, step-by-step install, what alerts mean, what to do when one fires, and troubleshooting. ~10 minute read.

- **`ADDING_COUNTRIES.md`** — how to expand coverage. Three scenarios (add a city, add a VFS country, add an embassy-direct country) ranked by difficulty. Embassy URL reference table with ~30 destinations. Schema explanation, validation steps, and notes on which countries don't need monitoring (visa-free / e-visa).

- **`smoke_test.py`** — Python implementation of all 7 smoke test stages. Clean exit codes, ANSI color output, structured failure reporting. Can be invoked directly or via the PowerShell wrapper.

### Validated against real production traffic (cumulative since v3.2.3)

- 22+ hours of continuous monitoring across 9 cycles, 290 city-checks per cycle
- 1,972 page-change events processed, 100% correctly classified (4 real positives, 1,968 noise events suppressed)
- Czech Republic appointment slots detected at 05:01 IST May 5, 2026 (delta=2126c, all 4 cities), externally verified by direct VFS portal screenshot showing "Earliest available slot: 06-05-2026"
- Wall time: 68-72 minutes per cycle in steady state (down from 104 min initial baseline due to JWT circuit-breaker persistence)
- Persistent-noise marker engaged correctly, escalating to strict mode at consecutive=2 and holding through consecutive=10
- Windows desktop toast path (added in v3.2.3) confirmed working end-to-end via smoke test stage 7

---

## [3.2.3] — 2026-05-05

**Production-ready release.** Consolidates four hotfixes shipped during 22+ hours of sustained-run validation on real VFS Global traffic. The system is now end-to-end verified: it detected real Czech Republic appointment slots opening on May 5, 2026 (4 cities, 16 slots), suppressed 100% of false positives across 1,972 page-change events, and now successfully delivers Windows desktop notifications.

### Fixed

- **Windows desktop toast notifications** — `_desktop_alert()` was missing a `win32` branch entirely. Versions v3.0 through v3.2.2c handled only macOS (`darwin`) and Linux (`notify-send`); on Windows the if/elif chain fell through with no toast call, then a bare `except: pass` silenced any errors. So when running with `live mode + desktop_alerts=True` on Windows, the tracker logged `"N NEW slot(s) found!"` but never invoked any Windows notification API. v3.2.3 adds a Windows branch that tries `windows-toasts` library first (clean Win10/11 native toast) and falls back to PowerShell `BalloonTip` if the library is not installed (no extra dependency required). All paths now log success/failure explicitly with typed exception handlers replacing the bare `except`.

- **PowerShell-written config files** — `_load_config()` and `load_centers_registry()` use `encoding="utf-8-sig"` to transparently strip an optional UTF-8 BOM. PowerShell's `Out-File` and `Set-Content` write UTF-8 with BOM by default; this used to crash plain `json.load()` with `Expecting value: line 1 column 1 (char 0)` the moment a user wrote a config file from PowerShell.

- **`verify-urls` false alarms** — switched from `requests.head()` to streaming `requests.get()` reading first 4KB. Cloudflare returns 404 to HEAD on SPA root routes, which made the old preflight report 69 false-alarm 4xx errors against perfectly working VFS Global URLs.

- **UnicodeEncodeError on Windows console** — added `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` after `bootstrap()` on `win32`. Without this, `selftest`, `verify-urls`, `status`, and any emoji-in-output command crashed on cp1252 PowerShell consoles.

### Added

- `windows-toasts` as an optional Windows-only dependency (`requirements.txt` uses environment marker `sys_platform == "win32"`).
- `smoke_test.ps1` — automated end-to-end smoke test that verifies install, imports, JSON loaders, the toast path, and basic CLI subcommands.
- `QUICKSTART.md` — single-page setup guide focused on getting from zero to working tracker in 5 minutes.

### Validated against real production traffic

- 22 hours of continuous monitoring across 9 cycles, 290 city-checks per cycle
- 1,972 page-change events detected, 100% correctly classified (4 real positives, 1,968 noise events suppressed)
- Czech Republic appointment slots detected at 05:01 IST May 5, 2026 (delta=2126c, all 4 cities), externally verified by direct VFS portal screenshot
- Wall time: 68-72 minutes per cycle in steady state (down from 104 min initial baseline due to JWT circuit-breaker persistence)
- Persistent-noise marker engaged correctly, escalating to strict mode at consecutive=2 and holding through consecutive=10

---

## [3.2.2] — 2026-05-03

**Production-blocking fixes from v3.2 terminal-log audit.** v3.2 fired 866 false slot notifications across 2 cycles in production due to hash-based page-change detection on stable VFS content (Nuxt nonces, build IDs). v3.2.2 replaces the entire page-change classifier with a delta-based approach.

### Added

- **Delta-based page-change classifier** — computes `difflib.SequenceMatcher` diff between previous baseline preview and current page text; classifies only the new content, not the whole page. Suppresses if delta < 30 chars or pure noise. Whole-page fallback if delta > 8KB.

- **Persistent-noise marker** — new `page_hashes.consecutive_changes` and `last_change_at` columns. After 2+ consecutive cycles of suppressed page changes for the same target, the classifier flips to `strict_mode=True` and requires 3 weak positives instead of 2 before alerting. Auto-decays on a clean cycle.

- **Notification rate-limit** — `Notifier.NOTIFICATION_CAP=25`. Overflow becomes a single consolidated summary alert (with country breakdown) instead of N individual notifications. Stops the storm.

- **Selector-phase 5x speedup** — calibration was taking 105s/country in Step 3 (87% of total runtime) because Selenium `implicit_wait=5s × 21 selectors`. v3.2.2 wraps Step 3 in a context manager that drops `implicit_wait` to 0.3s. Total `calibrate --all` runtime: ~17 minutes instead of 83.

- **JWT circuit-breaker** — `VFSJWTSession.FAILURE_CIRCUIT_BREAKER=6`. After 6 consecutive harvest failures for a country, JWT path short-circuits and the tracker falls through to anonymous endpoints + page-change. Surfaced loudly in `status` output.

- **`selftest` CLI** — 30-second offline integration check covering 10 critical paths (DB migration, classifier, delta computation, noise patterns, rate limit, JWT cache, etc.). Run before every calibration to catch regressions.

- **`run --dry-run`** — skip outbound notifications, just log what would have fired. Safe way to validate against real portals without spamming yourself.

- Cycle/interval mismatch warning. `NOISE_PATTERNS` expanded from 7 to 22 entries.

---

## [3.2.1] — 2026-05-02

URL audit and confidence scoring.

### Fixed

- Portugal moved from BLS to VFS (was broken in v3.2 — pointed at non-existent BLS Portugal URL)
- Algeria/Tunisia/Mozambique moved from BLS to embassy_direct (no scrapeable portal)

### Added

- VFS lift-api JWT replay path (real-time slot data via authenticated requests, cached 25 min)
- Calibrator click-through phase (Step 3.5) to surface APIs gated behind buttons
- Parallel calibration (`--workers N`)
- Per-country `confidence` field (high/medium/low)
- New `verify-urls` preflight CLI

---

## [3.2] — 2026-05-01

Multi-processor registry expansion.

### Added

- 82 visa application centers across 7 processors (VFS, BLS, TLS, CGI, embassy direct, etc.) covering 75+ destinations from 15 Indian cities
- New `coverage` and `list-countries` CLI commands

### Known issues (fixed in 3.2.2)

- Hash-based page-change detection caused 866 false positives in 2 production cycles
- Step 3 selector phase took 105s/country
- No rate-limit on notifications
- JWT failures retried indefinitely

---

## Historical: v3.0–v3.1

See git history. Three-layer architecture (API interception, authenticated scraping, page-change) was established in v3.0. v3.1 added the dashboard.
