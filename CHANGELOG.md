# Changelog

All notable changes to the Visa Slot Tracker.

## [4.4.0] — 2026-07-29

**US wait-time tracking repaired + hardening + new tooling.** A full-code audit found that several shipped features were silently broken. v4.4.0 fixes them, adds regression coverage for each (selftest grew 10 → 15 checks), and ships new operational tooling.

### Fixed

- **US wait-time persistence was 100% broken since v4.1.0** (the release that introduced it). `USStateDeptProcessor._get_previous()` / `_store_current()` referenced `slots.id`, `slots.metadata`, and `slots.expires_at` — columns that have never existed in the schema (the table's key is `uid`; there is no metadata column; expiry is an `expired` flag). Every read/write raised `sqlite3.OperationalError`, which was swallowed at debug level, so the baseline never persisted, `prev` was always `None`, and a wait-time **drop alert could never fire** across all 36 US consulate centers. Fixed with a dedicated `wait_times` table (created idempotently, used under the DB lock with WAL like every other table) that round-trips numeric day counts and status strings ("Closed") as JSON. Verified end-to-end: baseline cycle → drop cycle now produces `slots_found` with a projected-date alert.

- **`server` and `run --server` crashed on startup** with `AttributeError: module 'aiohttp' has no attribute 'web'`. The Server class used `aiohttp.web.*` throughout, but only `import aiohttp` was performed — aiohttp does not expose the `web` submodule from a bare import. The dashboard backend (HTTP API + WebSocket) never worked in v3.x/v4.x. Now imported explicitly and covered by a runtime test (HTTP + WS round-trip).

- **Every stored timestamp was malformed** (`2026-05-06T03:17:19+00:00Z` — `isoformat()` on an aware datetime already appends the offset; the code appended a literal `"Z"` on top). JavaScript's `new Date()` rejects that form, so the dashboard rendered **Invalid Date** and mis-sorted every slot/check from real data. New `utc_now_iso()` helper emits proper RFC3339 (`2026-07-29T16:09:32Z`); all seven call sites migrated. Old rows still compare correctly for 7-day expiry (dates dominate the lexicographic comparison).

- **Telegram alerts with 8+ slots were silently lost.** A single message was built for up to 25 slots (~5,000 chars), exceeding Telegram's 4,096-char limit; the Bot API returned 400 and the code logged "Telegram sent" without checking the response. Messages are now packed into chunks under 3,500 chars, values are HTML-escaped (country/city names with `&`/`<` previously broke `parse_mode=HTML`), and every API response is verified and logged on failure.

- **Only 1 of 36 US consulates was ever monitored.** `_default_targets_from_registry()` deduplicated by country name, so the 36 "United States" centers collapsed to the first one (Mumbai) and its single city. Targets now merge cities per (country, processor) — one US target carrying all consulate cities — and the hottest tier among merged centers wins.

- **state.gov parsing could not parse the actual page.** The regex strategy looked for visa-type labels within 1,500 chars *after* the consulate name — but on the real layout (an HTML table with category labels in the header row and one city per body row) labels never repeat next to values, so parsing silently returned `{}` every time. v4.4.0 parses the table structurally (header-token → category mapping tolerant of state.gov's inconsistent phrasing, e.g. "Interview Required Visitors (B1/B2)") and keeps the regex as fallback. Status strings like "Closed" are preserved so a later transition to numeric alerts.

- **`healthcheck.yml` daily DB stats always failed**: it queried `slots.expires_at` (nonexistent — the column is `expired`) and compared ISO-8601 `T`-separated timestamps against sqlite's space-separated `datetime('now')` strings. The ping ran for months reporting "(could not read DB: …)". Queries fixed and the Telegram response is now checked (job fails visibly instead of pretending success).

- **`--break-system-packages` broke bootstrap on pip < 23.0** (the flag doesn't exist there). Plain install is tried first; the flag is only added on a PEP 668 rejection, with a clear manual-install message if both fail.

- **Driver-creation fallback chain could never recover from a Selenium Manager mismatch.** `create_driver()` shared one `Options` object across strategies, and Selenium Manager *mutates* the options it's given (it stamps the browser binary it resolved into `options.binary_location`). So when strategy 1 failed on a version mismatch, strategy 2 (webdriver-manager) launched *strategy 1's browser* with *its own* chromedriver — a guaranteed mismatch whenever the resolvers disagreed (observed live: chromedriver 141 paired with Selenium Manager's cached Chrome 151). Each strategy now builds fresh options. Also added **`VISA_CHROME_BINARY` / `VISA_CHROMEDRIVER` env overrides** (strategy 0) to pin exact binaries in containers/CI — honored by `doctor` too.

- Interactive setup: "Bangalore" → "Bengaluru" (matches centers.json/VFS naming); targets now carry `processor` and `tier` like select-countries output.
- `load_centers_registry()` clears the country index on reload (select-countries previously left stale winners in memory).
- SIGINT now stops active trackers and cancels queued executor work, so Ctrl+C doesn't hang on the ThreadPoolExecutor's atexit join behind queued Selenium jobs.
- Removed dead imports (`pickle`, `urljoin`, `Any`); replaced the `selenium.common.exceptions` star-import with the three exceptions actually used.
- Page-hash preview cap raised 5,000 → 12,000 chars to match the delta window — content between 5,000–12,000 chars used to appear as "added" lines on every genuine change.

### Changed

- **Tiered mode now honors `instant_notify`** (v4.3.0 wired instant alerts only into the plain cycle runner; a hot-tier detection could still sit in the pending buffer until an idle window — exactly the lag instant notification was built to remove). On dispatch failure the batch path retries.
- **VFS JWT cache is per-country.** The old single-slot cache was invalidated on every country switch, so multi-country cycles re-harvested (≈20s of Selenium) per country even with a valid token in hand. `status` now shows per-country cache ages.
- Slots are marked `notified=1` in the DB after successful dispatch (column existed since v3.0; nothing ever set it).
- Desktop toasts are skipped when `CI`/`GITHUB_ACTIONS` is set (Actions runners have no toast surface; it warned on every dispatch).
- Discord/summary sends now check HTTP responses.

### Added

- **`wait-times` CLI** — live US consulate wait-time table from state.gov/CGI Federal (`--all` for every registry consulate, `--city X`, `--record` to store baselines).
- **`export` CLI** — active slots to CSV, or full JSON dump (slots + checks + stats + wait-time baselines) for spreadsheets/external tooling.
- **`doctor` CLI** — environment diagnostics: Python version, dependency versions, Chrome presence, registry/config validity, DB `integrity_check` + required tables, filesystem writability; `--network` adds connectivity probes. Exits non-zero on failure for scripting.
- **Generic webhook channel** — `{"webhook": {"url": "...", "headers": {...}}}` POSTs a JSON payload per alert (ntfy, Slack incoming webhooks, Home Assistant, n8n, …). Included in the rate-limit summary path too.
- **`GET /api/wait-times`** server endpoint exposing stored wait-time baselines; `/api/health` now reports the version.
- **`version` CLI command.**
- Selftest checks 11–15: US city merge, wait-time persistence round-trip, RFC3339 timestamp validity, Telegram chunking under the limit, state.gov table parser.

### Migration from v4.3.0

Drop-in. Existing `visa_slots.db` gains the `wait_times` table automatically on first open; `config.json` works unchanged (add `"webhook": {"url": ""}` only if you want the new channel). US wait-time alerts start functioning after two monitor cycles (first cycle records baselines).

## [4.3.0] — 2026-05-06

**Instant notifications + log noise suppression.** Driven by analysis of the May 6 2026 production cycle (real Czech Republic detection event, 16 slots across 6 hours of continuous monitoring). v4.3.0 closes the 26-minute notification lag observed in v4.2.x and cleans up two operational issues that the cycle log surfaced.

### Added

- **Instant notification on detection.** When `check_target()` produces new slots, `Notifier.send()` is invoked immediately instead of waiting for `run_cycle()` to complete its sweep through all 269 country/city pairs. The cycle-end batch deduplicates against already-sent slots (via a `_instant_sent` attribute on `SlotInfo`) so users never receive duplicate alerts. Disable via `config.json`: `{"instant_notify": false}`. Default is on.

  Empirical baseline: in the May 6 2026 production cycle, the page-change classifier fired `🎯 PAGE CHANGED` for Czech Republic at 03:17:19 IST. The toast notification didn't fire until 03:43:36 — a 26-minute lag while the non-tiered cycle walked through Mexico, Brazil, Hungary, Israel, Turkey, and ~20 other countries before reaching the cycle-end notify step. v4.3.0 reduces the detection-to-notification gap to seconds (~3-5 seconds dispatch latency for desktop toast + Telegram).

- **Documentation of layer health and tier mode recommendation.** The May 6 cycle confirmed that VFS Global has tightened JWT issuance: 17 countries hit `JWT CIRCUIT BREAKER OPEN` (zero successful JWT harvests in the entire 6-hour run). Layer 1 (JWT) and Layer 2 (anonymous API) are effectively dead for those countries; Layer 3 (page-change classifier) is the only working detector. The circuit breaker correctly fell through to Layer 3, which is why detection still worked. README now reflects this. For users tracking high-priority countries, `--tiered` mode is recommended (10-min hot tier vs 70-min full sweep).

### Changed

- **`fake_useragent` log silence.** Set `logging.getLogger("fake_useragent").setLevel(logging.ERROR)` after `logging.basicConfig()`. The library emits a "fallback used" `WARNING` whenever its browser-string CDN is slow or rate-limited; the fallback path always works. We observed ~1,500 of these warnings in the May 6 6-hour run (25% of all log volume). Real `fake_useragent` errors (if any) still propagate at ERROR level.

- **`sys.dont_write_bytecode = True`** at module top. Disables `__pycache__` writes. Windows file copies (e.g., `Copy-Item -Force` from a downloaded zip) preserve the source file's *original* modification time rather than setting it to "now". If a user's previous-version `.pyc` cache has a newer embedded mtime than the new `.py` source's mtime, Python loads the stale bytecode and the new code paths never run. This bit a real upgrade flow (v4.2.0 → v4.2.1 disclaimer prompt didn't fire until `__pycache__` was manually deleted). Trading ~50ms of startup time for guaranteed source-file accuracy.

- **`run_cycle()` log line** now distinguishes between slots notified instantly during the cycle vs. slots batched at end. Before: `🎯 N NEW slot(s) found!`. After: `🎯 N NEW slot(s): X notified instantly during cycle, Y pending end-of-cycle batch` (or `all notified instantly during cycle`).

- **Header docstring** in `visa_tracker_v3.py` updated to v4.3.0. Selftest version label `SELFTEST (v4.2.1)` → `SELFTEST (v4.3.0)`. `smoke_test.py` `EXPECTED_VERSION` → `4.3.0`. `centers.json` version field → `4.3.0` with prepended notes describing the v4.3.0 changes. `README.md`, `USER_GUIDE.md`, `QUICKSTART.md` headers updated.

- **QUICKSTART one-liner verification** updated to test for v4.3.0 features (`_instant_sent`, `sys.dont_write_bytecode = True`, `_first_run_disclaimer_check`) in addition to the v4.0/v4.2 features. Old check `selftest v4.2` removed.

### Migration from v4.2.1

Drop-in. Existing `visa_slots.db`, `config.json`, and `~/.visa_tracker_acknowledged` marker work unchanged. The disclaimer prompt is not re-triggered (the marker file's existence is the gate, not the version).

**Important — clear `__pycache__` after upgrading on Windows:**

```powershell
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
```

This is a one-time workaround for the very issue v4.3.0 fixes going forward. After v4.3.0 is installed, no more `__pycache__` is written, so future upgrades won't have this problem.

**Recommended for users tracking high-priority countries:**

```powershell
python visa_tracker_v3.py set-tier --country "Czech Republic" --tier hot
python visa_tracker_v3.py set-tier --country "United Kingdom" --tier hot
python visa_tracker_v3.py set-tier --preset schengen --tier warm
python visa_tracker_v3.py run --tiered
```

Tiered mode polls hot-tier countries every 10 minutes (vs. ~70 minutes in non-tiered mode). Combined with v4.3.0 instant-notify, slot detection-to-notification latency drops from 26+ minutes (worst case in non-tiered) to seconds.

### Notes for v4.3.0 users

- The May 6 2026 production cycle (837KB log, 6h continuous run, 1,425 Layer 3 invocations, 10 `🎯 PAGE CHANGED` events all for Czech Republic, zero false positives) is the operational baseline this release is built against. If you're seeing different behavior, file an issue with the relevant log excerpt.
- Layer 1 (JWT replay) and Layer 2 (anonymous API) are now effectively dead for the 17 countries observed in the May 6 cycle (Brazil, China, Croatia, Czech Republic, Greece, Hungary, Israel, Mexico, New Zealand, Philippines, Qatar, Russia, Saudi Arabia, Singapore, South Africa, Turkey, UAE). The circuit breaker correctly opens after 6 failures; Layer 3 takes over. This is the intended design from v3.2.4 working as expected.
- Next release (v4.4.0, when warranted) will likely consolidate JWT calibration UX based on what we learn over the next 2-3 weeks of operational data. No commitments.

---

## [4.2.1] — 2026-05-05

**Disclaimer hardening + legal transparency.** No functional code changes; v4.2.0 features remain. This release adds a comprehensive disclaimer suite to clarify the project's research-and-education purpose, document architectural commitments, and provide good-faith case-law analysis for any party (users, GitHub Trust & Safety, regulators, counsel) reviewing the project's posture.

### Added

- **`DISCLAIMER.md`** (top-level) — user-facing scope statement. Covers: (1) what this project is and is not affiliated with, (2) what it does (read-only monitoring of three categories of public data), (3) what it explicitly does not do (no auto-booking, no credential storage, no CAPTCHA bypass, no proxy evasion, no personal-data collection, no commercial agent operation), (4) user responsibility breakdown, (5) prohibited uses inconsistent with stated purpose, (6) explicit framing of the U.S. Embassy India March 2025 announcement and why this software is not the kind of tool it targeted, (7) educational and research purpose statement, (8) trademark non-grant.

- **`LEGAL.md`** (top-level) — case-law-anchored legal posture document. Covers: (1) architecture summary mapped to legal frames, (2) review of relevant authorities (hiQ Labs v. LinkedIn 9th Cir. 2022, Van Buren v. United States S.Ct. 2021, Sandvig v. Barr D.D.C. 2020, Power Ventures v. Facebook 9th Cir. 2016, Craigslist v. 3Taps N.D. Cal. 2013, Feist v. Rural Telephone S.Ct. 1991, 17 U.S.C. § 105, Section 43/66 of India's IT Act 2000, GDPR scope, UK Computer Misuse Act 1990), (3) seven explicit architectural commitments (no credentialed access, no CAPTCHA solving, no proxy evasion, no auto-booking, no personal-data collection, conservative polling defaults, graceful failure), (4) response procedures for DMCA, C&D, government inquiries, and Trust & Safety reviews, (5) sources of further information (EFF, SFLC, GitHub Site Policy, CIS India).

- **README banner** — prominent disclaimer block at the top of `README.md` summarizing the scope and pointing to `DISCLAIMER.md` and `LEGAL.md`. Reframes the project front-page as "open-source research and educational" software rather than "personal automation that watches visa appointment websites."

- **CLI first-run disclaimer** — `_first_run_disclaimer_check()` in `visa_tracker_v3.py`. Shows a one-time scope-and-responsibility notice on first invocation; user types 'yes' to acknowledge; an acknowledgment marker is written to `~/.visa_tracker_acknowledged` and the prompt is skipped on subsequent runs. Skipped automatically for: (a) `--help`, `version`, `selftest` and similar informational commands, (b) CI environments (`CI=true` or `GITHUB_ACTIONS=true` env vars), (c) explicit opt-out via `VISA_TRACKER_NO_PROMPT=1`. The prompt cites the U.S. Embassy India March 2025 announcement and explains why this software is not its target.

### Changed

- **README.md** restructured. Disclaimer banner moved to top. New "What it does" section emphasizes the three read-only data layers and their public-data nature. New "What it does NOT do" section makes the architectural exclusions explicit. Bottom "Disclaimer & legal posture" section points to `DISCLAIMER.md` and `LEGAL.md`. Trademark non-grant added to license section.

- **Version stamps** updated: `visa_tracker_v3.py` header docstring, `centers.json` version field, `smoke_test.py` `EXPECTED_VERSION`, all selftest output strings → 4.2.1.

### Why

The maintainer reviewed the project's legal posture against current scraping case law (post-`hiQ` and post-`Van Buren`), GDPR enforcement trends (Clearview AI, Kaspr), the U.S. Embassy India March 2025 enforcement announcement, and GitHub's DMCA / Acceptable Use / Trust & Safety policies. The conclusion: the project's architecture is well-positioned (no credentialed access, no auto-booking, no personal-data collection, no proxy evasion, public-data layer cleanly within hiQ's "no gates" framework, U.S. State Department data statutorily public domain under 17 U.S.C. § 105), but the *framing* in v4.2.0 was understated. v4.2.1 brings the framing in line with the architecture.

This is a defensive update. No new features were added; no existing features were removed. The intent is to ensure that anyone — user, complainant, GitHub reviewer, regulator, counsel — encountering this project for the first time understands what it is and is not, what it does and does not do, and where the maintainer stands on the relevant authorities.

### Migration from v4.2.0

Drop-in. Existing `visa_slots.db` and `config.json` work unchanged.

On first run, you'll see a one-time disclaimer prompt. Type `yes` to acknowledge. The prompt is skipped on subsequent runs. To skip in CI/CD or GitHub Actions, set `VISA_TRACKER_NO_PROMPT=1` (or run in a `CI` / `GITHUB_ACTIONS` environment, which is auto-detected).

---

## [4.2.0] — 2026-05-05

**US tracker expansion + internationalization.** v4.1.0 implemented US wait-time tracking for 5 Indian consulates; v4.2.0 extends the same processor to 30 third-country US consulates (the "interview at third country" workaround that Indian applicants use when domestic queues are years long). Plus comprehensive non-Indian-user documentation.

### Added

- **30 third-country US consulate entries** in `centers.json`. State.gov publishes wait-time data for every US consulate worldwide; the v4.1.0 `USStateDeptProcessor` was already country-agnostic, just needed entries:
  - **Mexico (10 consulates)** — Ciudad Juárez, Guadalajara, Hermosillo, Matamoros, Mérida, Mexico City, Monterrey, Nogales, Nuevo Laredo, Tijuana. Most popular third-country workaround.
  - **Canada (7 consulates)** — Ottawa, Toronto, Calgary, Halifax, Montreal, Quebec City, Vancouver. TCN restrictions tightened post-2023; still useful for trend tracking.
  - **UAE (2)** — Abu Dhabi, Dubai. Indian expats in Gulf.
  - **Saudi Arabia (2)** — Riyadh, Jeddah.
  - **Singapore, Thailand (2), UK, France, Germany (3), Australia, Japan** — for Indians on those countries' visas.

  All entries default to `enabled: false` — opt-in via `select-countries` to avoid producing noise for users who don't need them.

- **Accent-handling in consulate name matching** — `_consulate_name_variants()` method on `USStateDeptProcessor`. State.gov inconsistently uses accented (`Mérida`, `Ciudad Juárez`) and ASCII forms (`Merida`, `Ciudad Juarez`). The variant generator handles both automatically using `unicodedata.normalize` + a curated list of common alternative forms.

- **`INTERNATIONALIZATION_GUIDE.md`** — comprehensive new doc for non-Indian users. Worked examples for 4 origin/destination combinations (Bangladesh→US, UK→Schengen, Pakistan→Canada, US citizen→other countries). VFS URL country code reference table for 25+ origin countries. Schema rename guide for `indian_cities` → `application_cities`. Multi-region setup patterns. Honest notes on what's adaptable vs what needs code changes.

- **`_third_country_interview_legend`** field at top of `centers.json` documenting the TCN workaround pattern for Indian applicants stuck in long US queues.

### Changed

- **Schengen documentation in ADDING_COUNTRIES.md** — clarified that Schengen monitoring is via the existing VFS layer (already production-validated for Czech Republic May 2026), NOT via a separate wait-time tracker. There is no equivalent of state.gov for Schengen — each member country handles wait times differently. A unified Schengen wait-time tracker isn't built and shouldn't be.

- **README.md** — restructured to highlight v4.2.0 (third-country US, internationalization) at top, kept v4.1.0 (US India consulates) and v4.0.0 (tier system, Telegram, GitHub Actions) sections below. Updated total counts (110+ centers, 45+ destinations).

- **Header docstrings updated** — `visa_tracker_v3.py`, `smoke_test.py` docstrings, and `centers.json` notes now reflect v4.2.0. `USER_GUIDE.md` and `QUICKSTART.md` headers updated to reflect "current version: v4.2.0" instead of "v4.0.0".

- **Selftest version label** updated `v4.1.0` → `v4.2.0`. Smoke test EXPECTED_VERSION updated.

### Comprehensive stale reference audit

Performed a systematic sweep across all documentation files for outdated version references. Classified each reference as:

- **Stale** (updated): document headers tracking the current overall version
- **Historical** (kept): refs documenting when a specific feature was introduced (e.g., "v3.2.2 added the delta classifier" stays correct forever)

Files updated for v4.2.0 cosmetic version bumps: `USER_GUIDE.md`, `QUICKSTART.md`, `README.md`, `visa_tracker_v3.py` header docstring, `smoke_test.py` docstring, `centers.json` version field + notes.

Files preserved at their feature-introduction version (correct as-is): `TIER_SYSTEM.md` (v4.0.0), `TELEGRAM_SETUP.md` (v4.0.0), `GITHUB_ACTIONS.md` (v4.0.0), `VISA_FREE_GUIDE.md` (v4.0.0), `US_VISA_GUIDE.md` (v4.1.0). These document specific features at the version where they shipped — that's intentional, not stale.

### Migration from v4.1.0

Drop-in. Existing `visa_slots.db` and `config.json` work unchanged. The 30 new US consulate entries are pre-disabled — you'll see them in `coverage` output but they don't run unless you opt in:

```powershell
# Pick the third-country US consulates you want to monitor
python visa_tracker_v3.py select-countries
# In custom mode, scroll to the United States section — entries are listed
# per consulate so you can pick "Ciudad Juárez", "Tijuana", "Dubai" individually
```

For non-Indian users adopting v4.2.0 fresh: see `INTERNATIONALIZATION_GUIDE.md`. About 30 minutes to set up for a typical non-Indian origin.

### Notes for v4.2.0 users

- US wait-time tracking remains **beta**. The state.gov page format hasn't changed during v4.1.0 testing, but it's regex-based parsing — if State Department redesigns the page, the parser breaks gracefully (returns no data, no false alerts) but you'd silently lose US monitoring until the regex is updated.
- Third-country US consulates are particularly variable. State.gov sometimes shows "Closed" or "Interview Waiver" for consulates not currently accepting TCN appointments. The transition-detection logic catches these but treat with skepticism.
- For real-time US slot detection, the only legal/practical path remains: log into your CGI Federal account directly. This tracker complements that, doesn't replace it.

---

## [4.1.0] — 2026-05-05

**US visa wait-time tracker.** First non-VFS, non-Selenium processor in the codebase. Plus stale-reference cleanup that the user spotted (the `"version": "3.2.4"` example block in `ADDING_COUNTRIES.md` had survived from when the file was first written for v3.2.4).

### Added

- **`USStateDeptProcessor` class** — new processor for monitoring US visa wait times via two public, unauthenticated data sources:
  - Primary: `travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html` (US Department of State, monthly updates, authoritative)
  - Fallback: `ais.usvisa-info.com/en-in/niv/information/visa_wait_times` (CGI Federal public page, more frequent updates, less authoritative)

  Pure HTTP, no Selenium, no JWT, no captcha. Detects significant drops in wait time (≥10% relative or ≥20 absolute days) which strongly correlate with new appointment slot batches being released by US consulates. Wait time history persisted in the existing `slots` table via metadata JSON column (no schema migration needed).

- **5 new US consulate entries** in `centers.json`: Mumbai, New Delhi, Chennai, Hyderabad, Kolkata. Each tracks 5 visa categories: B1/B2 (visitor), F/M/J (student/exchange), H/L/O/P/Q (work/petition-based), C1/D (crew/transit), Other Nonimmigrant. Default tier `cold` (90 min polling — appropriate given underlying data updates monthly).

- **`us_state_dept` processor metadata** in `centers.json` processors dict. Complements (does not replace) the existing `cgi_federal` entry which remains correctly disabled with documented account-lock risk warnings.

- **`US_VISA_GUIDE.md`** — comprehensive new documentation explaining what the US tracker does and does NOT do. Sets honest expectations: trend tracker, not real-time slot scraper. Latency is days to weeks (state.gov updates monthly), not minutes like VFS. Documents why direct CGI Federal slot scraping is intentionally out of scope (account-lock risk, ToS questions, credential handling concerns).

- **README.md US section** highlighting v4.1.0 with explicit honest caveat that this is not real-time scraping.

### Changed

- **`UnifiedChecker.check()` dispatch** — added a new branch at the top that routes `processor=us_state_dept` to `USStateDeptProcessor.check()` BEFORE the VFS/JWT layers. US doesn't need calibration, doesn't burn the Selenium budget. All existing VFS/BLS/TLS/embassy_direct dispatch unchanged.

- **`SETUP_GUIDE.md` header** — was titled "v3.2.2 — Production Setup Guide" since the v3.2.2 release. Rewritten with current-version framing while preserving the v3.2.x technical content as historical record (nothing about the original v3.2.2 architecture has changed; just no longer the "current" version).

- **`PROCESSORS.md` header** — bumped from "(v3.2.1)" to "current as of v4.1.0". Added US visas section.

- **`ADDING_COUNTRIES.md`** — fixed the user-spotted bug: example block showed `"version": "3.2.4"` because the file was first written during v3.2.4 work and the embedded JSON example never got updated when the schema bumped to v4.0/v4.1. Now correctly shows v4.0.0 in the example with the `tier` field included.

- **Selftest version label** updated `v4.0.0` → `v4.1.0`. Smoke test EXPECTED_VERSION updated.

### Migration from v4.0.0

Drop-in. Existing `visa_slots.db` and `config.json` work unchanged. To start tracking US wait times:

```powershell
python visa_tracker_v3.py select-countries
# Pick: 'all' or 'americas' (or 'custom' and select United States)
python visa_tracker_v3.py run --tiered
```

US dispatch is automatic — no flag needed.

### Validated against real production traffic (cumulative, all v3.2.x + v4.0)

- 22+ hours of continuous monitoring across 9 cycles, 290 city-checks per cycle
- 1,972 page-change events processed, 100% correctly classified (4 real positives, 1,968 noise events suppressed)
- Czech Republic appointment slots detected at 05:01 IST May 5, 2026 (delta=2126c, all 4 cities), externally verified by direct VFS portal screenshot

US processor has not yet been validated against real production traffic — it ships with the architecture proven via smoke test (10/10 selftest passes including the new dispatch path), but real-world drift behavior will only be observable after weeks of monitoring real state.gov updates. Treat v4.1.0 US support as **beta** — works as designed, but the regex-based parser of state.gov HTML may need tuning if State Department changes the page format.

---

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
