#!/usr/bin/env python3
"""
Visa Slot Tracker v4.4.0 — US wait-time tracking repaired + hardening + new tooling

v4.4.0 is a bug-fix and capability release driven by a full-code audit:

  • FIXED: US wait-time persistence was 100% broken since v4.1.0. The
    USStateDeptProcessor read/wrote `slots.id`, `slots.metadata`, and
    `slots.expires_at` — columns that have never existed in the schema
    (the table has `uid`, no metadata, and an `expired` flag). Every
    baseline write failed silently, `prev` was always None, and a US
    wait-time drop alert could NEVER fire across all 36 US consulate
    centers. v4.4.0 adds a dedicated `wait_times` table (proper lock +
    WAL usage) and round-trips numeric and status values as JSON.
  • FIXED: `server` / `run --server` crashed on startup with
    AttributeError: module 'aiohttp' has no attribute 'web' — the code
    used `aiohttp.web.*` but only `import aiohttp` was performed. The
    web submodule is now imported explicitly.
  • FIXED: every stored timestamp ended in "+00:00Z" (isoformat already
    appends the UTC offset; the code appended a literal "Z" on top).
    JavaScript's `new Date()` rejects that form, so the dashboard showed
    "Invalid Date" / broken sorting for every slot. New `utc_now_iso()`
    helper emits proper RFC3339 ("2026-07-29T16:09:32Z").
  • FIXED: Telegram alerts over ~4096 chars (≈8+ slots) were rejected by
    the Bot API and silently dropped — the code logged "Telegram sent"
    without checking the response. Messages are now chunked under the
    limit, HTML-escaped, and each API response is verified.
  • FIXED: default targets collapsed all 36 "United States" consulate
    centers into one (first-seen city only). Cities are now merged per
    (country, processor), so all US consulates are actually monitored.
  • FIXED: state.gov wait-time parsing now understands the real HTML
    table layout (city rows × visa-category header columns) instead of
    only the label-adjacent-to-value regex, which matched nothing on a
    standard table. Regex path retained as fallback.
  • Tiered mode now honors instant_notify (v4.3.0 shipped instant
    alerts only in the plain cycle runner).
  • VFS JWT cache is per-country (was: single global token, so every
    country switch re-harvested via a fresh Selenium session).
  • Slots are marked notified=1 in the DB after a successful dispatch.
  • Desktop toasts are skipped in CI environments (no notify-send).
  • New CLI: `wait-times` (live US consulate wait-time table),
    `export` (slots/checks → JSON/CSV), `doctor` (environment
    diagnostics: deps, Chrome, config, DB integrity).
  • New notification channel: generic `webhook` (POSTs a JSON payload —
    works with ntfy, Slack incoming webhooks, Home Assistant, etc.).
  • New server endpoint: GET /api/wait-times.
  • Cleanups: dead imports removed (pickle, urljoin, Any), explicit
    selenium exception imports, page-hash preview cap aligned with the
    delta window (12000), pip bootstrap works on pip < 23
    (--break-system-packages made conditional), SIGINT now shuts the
    executor down cleanly.

v4.3.0 acts on findings from the May 6 2026 production cycle (real Czech
Republic detection, 16 slots) where notifications fired 26 minutes after
the actual page-change event because the cycle walked sequentially through
all 269 country/city pairs before the batch notify ran. v4.3.0 ships:

  • Instant notification on detection — when a target produces new slots,
    the toast/Telegram/email/Discord alert fires immediately rather than
    waiting for cycle end. Cycle-end batch dedupes against already-sent
    slots so users never get duplicate alerts. Disable via
    `{"instant_notify": false}` in config.json. Default is on.
  • fake_useragent log silence — the library emits a "fallback used"
    WARNING on every browser-string request when its CDN is slow or
    rate-limited. The fallback works fine; we observed ~1,500 of these
    warnings per 6h run (25% of all log volume). Set the logger level
    to ERROR to suppress the cosmetic chatter while keeping real errors
    visible.
  • sys.dont_write_bytecode = True — disables __pycache__ writes. Stale
    .pyc bytecode masked the v4.2.0→v4.2.1 disclaimer prompt on Windows
    until __pycache__ was manually nuked. Trading 50ms startup for
    guaranteed source-file accuracy is correct for a CLI tool that users
    upgrade by overwriting files.

v4.2.1 — Disclaimer hardening + legal transparency

v4.2.1 was a defensive update. No functional code changes; v4.2.0 features
remained. Comprehensive disclaimer suite: DISCLAIMER.md (user-facing scope),
LEGAL.md (case-law-anchored posture: hiQ, Van Buren, Sandvig, Power Ventures,
3Taps, Feist, 17 USC 105, IT Act 43/66, GDPR, CMA), README banner, CLI
first-run prompt with ~/.visa_tracker_acknowledged marker. Auto-skips for
--help, CI envs, VISA_TRACKER_NO_PROMPT=1.

v4.2.0 expansions:
  • Extended USStateDeptProcessor to 30+ US consulates worldwide (Mexico,
    Canada, UAE, Saudi Arabia, Singapore, Thailand, UK). State.gov publishes
    wait times for every US consulate globally; the processor was already
    country-agnostic, just needed centers.json entries. High-value for the
    "third-country interview" workaround pattern Indians use when domestic
    US queues are years long — Mexico (9 consulates) is the most popular
    workaround, Canada (7) less so post-2023 policy changes, UAE (2) and
    Saudi Arabia (2) for Indians on Gulf work visas.
  • Accent-handling in consulate name matching (e.g. "Ciudad Juárez" vs
    "Ciudad Juarez", "Mérida" vs "Merida"). State.gov uses accented forms
    on some pages, ASCII on others.
  • New INTERNATIONALIZATION_GUIDE.md for non-Indian users. Documents how
    to adapt the repo for tracking visas from any origin country, with
    worked examples (Bangladesh→US, UK→Schengen, Pakistan→Canada). The
    schema was always passport-agnostic; just needed proper docs.
  • Schengen documentation enhanced in ADDING_COUNTRIES.md. Honest framing:
    Schengen unified wait-time tracking IS NOT possible because there is
    no equivalent state.gov-style data source — each Schengen member
    handles wait times differently. The existing VFS layer (validated for
    Schengen via real Czech Republic detections May 2026) IS the right
    mechanism. Documented per-country specifics for all 17 Schengen members.
  • Stale reference cleanup pass — every doc header updated to reflect
    current version.

v4.1.0 — US visa wait-time tracker (Indian consulates)

v4.1.0 added the first non-VFS, non-Selenium processor: US Department of State
wait-time monitoring. Initially Indian travelers could monitor 5 US consulates
(Mumbai, Delhi, Chennai, Hyderabad, Kolkata) across 5 visa categories
(B1/B2, F/M/J, H/L/O/P/Q, C1/D, Other) without needing DS-160 or auth.

What's new in v4.1.0:
  • USStateDeptProcessor (new class) — fetches official wait-time data from
    travel.state.gov + ais.usvisa-info.com/en-in/niv/information/visa_wait_times.
    Pure HTTP, no Selenium, no JWT, no captcha. Detects significant drops
    in wait time which strongly correlate with new appointment slot batches
    being released by US consulates.
  • centers.json schema additions: 5 new US consulate entries with
    processor='us_state_dept'. Bumped to v4.1.0.
  • New documentation: US_VISA_GUIDE.md — explains scope (trend tracker, not
    real-time slot scraper), limitations (state.gov updates monthly), and
    how to use US alerts (race to ais.usvisa-info.com after auth).
  • Stale documentation references (v3.2.4 example in ADDING_COUNTRIES.md,
    v3.2.2 header in SETUP_GUIDE.md, v3.2.1 header in PROCESSORS.md)
    updated to reflect current version.

What's preserved from v4.0.0 (no breaking changes):
  • Tier system (hot/warm/cold polling, --tiered flag, set-tier CLI)
  • Country selection (select-countries CLI with 6 presets)
  • Telegram setup wizard (setup-telegram CLI)
  • GitHub Actions deployment (3 workflow files)
  • Visa-free / e-visa flagging (_indian_passport_status field)
  • Telegram env var support (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    NOTIFICATION_DRY_RUN)

What's preserved from v3.2.x (no breaking changes):
  • Three-layer detection: VFS JWT replay, anonymous API, delta page-change
  • Persistent-noise marker, notification rate-limit, selector-phase 5x speedup
  • JWT circuit breaker
  • windows-toasts desktop notifications + PowerShell BalloonTip fallback
  • UTF-8 BOM-tolerant config
  • Streaming GET preflight
  • All v3.2.x CLI commands: selftest, verify-urls, calibrate, status,
    coverage, run

Migration from v4.0.0: drop in v4.1 files, your existing visa_slots.db works
unchanged, your existing config.json works unchanged. To start tracking US
wait times: run select-countries and pick 'all' or 'americas' preset, then
run as usual. US dispatch is automatic — UnifiedChecker routes us_state_dept
processor to USStateDeptProcessor.

Three-layer detection strategy:
  Layer 1: API Interception — Capture the XHR/fetch calls that frontends make
           to get appointment data. Fastest, most reliable, no DOM guessing.
  Layer 2: Authenticated Scraping — Real login flows with session persistence,
           then monitor known calendar endpoints.
  Layer 3: Page-Change Detection — DELTA-based: hash page content, on change
           classify ONLY the diff (not the whole page), filter cosmetic noise,
           rate-limit notifications, mark noisy countries.

v3.2.2 changes vs v3.2.1 (production-blocking fixes from terminal-log audit):
  - Page-change DELTA classifier: previously the classifier read the full
    post-noise page text on every hash change, so a static "Book your
    appointment" UI label fired slots_likely on every cosmetic page mutation.
    v3.2.2 computes the diff between the previous baseline preview and the
    current text using difflib, then classifies only the changed lines. If
    the diff is empty, pure-noise, or under 30 chars, the change is suppressed.
  - Persistent-noise marker: a country firing page_changed in 2 consecutive
    cycles gets flagged "noisy" in the DB. Subsequent cycles require a higher
    classifier threshold (3 weak positives instead of 2). Auto-decays after
    3 clean cycles. New DB column: page_hashes.consecutive_changes.
  - Notification rate-limit: max 25 slot alerts per cycle. Overflow becomes
    a single summary alert with a link to the dashboard. Stops the
    "375 NEW slot(s) found!" notification storm seen in the v3.2 run log.
  - Selector phase implicit_wait fix: Step 3 was eating 105s/country (87% of
    runtime) because Selenium's implicit_wait=5s × 21 selectors = 105s of
    timeouts on missed selectors. v3.2.2 drops implicit_wait to 0.3s during
    Step 3, restores after. ~5x calibration speedup (83min -> ~17min).
  - JWT circuit-breaker: VFSJWTSession tracks per-country consecutive harvest
    failures. After 6 in a row, logs loudly and short-circuits to None for
    that country. Resets on next successful harvest.
  - Cycle/interval mismatch warning: run_monitor logs a clear warning when
    a cycle takes >2× the configured interval (so you know you're effectively
    running back-to-back instead of polling).
  - New CLI: `selftest` runs an offline ~30s integration check (registry
    load, classifier, JWT class, DB migration, click-through XPaths,
    notifier on empty input). Catches v3.2.x regressions without a real
    calibration run.
  - run --dry-run: skip all outbound notifications, just log what would
    have fired. Useful for safe v3.2.2 validation against real portals.

v3.2.1 changes vs v3.2:
  - URL audit: Portugal moved BLS->VFS, Algeria/Tunisia/Mozambique moved
    BLS->embassy_direct (the BLS URLs were pattern-generated, not real).
  - Calibrator: added click-through phase (Step 3.5) so countries that gate
    their slot API behind a "Book/Continue" button get their endpoints
    discovered too. Czech Republic was the only country that auto-fired
    its API on landing in v3.2; click-through generalizes that pattern.
  - Calibrator: optional --workers N flag for parallel calibration.
  - Calibrator: captures full request details (URL + method + headers
    matching pattern) instead of just URLs.
  - Calibrator: writes a `confidence` (high|medium|low) into the DB record.
  - UnifiedChecker: tries the processor-level `known_api_endpoints` (from
    centers.json) before falling back to per-country calibration data.
  - VFS lift-api JWT replay path: harvests a fresh JWT via headless
    Selenium and replays /appointment/slots with country params. Cached
    for 25 minutes (typical token TTL is shorter; cache wins both ways).
  - Page-change detector: tighter `_classify_change` with extended noise
    pattern library; suppresses cosmetic changes (cookie banners, news
    ticker, A/B variants).
  - SlotInfo: confidence is now sourced from the calibration record, not
    hard-coded to "medium".
  - New CLI: `verify-urls` — preflights every enabled center URL with a
    HEAD/GET and reports DNS errors, 404s, and Cloudflare blocks. Runs in
    seconds and saves you from a 90-minute calibration on broken URLs.

Run:
    python visa_tracker_v3.py setup              # Interactive first-time setup
    python visa_tracker_v3.py selftest           # NEW v3.2.2: offline 30s integration check
    python visa_tracker_v3.py verify-urls        # Preflight all URLs (fast)
    python visa_tracker_v3.py calibrate USA      # Calibrate one country
    python visa_tracker_v3.py calibrate --all                # Sequential
    python visa_tracker_v3.py calibrate --all --workers 4    # Parallel
    python visa_tracker_v3.py run                # Start monitoring
    python visa_tracker_v3.py run --once         # Single check cycle
    python visa_tracker_v3.py run --dry-run      # NEW v3.2.2: skip notifications
    python visa_tracker_v3.py server             # API + WebSocket server
    python visa_tracker_v3.py run --server       # Monitor + server together
    python visa_tracker_v3.py status             # Diagnostic snapshot
    python visa_tracker_v3.py coverage           # Show registry coverage
    python visa_tracker_v3.py list-countries     # List all supported countries
    python visa_tracker_v3.py wait-times         # NEW v4.4.0: live US consulate wait times
    python visa_tracker_v3.py export --format csv # NEW v4.4.0: export slots/checks
    python visa_tracker_v3.py doctor             # NEW v4.4.0: environment diagnostics
"""

import asyncio
import json
import time
import logging
import smtplib
import hashlib
import sqlite3
import os
import sys

# v4.3.0 — disable bytecode caching to prevent stale __pycache__/.pyc files
# from masking new code paths after a version upgrade. Windows file copies
# preserve the source's original mtime, which can cause Python to load a
# previous version's bytecode even after the .py source has been replaced.
# This bit a real user upgrading v4.2.0 → v4.2.1 (the new disclaimer prompt
# never fired until __pycache__ was manually nuked). Trading a small startup
# cost (~50ms) for guaranteed source-file accuracy is correct for a CLI tool
# that the user upgrades by overwriting files.
sys.dont_write_bytecode = True

import signal
import random
import re
import traceback
import threading
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, asdict
from html import escape as html_escape
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

__version__ = "4.4.0"


def utc_now_iso() -> str:
    """RFC3339 UTC timestamp, e.g. '2026-07-29T16:09:32Z'.

    v4.4.0 fix: the previous idiom `datetime.now(tz=utc).isoformat() + "Z"`
    produced '...+00:00Z' — isoformat() already appends the offset, so the
    extra Z made the string unparseable for JavaScript's Date() (dashboard
    showed 'Invalid Date' for every slot) and for strict RFC3339 parsers.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEPENDENCY BOOTSTRAP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUIRED_PKGS = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "selenium": "selenium",
    "aiohttp": "aiohttp",
    "websockets": "websockets",
    "fake_useragent": "fake-useragent",
    "webdriver_manager": "webdriver-manager",
}

def bootstrap():
    import subprocess
    missing = []
    for mod, pkg in REQUIRED_PKGS.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[setup] Installing: {', '.join(missing)}")
        base_cmd = [sys.executable, "-m", "pip", "install", "-q"] + missing
        try:
            # Plain install first — works everywhere pip works.
            subprocess.check_call(base_cmd)
        except subprocess.CalledProcessError:
            # PEP 668 "externally managed environment" (Debian/Ubuntu system
            # Python) rejects plain installs; retry with the override flag.
            # Doing it this way round keeps pip < 23.0 working too, where
            # --break-system-packages doesn't exist and would itself error.
            try:
                subprocess.check_call(base_cmd + ["--break-system-packages"])
            except subprocess.CalledProcessError as e:
                print(f"[setup] Automatic install failed ({e}).")
                print(f"[setup] Install manually:  {sys.executable} -m pip install {' '.join(missing)}")
                sys.exit(1)

bootstrap()

# v3.2.2a fix: Force UTF-8 on stdout/stderr on Windows so the emoji,
# box-drawing, and check-mark characters in print() calls (used by
# selftest, verify-urls, coverage, status, list-countries) don't crash
# under PowerShell's default cp1252 codec with UnicodeEncodeError.
# Python's logging handles this internally via the FileHandler's
# encoding="utf-8", but bare print() statements default to whatever
# sys.stdout.encoding is — which on Windows is cp1252.
# errors='replace' substitutes '?' for unencodable chars instead of
# crashing, just in case the reconfigure itself fails on a weird host.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Silence harmless 3rd-party warnings on Python 3.14 (urllib3/charset_normalizer
# pin chatter that has no functional impact). v3.2.1.
import warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning  # noqa
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass
try:
    from requests.exceptions import RequestsDependencyWarning  # noqa
    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except Exception:
    pass
warnings.filterwarnings("ignore", message=r".*urllib3.*doesn't match.*")
warnings.filterwarnings("ignore", message=r".*charset_normalizer.*doesn't match.*")

import requests
from bs4 import BeautifulSoup
# v4.4.0 fix: aiohttp does NOT expose .web from a bare `import aiohttp` —
# every aiohttp.web.* reference in the Server class raised AttributeError,
# so `server` and `run --server` crashed on startup. Import it explicitly.
from aiohttp import web as aiohttp_web
import websockets

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)

try:
    from fake_useragent import UserAgent
    _ua = UserAgent(browsers=["chrome"], os=["windows", "macos"])
    def rand_ua(): return _ua.random
except:
    def rand_ua():
        v = random.randint(120, 126)
        return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36")

# ── Logging ──
LOG_FMT = "%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s"
logging.basicConfig(
    level=logging.INFO, format=LOG_FMT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("visa_tracker.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("tracker")

# v4.3.0 — silence fake_useragent's chatty fallback warnings.
# The library tries to fetch a fresh browser-string list at every call and
# warns when it can't (offline, rate-limited, CDN slow). The fallback path
# always works fine. In a typical 6h run we observed ~1,500 of these
# warnings — 25% of total log volume — and they tell the user nothing
# actionable. Setting the logger level to ERROR keeps real errors visible
# but suppresses the cosmetic fallback chatter.
logging.getLogger("fake_useragent").setLevel(logging.ERROR)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SlotInfo:
    country: str
    city: str
    visa_type: str
    date: str
    time_slot: str = "—"
    portal: str = ""
    booking_url: str = ""
    found_at: str = ""
    detection_method: str = ""  # "api" | "scrape" | "page_change" | "manual"
    confidence: str = "high"    # "high" | "medium" | "low"
    raw_data: str = ""

    def __post_init__(self):
        if not self.found_at:
            self.found_at = utc_now_iso()

    @property
    def uid(self) -> str:
        blob = f"{self.country}|{self.city}|{self.visa_type}|{self.date}|{self.time_slot}"
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self)
        d["uid"] = self.uid
        return d


@dataclass
class CheckResult:
    country: str
    city: str
    portal: str
    status: str          # "slots_found" | "no_change" | "page_changed" | "error" | "captcha" | "login_needed"
    slots: list
    error: str = ""
    duration_ms: int = 0
    method: str = ""     # which detection layer found results
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = utc_now_iso()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Database:
    def __init__(self, path="visa_slots.db"):
        self.path = path
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=5000")
        return c

    def _init(self):
        with self._lock:
            conn = self._conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS slots (
                    uid TEXT PRIMARY KEY,
                    country TEXT, city TEXT, visa_type TEXT,
                    date TEXT, time_slot TEXT, portal TEXT,
                    booking_url TEXT, found_at TEXT,
                    detection_method TEXT, confidence TEXT,
                    raw_data TEXT,
                    notified INTEGER DEFAULT 0,
                    expired INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checked_at TEXT, country TEXT, city TEXT, portal TEXT,
                    status TEXT, slots_found INTEGER, duration_ms INTEGER,
                    method TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS page_hashes (
                    key TEXT PRIMARY KEY,
                    hash TEXT,
                    last_checked TEXT,
                    content_preview TEXT,
                    consecutive_changes INTEGER DEFAULT 0,
                    last_change_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    portal TEXT PRIMARY KEY,
                    cookies TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS wait_times (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS calibration (
                    country_portal TEXT PRIMARY KEY,
                    working_selectors TEXT,
                    api_endpoints TEXT,
                    login_required INTEGER,
                    page_structure TEXT,
                    last_calibrated TEXT,
                    notes TEXT,
                    confidence TEXT DEFAULT 'medium'
                );
                CREATE INDEX IF NOT EXISTS idx_slots_country ON slots(country);
                CREATE INDEX IF NOT EXISTS idx_checks_at ON checks(checked_at);
            """)
            # ── v3.2.1 migration: add confidence column to calibration if
            # upgrading from v3.2. ALTER TABLE IF NOT EXISTS isn't supported
            # in SQLite, so we probe pragma and conditionally add.
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(calibration)").fetchall()]
                if "confidence" not in cols:
                    conn.execute("ALTER TABLE calibration ADD COLUMN confidence TEXT DEFAULT 'medium'")
                    log.info("DB migration v3.2.1: added calibration.confidence column")
            except Exception as e:
                log.warning(f"Migration check failed (non-fatal): {e}")

            # ── v3.2.2 migration: add persistent-noise tracking columns to
            # page_hashes. Same idempotent ALTER pattern as above.
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(page_hashes)").fetchall()]
                if "consecutive_changes" not in cols:
                    conn.execute("ALTER TABLE page_hashes ADD COLUMN consecutive_changes INTEGER DEFAULT 0")
                    log.info("DB migration v3.2.2: added page_hashes.consecutive_changes column")
                if "last_change_at" not in cols:
                    conn.execute("ALTER TABLE page_hashes ADD COLUMN last_change_at TEXT")
                    log.info("DB migration v3.2.2: added page_hashes.last_change_at column")
            except Exception as e:
                log.warning(f"v3.2.2 migration check failed (non-fatal): {e}")
            conn.commit()
            conn.close()

    def is_new(self, slot: SlotInfo) -> bool:
        with self._lock:
            conn = self._conn()
            row = conn.execute("SELECT uid FROM slots WHERE uid=?", (slot.uid,)).fetchone()
            conn.close()
            return row is None

    def save_slot(self, slot: SlotInfo):
        with self._lock:
            conn = self._conn()
            conn.execute("""
                INSERT OR REPLACE INTO slots
                (uid,country,city,visa_type,date,time_slot,portal,
                 booking_url,found_at,detection_method,confidence,raw_data)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (slot.uid, slot.country, slot.city, slot.visa_type,
                  slot.date, slot.time_slot, slot.portal,
                  slot.booking_url, slot.found_at, slot.detection_method,
                  slot.confidence, slot.raw_data))
            conn.commit()
            conn.close()

    def log_check(self, r: CheckResult):
        with self._lock:
            conn = self._conn()
            conn.execute("""
                INSERT INTO checks (checked_at,country,city,portal,status,slots_found,duration_ms,method,error)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (r.checked_at, r.country, r.city, r.portal,
                  r.status, len(r.slots), r.duration_ms, r.method, r.error))
            conn.commit()
            conn.close()

    def get_page_hash(self, key: str) -> Optional[str]:
        with self._lock:
            conn = self._conn()
            row = conn.execute("SELECT hash FROM page_hashes WHERE key=?", (key,)).fetchone()
            conn.close()
            return row[0] if row else None

    def get_page_state(self, key: str) -> Optional[dict]:
        """v3.2.2: return hash + full preview + noise-tracking state for delta-classifier."""
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT hash, content_preview, "
                "COALESCE(consecutive_changes, 0), last_change_at, last_checked "
                "FROM page_hashes WHERE key=?", (key,)
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "hash": row[0],
                "preview": row[1] or "",
                "consecutive_changes": int(row[2] or 0),
                "last_change_at": row[3],
                "last_checked": row[4],
            }

    def set_page_hash(self, key: str, h: str, preview: str = "",
                      consecutive_changes: Optional[int] = None,
                      mark_change: bool = False):
        """v3.2.2: also persists noise tracking. Backward-compatible signature."""
        now = utc_now_iso()
        with self._lock:
            conn = self._conn()
            # Read current consecutive_changes if not given
            if consecutive_changes is None:
                row = conn.execute(
                    "SELECT COALESCE(consecutive_changes,0) FROM page_hashes WHERE key=?",
                    (key,)
                ).fetchone()
                consecutive_changes = (int(row[0]) if row else 0)
                if mark_change:
                    consecutive_changes += 1
            last_change_at = now if mark_change else None
            # Preserve previous last_change_at if not marking a fresh change
            if last_change_at is None:
                row = conn.execute(
                    "SELECT last_change_at FROM page_hashes WHERE key=?", (key,)
                ).fetchone()
                last_change_at = row[0] if row else None
            # v4.4.0: preview cap raised 5000 → 12000 to match the delta
            # window in _compute_delta. With a 5000-char baseline, any page
            # text between 5000 and 12000 chars showed up as "added" lines
            # on every genuine hash change, inflating the delta.
            conn.execute("""
                INSERT OR REPLACE INTO page_hashes
                (key, hash, last_checked, content_preview,
                 consecutive_changes, last_change_at)
                VALUES (?,?,?,?,?,?)
            """, (key, h, now, preview[:12000],
                  consecutive_changes, last_change_at))
            conn.commit()
            conn.close()

    def reset_page_noise(self, key: str):
        """v3.2.2: clear consecutive_changes counter when a country goes clean."""
        with self._lock:
            conn = self._conn()
            conn.execute(
                "UPDATE page_hashes SET consecutive_changes=0 WHERE key=?", (key,)
            )
            conn.commit()
            conn.close()

    def save_calibration(self, country_portal: str, data: dict):
        with self._lock:
            conn = self._conn()
            conn.execute("""
                INSERT OR REPLACE INTO calibration
                (country_portal, working_selectors, api_endpoints,
                 login_required, page_structure, last_calibrated, notes, confidence)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                country_portal,
                json.dumps(data.get("selectors", [])),
                json.dumps(data.get("api_endpoints", [])),
                1 if data.get("login_required") else 0,
                json.dumps(data.get("page_structure", {})),
                utc_now_iso(),
                data.get("notes", ""),
                data.get("confidence", "medium"),
            ))
            conn.commit()
            conn.close()

    def get_calibration(self, country_portal: str) -> Optional[dict]:
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT working_selectors, api_endpoints, login_required, "
                "page_structure, last_calibrated, notes, "
                "COALESCE(confidence, 'medium') AS confidence "
                "FROM calibration WHERE country_portal=?",
                (country_portal,)
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "selectors": json.loads(row[0]) if row[0] else [],
                "api_endpoints": json.loads(row[1]) if row[1] else [],
                "login_required": bool(row[2]),
                "page_structure": json.loads(row[3]) if row[3] else {},
                "last_calibrated": row[4],
                "notes": row[5],
                "confidence": row[6] or "medium",
            }

    def save_session(self, portal: str, cookies: list):
        with self._lock:
            conn = self._conn()
            conn.execute("""
                INSERT OR REPLACE INTO sessions (portal,cookies,updated_at)
                VALUES (?,?,?)
            """, (portal, json.dumps(cookies), utc_now_iso()))
            conn.commit()
            conn.close()

    # ── v4.4.0: wait-time persistence ────────────────────────────────────
    # The USStateDeptProcessor previously abused the slots table with
    # column names (`id`, `metadata`, `expires_at`) that never existed in
    # this schema, so every read/write raised OperationalError (swallowed
    # at debug level) and no wait-time comparison ever happened. A small
    # dedicated key/value table keeps it honest. Values round-trip as JSON
    # so both numeric day counts and status strings ("Closed") survive.

    def set_wait_time(self, key: str, value):
        with self._lock:
            conn = self._conn()
            conn.execute("""
                INSERT OR REPLACE INTO wait_times (key, value, updated_at)
                VALUES (?,?,?)
            """, (key, json.dumps(value), utc_now_iso()))
            conn.commit()
            conn.close()

    def get_wait_time(self, key: str):
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT value FROM wait_times WHERE key=?", (key,)
            ).fetchone()
            conn.close()
        if not row or row[0] is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None

    def get_all_wait_times(self) -> list[dict]:
        with self._lock:
            conn = self._conn()
            rows = conn.execute(
                "SELECT key, value, updated_at FROM wait_times ORDER BY key"
            ).fetchall()
            conn.close()
        out = []
        for key, value, updated_at in rows:
            try:
                parsed = json.loads(value) if value is not None else None
            except (json.JSONDecodeError, TypeError):
                parsed = value
            out.append({"key": key, "value": parsed, "updated_at": updated_at})
        return out

    def mark_notified(self, uids: list[str]):
        """v4.4.0: flag slots as notified after a successful dispatch.

        The column existed since v3.0 but nothing ever set it, so the
        dashboard's `notified` field was always 0.
        """
        if not uids:
            return
        with self._lock:
            conn = self._conn()
            conn.executemany(
                "UPDATE slots SET notified=1 WHERE uid=?",
                [(u,) for u in uids],
            )
            conn.commit()
            conn.close()

    def get_session(self, portal: str) -> Optional[list]:
        with self._lock:
            conn = self._conn()
            row = conn.execute("SELECT cookies FROM sessions WHERE portal=?", (portal,)).fetchone()
            conn.close()
            return json.loads(row[0]) if row else None

    def get_active_slots(self) -> list[dict]:
        with self._lock:
            conn = self._conn()
            rows = conn.execute("""
                SELECT uid,country,city,visa_type,date,time_slot,
                       portal,booking_url,found_at,detection_method,confidence,notified
                FROM slots WHERE expired=0 ORDER BY found_at DESC LIMIT 500
            """).fetchall()
            conn.close()
        cols = ["uid","country","city","visa_type","date","time_slot",
                "portal","booking_url","found_at","detection_method","confidence","notified"]
        return [dict(zip(cols, r)) for r in rows]

    def recent_checks(self, limit=100) -> list[dict]:
        with self._lock:
            conn = self._conn()
            rows = conn.execute("""
                SELECT checked_at,country,city,portal,status,slots_found,duration_ms,method,error
                FROM checks ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            conn.close()
        cols = ["checked_at","country","city","portal","status",
                "slots_found","duration_ms","method","error"]
        return [dict(zip(cols, r)) for r in rows]

    def stats(self) -> dict:
        with self._lock:
            conn = self._conn()
            total = conn.execute("SELECT COUNT(*) FROM slots WHERE expired=0").fetchone()[0]
            countries = conn.execute("SELECT COUNT(DISTINCT country) FROM slots WHERE expired=0").fetchone()[0]
            cities = conn.execute("SELECT COUNT(DISTINCT city) FROM slots WHERE expired=0").fetchone()[0]
            last = conn.execute("SELECT checked_at FROM checks ORDER BY id DESC LIMIT 1").fetchone()
            total_checks = conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM checks WHERE status='error'").fetchone()[0]
            conn.close()
        return {
            "total_slots": total, "countries": countries, "cities": cities,
            "total_checks": total_checks, "error_checks": errors,
            "last_check": last[0] if last else None,
        }

    def expire_old(self, days=7):
        # Formatted like utc_now_iso() so lexicographic comparison against
        # stored found_at values stays coherent (old "+00:00Z" rows still
        # compare correctly at day granularity — dates dominate the sort).
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)) \
            .isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._lock:
            conn = self._conn()
            conn.execute("UPDATE slots SET expired=1 WHERE found_at < ?", (cutoff,))
            conn.commit()
            conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BROWSER MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BrowserManager:
    def __init__(self, config: dict):
        self.headless = config.get("headless", True)
        self.proxies = config.get("proxies", [])
        self._proxy_idx = 0
        self.timeout = config.get("page_timeout", 30)

    def _next_proxy(self) -> Optional[str]:
        if not self.proxies: return None
        p = self.proxies[self._proxy_idx % len(self.proxies)]
        self._proxy_idx += 1
        return p

    def create_driver(self, capture_network=False) -> webdriver.Chrome:
        """
        Create a Chrome driver. Strategy (in order):
          1. Selenium Manager (built into Selenium 4.6+) — auto-matches Chrome version
          2. webdriver-manager — fallback, but pin to a recent stable
          3. System chromedriver — last resort

        FIX (v3.1): Previously used webdriver-manager as primary, which pinned
        chromedriver 147 against Chrome 148, causing 100% of checks to fail with
        "session not created: This version of ChromeDriver only supports Chrome 148".
        Selenium Manager is now Selenium's official driver resolver and matches
        the installed browser automatically.
        """
        ua = rand_ua()
        proxy = self._next_proxy()

        # v4.4.0: each strategy gets a FRESH Options object. Selenium Manager
        # MUTATES the options it's given (it stamps the browser binary it
        # resolved into options.binary_location). With a shared object,
        # strategy 1's browser choice leaked into strategy 2, pairing
        # webdriver-manager's chromedriver with Selenium Manager's Chrome —
        # a guaranteed version mismatch whenever the two resolvers disagree.
        def _build_opts() -> Options:
            opts = Options()
            if self.headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument(f"--user-agent={ua}")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-infobars")
            # Reduce noisy warnings/banners on real devices
            opts.add_argument("--lang=en-US")
            opts.add_argument("--disable-features=Translate,InterestFeedContentSuggestions")
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)
            if proxy:
                opts.add_argument(f"--proxy-server={proxy}")
            if capture_network:
                opts.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
            return opts

        driver = None
        last_err = None

        # ── Strategy 0 (v4.4.0): explicit env overrides ──
        # VISA_CHROME_BINARY / VISA_CHROMEDRIVER pin the exact browser and
        # driver. Deterministic escape hatch for containers/CI where the
        # auto-resolvers pick mismatched versions (e.g. a stale chromedriver
        # on PATH next to a Playwright-managed Chromium).
        env_binary = os.environ.get("VISA_CHROME_BINARY", "").strip()
        env_driver = os.environ.get("VISA_CHROMEDRIVER", "").strip()
        if env_binary or env_driver:
            try:
                from selenium.webdriver.chrome.service import Service as ChromeService
                opts = _build_opts()
                if env_binary:
                    opts.binary_location = env_binary
                if env_driver:
                    driver = webdriver.Chrome(
                        service=ChromeService(executable_path=env_driver), options=opts)
                else:
                    driver = webdriver.Chrome(options=opts)
                log.debug(f"Driver: env override (binary={env_binary or 'auto'}, "
                          f"driver={env_driver or 'auto'})")
            except Exception as e:
                last_err = e
                log.warning(f"Env-override driver failed: {str(e)[:160]}")

        # ── Strategy 1: Selenium Manager (Selenium 4.6+) ──
        # No service= argument means Selenium auto-resolves the driver matching
        # the installed Chrome browser. This is the only strategy that works
        # reliably across Chrome auto-updates.
        if driver is None:
            try:
                driver = webdriver.Chrome(options=_build_opts())
                log.debug("Driver: Selenium Manager (auto-resolved)")
            except Exception as e:
                last_err = e
                log.warning(f"Selenium Manager failed: {str(e)[:160]}")

        # ── Strategy 2: webdriver-manager fallback ──
        if driver is None:
            try:
                from selenium.webdriver.chrome.service import Service as ChromeService
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                service = ChromeService(executable_path=driver_path)
                driver = webdriver.Chrome(service=service, options=_build_opts())
                log.info(f"Driver: webdriver-manager fallback ({driver_path})")
            except Exception as e:
                last_err = e
                log.warning(f"webdriver-manager fallback failed: {str(e)[:160]}")

        if driver is None:
            raise RuntimeError(
                f"Could not create Chrome driver. Last error: {last_err}. "
                f"Make sure Chrome/Chromium is installed and matches your "
                f"selenium version (>=4.6 recommended). In containers, pin "
                f"VISA_CHROME_BINARY and VISA_CHROMEDRIVER env vars."
            )

        # Apply stealth patches
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = { runtime: {} };
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (params) =>
                        params.name === 'notifications'
                            ? Promise.resolve({state: Notification.permission})
                            : originalQuery(params);
                """
            })
        except Exception:
            pass  # CDP commands may not work in all configurations

        driver.set_page_load_timeout(self.timeout)
        driver.implicitly_wait(5)
        return driver

    def restore_cookies(self, driver, cookies: list, domain: str):
        """Restore saved session cookies."""
        driver.get(f"https://{domain}")
        time.sleep(1)
        for cookie in cookies:
            try:
                # Remove problematic fields
                for key in ["sameSite", "expiry", "httpOnly", "secure"]:
                    cookie.pop(key, None)
                driver.add_cookie(cookie)
            except:
                pass
        driver.refresh()
        time.sleep(2)

    def wait_for_spa(self, driver, max_seconds: int = 25, min_text_length: int = 200) -> bool:
        """
        Wait for a SPA (Nuxt/React/Vue) to hydrate before grabbing the DOM.

        Why this exists: VFS Global is a Nuxt SPA. The initial HTML is just a
        loading spinner inside `<div id="__nuxt">`. The previous calibrator did
        `time.sleep(6)` and grabbed the source — yielding text_length=34 across
        all 78 countries because Nuxt hadn't hydrated yet.

        Strategy: poll for either of these signals (whichever first):
          - <body> textContent length > min_text_length (real content rendered)
          - networkIdle for ~1s (no XHR in-flight)
          - common content markers visible (forms, buttons, calendar elements)

        Returns True if hydrated, False if timed out (still returns the page).
        """
        start = time.time()
        deadline = start + max_seconds
        last_len = 0
        stable_count = 0

        while time.time() < deadline:
            try:
                # Quick JS probe: how much real text is on the page?
                text_len = driver.execute_script("return (document.body && document.body.innerText) ? document.body.innerText.length : 0;")
                visible_inputs = driver.execute_script("return document.querySelectorAll('input,select,button,a[href],form').length;")
                doc_state = driver.execute_script("return document.readyState;")

                # Hydrated heuristic: meaningful content + interactive elements + ready
                if text_len >= min_text_length and visible_inputs >= 3 and doc_state == "complete":
                    # One more confirm: text length stable across two polls (no flicker)
                    if last_len > 0 and abs(text_len - last_len) < 50:
                        stable_count += 1
                        if stable_count >= 2:
                            return True
                    last_len = text_len
                else:
                    last_len = text_len
                    stable_count = 0
            except Exception:
                pass
            time.sleep(0.7)

        # Timed out — return whatever we have
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LAYER 1: API INTERCEPTOR
#  Capture XHR/fetch calls the frontend makes to get appointment data.
#  This is the most reliable method — no DOM parsing needed.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class APIInterceptor:
    """
    Opens a page with network logging enabled, captures all API calls,
    identifies appointment-related endpoints, and extracts slot data.
    """

    # Keywords that suggest an API response contains appointment data.
    # NOTE (v3.1): only match when keyword appears in the URL *path*, not in
    # query strings or hostnames. Many tracking/analytics URLs contain
    # "calendar" or "schedule" in query params and were being misclassified.
    APPOINTMENT_KEYWORDS = [
        "appointment", "/slot", "/slots", "available", "/schedule",
        "/calendar", "timeslot", "/booking", "availability", "/center",
    ]

    # Hosts that are NEVER appointment APIs — cuts false positives by 90%+
    BLOCKED_HOSTS = (
        "google-analytics.com", "googletagmanager.com", "doubleclick.net",
        "facebook.com", "facebook.net", "google.com", "gstatic.com",
        "cloudflare.com", "cloudflareinsights.com", "hotjar.com", "newrelic.com",
        "sentry.io", "bugsnag.com", "datadog", "segment.io", "intercom.io",
        "mixpanel.com", "fullstory.com", "linkedin.com", "twitter.com", "x.com",
        "youtube.com", "ytimg.com", "fonts.gstatic", "cdnjs.cloudflare",
        "ssl.gstatic.com", "stripe.com", "recaptcha.net",
    )

    DATE_PATTERNS = [
        re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b'),                  # 2026-05-15
        re.compile(r'\b(\d{2})/(\d{2})/(\d{4})\b'),                  # 15/05/2026
        re.compile(r'\b(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\b'),     # 15 May 2026
    ]

    # Field names whose values should NEVER be considered appointment dates,
    # even if they match a date regex. These were the source of false positives
    # (cookie expiries, build timestamps, copyright years registered as "slots").
    NOISY_DATE_KEYS = {
        "created_at", "createdat", "created", "updated_at", "updatedat", "updated",
        "modified_at", "modifiedat", "modified", "last_modified", "lastmodified",
        "expires", "expiry", "expires_at", "expiresat", "expiration", "exp",
        "issued_at", "issuedat", "issued", "iat", "nbf",
        "build_date", "builddate", "version_date", "release_date",
        "copyright_year", "copyrightyear", "year", "birthdate", "dob",
        "deleted_at", "archived_at",
    }

    # Field names that strongly suggest the value IS an appointment date.
    APPOINTMENT_KEYS = {
        "date", "appointment_date", "appointmentdate", "available_date", "availabledate",
        "slot_date", "slotdate", "startdate", "start_date", "appointment", "slot",
        "available_on", "availableon", "scheduled_for", "scheduledfor", "booking_date",
        "bookingdate", "earliest", "next_available", "nextavailable",
    }

    def __init__(self, browser_mgr: BrowserManager, db: Database):
        self.browser = browser_mgr
        self.db = db
        self.log = logging.getLogger("layer1.api")

    def intercept(self, url: str, country: str, city: str,
                  visa_types: list, wait_seconds: int = 10) -> list[dict]:
        """
        Load a page, capture all network requests, return any that
        look like appointment API responses.
        """
        driver = None
        api_calls = []

        try:
            driver = self.browser.create_driver(capture_network=True)
            self.log.info(f"Loading {url} with network capture...")
            driver.get(url)

            # Wait for SPA hydration (Nuxt/React/Vue) — was a hardcoded sleep before
            hydrated = self.browser.wait_for_spa(driver, max_seconds=max(wait_seconds, 20))
            if not hydrated:
                self.log.warning(f"  SPA did not hydrate within timeout (still capturing what we have)")

            # Scroll to trigger lazy loading after hydration
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
                time.sleep(1.5)
                driver.execute_script("window.scrollTo(0, 0)")
                time.sleep(0.8)
            except Exception:
                pass

            # Extract network logs
            try:
                logs = driver.get_log("performance")
            except:
                self.log.warning("Network logging not available")
                return []

            for entry in logs:
                try:
                    msg = json.loads(entry["message"])["message"]

                    # Capture responses
                    if msg["method"] == "Network.responseReceived":
                        resp = msg["params"]["response"]
                        req_url = resp["url"]
                        mime = resp.get("mimeType", "")

                        # Filter: skip blocked tracking/analytics hosts entirely
                        host = ""
                        try:
                            host = urlparse(req_url).hostname or ""
                        except Exception:
                            host = ""
                        if any(h in host for h in self.BLOCKED_HOSTS):
                            continue

                        # Only interested in JSON/API responses
                        if "json" in mime or "javascript" in mime or "/api/" in req_url:
                            # Match keywords against URL *path* only (not querystring/host)
                            try:
                                path_lower = (urlparse(req_url).path or "").lower()
                            except Exception:
                                path_lower = req_url.lower()

                            if any(kw in path_lower for kw in self.APPOINTMENT_KEYWORDS):
                                # Try to get response body
                                try:
                                    req_id = msg["params"]["requestId"]
                                    body = driver.execute_cdp_cmd(
                                        "Network.getResponseBody",
                                        {"requestId": req_id}
                                    )
                                    body_text = body.get("body", "")

                                    api_calls.append({
                                        "url": req_url,
                                        "mime": mime,
                                        "body": body_text[:5000],
                                        "status": resp.get("status", 0),
                                    })
                                    self.log.info(f"  Captured API: {req_url[:80]}")
                                except:
                                    # Response body may have been evicted
                                    api_calls.append({
                                        "url": req_url,
                                        "mime": mime,
                                        "body": "",
                                        "status": resp.get("status", 0),
                                    })

                except (json.JSONDecodeError, KeyError):
                    continue

            self.log.info(f"  Captured {len(api_calls)} appointment-related API calls")
            return api_calls

        except Exception as e:
            self.log.error(f"API interception failed: {e}")
            return []
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def extract_slots_from_api(self, api_data: list[dict], country: str,
                                city: str, visa_types: list,
                                booking_url: str) -> list[SlotInfo]:
        """Parse captured API responses for appointment dates."""
        slots = []

        for call in api_data:
            body = call.get("body", "")
            if not body:
                continue

            # Try JSON parse
            try:
                data = json.loads(body)
            except:
                # Try to find JSON in the response
                json_match = re.search(r'(\[.*\]|\{.*\})', body, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                    except:
                        continue
                else:
                    continue

            # Extract dates from the parsed data
            dates = self._extract_dates_recursive(data)
            for d in dates:
                for vtype in visa_types:
                    slots.append(SlotInfo(
                        country=country,
                        city=city,
                        visa_type=vtype,
                        date=d["date"],
                        time_slot=d.get("time", "Check portal"),
                        portal=call.get("url", "").split("/")[2] if "/" in call.get("url", "") else "API",
                        booking_url=booking_url,
                        detection_method="api",
                        confidence="high",
                        raw_data=json.dumps({"api_url": call["url"], "entry": d})[:500],
                    ))

        return slots

    def _extract_dates_recursive(self, data, depth=0, parent_key="") -> list[dict]:
        """
        Recursively walk JSON to find date-like values that look like real
        appointment slots — not build timestamps, cookie expiries, or copyright years.

        Rules (v3.1):
        - Only emit a date if it's parseable, in the future, and within 365 days.
        - Skip values whose parent key looks like a metadata timestamp
          (created_at, expiry, build_date, etc).
        - Prefer dates whose parent key clearly indicates appointment context.
        """
        if depth > 12:
            return []

        results = []
        pk = parent_key.lower().replace("-", "_")

        if isinstance(data, dict):
            for key, val in data.items():
                k = str(key).lower().replace("-", "_")

                # Skip noisy metadata fields entirely
                if k in self.NOISY_DATE_KEYS:
                    continue

                # If this dict itself has an appointment-flavored key, capture
                if k in self.APPOINTMENT_KEYS:
                    if isinstance(val, str) and self._looks_like_date(val):
                        d = self._normalize_date(val)
                        if d and self._is_plausible_appointment_date(d):
                            entry = {"date": d, "_source_key": k}
                            # Try to find an associated time
                            for tk in ("time", "slot_time", "starttime", "start_time", "time_slot", "timeslot"):
                                if tk in {kk.lower().replace("-","_") for kk in data.keys()}:
                                    tv = next((data[kk] for kk in data.keys() if kk.lower().replace("-","_") == tk), None)
                                    if tv:
                                        entry["time"] = str(tv)
                                        break
                            results.append(entry)
                else:
                    # Recurse, passing the key as parent context
                    results.extend(self._extract_dates_recursive(val, depth+1, k))

        elif isinstance(data, list):
            for item in data:
                results.extend(self._extract_dates_recursive(item, depth+1, parent_key))

        elif isinstance(data, str):
            # Bare strings (not in dict context) — only accept if parent key is appointment-y
            if pk in self.APPOINTMENT_KEYS and self._looks_like_date(data):
                d = self._normalize_date(data)
                if d and self._is_plausible_appointment_date(d):
                    results.append({"date": d, "_source_key": pk})

        return results

    def _looks_like_date(self, s: str) -> bool:
        if not isinstance(s, str) or len(s) < 8 or len(s) > 30:
            return False
        return any(p.search(s) for p in self.DATE_PATTERNS)

    def _normalize_date(self, s: str) -> Optional[str]:
        """Parse a date-ish string and return ISO YYYY-MM-DD, or None."""
        s = s.strip()
        # Try ISO first (most common in modern APIs)
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                    "%d %b %Y", "%d %B %Y"):
            try:
                # Strip timezone suffix variants for parsing
                s_clean = s.replace("Z", "").split("+")[0].split(".")[0] if "T" in s else s
                dt = datetime.strptime(s_clean, fmt.replace("Z","").replace(".%f",""))
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        # Last resort: extract first ISO date substring
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
        if m:
            try:
                dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None
        return None

    def _is_plausible_appointment_date(self, iso_date: str) -> bool:
        """A real appointment date is in the future and within ~1 year."""
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            delta = (dt - today).days
            # Allow today through 365 days out (some portals show same-day slots)
            return 0 <= delta <= 365
        except (ValueError, TypeError):
            return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LAYER 3: PAGE-CHANGE DETECTION
#  Hash the appointment page content. If the hash changes, something changed.
#  Works for EVERY portal, zero selector dependency.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PageChangeDetector:
    """
    The nuclear fallback that works for everything.
    Doesn't try to parse anything — just detects when a page changes.

    Strategy:
    1. First visit: store a hash of the page's "appointment-relevant" text
    2. Subsequent visits: compare hash
    3. If changed: alert user that something changed on the page
    4. Filter out noise (timestamps, session tokens) before hashing
    """

    # Patterns to strip before hashing (these change on every page load)
    NOISE_PATTERNS = [
        re.compile(r'\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?'),  # timestamps
        re.compile(r'[a-f0-9]{32,}'),                              # session tokens
        re.compile(r'csrf[^"]*"[^"]*"'),                           # CSRF tokens
        re.compile(r'nonce="[^"]*"'),                               # nonces
        re.compile(r'cache-\d+'),                                   # cache busters
        re.compile(r'__cf_\w+'),                                    # cloudflare stuff
        re.compile(r'_ga=[^;]+'),                                   # GA cookies
        # v3.2.1 additions: cosmetic / rotating content that triggered
        # false-positive page-change alerts in the v3.2 calibration run
        re.compile(r'(?i)cookies?\s+(policy|preferences?|settings?|consent)'),
        re.compile(r'(?i)accept\s+(all|cookies?)'),
        # v3.2.2: fixed bare-© case — VFS footers say "© 2026 VFS Global",
        # not "Copyright © 2026". v3.2.1 required literal "copyright".
        re.compile(r'(?i)(copyright\s*)?[\u00a9]\s*\d{4}'),
        re.compile(r'(?i)all rights reserved'),
        re.compile(r'(?i)last\s+updated[^.]{0,40}'),
        re.compile(r'(?i)visitor\s+count[^.]{0,30}'),
        re.compile(r'\b\d+\s+(views?|visitors?|online\s+users?)\b'),
        re.compile(r'(?i)build\s*(?:id|version|hash)?\s*[:#]?\s*[a-f0-9]{6,}'),
        re.compile(r'(?i)\bv\d+\.\d+(\.\d+)?(-[a-z0-9]+)?\b'),     # v1.2.3-abc
        re.compile(r'(?i)session\s*id[^.]{0,40}'),
        re.compile(r'\b\d{10,13}\b'),                                # unix timestamps
        # v3.2.2: Nuxt/React generated dynamic IDs (the smoking gun in
        # v3.2 production: 200 page_changed events per cycle were caused
        # by hash mismatches on stable content. Aggressive ID stripping.)
        re.compile(r'\bid="[a-z]+-[a-z0-9]{6,}"'),                    # id="some-abc1234"
        re.compile(r'\b__nuxt[_-]\w+'),
        re.compile(r'\bdata-v-[a-f0-9]{6,}'),                         # Vue scoped CSS
        re.compile(r'\baria-(labelledby|describedby|controls)="[a-z0-9-]{6,}"'),
    ]

    def __init__(self, browser_mgr: BrowserManager, db: Database):
        self.browser = browser_mgr
        self.db = db
        self.log = logging.getLogger("layer3.pagechange")

    def check(self, url: str, country: str, city: str,
              visa_types: list) -> CheckResult:
        t0 = time.time()
        hash_key = f"{country}|{city}|{url}"

        driver = None
        try:
            driver = self.browser.create_driver()
            driver.get(url)

            # Wait for SPA hydration before hashing — otherwise hash compares
            # the loading-spinner state of the page, not real content.
            self.browser.wait_for_spa(driver, max_seconds=20)
            # Tiny jitter so we don't all hit at the same moment
            time.sleep(random.uniform(0.5, 1.5))

            # Get page content
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            # Remove scripts, styles, and other non-content elements
            for tag in soup.select("script, style, noscript, iframe, link, meta"):
                tag.decompose()

            text = soup.get_text(" ", strip=True)
            text_lower = text.lower()

            # Check for Cloudflare
            if self._is_cloudflare(driver, text_lower):
                self.log.warning(f"  Cloudflare block on {country}/{city}")
                time.sleep(8)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                for tag in soup.select("script, style, noscript"):
                    tag.decompose()
                text = soup.get_text(" ", strip=True)
                text_lower = text.lower()

                if self._is_cloudflare(driver, text_lower):
                    return CheckResult(country, city, "page_change", "captcha", [],
                                     error="Cloudflare block persists",
                                     duration_ms=int((time.time()-t0)*1000),
                                     method="page_change")

            # Strip noise before hashing
            clean_text = self._strip_noise(text)
            current_hash = hashlib.sha256(clean_text.encode()).hexdigest()

            # v3.2.2: read full prior state (hash + preview + noise count)
            # in one query instead of separate calls.
            prev_state = self.db.get_page_state(hash_key)

            if prev_state is None or not prev_state.get("hash"):
                # First time seeing this page — store baseline (no slots)
                self.db.set_page_hash(hash_key, current_hash, clean_text)
                self.log.info(f"  Baseline stored for {country}/{city}")
                return CheckResult(country, city, "page_change", "baseline", [],
                                 duration_ms=int((time.time()-t0)*1000),
                                 method="page_change")

            prev_hash = prev_state["hash"]
            prev_preview = prev_state["preview"]
            consecutive_changes = prev_state["consecutive_changes"]

            if current_hash == prev_hash:
                # Hash matches — clear any stale noise marker on this country
                if consecutive_changes > 0:
                    self.db.reset_page_noise(hash_key)
                return CheckResult(country, city, "page_change", "no_change", [],
                                 duration_ms=int((time.time()-t0)*1000),
                                 method="page_change")

            # ── Hash changed — DELTA classification (v3.2.2 core fix) ──
            # The previous code classified the entire post-noise page text on
            # every hash change. Result: any VFS landing page containing
            # "book" or "available" as static UI copy fired slots_likely on
            # cosmetic mutations. The fix is to compute a text DELTA between
            # prev_preview and current text, and classify ONLY the diff.
            delta_text = self._compute_delta(prev_preview, clean_text)

            # Strip noise from the delta itself (some noise patterns only
            # surface in the diff context, e.g. timestamps that flip second-
            # by-second).
            delta_clean = self._strip_noise(delta_text).strip()

            # Persistent-noise marker: each consecutive cycle that produces a
            # hash change without resolving makes the country "noisier", which
            # raises the bar for slot emission. Auto-decays when a clean
            # cycle clears the marker.
            new_count = consecutive_changes + 1
            is_noisy = new_count >= 2

            # Update baseline + noise counter atomically
            self.db.set_page_hash(hash_key, current_hash, clean_text,
                                  consecutive_changes=new_count, mark_change=True)

            # Trivial diff — likely pure cosmetic mutation. Suppress alert.
            if len(delta_clean) < 30:
                self.log.info(
                    f"  Page changed for {country}/{city} but delta is trivial "
                    f"({len(delta_clean)} chars, {new_count} consecutive)"
                )
                return CheckResult(country, city, "page_change", "no_change", [],
                                 duration_ms=int((time.time()-t0)*1000),
                                 method="page_change")

            # Cap delta size — beyond 8KB, fall back to whole-page classification
            # (fundamental site rebuild, not cosmetic noise)
            classify_text = delta_clean.lower()
            if len(classify_text) > 8000:
                self.log.info(f"  Large delta ({len(classify_text)} chars) — using whole-page classifier")
                classify_text = text_lower

            # Classify the delta
            change_type = self._classify_change(
                classify_text,
                strict_mode=is_noisy,  # noisy countries need stronger signal
            )

            if change_type == "slots_likely":
                self.log.info(
                    f"  🎯 PAGE CHANGED (slots likely!) for {country}/{city} "
                    f"[delta={len(delta_clean)}c, consecutive={new_count}, "
                    f"strict={is_noisy}]"
                )
                slots = []
                for vtype in visa_types:
                    slots.append(SlotInfo(
                        country=country, city=city,
                        visa_type=vtype,
                        date="Check portal NOW",
                        time_slot="Page content changed — slots may be available",
                        portal="Page Monitor",
                        booking_url=url,
                        detection_method="page_change",
                        confidence="medium",
                        raw_data=(
                            f"hash_changed: {prev_hash[:8]}->{current_hash[:8]} "
                            f"delta_chars={len(delta_clean)} "
                            f"noisy={is_noisy} sample={delta_clean[:120]!r}"
                        )[:500],
                    ))
                return CheckResult(country, city, "page_change", "page_changed", slots,
                                 duration_ms=int((time.time()-t0)*1000),
                                 method="page_change")
            else:
                self.log.info(
                    f"  Page changed for {country}/{city} but classified as "
                    f"{change_type} (delta={len(delta_clean)}c, "
                    f"consecutive={new_count}, strict={is_noisy})"
                )
                return CheckResult(country, city, "page_change", "no_change", [],
                                 duration_ms=int((time.time()-t0)*1000),
                                 method="page_change")

        except Exception as e:
            return CheckResult(country, city, "page_change", "error", [],
                             error=str(e)[:300],
                             duration_ms=int((time.time()-t0)*1000),
                             method="page_change")
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def _compute_delta(self, prev_text: str, current_text: str) -> str:
        """v3.2.2: compute the line-level textual difference between the
        previous baseline preview and the current page text. Returns just
        the added/changed lines, joined by newlines.

        Uses difflib.ndiff under the hood. Caps prev/current at 12000 chars
        each to bound runtime — the diff is meant to surface what's NEW in
        the page, not what got removed (that's already gone).
        """
        import difflib
        # Normalize whitespace so trivial spacing changes don't show as diffs
        def _norm(s: str) -> list[str]:
            return [ln.strip() for ln in re.split(r'(?<=[.!?])\s+|\n+', s[:12000]) if ln.strip()]
        prev_lines = _norm(prev_text or "")
        curr_lines = _norm(current_text or "")
        # Use SequenceMatcher for O(n+m) instead of ndiff's O(n*m)
        sm = difflib.SequenceMatcher(a=prev_lines, b=curr_lines, autojunk=False)
        added = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("insert", "replace"):
                added.extend(curr_lines[j1:j2])
        return " ".join(added)

    def _is_cloudflare(self, driver, text_lower: str) -> bool:
        try:
            title = driver.title.lower()
            return ("just a moment" in title or
                    "cloudflare" in text_lower[:500] or
                    "challenge-platform" in driver.page_source[:2000].lower())
        except:
            return False

    def _strip_noise(self, text: str) -> str:
        """Remove dynamic content that changes every page load."""
        result = text
        for pattern in self.NOISE_PATTERNS:
            result = pattern.sub("", result)
        # Also strip pure whitespace differences
        result = " ".join(result.split())
        return result

    def _classify_change(self, text_lower: str, strict_mode: bool = False) -> str:
        """
        Classify whether a page change is likely appointment-related.

        v3.2.1: weighted signals — a single weak match no longer flips the
        verdict. We need either a strong positive (specific phrase) OR
        multiple weak positives, AND no negative override.

        v3.2.2: `strict_mode` raises the bar for countries flagged as noisy.
        Strict mode requires 3 weak positives instead of 2, AND ignores
        weak negatives below 3 hits. This stops a country that's been
        firing page_changed every cycle from emitting more slots until its
        text genuinely changes.
        """
        strong_positive = [
            "appointment available", "appointments available",
            "slot available", "slots available",
            "select date and time", "click to book your slot",
            "available appointment date", "earliest available",
            "book your appointment now", "new dates added",
            "now accepting appointments",
        ]
        weak_positive = [
            "available", "open slot", "book now", "select date",
            "new dates", "click to book", "schedule now",
        ]
        strong_negative = [
            "no appointment available", "no slots available",
            "no appointments available",
            "fully booked", "all slots are booked",
            "system down", "maintenance window", "service unavailable",
            "currently no appointments",
        ]
        weak_negative = [
            "no appointment", "no slots", "not available",
            "no dates", "temporarily unavailable", "maintenance",
        ]

        strong_pos_hits = sum(1 for p in strong_positive if p in text_lower)
        weak_pos_hits = sum(1 for p in weak_positive if p in text_lower)
        strong_neg_hits = sum(1 for p in strong_negative if p in text_lower)
        weak_neg_hits = sum(1 for p in weak_negative if p in text_lower)

        # Strong negative dominates — explicit "no slots" message
        if strong_neg_hits >= 1:
            return "still_no_slots"
        # Strong positive is enough on its own (even in strict mode)
        if strong_pos_hits >= 1:
            return "slots_likely"
        # Multiple weak negatives also count as "still no slots"
        if weak_neg_hits >= 2:
            return "still_no_slots"
        # v3.2.2: strict_mode raises threshold from 2 to 3 weak positives.
        # Stops repeat-firing countries from emitting on every cycle.
        threshold = 3 if strict_mode else 2
        if weak_pos_hits >= threshold and weak_neg_hits == 0:
            return "slots_likely"
        return "unknown_change"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PORTAL DEFINITIONS — Registry-driven, multi-processor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
#  Centers are loaded from `centers.json` (a structured registry covering
#  VFS Global, BLS International, TLScontact, CGI Federal/USTravelDocs, CKGS,
#  and embassy-direct flows for India-outbound applications).
#
#  Each center has: destination_country, destination_iso3, processor,
#  appointment_url, indian_cities[], visa_types[], enabled, priority.
#
#  Backward compatibility: if centers.json is missing, the legacy hard-coded
#  dicts below are used. The legacy URL pattern was wrong (it produced
#  `visa.vfsglobal.com/{slug}-india/en/book-an-appointment` which 404s — real
#  pattern is `visa.vfsglobal.com/ind/en/{iso3}/`). The registry uses the
#  correct pattern. Calibration must be re-run after upgrading.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CENTERS_REGISTRY: dict = {}   # populated by load_centers_registry()
COUNTRY_INDEX: dict[str, dict] = {}   # country_name (lower) → center dict

def load_centers_registry(path: str = "centers.json") -> dict:
    """Load the multi-processor centers registry. Returns {} if missing."""
    global CENTERS_REGISTRY, COUNTRY_INDEX
    p = Path(path)
    if not p.exists():
        # try sibling of this script
        p = Path(__file__).parent / path
    if not p.exists():
        return {}
    try:
        # v3.2.2c: utf-8-sig strips optional BOM (PowerShell-friendly)
        with open(p, encoding="utf-8-sig") as f:
            CENTERS_REGISTRY = json.load(f)
        # v4.4.0: reset the index on (re)load — reloading after an edit
        # (select-countries) used to leave stale winners in place.
        COUNTRY_INDEX.clear()
        # Build name -> center index for fast lookup. Prefer the highest-
        # priority enabled entry when multiple processors serve one country.
        prio_rank = {"high": 3, "medium": 2, "low": 1}
        for c in CENTERS_REGISTRY.get("centers", []):
            name = (c.get("destination_country") or "").strip().lower()
            if not name:
                continue
            existing = COUNTRY_INDEX.get(name)
            if existing is None:
                COUNTRY_INDEX[name] = c
                continue
            # Prefer enabled over disabled; then higher priority
            if c.get("enabled") and not existing.get("enabled"):
                COUNTRY_INDEX[name] = c
            elif c.get("enabled") == existing.get("enabled"):
                if prio_rank.get(c.get("priority"), 0) > prio_rank.get(existing.get("priority"), 0):
                    COUNTRY_INDEX[name] = c
        return CENTERS_REGISTRY
    except Exception as e:
        logging.getLogger("registry").warning(f"Failed to load {p}: {e}")
        return {}

# Legacy fallback dicts (used only when centers.json is missing)
VFS_COUNTRIES = {
    "United Kingdom": "gbr", "Canada": "can", "Australia": "aus",
    "New Zealand": "nzl", "France": "fra", "Germany": "deu",
    "Italy": "ita", "Netherlands": "nld", "Switzerland": "che",
    "Austria": "aut", "Belgium": "bel", "Luxembourg": "lux",
    "Ireland": "irl", "Sweden": "swe", "Norway": "nor",
    "Denmark": "dnk", "Finland": "fin", "Iceland": "isl",
    "Estonia": "est", "Latvia": "lva", "Lithuania": "ltu",
    "Greece": "grc", "Croatia": "hrv", "Slovenia": "svn",
    "Cyprus": "cyp", "Malta": "mlt", "Poland": "pol",
    "Czech Republic": "cze", "Hungary": "hun", "Romania": "rou",
    "Bulgaria": "bgr", "Serbia": "srb", "Portugal": "prt",
    "Japan": "jpn", "South Korea": "kor", "Singapore": "sgp",
    "Thailand": "tha", "Vietnam": "vnm", "Malaysia": "mys",
    "Indonesia": "idn", "Philippines": "phl", "Taiwan": "twn",
    "China": "chn",
    "United Arab Emirates": "are", "Saudi Arabia": "sau",
    "Qatar": "qat", "Bahrain": "bhr", "Kuwait": "kwt",
    "Oman": "omn", "Israel": "isr", "Turkey": "tur",
    "Jordan": "jor", "Lebanon": "lbn",
    "South Africa": "zaf", "Egypt": "egy", "Kenya": "ken",
    "Morocco": "mar", "Nigeria": "nga",
    "Mexico": "mex", "Brazil": "bra", "Argentina": "arg",
    "Chile": "chl", "Colombia": "col", "Peru": "per",
    "Russia": "rus", "Kazakhstan": "kaz", "Uzbekistan": "uzb",
    "Georgia": "geo", "Armenia": "arm", "Azerbaijan": "aze",
}

BLS_COUNTRIES = {
    # v3.2.1: only the two BLS countries that have verified India contracts.
    # v3.2 included Portugal, Algeria, Tunisia, Mozambique here based on a
    # `india.bls{country}visa.com` pattern that doesn't actually exist for
    # any of those four. Portugal is VFS Global; the others have no online
    # portal at all (embassy-direct).
    "Spain":       "https://india.blsspainvisa.com/",
    "Slovakia":    "https://blsslovakiavisa.com/india/",
}

TLS_COUNTRIES: dict = {}  # No active India contracts as of May 2026

CGI_COUNTRIES = {
    "United States of America": "https://www.usvisascheduling.com/",
}

CKGS_COUNTRIES: dict = {}  # CKGS handles inverse direction (US-side OCI/passport)

# Try to load the registry on module import
try:
    load_centers_registry()
except Exception:
    pass


def get_appointment_url(country: str) -> tuple[str, str]:
    """Return (url, portal_type) for a country. Registry first, fall back to legacy dicts."""
    # Registry path
    rec = COUNTRY_INDEX.get((country or "").strip().lower())
    if rec and rec.get("appointment_url"):
        proc = rec.get("processor", "unknown")
        portal_short = {
            "vfs_global": "vfs",
            "bls_international": "bls",
            "tls_contact": "tls",
            "cgi_federal": "cgi",
            "ckgs": "ckgs",
            "embassy_direct": "embassy",
            "indian_visa_online": "ivo",
        }.get(proc, proc)
        return rec["appointment_url"], portal_short

    # Legacy fallback
    if country in BLS_COUNTRIES:
        return BLS_COUNTRIES[country], "bls"
    if country in TLS_COUNTRIES:
        return TLS_COUNTRIES[country], "tls"
    if country in CGI_COUNTRIES:
        return CGI_COUNTRIES[country], "cgi"
    if country in VFS_COUNTRIES:
        iso3 = VFS_COUNTRIES[country]
        # NOTE: real VFS URL pattern is /ind/en/{iso3}/, NOT /{slug}-india/...
        return f"https://visa.vfsglobal.com/ind/en/{iso3}/", "vfs"
    return "", "unknown"


def get_processor_metadata(country: str) -> dict:
    """Return processor metadata (wait_strategy, auth_required, type, notes) for a country."""
    rec = COUNTRY_INDEX.get((country or "").strip().lower())
    if not rec:
        return {"wait_strategy": "spa", "auth_required": False, "type": "unknown"}
    proc_id = rec.get("processor")
    procs = CENTERS_REGISTRY.get("processors", {})
    return procs.get(proc_id, {"wait_strategy": "spa", "auth_required": False, "type": "unknown"})


def list_supported_countries() -> list[str]:
    """All destination country names from registry + legacy dicts."""
    names = set()
    for c in CENTERS_REGISTRY.get("centers", []):
        if c.get("destination_country"):
            names.add(c["destination_country"])
    names.update(VFS_COUNTRIES.keys())
    names.update(BLS_COUNTRIES.keys())
    names.update(TLS_COUNTRIES.keys())
    names.update(CGI_COUNTRIES.keys())
    return sorted(names)


def get_indian_cities_for(country: str) -> list[str]:
    """Indian cities where this destination has a VAC."""
    rec = COUNTRY_INDEX.get((country or "").strip().lower())
    if rec and rec.get("indian_cities"):
        return list(rec["indian_cities"])
    return ["New Delhi"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VFS JWT SESSION (v3.2.1)
#  The lift-api.vfsglobal.com endpoints are JWT-protected behind Cloudflare.
#  Direct anonymous fetch returns 403. Reference impl pattern (per
#  github.com/khanrn/vfs-slots-api-monitor): open the country's portal in a
#  real browser, harvest the Authorization JWT from network logs or
#  localStorage, then replay /appointment/slots with country-specific params.
#
#  This class manages that lifecycle:
#    - acquire(country): spin up Selenium, navigate to portal, capture JWT
#    - replay(endpoint, params): make authenticated request with cached JWT
#    - JWT cached in-memory for ~25 min (typical token TTL is shorter)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class VFSJWTSession:
    """Acquire and cache a VFS lift-api JWT via headless browser."""

    JWT_TTL_SECONDS = 25 * 60  # cache for 25 minutes
    JWT_HOST_HINTS = ("lift-api.vfsglobal.com",)
    # v3.2.2: after this many consecutive harvest failures for a country,
    # short-circuit further attempts and log loudly. Resets on next success
    # or when the country's row is re-calibrated.
    FAILURE_CIRCUIT_BREAKER = 6

    def __init__(self, browser_mgr: "BrowserManager"):
        self.browser = browser_mgr
        # v4.4.0: per-country token cache. The old single-slot cache
        # (_jwt/_jwt_country) was invalidated on every country switch, so a
        # multi-country cycle re-harvested via a fresh ~20s Selenium session
        # for each country even when its token was still valid.
        self._tokens: dict[str, tuple[str, float]] = {}  # country -> (jwt, acquired_at)
        self._lock = threading.Lock()
        # v3.2.2: track per-country consecutive harvest failures
        self._failures: dict[str, int] = {}
        self._circuit_open: set[str] = set()
        self.log = logging.getLogger("vfs_jwt")

    def get(self, country: str, portal_url: str) -> Optional[str]:
        """Return a fresh JWT, harvesting if needed. Thread-safe.

        v3.2.2: circuit-breaker — if a country has failed N times in a row,
        skip the harvest entirely and return None until something resets it.
        """
        with self._lock:
            # Circuit-open: don't even try
            if country in self._circuit_open:
                return None

            cached = self._tokens.get(country)
            if cached and (time.time() - cached[1]) < self.JWT_TTL_SECONDS:
                return cached[0]
            jwt = self._harvest(country, portal_url)
            if jwt:
                self._tokens[country] = (jwt, time.time())
                # Success — reset failure counter
                self._failures.pop(country, None)
            else:
                # Bump failure counter, possibly trip breaker
                self._failures[country] = self._failures.get(country, 0) + 1
                if self._failures[country] >= self.FAILURE_CIRCUIT_BREAKER:
                    self._circuit_open.add(country)
                    self.log.warning(
                        f"⚠ JWT CIRCUIT BREAKER OPEN for {country} after "
                        f"{self._failures[country]} consecutive harvest failures. "
                        f"Skipping JWT replay for this country until next "
                        f"calibration or successful harvest. Falling through "
                        f"to anonymous endpoints + page-change detection."
                    )
            return jwt

    def reset_circuit(self, country: Optional[str] = None):
        """v3.2.2: explicitly clear the breaker (called by selftest, calibrate)."""
        with self._lock:
            if country is None:
                self._circuit_open.clear()
                self._failures.clear()
            else:
                self._circuit_open.discard(country)
                self._failures.pop(country, None)

    def invalidate(self, country: Optional[str] = None):
        """v4.4.0: drop cached token(s) — e.g. after a 401 on replay."""
        with self._lock:
            if country is None:
                self._tokens.clear()
            else:
                self._tokens.pop(country, None)

    def health(self) -> dict:
        """v3.2.2: introspection for the `status` CLI command."""
        with self._lock:
            now = time.time()
            return {
                "cached_countries": {
                    c: round(now - acquired, 1)
                    for c, (_tok, acquired) in self._tokens.items()
                },
                "open_circuits": sorted(self._circuit_open),
                "failure_counts": dict(self._failures),
            }

    def _harvest(self, country: str, portal_url: str) -> Optional[str]:
        """Open the portal in headless Chrome and pull JWT from net or storage."""
        driver = None
        try:
            self.log.info(f"  Harvesting JWT for {country} via {portal_url}")
            driver = self.browser.create_driver(capture_network=True)
            driver.get(portal_url)
            self.browser.wait_for_spa(driver, max_seconds=20)
            time.sleep(2)

            # Method 1: scan network log for Authorization header on lift-api
            # requests. CDP gives request headers via Network.requestWillBeSent.
            try:
                logs = driver.get_log("performance")
                for entry in logs:
                    try:
                        msg = json.loads(entry["message"])["message"]
                        if msg["method"] != "Network.requestWillBeSent":
                            continue
                        req = msg["params"]["request"]
                        url = req.get("url", "")
                        if not any(h in url for h in self.JWT_HOST_HINTS):
                            continue
                        headers = req.get("headers", {})
                        # Header keys are case-insensitive; try common variants
                        for k in ("Authorization", "authorization", "AUTHORIZATION"):
                            v = headers.get(k)
                            if v and v.lower().startswith("bearer "):
                                token = v.split(None, 1)[1].strip()
                                if len(token) > 40:
                                    self.log.info(f"  ✓ JWT from net log ({len(token)} chars)")
                                    return token
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception as e:
                self.log.debug(f"  Net-log harvest failed: {e}")

            # Method 2: pull from localStorage / sessionStorage
            for storage in ("localStorage", "sessionStorage"):
                try:
                    keys = driver.execute_script(
                        f"return Object.keys(window.{storage});"
                    ) or []
                    for k in keys:
                        if not any(p in k.lower() for p in
                                   ("token", "auth", "jwt", "access", "id_token")):
                            continue
                        try:
                            val = driver.execute_script(
                                f"return window.{storage}.getItem(arguments[0]);", k
                            )
                            if not val or len(val) < 40:
                                continue
                            # Sometimes the value is a JSON blob with the
                            # actual token nested inside
                            try:
                                parsed = json.loads(val)
                                if isinstance(parsed, dict):
                                    for tk in ("token", "access_token",
                                               "accessToken", "id_token", "idToken",
                                               "jwt"):
                                        if tk in parsed and isinstance(parsed[tk], str):
                                            self.log.info(f"  ✓ JWT from {storage}.{k}.{tk}")
                                            return parsed[tk]
                            except (json.JSONDecodeError, TypeError):
                                pass
                            # Heuristic: looks like a JWT? (3 base64 segments)
                            if val.count(".") == 2 and all(
                                len(s) > 6 for s in val.split(".")
                            ):
                                self.log.info(f"  ✓ JWT from {storage}.{k}")
                                return val
                        except Exception:
                            continue
                except Exception:
                    continue

            self.log.info("  No JWT harvested (login may be required)")
            return None

        except Exception as e:
            self.log.warning(f"  JWT harvest error: {str(e)[:200]}")
            return None
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def replay(self, endpoint: str, jwt: str, params: dict,
               method: str = "GET", timeout: int = 12,
               country: Optional[str] = None) -> Optional[dict]:
        """Make an authenticated request to a VFS lift-api endpoint."""
        headers = {
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/json",
            "User-Agent": rand_ua(),
            "Origin": "https://visa.vfsglobal.com",
            "Referer": "https://visa.vfsglobal.com/",
        }
        try:
            if method.upper() == "POST":
                resp = requests.post(endpoint, json=params,
                                     headers=headers, timeout=timeout)
            else:
                resp = requests.get(endpoint, params=params,
                                    headers=headers, timeout=timeout)
            if resp.status_code == 401:
                self.log.warning("  JWT replay: 401 — token expired, will re-harvest")
                self.invalidate(country)  # force re-acquisition next call
                return None
            if resp.status_code == 403:
                self.log.debug("  JWT replay: 403 — Cloudflare or scope mismatch")
                return None
            if resp.status_code >= 400:
                self.log.debug(f"  JWT replay: {resp.status_code}")
                return None
            try:
                return {"status": resp.status_code, "body": resp.text[:8000]}
            except Exception:
                return None
        except Exception as e:
            self.log.debug(f"  JWT replay exception: {e}")
            return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  US VISA WAIT-TIME PROCESSOR (v4.1.0)
#
#  The US is a special case. Unlike VFS countries where slot calendars are
#  visible (sometimes auth-gated, sometimes not), CGI Federal's appointment
#  system at ais.usvisa-info.com requires DS-160 + paid receipt + login
#  before showing any slot data. That's outside what a public tracker can do.
#
#  What we CAN do is monitor official wait-time data from two public sources:
#
#    1. travel.state.gov — Global Visa Wait Times. Updated MONTHLY by the
#       US Department of State. Authoritative but slow. Useful for long-term
#       trend signals: "Mumbai dropped from 437 to 219 days in June".
#
#    2. ais.usvisa-info.com/en-in/niv/information/visa_wait_times — CGI
#       Federal's public wait times page (no auth needed). Updates more
#       frequently (operational changes, new appointment releases). Less
#       authoritative — sometimes lags state.gov, sometimes leads.
#
#  When the wait time DROPS significantly (e.g., from 400 days to 100 days)
#  it's a strong signal that the consulate has released a batch of new
#  appointments. Race to ais.usvisa-info.com (with your account/DS-160) to
#  grab one.
#
#  This is a TREND tracker, not a real-time slot scraper. Latency is days
#  to weeks, not minutes. See US_VISA_GUIDE.md for full context.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class USStateDeptProcessor:
    """
    Monitors US Department of State + CGI Federal public wait-time pages for
    significant drops at the 5 Indian consulates: Mumbai, New Delhi, Chennai,
    Hyderabad, Kolkata.

    Architecture:
      - Pure HTTP (requests). No Selenium, no JWT, no captcha bypass needed.
      - Two data sources tried in order; whichever gives fresher data wins.
      - Per-(consulate, visa_type) wait time stored in DB; alerts fire when
        wait time decreases by ≥ALERT_DROP_THRESHOLD_PCT or transitions from
        a non-numeric state ("Closed", "No appointments") to a numeric value.
      - Conservative on alerting: state.gov updates monthly so most cycles
        return no_change. That's by design.

    Visa categories tracked (state.gov labels):
      - Visitor (B1/B2 — business + tourism)
      - Student/Exchange Visitor (F, J)
      - Petition-Based Temporary Workers (H, L, O, P, Q)
      - Crew/Transit (C1/D)
      - Other Nonimmigrant Visa
    """

    STATE_GOV_URL = "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html"
    CGI_FEDERAL_URL = "https://ais.usvisa-info.com/en-in/niv/information/visa_wait_times"

    # Alert when wait time drops by this % or more (10% = "Mumbai 400 → 360 days")
    ALERT_DROP_THRESHOLD_PCT = 10.0
    # Alert on absolute drop ≥ this many days even if % is below threshold
    # (e.g., 50 → 30 days is only 40% but you'd want to know)
    ALERT_ABSOLUTE_DROP_DAYS = 20

    # Indian consulate codes — match the labels used on travel.state.gov
    INDIAN_CONSULATES = ["Mumbai", "New Delhi", "Chennai", "Hyderabad", "Kolkata"]

    # Map visa type labels to short codes for SlotInfo
    VISA_TYPE_CODES = {
        "Visitor (B1/B2)": "B1/B2",
        "Visitors (B1/B2)": "B1/B2",
        "Student/Exchange Visitor (F, M, J)": "F/M/J",
        "Petition-Based Temporary Workers (H, L, O, P, Q)": "H/L/O/P/Q",
        "Crew/Transit (C1/D)": "C1/D",
        "Other Nonimmigrant Visas": "Other",
    }

    def __init__(self, db: 'Database'):
        self.db = db
        self.log = logging.getLogger("us_state_dept")

    def check(self, country: str, city: str,
              visa_types: list[str]) -> 'CheckResult':
        """Run wait-time check for one US consulate. `city` is the consulate
        name (Mumbai/New Delhi/Chennai/Hyderabad/Kolkata)."""
        t0 = time.time()
        slots: list[SlotInfo] = []

        # Fetch both sources; either may fail on a given day. Use whichever
        # works.
        wait_data = self._fetch_wait_times(city)

        if not wait_data:
            return CheckResult(
                country, city, "us_state_dept", "error", [],
                error="Could not fetch wait time data from state.gov or CGI Federal",
                method="us_wait_time",
                duration_ms=int((time.time() - t0) * 1000),
            )

        # Compare each visa type against last known value
        for visa_label, current_days in wait_data.items():
            visa_code = self.VISA_TYPE_CODES.get(visa_label, visa_label[:20])

            # Read previous value from DB. Use a stable key per (consulate, visa).
            db_key = f"us_waittime|{city}|{visa_code}"
            prev = self._get_previous(db_key)

            # Always store current value for next cycle (whether or not it's an alert)
            self._store_current(db_key, current_days)

            if prev is None:
                # First observation — no comparison possible. Log baseline.
                self.log.info(f"  US/{city}/{visa_code}: baseline {current_days}")
                continue

            # Detect significant drop
            alert = self._is_significant_drop(prev, current_days)
            if alert:
                # Build a SlotInfo representing the new (earlier) projected
                # appointment date. Today + N days = projected available date.
                today = datetime.now()
                if isinstance(current_days, (int, float)) and current_days >= 0:
                    proj_date = (today + timedelta(days=int(current_days))).strftime("%Y-%m-%d")
                else:
                    proj_date = "TBD"

                slots.append(SlotInfo(
                    country="United States",
                    city=city,
                    visa_type=visa_code,
                    date=proj_date,
                    time_slot=f"wait dropped {prev} → {current_days} days",
                    portal="us_state_dept",
                    detection_method="us_wait_time_drop",
                    booking_url="https://ais.usvisa-info.com/en-in/niv/users/sign_in",
                    confidence="medium",  # state.gov is authoritative but monthly latency
                    raw_data=json.dumps({
                        "consulate": city, "visa": visa_code,
                        "previous_days": prev, "current_days": current_days,
                    })[:500],
                ))
                self.log.info(
                    f"  🇺🇸 US/{city}/{visa_code}: WAIT TIME DROP "
                    f"{prev} → {current_days} days "
                    f"(projected appointment: {proj_date})"
                )

        if slots:
            return CheckResult(
                country, city, "us_state_dept", "slots_found", slots,
                method="us_wait_time",
                duration_ms=int((time.time() - t0) * 1000),
            )
        return CheckResult(
            country, city, "us_state_dept", "no_change", [],
            method="us_wait_time",
            duration_ms=int((time.time() - t0) * 1000),
        )

    def _fetch_wait_times(self, consulate: str) -> dict:
        """Fetch wait times for a single Indian consulate.

        Returns dict {visa_type_label: days_or_status_string} or empty dict
        on failure. Tries state.gov first; falls back to CGI Federal.
        """
        # Try state.gov
        try:
            data = self._fetch_state_gov(consulate)
            if data:
                return data
        except Exception as e:
            self.log.debug(f"  state.gov fetch failed for {consulate}: {e}")

        # Fallback to CGI Federal
        try:
            data = self._fetch_cgi_federal(consulate)
            if data:
                return data
        except Exception as e:
            self.log.debug(f"  CGI Federal fetch failed for {consulate}: {e}")

        return {}

    def _consulate_name_variants(self, name: str) -> list:
        """Generate accent variants of a consulate name (Ciudad Juárez vs
        Ciudad Juarez, Mérida vs Merida). State.gov uses both forms inconsistently.

        v4.2.0: needed for non-India consulates (Mexico, etc.)
        """
        variants = [name]
        # Strip accents to get an ASCII variant
        import unicodedata
        ascii_form = ''.join(
            c for c in unicodedata.normalize('NFKD', name)
            if not unicodedata.combining(c)
        )
        if ascii_form != name:
            variants.append(ascii_form)

        # Special cases — common alternative forms used by state.gov
        special_cases = {
            "New Delhi": ["New Delhi", "Delhi, India"],
            "Mumbai": ["Mumbai"],
            "Ciudad Juárez": ["Ciudad Juárez", "Ciudad Juarez", "Juarez"],
            "Mérida": ["Mérida", "Merida"],
            "Mexico City": ["Mexico City", "Mexico, D.F.", "Mexico DF"],
            "Quebec City": ["Quebec City", "Quebec"],
            "Montreal": ["Montreal", "Montréal"],
            "Abu Dhabi": ["Abu Dhabi"],
            "Dubai": ["Dubai"],
            "Riyadh": ["Riyadh"],
            "Jeddah": ["Jeddah", "Jiddah"],
            "London": ["London", "London, England"],
        }
        if name in special_cases:
            for v in special_cases[name]:
                if v not in variants:
                    variants.append(v)

        return variants

    # Header-token → canonical visa label. state.gov phrases its column
    # headers inconsistently ("Visitors (B1/B2)", "Interview Required
    # Visitors (B1/B2)", …) but the parenthetical category codes are stable.
    HEADER_TOKEN_TO_LABEL = {
        "b1/b2": "Visitor (B1/B2)",
        "b1 / b2": "Visitor (B1/B2)",
        "f, m, j": "Student/Exchange Visitor (F, M, J)",
        "f,m,j": "Student/Exchange Visitor (F, M, J)",
        "h, l, o, p, q": "Petition-Based Temporary Workers (H, L, O, P, Q)",
        "h,l,o,p,q": "Petition-Based Temporary Workers (H, L, O, P, Q)",
        "c1/d": "Crew/Transit (C1/D)",
        "c1 / d": "Crew/Transit (C1/D)",
        "other nonimmigrant": "Other Nonimmigrant Visas",
    }

    def _parse_wait_table(self, html: str, consulate: str) -> dict:
        """v4.4.0: parse the real state.gov layout — an HTML table whose
        header row carries the visa-category labels and whose body rows are
        one city each. The old regex strategy looked for a visa label within
        1500 chars *after* the city name, which never matches a standard
        table (labels appear once, in the header) — so state.gov parsing
        silently returned {} and everything fell through to CGI Federal.
        """
        soup = BeautifulSoup(html, "html.parser")
        variants = {v.lower() for v in self._consulate_name_variants(consulate)}

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            header_cells = [c.get_text(" ", strip=True)
                            for c in rows[0].find_all(["th", "td"])]
            col_map: dict[int, str] = {}
            for idx, header in enumerate(header_cells):
                hl = header.lower()
                for token, label in self.HEADER_TOKEN_TO_LABEL.items():
                    if token in hl:
                        col_map[idx] = label
                        break
            if not col_map:
                continue

            for row in rows[1:]:
                cells = [c.get_text(" ", strip=True)
                         for c in row.find_all(["td", "th"])]
                if not cells:
                    continue
                city_cell = cells[0].strip().lower()
                if not any(v == city_cell or v in city_cell for v in variants):
                    continue
                result: dict = {}
                for idx, label in col_map.items():
                    if idx >= len(cells):
                        continue
                    cell = cells[idx].strip()
                    m = re.search(r"(\d{1,4})", cell)
                    if m:
                        days = int(m.group(1))
                        if 0 <= days <= 1500:
                            result[label] = days
                    elif cell:
                        # Non-numeric status ("Closed", "Emergency only") —
                        # keep it so a later transition to numeric alerts.
                        result[label] = cell[:40]
                if result:
                    return result
        return {}

    def _fetch_state_gov(self, consulate: str) -> dict:
        """Scrape state.gov wait times page for a specific consulate.

        The page is server-rendered HTML (Drupal). v4.4.0 parses the wait
        table structurally first (header columns × city rows); the legacy
        regex proximity strategy remains as a fallback for layout drift.
        """
        try:
            resp = requests.get(
                self.STATE_GOV_URL,
                timeout=15,
                headers={
                    "User-Agent": rand_ua(),
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            if resp.status_code != 200:
                return {}
        except requests.exceptions.RequestException as e:
            self.log.debug(f"state.gov request failed: {e}")
            return {}

        html = resp.text

        # v4.4.0: structural table parse first
        table_result = self._parse_wait_table(html, consulate)
        if table_result:
            return table_result

        # Legacy fallback: proximity regex strategy
        # 1. Find the consulate name as text
        # 2. Extract the next ~1500 chars (one row's worth of data)
        # 3. Look for numeric values or status keywords
        result: dict = {}

        # Look for the consulate's data row. Use accent-aware variants
        # (v4.2.0 — handles Mexican/French/etc. consulate names)
        consulate_variants = self._consulate_name_variants(consulate)

        for variant in consulate_variants:
            # Match the consulate name followed by data within ~1000 chars
            pattern = re.compile(
                re.escape(variant) + r'(.{0,1500})',
                re.DOTALL | re.IGNORECASE,
            )
            match = pattern.search(html)
            if not match:
                continue

            row_html = match.group(1)
            # Extract visa categories and their values. Each visa label is
            # followed by either a number (days) or a keyword.
            for visa_label, code in self.VISA_TYPE_CODES.items():
                # Look for visa label followed by number or keyword
                value_pattern = re.compile(
                    re.escape(visa_label) + r'.{0,200}?(\d{1,4})\s*(?:Calendar\s+)?(?:Days?)?',
                    re.IGNORECASE | re.DOTALL,
                )
                value_match = value_pattern.search(row_html)
                if value_match:
                    try:
                        days = int(value_match.group(1))
                        # Sanity check — wait times shouldn't be over 1500 days
                        if 0 <= days <= 1500:
                            result[visa_label] = days
                    except ValueError:
                        pass
            if result:
                break  # Found data for this variant

        return result

    def _fetch_cgi_federal(self, consulate: str) -> dict:
        """Fallback: scrape CGI Federal's public wait times page.

        This page covers all Indian consulates on a single URL. Lighter weight
        than state.gov but less authoritative.
        """
        try:
            resp = requests.get(
                self.CGI_FEDERAL_URL,
                timeout=15,
                headers={
                    "User-Agent": rand_ua(),
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            if resp.status_code != 200:
                return {}
        except requests.exceptions.RequestException as e:
            self.log.debug(f"CGI Federal request failed: {e}")
            return {}

        html = resp.text
        result: dict = {}

        # CGI Federal page has dropdown-selected consulate data. Without
        # session state we can only see the rendered initial state which
        # typically includes ALL India consulates. Parse similarly.
        pattern = re.compile(
            re.escape(consulate) + r'(.{0,1000})',
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(html)
        if not match:
            return {}

        row_html = match.group(1)
        for visa_label, _code in self.VISA_TYPE_CODES.items():
            value_pattern = re.compile(
                re.escape(visa_label) + r'.{0,200}?(\d{1,4})\s*(?:Days?)?',
                re.IGNORECASE | re.DOTALL,
            )
            value_match = value_pattern.search(row_html)
            if value_match:
                try:
                    days = int(value_match.group(1))
                    if 0 <= days <= 1500:
                        result[visa_label] = days
                except ValueError:
                    pass

        return result

    def _is_significant_drop(self, prev, current) -> bool:
        """Decide if the wait time change warrants an alert."""
        # Both numeric: check % drop and absolute drop
        if isinstance(prev, (int, float)) and isinstance(current, (int, float)):
            if current >= prev:
                return False  # No drop
            drop = prev - current
            if drop >= self.ALERT_ABSOLUTE_DROP_DAYS:
                return True
            pct = (drop / max(prev, 1)) * 100
            return pct >= self.ALERT_DROP_THRESHOLD_PCT

        # Transition from non-numeric (Closed, etc.) to numeric: alert
        if not isinstance(prev, (int, float)) and isinstance(current, (int, float)):
            return True

        return False

    def _get_previous(self, db_key: str):
        """Read the previous wait-time value from the wait_times table.

        v4.4.0 fix: this used to query `slots.metadata` filtered by
        `slots.id` — neither column has ever existed (the table's key is
        `uid` and it has no metadata/expires_at columns). The
        OperationalError was swallowed at debug level, so `prev` was always
        None and a wait-time drop alert could never fire. Same story for
        `_store_current` below. See Database.set_wait_time/get_wait_time.
        """
        try:
            return self.db.get_wait_time(db_key)
        except Exception as e:
            self.log.debug(f"Could not read previous wait time: {e}")
            return None

    def _store_current(self, db_key: str, value):
        """Persist the current wait-time value for next cycle's comparison."""
        try:
            self.db.set_wait_time(db_key, value)
        except Exception as e:
            self.log.debug(f"Could not store wait time: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UNIFIED CHECKER — Uses all three layers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UnifiedChecker:
    """
    For each country/city, tries detection layers in order:
      1. Layer 1a: JWT-replay against processor `known_api_endpoints`
                   (v3.2.1 — VFS lift-api primarily)
      1b: Layer 1b: Anonymous GET against any per-country calibrated endpoints
      2. Layer 3:   Page-Change Detection (always works, guaranteed)

    The slot's `confidence` matches the calibration confidence (high/medium/
    low), so the dashboard can group / filter alerts by signal quality.
    """

    def __init__(self, browser_mgr: BrowserManager, db: Database):
        self.browser = browser_mgr
        self.db = db
        self.api_interceptor = APIInterceptor(browser_mgr, db)
        self.page_detector = PageChangeDetector(browser_mgr, db)
        self.vfs_jwt = VFSJWTSession(browser_mgr)  # v3.2.1
        self.us_state_dept = USStateDeptProcessor(db)  # v4.1.0
        self.log = logging.getLogger("checker")

    def _confidence_for(self, calibration: Optional[dict],
                        country: str) -> str:
        """Resolve the confidence to attach to slots from this country."""
        if calibration and calibration.get("confidence"):
            return calibration["confidence"]
        # Fall back to registry default
        rec = COUNTRY_INDEX.get((country or "").strip().lower())
        if rec and rec.get("confidence"):
            return rec["confidence"]
        return "medium"

    def check(self, country: str, city: str,
              visa_types: list[str]) -> CheckResult:
        """Run detection for one country/city combo."""
        t0 = time.time()

        # ── v4.1.0: US visa wait-time path (no Selenium, no calibration) ──
        # Dispatched BEFORE the VFS layer because US doesn't use VFS, doesn't
        # need calibration, and shouldn't burn JWT/Selenium budget.
        rec_for_proc = COUNTRY_INDEX.get((country or "").strip().lower(), {})
        if rec_for_proc.get("processor") == "us_state_dept":
            return self.us_state_dept.check(country, city, visa_types)

        url, portal_type = get_appointment_url(country)

        if not url:
            return CheckResult(country, city, "unknown", "error", [],
                             error=f"No portal URL for {country}",
                             method="none")

        # Check if we have calibration data
        cal_key = f"{country}|{portal_type}"
        calibration = self.db.get_calibration(cal_key)
        confidence = self._confidence_for(calibration, country)
        proc_meta = get_processor_metadata(country)

        # ── Layer 1a: VFS JWT replay (v3.2.1) ──
        # If this is a VFS country and the processor metadata declares
        # known_api_endpoints, try the JWT-acquire-and-replay flow first.
        # Falls through silently on auth failures.
        if (portal_type == "vfs"
                and proc_meta.get("auth_method") == "jwt_via_selenium"
                and proc_meta.get("known_api_endpoints")):
            try:
                jwt = self.vfs_jwt.get(country, url)
                if jwt:
                    rec = COUNTRY_INDEX.get((country or "").strip().lower(), {})
                    iso3 = rec.get("destination_iso3", "")
                    api_data = []
                    for ep in proc_meta["known_api_endpoints"]:
                        # Build params for the slot/earliestslot endpoint.
                        # The ref impl uses these field names; if the live
                        # API rejects them, the request just 4xx's and we
                        # fall through to page-change.
                        params = {
                            "countryCode": "ind",
                            "missionCode": iso3 or "",
                            "languageCode": "en-US",
                            "applicantsCount": 1,
                            "days": 90,
                            "slotType": 2,
                        }
                        replayed = self.vfs_jwt.replay(ep, jwt, params,
                                                       country=country)
                        if replayed:
                            api_data.append({
                                "url": ep,
                                "body": replayed.get("body", ""),
                                "status": replayed.get("status", 0),
                            })
                    if api_data:
                        slots = self.api_interceptor.extract_slots_from_api(
                            api_data, country, city, visa_types, url
                        )
                        # Override slot confidence with country-specific
                        for s in slots:
                            s.confidence = confidence
                        if slots:
                            return CheckResult(country, city, portal_type,
                                "slots_found", slots, method="api_jwt",
                                duration_ms=int((time.time()-t0)*1000))
            except Exception as e:
                self.log.debug(f"  JWT replay path failed: {e}")

        # ── Layer 1b: try any anonymous endpoints from calibration ──
        if calibration and calibration.get("api_endpoints"):
            self.log.info(f"  Layer 1 (API): trying calibrated endpoints for {country}/{city}")
            try:
                api_data = []
                for endpoint in calibration["api_endpoints"]:
                    # Skip known JWT-auth endpoints — those go through 1a
                    if "lift-api.vfsglobal.com" in endpoint:
                        continue
                    try:
                        resp = requests.get(endpoint, timeout=10, headers={
                            "User-Agent": rand_ua(),
                            "Accept": "application/json",
                        })
                        if resp.status_code == 200:
                            api_data.append({
                                "url": endpoint,
                                "body": resp.text[:5000],
                                "status": resp.status_code,
                            })
                    except:
                        pass

                if api_data:
                    slots = self.api_interceptor.extract_slots_from_api(
                        api_data, country, city, visa_types, url
                    )
                    for s in slots:
                        s.confidence = confidence
                    if slots:
                        return CheckResult(country, city, portal_type, "slots_found",
                                         slots, method="api",
                                         duration_ms=int((time.time()-t0)*1000))
            except Exception as e:
                self.log.debug(f"  Layer 1 failed: {e}")

        # ── Layer 3: Page-change detection (always works) ──
        self.log.info(f"  Layer 3 (PageChange): monitoring {country}/{city}")
        result = self.page_detector.check(url, country, city, visa_types)
        # Stamp slots with the right confidence
        for s in result.slots:
            s.confidence = confidence
        result.duration_ms = int((time.time()-t0)*1000)
        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CALIBRATION ENGINE
#  Inspects each country's portal and discovers what works
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Calibrator:
    """
    Visits each country's appointment page and discovers:
    - Whether login is required
    - What API endpoints the frontend calls
    - What DOM selectors work for calendar/date elements
    - The page structure (SPA, static, etc.)

    Saves results to database for the checker to use.
    """

    ALL_SELECTORS = [
        "td.day", "td.day:not(.disabled)",
        "td.day:not(.disabled):not(.old):not(.new):not(.off)",
        ".datepicker td:not(.disabled)",
        "[class*='calendar'] td", "[class*='calendar'] [class*='available']",
        ".mat-calendar-body-cell:not(.mat-calendar-body-disabled)",
        "[data-available='true']", ".slot-available", ".date-available",
        ".fc-daygrid-day:not(.fc-day-disabled)",
        ".calendar-date.open", ".day-cell:not(.unavailable)",
        ".time-slot:not(.disabled)", "[class*='timeslot']:not(.booked)",
        "select[id*='location']", "select[id*='center']",
        "select[id*='city']", "select[id*='category']",
        "select[id*='visa']", "select[name*='location']",
    ]

    def __init__(self, browser_mgr: BrowserManager, db: Database):
        self.browser = browser_mgr
        self.db = db
        self.api_interceptor = APIInterceptor(browser_mgr, db)
        self.log = logging.getLogger("calibrator")

    def calibrate_country(self, country: str) -> dict:
        """Fully inspect and calibrate one country."""
        url, portal_type = get_appointment_url(country)
        if not url:
            self.log.error(f"No URL for {country}")
            return {"error": f"No portal URL for {country}"}

        self.log.info(f"\n{'='*60}")
        self.log.info(f"CALIBRATING: {country} ({portal_type})")
        self.log.info(f"URL: {url}")
        self.log.info(f"{'='*60}")

        result = {
            "country": country,
            "portal": portal_type,
            "url": url,
            "login_required": False,
            "cloudflare_detected": False,
            "selectors": [],
            "api_endpoints": [],
            "page_structure": {},
            "notes": "",
        }

        driver = None
        try:
            # ── Step 1: Load page with network capture ──
            self.log.info("Step 1: Loading page with network capture...")
            driver = self.browser.create_driver(capture_network=True)
            driver.get(url)

            # Critical: wait for the SPA to hydrate before introspecting it.
            # Previously this was time.sleep(6), which caught Nuxt mid-load
            # and produced "text_length: 34" for 78/78 countries.
            hydrated = self.browser.wait_for_spa(driver, max_seconds=25)
            result["page_structure"]["hydrated"] = hydrated
            if not hydrated:
                self.log.warning("  SPA did not fully hydrate — results may be incomplete")
                result["notes"] += "SPA hydration timed out — page may need manual inspection. "

            # ── Step 2: Check for Cloudflare ──
            title = driver.title.lower()
            src_preview = driver.page_source[:3000].lower()

            if "just a moment" in title or "cloudflare" in src_preview:
                result["cloudflare_detected"] = True
                self.log.warning("  Cloudflare detected — waiting 10s...")
                time.sleep(10)

                if "just a moment" in driver.title.lower():
                    result["notes"] += "Cloudflare block persists. Use proxies or increase interval. "
                    self.log.error("  Cloudflare block persists!")

            # ── Step 3: Analyze page content ──
            self.log.info("Step 2: Analyzing page content...")
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            for tag in soup.select("script, style, noscript"):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
            text_lower = text.lower()

            # Login detection
            login_indicators = ["sign in", "log in", "login", "email", "password",
                              "create account", "register"]
            result["login_required"] = sum(1 for p in login_indicators if p in text_lower) >= 2

            if result["login_required"]:
                self.log.info("  Login appears required")
                result["notes"] += "Login required before calendar is visible. "

            # Page type
            result["page_structure"]["has_forms"] = bool(soup.select("select, form"))
            result["page_structure"]["has_tables"] = bool(soup.select("table"))
            result["page_structure"]["has_calendar_classes"] = bool(
                soup.select("[class*='calendar'], [class*='datepicker'], .fc-view")
            )
            result["page_structure"]["text_length"] = len(text)
            result["page_structure"]["title"] = driver.title

            # No-slots detection
            no_slot_phrases = ["no appointment", "no slots", "fully booked",
                             "not available", "no dates"]
            result["page_structure"]["shows_no_slots"] = any(
                p in text_lower for p in no_slot_phrases
            )

            # ── Step 4: Test all CSS selectors ──
            self.log.info("Step 3: Testing CSS selectors...")
            # v3.2.2: implicit_wait was 5s. With 21 selectors and most missing,
            # this loop spent 105s/country = 87% of total calibration runtime
            # in the v3.2 production log. Drop implicit_wait to a minimal
            # value just for this phase, then restore. Per-country savings:
            # ~100s. For --all (42 countries) this drops total time from
            # 83 min to ~17 min.
            try:
                driver.implicitly_wait(0.3)
            except Exception:
                pass
            try:
                for sel in self.ALL_SELECTORS:
                    try:
                        elems = driver.find_elements(By.CSS_SELECTOR, sel)
                        if elems:
                            sample = elems[0]
                            info = {
                                "selector": sel,
                                "count": len(elems),
                                "sample_text": sample.text[:100] if sample.text else "",
                                "sample_class": sample.get_attribute("class") or "",
                            }
                            result["selectors"].append(info)
                            self.log.info(f"  ✓ {sel} → {len(elems)} elements")
                    except:
                        pass
            finally:
                try:
                    driver.implicitly_wait(5)
                except Exception:
                    pass

            # ── Step 4.5: Click-through phase (NEW v3.2.1) ──
            # Many VFS / BLS portals don't fire their slot-availability API
            # until the user clicks past the landing page (e.g. "Book
            # Appointment" or "View Available Slots"). Czech Republic was the
            # only country in v3.2 calibration that auto-fired its API on
            # landing — that's the exception, not the rule. This phase clicks
            # through landing buttons in priority order and re-captures the
            # network for a few seconds after each click.
            #
            # We deliberately do NOT click anything that looks like:
            #   - login/sign-in (we're not authenticated, would fail)
            #   - download/print/cancel (irrelevant)
            #   - radio/checkbox (selection inside a form, not navigation)
            self.log.info("Step 3.5: Click-through phase to surface gated APIs...")
            click_targets = [
                # Priority order: most general first, falling back to specific
                "//button[contains(translate(., 'BOOK', 'book'), 'book') and not(contains(translate(., 'LOGIN', 'login'), 'login'))]",
                "//a[contains(translate(., 'BOOK', 'book'), 'book') and not(contains(translate(., 'LOGIN', 'login'), 'login'))]",
                "//button[contains(translate(., 'APPOINTMENT', 'appointment'), 'appointment')]",
                "//a[contains(translate(., 'APPOINTMENT', 'appointment'), 'appointment')]",
                "//button[contains(translate(., 'CONTINUE', 'continue'), 'continue')]",
                "//button[contains(translate(., 'START', 'start'), 'start')]",
                "//button[contains(translate(., 'AVAILABLE', 'available'), 'available')]",
                "//a[contains(translate(., 'AVAILABLE', 'available'), 'available')]",
                "//button[contains(translate(., 'SCHEDULE', 'schedule'), 'schedule')]",
                "//button[contains(translate(., 'CATEGORY', 'category'), 'category')]",
                "//button[contains(@class, 'primary') or contains(@class, 'cta')]",
            ]
            click_count = 0
            max_clicks = 3
            for xpath in click_targets:
                if click_count >= max_clicks:
                    break
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for elem in elements[:1]:  # only first match per pattern
                        try:
                            # Skip if not visible/enabled
                            if not elem.is_displayed() or not elem.is_enabled():
                                continue
                            label = (elem.text or "")[:40].strip()
                            if not label:
                                continue
                            # Skip dangerous labels
                            label_lower = label.lower()
                            if any(skip in label_lower for skip in
                                   ("login", "sign in", "register", "logout",
                                    "cancel", "close", "back", "previous",
                                    "download", "print", "delete", "remove",
                                    "decline", "reject", "no thanks")):
                                continue
                            # Click via JS to bypass overlay issues
                            driver.execute_script("arguments[0].click();", elem)
                            self.log.info(f"  ↪ Clicked: '{label}'")
                            click_count += 1
                            # Wait for any new XHRs / page mutations to settle
                            self.browser.wait_for_spa(driver, max_seconds=10)
                            time.sleep(2)
                            # Cloudflare or auth-wall check after click
                            t = driver.title.lower()
                            if "just a moment" in t or "captcha" in t:
                                self.log.warning("  ⚠ Click triggered Cloudflare/CAPTCHA — backing off")
                                result["notes"] += "Click-through hit Cloudflare. "
                                break
                            # If we hit a login wall, note it but keep trying
                            current_text = (driver.find_element(By.TAG_NAME, "body").text or "").lower()[:1500]
                            if any(p in current_text for p in ("please log in", "sign in to continue", "enter your email")):
                                result["login_required"] = True
                                self.log.info("  → Reached login wall; further clicks would need creds")
                                break
                            break  # Move to next pattern
                        except (StaleElementReferenceException,
                                ElementClickInterceptedException,
                                ElementNotInteractableException):
                            continue
                        except Exception as click_err:
                            self.log.debug(f"  Click failed: {click_err}")
                            continue
                except Exception:
                    continue
            if click_count == 0:
                self.log.info("  No actionable buttons found on landing")
            else:
                self.log.info(f"  Click-through completed: {click_count} clicks")
            result["page_structure"]["clicks_performed"] = click_count

            # ── Step 5: Capture API calls ──
            self.log.info("Step 4: Capturing network API calls...")
            try:
                logs = driver.get_log("performance")
                for entry in logs:
                    try:
                        msg = json.loads(entry["message"])["message"]
                        if msg["method"] == "Network.responseReceived":
                            resp_url = msg["params"]["response"]["url"]
                            mime = msg["params"]["response"].get("mimeType", "")

                            # Skip tracking/analytics hosts (matches APIInterceptor)
                            try:
                                host = urlparse(resp_url).hostname or ""
                            except Exception:
                                host = ""
                            if any(h in host for h in APIInterceptor.BLOCKED_HOSTS):
                                continue

                            # Promote VFS lift-api responses unconditionally —
                            # they're the slot-availability backend regardless
                            # of URL path keywords.
                            is_vfs_lift = "lift-api.vfsglobal.com" in host

                            if ("json" in mime or "/api/" in resp_url.lower() or is_vfs_lift):
                                # Match against path only, not querystring
                                try:
                                    path_lower = (urlparse(resp_url).path or "").lower()
                                except Exception:
                                    path_lower = resp_url.lower()
                                if is_vfs_lift or any(kw in path_lower for kw in APIInterceptor.APPOINTMENT_KEYWORDS):
                                    result["api_endpoints"].append(resp_url)
                                    flag = " [VFS lift-api]" if is_vfs_lift else ""
                                    self.log.info(f"  ✓ API: {resp_url[:100]}{flag}")
                    except:
                        pass
            except:
                self.log.info("  Network logging unavailable")

            # Deduplicate API endpoints
            result["api_endpoints"] = list(set(result["api_endpoints"]))

            # Merge in processor-level known endpoints (v3.2.1). E.g. for
            # vfs_global, this seeds lift-api.vfsglobal.com endpoints that we
            # know exist even if click-through didn't surface them. The
            # checker treats these as JWT-replay candidates.
            proc_meta = get_processor_metadata(country)
            for ep in (proc_meta.get("known_api_endpoints") or []):
                if ep not in result["api_endpoints"]:
                    result["api_endpoints"].append(ep)
                    self.log.info(f"  + processor-known: {ep[:100]}")

            # ── Step 6: Save screenshot ──
            os.makedirs("calibration_output", exist_ok=True)
            slug = country.lower().replace(" ", "_")
            try:
                driver.save_screenshot(f"calibration_output/{slug}.png")
                self.log.info(f"  Screenshot: calibration_output/{slug}.png")
            except:
                pass

            # Save HTML
            with open(f"calibration_output/{slug}.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            self.log.info(f"  HTML saved: calibration_output/{slug}.html")

            # ── Step 7: Summary ──
            self.log.info(f"\n  {'─'*40}")
            self.log.info(f"  RESULT for {country}:")
            self.log.info(f"    Login required:     {result['login_required']}")
            self.log.info(f"    Cloudflare:         {result['cloudflare_detected']}")
            self.log.info(f"    Working selectors:  {len(result['selectors'])}")
            self.log.info(f"    API endpoints:      {len(result['api_endpoints'])}")
            self.log.info(f"    No-slots message:   {result['page_structure'].get('shows_no_slots', False)}")

            # Determine best strategy + confidence (v3.2.1)
            #
            # Confidence reflects how reliable a signal we expect from this
            # country's check pipeline:
            #   high   = real API endpoint discovered (or known on processor)
            #            with at least one selector or a successful click; we
            #            can act on hits with low false-positive risk
            #   medium = working DOM selectors, no API; DOM scrape can detect
            #            slot existence but with some noise
            #   low    = page-change fallback only; will fire on cosmetic
            #            noise (cookie banners, A/B copy, news ticker)
            has_api = bool(result["api_endpoints"])
            has_selectors = bool(result["selectors"])
            clicks = result["page_structure"].get("clicks_performed", 0)

            if has_api and (has_selectors or clicks > 0):
                strategy = "API interception (best)"
                confidence = "high"
            elif has_api:
                # API endpoint exists but page surface looks dead — could be
                # a known-endpoint plant from the processor metadata. Treat
                # as medium until a checker run confirms the JWT flow works.
                strategy = "API interception (unverified)"
                confidence = "medium"
            elif has_selectors:
                strategy = "DOM scraping with discovered selectors"
                confidence = "medium"
            else:
                strategy = "Page-change detection (fallback — high noise risk)"
                confidence = "low"
            result["confidence"] = confidence
            result["notes"] += f"Best strategy: {strategy}. "
            self.log.info(f"    Strategy:           {strategy}")
            self.log.info(f"    Confidence:         {confidence}")
            self.log.info(f"  {'─'*40}")

            # Save to database
            cal_key = f"{country}|{portal_type}"
            self.db.save_calibration(cal_key, result)

            return result

        except Exception as e:
            self.log.error(f"Calibration failed for {country}: {e}")
            traceback.print_exc()
            result["notes"] += f"Error: {str(e)[:200]}"
            return result
        finally:
            if driver:
                try: driver.quit()
                except: pass

    def calibrate_all(self, countries: list[str], workers: int = 1) -> dict:
        """Calibrate all countries and produce a report.

        v3.2.1: optional parallel workers. With workers > 1, runs N Selenium
        drivers concurrently via ThreadPoolExecutor. Default is sequential
        (workers=1) — VFS will rate-limit aggressive parallel hits from one
        IP. 2-4 is a reasonable upper bound on residential connections.
        """
        report = {
            "calibrated_at": utc_now_iso(),
            "countries": {},
            "summary": {
                "total": len(countries),
                "api_capable": 0,
                "selector_capable": 0,
                "page_change_only": 0,
                "login_required": 0,
                "cloudflare_blocked": 0,
                "errors": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
        }

        def _do_one(idx: int, country: str) -> tuple[str, dict]:
            self.log.info(f"\n[{idx+1}/{len(countries)}] Calibrating {country}...")
            try:
                return country, self.calibrate_country(country)
            except Exception as e:
                return country, {"error": str(e)}

        if workers > 1:
            self.log.info(f"\nParallel calibration: {workers} workers")
            from concurrent.futures import as_completed
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_do_one, i, c): c
                    for i, c in enumerate(countries)
                }
                for fut in as_completed(futures):
                    country, result = fut.result()
                    report["countries"][country] = result
                    self._tally(result, report["summary"])
                    # Brief stagger so spawned workers don't all hit at once
                    time.sleep(random.uniform(0.5, 1.5))
        else:
            for i, country in enumerate(countries):
                _, result = _do_one(i, country)
                report["countries"][country] = result
                self._tally(result, report["summary"])
                # Don't hammer servers
                time.sleep(random.uniform(3, 6))

        # Save report
        with open("calibration_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        s = report["summary"]
        self.log.info(f"\n{'='*60}")
        self.log.info(f"CALIBRATION COMPLETE")
        self.log.info(f"{'='*60}")
        self.log.info(f"  Total countries:      {s['total']}")
        self.log.info(f"  API capable:          {s['api_capable']}")
        self.log.info(f"  Selector capable:     {s['selector_capable']}")
        self.log.info(f"  Page-change only:     {s['page_change_only']}")
        self.log.info(f"  Login required:       {s['login_required']}")
        self.log.info(f"  Cloudflare blocked:   {s['cloudflare_blocked']}")
        self.log.info(f"  Errors:               {s['errors']}")
        self.log.info(f"")
        self.log.info(f"  Confidence buckets:")
        self.log.info(f"    high:               {s['high_confidence']}")
        self.log.info(f"    medium:             {s['medium_confidence']}")
        self.log.info(f"    low:                {s['low_confidence']}")
        self.log.info(f"\n  Report: calibration_report.json")
        self.log.info(f"{'='*60}")

        return report

    @staticmethod
    def _tally(result: dict, summary: dict) -> None:
        """Update aggregate counts from one country's result."""
        if not isinstance(result, dict) or "error" in result and not result.get("api_endpoints"):
            summary["errors"] += 1
            return
        if result.get("api_endpoints"):
            summary["api_capable"] += 1
        elif result.get("selectors"):
            summary["selector_capable"] += 1
        else:
            summary["page_change_only"] += 1
        if result.get("login_required"):
            summary["login_required"] += 1
        if result.get("cloudflare_detected"):
            summary["cloudflare_blocked"] += 1
        conf = result.get("confidence", "medium")
        if conf == "high":   summary["high_confidence"] += 1
        elif conf == "low":  summary["low_confidence"] += 1
        else:                summary["medium_confidence"] += 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NOTIFICATIONS (same as v2 but cleaner)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Notifier:
    """Unified notification dispatcher.

    v3.2.2: rate-limited. If a single send() call exceeds NOTIFICATION_CAP
    slots, sends one consolidated summary alert per channel instead of N
    individual alerts. Stops the "375 NEW slot(s) found!" notification spam
    seen in the v3.2 production run.
    """

    NOTIFICATION_CAP = 25  # max individual alerts per send() call

    def __init__(self, config: dict):
        self.config = config
        self.log = logging.getLogger("notifier")
        self.dry_run = bool(config.get("notification_dry_run", False))

        # v4.0.0: env-var overrides for Telegram (required for GitHub Actions
        # where secrets cannot live in config.json). If TELEGRAM_BOT_TOKEN
        # and TELEGRAM_CHAT_ID are set in the environment, they override
        # whatever's in config.json. NOTIFICATION_DRY_RUN=true also overrides.
        env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        env_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if env_token:
            tg = self.config.setdefault("telegram", {})
            tg["bot_token"] = env_token
            self.log.info("  Telegram: bot_token loaded from environment")
        if env_chat:
            tg = self.config.setdefault("telegram", {})
            existing = tg.get("chat_ids", [])
            # Allow comma-separated env var for multiple recipients
            new_chats = [c.strip() for c in env_chat.split(",") if c.strip()]
            tg["chat_ids"] = list(dict.fromkeys(existing + new_chats))  # dedupe, preserve order
            self.log.info(f"  Telegram: {len(new_chats)} chat_id(s) loaded from environment")

        env_dry = os.environ.get("NOTIFICATION_DRY_RUN", "").strip().lower()
        if env_dry in ("1", "true", "yes"):
            self.dry_run = True
            self.log.info("  NOTIFICATION_DRY_RUN=true (env var override)")

    def send(self, slots: list[SlotInfo]):
        """Send alerts via all configured channels.

        v3.2.2: caps at NOTIFICATION_CAP. Overflow becomes a single summary.
        """
        if not slots:
            return

        if self.dry_run:
            self.log.warning(
                f"[DRY-RUN] Would have sent {len(slots)} slot alert(s) — "
                f"first 3: {[(s.country, s.city, s.confidence) for s in slots[:3]]}"
            )
            return

        # v3.2.2: rate-limit
        cap = self.NOTIFICATION_CAP
        is_capped = len(slots) > cap
        if is_capped:
            self.log.warning(
                f"NOTIFICATION RATE-LIMIT: {len(slots)} slots exceeds cap of {cap}. "
                f"Sending consolidated summary instead of individual alerts. "
                f"This usually means page-change detection is firing on cosmetic noise — "
                f"check the dashboard and consider re-calibrating the noisiest countries."
            )
            self._send_summary(slots, total=len(slots))
            return

        # Email
        email_cfg = self.config.get("email", {})
        if email_cfg.get("enabled"):
            self._send_email(slots, email_cfg)

        # Telegram
        tg_cfg = self.config.get("telegram", {})
        if tg_cfg.get("bot_token"):
            self._send_telegram(slots, tg_cfg)

        # Discord
        disc_cfg = self.config.get("discord", {})
        if disc_cfg.get("webhook_url"):
            self._send_discord(slots, disc_cfg)

        # Generic webhook (v4.4.0) — ntfy / Slack / Home Assistant / any
        # endpoint that accepts a JSON POST.
        wh_cfg = self.config.get("webhook", {})
        if wh_cfg.get("url"):
            self._send_webhook(slots, wh_cfg)

        # Desktop sound. Skipped in CI — GitHub Actions runners have no
        # notify-send/toast surface, so it just warned on every dispatch.
        if self.config.get("desktop_alerts", True) and not (
                os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")):
            self._desktop_alert(slots)

    def _send_summary(self, slots: list[SlotInfo], total: int):
        """v3.2.2: one consolidated alert instead of N individual ones."""
        # Group by country
        from collections import Counter
        by_country = Counter((s.country, s.confidence) for s in slots)
        lines = [
            f"⚠ Visa Tracker — {total} slot alert(s) detected (rate-limited).",
            f"This is unusually many. Open the dashboard to triage.",
            "",
            "Top countries (count, confidence):",
        ]
        for (country, conf), n in by_country.most_common(15):
            lines.append(f"  · {country:<26} {conf:<6} {n}")
        if len(by_country) > 15:
            lines.append(f"  · …{len(by_country)-15} more")
        body = "\n".join(lines)
        subject = f"⚠ Visa Tracker rate-limit alert — {total} events"

        # Email
        email_cfg = self.config.get("email", {})
        if email_cfg.get("enabled"):
            try:
                for rcpt in email_cfg.get("recipients", []):
                    msg = MIMEMultipart()
                    msg["Subject"] = subject
                    msg["From"] = email_cfg["sender"]
                    msg["To"] = rcpt
                    msg.attach(MIMEText(body, "plain"))
                    with smtplib.SMTP(email_cfg["smtp_host"], email_cfg.get("smtp_port", 587)) as srv:
                        srv.starttls()
                        srv.login(email_cfg["sender"], email_cfg["password"])
                        srv.sendmail(email_cfg["sender"], rcpt, msg.as_string())
                self.log.info("Summary email sent")
            except Exception as e:
                self.log.error(f"Summary email failed: {e}")

        # Telegram
        tg_cfg = self.config.get("telegram", {})
        if tg_cfg.get("bot_token"):
            try:
                for chat_id in tg_cfg.get("chat_ids", []):
                    r = requests.post(
                        f"https://api.telegram.org/bot{tg_cfg['bot_token']}/sendMessage",
                        json={"chat_id": chat_id, "text": body},
                        timeout=10,
                    )
                    if r.status_code != 200:
                        self.log.error(f"Summary Telegram failed: HTTP {r.status_code} {r.text[:120]}")
                self.log.info("Summary Telegram sent")
            except Exception as e:
                self.log.error(f"Summary Telegram failed: {e}")

        # Discord
        disc_cfg = self.config.get("discord", {})
        if disc_cfg.get("webhook_url"):
            try:
                r = requests.post(disc_cfg["webhook_url"],
                    json={"content": body[:1900]}, timeout=10)
                if r.status_code >= 400:
                    self.log.error(f"Summary Discord failed: HTTP {r.status_code}")
                else:
                    self.log.info("Summary Discord sent")
            except Exception as e:
                self.log.error(f"Summary Discord failed: {e}")

        # Generic webhook (v4.4.0)
        wh_cfg = self.config.get("webhook", {})
        if wh_cfg.get("url"):
            try:
                requests.post(wh_cfg["url"], json={
                    "event": "visa_slots_rate_limited",
                    "count": total,
                    "sent_at": utc_now_iso(),
                    "summary": body,
                }, timeout=10)
            except Exception as e:
                self.log.error(f"Summary webhook failed: {e}")

    def _send_email(self, slots, cfg):
        try:
            subject = f"🎯 {len(slots)} Visa Slot(s) Found!"

            plain_lines = [f"VISA SLOT ALERT — {len(slots)} slot(s)\n"]
            for s in slots:
                plain_lines.append(f"  {s.country} | {s.city} | {s.visa_type}")
                plain_lines.append(f"  Date: {s.date} | {s.time_slot}")
                plain_lines.append(f"  Confidence: {s.confidence} ({s.detection_method})")
                plain_lines.append(f"  Book: {s.booking_url}\n")
            plain = "\n".join(plain_lines)

            for rcpt in cfg.get("recipients", []):
                msg = MIMEMultipart()
                msg["Subject"] = subject
                msg["From"] = cfg["sender"]
                msg["To"] = rcpt
                msg.attach(MIMEText(plain, "plain"))

                with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587)) as srv:
                    srv.starttls()
                    srv.login(cfg["sender"], cfg["password"])
                    srv.sendmail(cfg["sender"], rcpt, msg.as_string())
                self.log.info(f"Email sent to {rcpt}")
        except Exception as e:
            self.log.error(f"Email failed: {e}")

    # Telegram hard limit is 4096 chars/message. Chunk below that with
    # headroom — a 25-slot alert (~5000 chars) used to get a 400 from the
    # Bot API and the alert was silently lost.
    TELEGRAM_CHUNK_CHARS = 3500

    @classmethod
    def _telegram_chunks(cls, header: str, blocks: list[str]) -> list[str]:
        """v4.4.0: pack per-slot blocks into messages under the API limit."""
        chunks: list[str] = []
        current = header
        for block in blocks:
            candidate = current + "\n" + block
            if len(candidate) > cls.TELEGRAM_CHUNK_CHARS and current != header:
                chunks.append(current)
                current = header + "\n" + block
            else:
                current = candidate
        if current.strip():
            chunks.append(current)
        return chunks

    def _post_telegram(self, cfg: dict, chat_id: str, text: str) -> bool:
        """POST one message; verify the API response instead of assuming ok."""
        resp = requests.post(
            f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
            json={"chat_id": chat_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code != 200 or not body.get("ok"):
            self.log.error(
                f"Telegram send failed for chat {chat_id}: HTTP {resp.status_code} "
                f"{body.get('description', resp.text[:120])}"
            )
            return False
        return True

    def _send_telegram(self, slots, cfg):
        try:
            header = f"🎯 <b>Visa Slot Alert!</b> ({len(slots)} slot{'s' if len(slots)>1 else ''})"
            blocks = []
            for s in slots:
                conf = "🟢" if s.confidence == "high" else "🟡"
                url = html_escape(s.booking_url or "", quote=True)
                blocks.append(
                    f"{conf} <b>{html_escape(s.country)}</b> — {html_escape(s.city)}\n"
                    f"   📋 {html_escape(s.visa_type)}\n"
                    f"   📅 {html_escape(s.date)} {html_escape(s.time_slot)}\n"
                    f"   🔍 {html_escape(s.detection_method)} ({html_escape(s.confidence)})\n"
                    f"   🔗 <a href='{url}'>Book Now</a>\n"
                )
            chunks = self._telegram_chunks(header, blocks)

            sent = 0
            for chat_id in cfg.get("chat_ids", []):
                for chunk in chunks:
                    if self._post_telegram(cfg, chat_id, chunk):
                        sent += 1
            self.log.info(f"Telegram sent ({sent} message(s), {len(chunks)} chunk(s)/chat)")
        except Exception as e:
            self.log.error(f"Telegram failed: {e}")

    def _send_discord(self, slots, cfg):
        try:
            embeds = []
            for s in slots:
                color = 0x10b981 if s.confidence == "high" else 0xf59e0b
                embeds.append({
                    "title": f"🎯 {s.country} — {s.city}",
                    "description": (
                        f"**Visa:** {s.visa_type}\n"
                        f"**Date:** {s.date}\n"
                        f"**Time:** {s.time_slot}\n"
                        f"**Method:** {s.detection_method} ({s.confidence})\n"
                        f"[Book Now]({s.booking_url})"
                    ),
                    "color": color,
                })

            for i in range(0, len(embeds), 10):
                resp = requests.post(cfg["webhook_url"], json={
                    "content": f"🎯 **{len(slots)} Visa Slot(s) Found!**",
                    "embeds": embeds[i:i+10],
                }, timeout=10)
                if resp.status_code >= 400:
                    self.log.error(
                        f"Discord send failed: HTTP {resp.status_code} {resp.text[:120]}"
                    )
            self.log.info("Discord sent")
        except Exception as e:
            self.log.error(f"Discord failed: {e}")

    def _send_webhook(self, slots, cfg):
        """v4.4.0: generic JSON webhook. Works with ntfy, Slack incoming
        webhooks (as a raw JSON payload), Home Assistant, n8n, etc."""
        try:
            payload = {
                "event": "visa_slots_found",
                "count": len(slots),
                "sent_at": utc_now_iso(),
                "slots": [s.to_dict() for s in slots],
            }
            headers = {"Content-Type": "application/json"}
            headers.update(cfg.get("headers", {}))
            resp = requests.post(cfg["url"], json=payload,
                                 headers=headers, timeout=10)
            if resp.status_code >= 400:
                self.log.error(
                    f"Webhook send failed: HTTP {resp.status_code} {resp.text[:120]}"
                )
            else:
                self.log.info(f"Webhook sent ({resp.status_code})")
        except Exception as e:
            self.log.error(f"Webhook failed: {e}")

    def _desktop_alert(self, slots):
        """Display a desktop toast notification.

        v3.2.2d: adds win32 branch (was missing — silent failure on Windows for
        all of v3.0–v3.2.2c). Logs success/failure explicitly; replaces the
        bare except with typed exception handlers so failures surface in logs.
        """
        import subprocess
        countries_set = sorted(set(s.country for s in slots))
        countries_display = ", ".join(countries_set[:5]) + (
            f" (+{len(countries_set)-5} more)" if len(countries_set) > 5 else ""
        )
        msg = f"{len(slots)} visa slot(s): {countries_display}"
        title = "🎯 Visa Slot Alert"

        try:
            if sys.platform == "darwin":
                # macOS: osascript display notification
                # Escape double quotes in msg/title for AppleScript
                safe_msg = msg.replace('"', '\\"')
                safe_title = title.replace('"', '\\"')
                subprocess.run(
                    ["osascript", "-e",
                     f'display notification "{safe_msg}" with title "{safe_title}" sound name "Glass"'],
                    check=True, timeout=10,
                )
                self.log.info(f"  ✓ Desktop toast sent (macOS): {msg}")

            elif sys.platform == "linux":
                # Linux: notify-send via libnotify
                subprocess.run(
                    ["notify-send", "-u", "critical", "-t", "30000", title, msg],
                    check=True, timeout=10,
                )
                self.log.info(f"  ✓ Desktop toast sent (Linux): {msg}")

            elif sys.platform == "win32":
                # Windows: try windows-toasts library first (clean Win10/11 toast),
                # fall back to PowerShell BalloonTip (no extra dependencies needed).
                try:
                    from windows_toasts import Toast, WindowsToaster
                    toaster = WindowsToaster("Visa Tracker")
                    toast = Toast()
                    toast.text_fields = [title, msg]
                    toaster.show_toast(toast)
                    self.log.info(f"  ✓ Desktop toast sent (Windows, windows-toasts): {msg}")
                except ImportError:
                    # Fallback: PowerShell System.Windows.Forms BalloonTip
                    # Escape single quotes (we use single quotes around args)
                    safe_msg = msg.replace("'", "''")
                    safe_title = title.replace("'", "''")
                    ps_cmd = (
                        '[reflection.assembly]::loadwithpartialname("System.Windows.Forms") | Out-Null;'
                        '[reflection.assembly]::loadwithpartialname("System.Drawing") | Out-Null;'
                        '$n = new-object system.windows.forms.notifyicon;'
                        '$n.icon = [System.Drawing.SystemIcons]::Information;'
                        '$n.visible = $true;'
                        f"$n.showballoontip(15000, '{safe_title}', '{safe_msg}', "
                        '[system.windows.forms.tooltipicon]::Info);'
                        'Start-Sleep -Seconds 16; $n.dispose()'
                    )
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    subprocess.run(
                        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                        check=True, timeout=20,
                        creationflags=creationflags,
                    )
                    self.log.info(f"  ✓ Desktop toast sent (Windows, PowerShell BalloonTip): {msg}")
                    self.log.info("    Tip: install 'windows-toasts' (pip) for native Win11 toast UI.")

            else:
                self.log.warning(f"  ⚠ Desktop toast: unsupported platform '{sys.platform}'")

            # Terminal bell as audio cue (best-effort, all platforms)
            try:
                print("\a\a\a", flush=True)
            except Exception:
                pass

        except subprocess.TimeoutExpired:
            self.log.warning(f"  ⚠ Desktop toast timed out after 10-20s")
        except subprocess.CalledProcessError as e:
            self.log.warning(f"  ⚠ Desktop toast subprocess failed (returncode={e.returncode}): {e}")
        except FileNotFoundError as e:
            self.log.warning(f"  ⚠ Desktop toast binary not found: {e}")
        except Exception as e:
            self.log.warning(f"  ⚠ Desktop toast failed: {type(e).__name__}: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WEBSOCKET + HTTP SERVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Server:
    def __init__(self, db: Database, http_port=8080, ws_port=8081, tracker=None):
        self.db = db
        self.http_port = http_port
        self.ws_port = ws_port
        self.ws_clients: set = set()
        self.tracker = tracker  # optional: enables /api/run-now to trigger a cycle
        self._run_now_task = None
        self.log = logging.getLogger("server")

    async def broadcast(self, event: str, data: dict):
        if not self.ws_clients: return
        msg = json.dumps({"type": event, "data": data,
                         "ts": utc_now_iso()})
        dead = set()
        for ws in self.ws_clients:
            try: await ws.send(msg)
            except: dead.add(ws)
        self.ws_clients -= dead

    async def ws_handler(self, websocket):
        self.ws_clients.add(websocket)
        self.log.info(f"WS client connected ({len(self.ws_clients)})")
        try:
            await websocket.send(json.dumps({
                "type": "init",
                "data": {
                    "slots": self.db.get_active_slots(),
                    "checks": self.db.recent_checks(50),
                    "stats": self.db.stats(),
                },
            }))
            async for msg in websocket:
                try:
                    cmd = json.loads(msg)
                    if cmd.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except: pass
        except websockets.exceptions.ConnectionClosed: pass
        finally:
            self.ws_clients.discard(websocket)

    async def http_handler(self, request):
        path = request.path
        method = request.method

        # CORS preflight
        if method == "OPTIONS":
            return aiohttp_web.Response(status=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })

        cors = {"Access-Control-Allow-Origin": "*"}

        # POST /api/run-now — manual trigger from dashboard
        if path == "/api/run-now" and method == "POST":
            if not self.tracker:
                return aiohttp_web.json_response(
                    {"ok": False, "error": "Tracker not attached to server"},
                    status=503, headers=cors,
                )
            # Don't queue multiple manual runs; if one is in-flight, just acknowledge
            if self._run_now_task and not self._run_now_task.done():
                return aiohttp_web.json_response(
                    {"ok": True, "queued": False, "msg": "Manual cycle already running"},
                    headers=cors,
                )
            self._run_now_task = asyncio.create_task(self.tracker.run_cycle())
            return aiohttp_web.json_response(
                {"ok": True, "queued": True, "msg": "Manual cycle started"},
                headers=cors,
            )

        # GET endpoints
        getters = {
            "/api/slots":  lambda: self.db.get_active_slots(),
            "/api/checks": lambda: self.db.recent_checks(100),
            "/api/stats":  lambda: self.db.stats(),
            "/api/wait-times": lambda: self.db.get_all_wait_times(),  # v4.4.0
            "/api/health": lambda: {
                "status": "ok",
                "version": __version__,
                "clients": len(self.ws_clients),
                "tracker_attached": self.tracker is not None,
                "running": getattr(self.tracker, "_running", None) if self.tracker else None,
            },
        }
        handler = getters.get(path)
        if not handler:
            return aiohttp_web.Response(status=404, headers=cors)
        try:
            return aiohttp_web.json_response(handler(), headers=cors)
        except Exception as e:
            self.log.error(f"HTTP handler error on {path}: {e}")
            return aiohttp_web.json_response({"error": str(e)}, status=500, headers=cors)

    async def start(self):
        # Keep a reference on self — a bare local would be eligible for GC
        # after start() returns.
        self._ws_server = await websockets.serve(self.ws_handler, "0.0.0.0", self.ws_port)
        self.log.info(f"WebSocket: ws://0.0.0.0:{self.ws_port}")

        app = aiohttp_web.Application()
        # GETs
        for path in ["/api/slots", "/api/checks", "/api/stats",
                     "/api/wait-times", "/api/health"]:
            app.router.add_get(path, self.http_handler)
            app.router.add_options(path, self.http_handler)
        # POSTs
        app.router.add_post("/api/run-now", self.http_handler)
        app.router.add_options("/api/run-now", self.http_handler)

        runner = aiohttp_web.AppRunner(app)
        await runner.setup()
        await aiohttp_web.TCPSite(runner, "0.0.0.0", self.http_port).start()
        self.log.info(f"HTTP API: http://0.0.0.0:{self.http_port}")
        self.log.info(f"  Endpoints: /api/slots, /api/checks, /api/stats, /api/wait-times, /api/health, /api/run-now")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# v4.4.0: trackers register here so the SIGINT handler can stop them cleanly.
_ACTIVE_TRACKERS: list = []


def _default_targets_from_registry() -> list[dict]:
    """Seed default targets from the centers.json registry. Falls back to a
    hand-curated short list if the registry is missing or empty.

    Selects all enabled centers with priority='high' or 'medium' to keep the
    bootstrap experience reasonable (~40 targets) without overwhelming a
    fresh install. Lower-priority countries can be added by editing config.

    v4.0.0: each target now has a `tier` field (default 'cold'). Use the
    `set-tier` CLI command to promote countries to 'hot' or 'warm'.
    """
    targets: list[dict] = []
    # v4.4.0 fix: dedupe key is (country, processor), and cities MERGE
    # across centers instead of first-one-wins. The registry keeps one
    # center per US consulate — 36 entries all named "United States" — and
    # the old country-only dedupe collapsed them to the single first city,
    # so 35 of the 36 US consulates were silently never monitored.
    by_key: dict[tuple, dict] = {}
    if CENTERS_REGISTRY:
        for c in CENTERS_REGISTRY.get("centers", []):
            if not c.get("enabled"):
                continue
            if c.get("priority") not in ("high", "medium"):
                continue
            # v4.0.0: skip visa-free / e-visa entries even if priority allows
            if c.get("_indian_passport_status") in ("visa_free", "evisa"):
                continue
            name = c.get("destination_country")
            if not name:
                continue
            key = (name, c.get("processor"))
            existing = by_key.get(key)
            if existing is None:
                entry = {
                    "country": name,
                    "cities": list(c.get("indian_cities", ["New Delhi"])),
                    "visa_types": c.get("visa_types", ["Tourist", "Business"]),
                    "processor": c.get("processor"),
                    "tier": c.get("tier", "cold"),  # v4.0.0
                }
                by_key[key] = entry
                targets.append(entry)
            else:
                for city in c.get("indian_cities", []):
                    if city not in existing["cities"]:
                        existing["cities"].append(city)
                # A hotter tier on any merged center wins for the target
                tier_rank = {"hot": 3, "warm": 2, "cold": 1}
                if tier_rank.get(c.get("tier", "cold"), 1) > tier_rank.get(existing["tier"], 1):
                    existing["tier"] = c.get("tier", "cold")
    if targets:
        return targets
    # Hand-curated fallback (registry missing)
    return [
        {"country": "United Kingdom", "cities": ["New Delhi", "Mumbai", "Chennai", "Bengaluru"],
         "visa_types": ["Standard Visitor", "Student", "Skilled Worker"], "processor": "vfs_global",
         "tier": "cold"},
        {"country": "Canada", "cities": ["New Delhi", "Mumbai", "Bengaluru", "Chandigarh"],
         "visa_types": ["Visitor", "Study Permit", "Work Permit"], "processor": "vfs_global",
         "tier": "cold"},
        {"country": "Germany", "cities": ["New Delhi", "Mumbai", "Chennai", "Bengaluru"],
         "visa_types": ["Schengen", "National", "Student"], "processor": "vfs_global",
         "tier": "cold"},
        {"country": "France", "cities": ["New Delhi", "Mumbai", "Chennai", "Bengaluru"],
         "visa_types": ["Schengen-Tourist", "Schengen-Business"], "processor": "vfs_global",
         "tier": "cold"},
        {"country": "Spain", "cities": ["New Delhi", "Mumbai", "Bengaluru", "Chennai"],
         "visa_types": ["Schengen-Tourist", "Schengen-Business"], "processor": "bls_international",
         "tier": "cold"},
    ]


class VisaTracker:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.db = Database()
        self.browser = BrowserManager(self.config.get("browser", {}))
        self.checker = UnifiedChecker(self.browser, self.db)
        self.notifier = Notifier(self.config)
        self.calibrator = Calibrator(self.browser, self.db)
        self.server: Optional[Server] = None
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get("max_concurrent", 2)
        )
        self._running = True
        # v4.4.0: registered so the SIGINT handler can shut the executor
        # down instead of leaving non-daemon worker threads to hang exit.
        _ACTIVE_TRACKERS.append(self)

    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            # v3.2.2c: utf-8-sig transparently strips a UTF-8 BOM if present.
            # PowerShell's `Out-File -Encoding utf8` (and Set-Content) writes
            # files with a BOM by default, which makes Python's plain
            # json.load() crash with "Expecting value: line 1 column 1".
            # utf-8-sig accepts both BOM and non-BOM input.
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f)
        cfg = self._default_config()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        log.info(f"Default config written to {path}")
        return cfg

    def _default_config(self) -> dict:
        return {
            "check_interval_seconds": 180,
            "max_concurrent": 2,
            "desktop_alerts": True,
            # v4.0.0 — tier system. Used only when running with --tiered flag.
            # Hot tier countries are checked every 10 min, cold every 90 min.
            "tier_intervals": {
                "hot":  600,    # 10 min — for immigration priorities
                "warm": 1800,   # 30 min — for active interest countries
                "cold": 5400,   # 90 min — for the long tail
            },
            "browser": {"headless": True, "page_timeout": 30, "proxies": []},
            "email": {
                "enabled": False, "smtp_host": "smtp.gmail.com", "smtp_port": 587,
                "sender": "", "password": "", "recipients": []
            },
            "telegram": {"bot_token": "", "chat_ids": []},
            "discord": {"webhook_url": ""},
            "webhook": {"url": ""},  # v4.4.0: generic JSON webhook
            "instant_notify": True,
            "targets": _default_targets_from_registry()
        }

    async def check_target(self, target: dict) -> list[SlotInfo]:
        country = target["country"]
        cities = target.get("cities", ["New Delhi"])
        visa_types = target.get("visa_types", ["Tourist"])
        loop = asyncio.get_event_loop()
        new_slots = []

        for city in cities:
            if not self._running: break
            try:
                result = await loop.run_in_executor(
                    self.executor, self.checker.check, country, city, visa_types
                )
                self.db.log_check(result)

                for slot in result.slots:
                    if self.db.is_new(slot):
                        self.db.save_slot(slot)
                        new_slots.append(slot)

                icon = {"slots_found": "🎯", "page_changed": "🔔",
                        "no_change": "·", "baseline": "📋",
                        "captcha": "🛡", "error": "❌",
                        "login_needed": "🔐"}.get(result.status, "?")

                log.info(f"  {icon} {country}/{city}: {result.status} "
                        f"({result.duration_ms}ms) [{result.method}]")

                if self.server:
                    await self.server.broadcast("check", {
                        "country": country, "city": city,
                        "status": result.status,
                        "slots_found": len(result.slots),
                        "method": result.method,
                    })

            except Exception as e:
                log.error(f"  ❌ {country}/{city}: {e}")

            await asyncio.sleep(random.uniform(2, 5))

        # v4.3.0 — instant notification.
        # In v4.2.x and earlier, notifications fired only at end of cycle.
        # When we ran the May 6 2026 production cycle, Czech Republic was
        # detected at 03:17 but the toast didn't fire until 03:43 — a 26-min
        # lag while the cycle walked through every other country. For a
        # competitive slot this is too slow. v4.3.0 fires the notification
        # the moment a target produces new slots; the cycle-end batch then
        # skips slots already notified to avoid duplicate alerts.
        # Disable via config: {"instant_notify": false}
        if new_slots and self.config.get("instant_notify", True):
            try:
                await loop.run_in_executor(None, self.notifier.send, new_slots)
                # Mark these so cycle-end batch doesn't re-notify
                for s in new_slots:
                    s._instant_sent = True
                if not self.notifier.dry_run:
                    self.db.mark_notified([s.uid for s in new_slots])
            except Exception as e:
                log.error(f"  ❌ Instant notification failed for {country}: {e}")
                # Don't mark as sent — let cycle-end batch retry

        return new_slots

    async def run_cycle(self) -> list[SlotInfo]:
        log.info(f"\n{'━'*60}")
        log.info(f"🔍 Check cycle — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        targets = self.config.get("targets", [])
        all_new = []

        for target in targets:
            if not self._running: break
            result = await self.check_target(target)
            all_new.extend(result)

        if all_new:
            # v4.3.0 — skip slots already notified instantly during the cycle
            pending = [s for s in all_new if not getattr(s, '_instant_sent', False)]
            instant_count = len(all_new) - len(pending)

            if instant_count > 0 and pending:
                log.info(f"🎯 {len(all_new)} NEW slot(s): {instant_count} notified "
                        f"instantly during cycle, {len(pending)} pending end-of-cycle batch")
            elif instant_count > 0:
                log.info(f"🎯 {len(all_new)} NEW slot(s) — all notified instantly during cycle")
            else:
                log.info(f"🎯 {len(all_new)} NEW slot(s) found!")

            if pending:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.notifier.send, pending)
                if not self.notifier.dry_run:
                    self.db.mark_notified([s.uid for s in pending])
            if self.server:
                await self.server.broadcast("new_slots", {
                    "slots": [s.to_dict() for s in all_new],
                    "count": len(all_new),
                })
        else:
            log.info("No new slots this cycle")

        self.db.expire_old(7)
        log.info(f"{'━'*60}")
        return all_new

    async def run_monitor(self):
        interval = self.config.get("check_interval_seconds", 180)
        targets = self.config.get("targets", [])
        log.info(f"Monitor started: {len(targets)} targets, {interval}s interval")
        warned_about_interval = False

        while self._running:
            cycle_start = time.time()
            try: await self.run_cycle()
            except Exception as e: log.error(f"Cycle error: {e}")
            cycle_duration = time.time() - cycle_start

            # v3.2.2: warn loudly if cycle takes longer than 2× interval — the
            # v3.2 production log showed 65-135 min cycles against a 3-min
            # interval, meaning the loop runs back-to-back continuously.
            if cycle_duration > 2 * interval and not warned_about_interval:
                log.warning(
                    f"⚠ INTERVAL MISMATCH: cycle took {cycle_duration:.0f}s "
                    f"({cycle_duration/60:.0f}min) but check_interval is {interval}s "
                    f"({interval/60:.0f}min). The tracker is running back-to-back, "
                    f"not polling. Either: (a) reduce target count, "
                    f"(b) raise interval to ~{int(cycle_duration*1.2)}s, "
                    f"or (c) accept continuous mode. This warning fires once."
                )
                warned_about_interval = True

            log.info(f"Next check in {interval}s...")
            await asyncio.sleep(interval)

    async def run_monitor_tiered(self):
        """v4.0.0: Tier-aware priority-queue scheduler.

        Each (country, city) target carries a tier inherited from centers.json
        (`hot` / `warm` / `cold`). Each tier has its own polling interval
        from config.json (`tier_intervals`). The scheduler picks the next-due
        target at any moment, checks it, then reschedules at `now + interval`.

        Result: hot countries get checked every ~10 min, cold countries
        every ~90 min, all from a single Python process with one Chrome
        worker (so VFS still sees human-pattern traffic, no Cloudflare
        flagging risk).

        Backward compat: targets without a tier default to "cold".
        Centers without a tier in centers.json default to "cold".
        Old config.json files without `tier_intervals` get sensible defaults.
        """
        from heapq import heappush, heappop
        import itertools

        # ── Build the per-(country, city) work queue ────────────────────────
        # Targets in config look like: {"country": "UK", "cities": [...], "tier": "hot"}
        # We expand them to per-city items so each city can be scheduled separately.
        tier_intervals = self.config.get("tier_intervals", {
            "hot":  600,    # 10 min
            "warm": 1800,   # 30 min
            "cold": 5400,   # 90 min
        })

        # Sanity check: hot interval should be at least 5x check duration to
        # avoid the queue running back-to-back on hot targets only.
        min_interval = min(tier_intervals.values())
        if min_interval < 60:
            log.warning(
                f"⚠ TIER CONFIG: min tier interval is {min_interval}s. "
                f"That's aggressive — recommend ≥300s (5min) to avoid VFS "
                f"rate-limit detection."
            )

        targets = self.config.get("targets", [])
        if not targets:
            log.error("No targets configured. Run: python visa_tracker_v3.py select-countries")
            return

        # Priority queue: (next_due_unix_ts, tiebreaker, work_item)
        # tiebreaker keeps insertion order stable for equal timestamps
        counter = itertools.count()
        queue: list = []
        now = time.time()

        # Spread initial schedules across a small window so we don't slam VFS
        # the moment the tracker starts.
        spread_seconds = min(60, len(targets))
        for idx, target in enumerate(targets):
            country = target["country"]
            cities = target.get("cities", ["New Delhi"])
            visa_types = target.get("visa_types", ["Tourist"])
            tier = target.get("tier", "cold")
            for city in cities:
                # Stagger first checks within the spread window
                first_check = now + (idx * spread_seconds / max(1, len(targets)))
                heappush(queue, (
                    first_check, next(counter),
                    {"country": country, "city": city,
                     "visa_types": visa_types, "tier": tier},
                ))

        # Tier counts for log header
        tier_counts: dict[str, int] = {}
        for _, _, item in queue:
            tier_counts[item["tier"]] = tier_counts.get(item["tier"], 0) + 1
        log.info(
            f"Tiered monitor started: {len(queue)} targets — "
            + ", ".join(f"{n} {t}" for t, n in sorted(tier_counts.items()))
        )
        log.info(
            f"  Intervals: "
            + ", ".join(f"{t}={tier_intervals.get(t, 5400)}s" for t in sorted(tier_intervals))
        )

        # Per-cycle accumulator: collect new slots from a tier's pass and
        # notify together rather than one-at-a-time. We notify whenever the
        # queue's next-due time is more than 30s in the future (i.e., we
        # have idle time before the next check).
        pending_alerts: list[SlotInfo] = []
        loop = asyncio.get_event_loop()

        # ── Main scheduling loop ─────────────────────────────────────────────
        while self._running:
            # Flush pending notifications if we're idle (no immediate work
            # AND we have alerts waiting) OR if buffer is getting big
            if pending_alerts and (
                (queue and queue[0][0] > time.time() + 30) or
                len(pending_alerts) >= 5
            ):
                log.info(f"🎯 {len(pending_alerts)} NEW slot(s) found! (tiered batch)")
                try:
                    await loop.run_in_executor(None, self.notifier.send, pending_alerts)
                    if not self.notifier.dry_run:
                        self.db.mark_notified([s.uid for s in pending_alerts])
                    if self.server:
                        await self.server.broadcast("new_slots", {
                            "slots": [s.to_dict() for s in pending_alerts],
                            "count": len(pending_alerts),
                        })
                except Exception as e:
                    log.error(f"Notification dispatch failed: {e}")
                pending_alerts = []

            # Wait until next due
            if not queue:
                log.warning("Queue empty — exiting tiered monitor")
                break

            next_due, _, item = queue[0]
            wait_for = next_due - time.time()
            if wait_for > 0:
                # Sleep in 30s chunks so Ctrl+C / shutdown is responsive
                while wait_for > 0 and self._running:
                    chunk = min(30.0, wait_for)
                    await asyncio.sleep(chunk)
                    wait_for = next_due - time.time()
                if not self._running:
                    break

            # Pop and check
            _, _, item = heappop(queue)
            country, city = item["country"], item["city"]
            tier = item["tier"]

            try:
                # Run the actual check via the existing checker (preserves
                # the validated v3.2.x detection pipeline verbatim)
                result = await loop.run_in_executor(
                    self.executor,
                    self.checker.check, country, city, item["visa_types"],
                )
                self.db.log_check(result)

                fresh: list[SlotInfo] = []
                for slot in result.slots:
                    if self.db.is_new(slot):
                        self.db.save_slot(slot)
                        fresh.append(slot)

                # v4.4.0: tiered mode now honors instant_notify too. v4.3.0
                # only wired instant alerts into the plain cycle runner, so
                # a hot-tier detection could still sit in pending_alerts
                # until the next idle window — exactly the lag instant
                # notification was built to remove.
                if fresh and self.config.get("instant_notify", True):
                    try:
                        await loop.run_in_executor(None, self.notifier.send, fresh)
                        if not self.notifier.dry_run:
                            self.db.mark_notified([s.uid for s in fresh])
                        if self.server:
                            await self.server.broadcast("new_slots", {
                                "slots": [s.to_dict() for s in fresh],
                                "count": len(fresh),
                            })
                    except Exception as e:
                        log.error(f"Instant notification failed for {country}: {e}")
                        pending_alerts.extend(fresh)  # let the batch retry
                else:
                    pending_alerts.extend(fresh)

                icon = {"slots_found": "🎯", "page_changed": "🔔",
                        "no_change": "·", "baseline": "📋",
                        "captcha": "🛡", "error": "❌",
                        "login_needed": "🔐"}.get(result.status, "?")
                tier_label = {"hot": "🔥", "warm": "🌤", "cold": "❄"}.get(tier, "?")
                log.info(
                    f"  {icon} {tier_label} {country}/{city}: {result.status} "
                    f"({result.duration_ms}ms) [{result.method}]"
                )

                if self.server:
                    await self.server.broadcast("check", {
                        "country": country, "city": city, "tier": tier,
                        "status": result.status,
                        "slots_found": len(result.slots),
                        "method": result.method,
                    })
            except Exception as e:
                log.error(f"  ❌ {tier} {country}/{city}: {e}")

            # Reschedule based on tier
            interval = tier_intervals.get(tier, 5400)
            heappush(queue, (
                time.time() + interval, next(counter), item,
            ))

            # Anti-bot jitter — random 2-5s pause between checks
            await asyncio.sleep(random.uniform(2, 5))

            # Periodic DB cleanup (every ~hour worth of checks)
            if int(time.time()) % 3600 < 5:
                self.db.expire_old(7)

        # Flush any remaining alerts on shutdown
        if pending_alerts:
            log.info(f"Flushing {len(pending_alerts)} pending alerts before shutdown")
            try:
                await loop.run_in_executor(None, self.notifier.send, pending_alerts)
            except Exception as e:
                log.error(f"Final flush failed: {e}")
        log.info("Tiered monitor stopped cleanly.")

    async def run_with_server(self):
        self.server = Server(self.db, tracker=self)
        await self.server.start()
        await self.run_monitor()

    async def run_server_only(self):
        # Server-only mode: still pass tracker reference so /api/run-now works
        self.server = Server(self.db, tracker=self)
        await self.server.start()
        log.info("Server running. Ctrl+C to stop.")
        await asyncio.Future()

    def stop(self):
        self._running = False
        # cancel_futures drops queued checks so a Ctrl+C doesn't hang on the
        # executor's atexit join while a backlog of Selenium jobs drains.
        self.executor.shutdown(wait=False, cancel_futures=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INTERACTIVE SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def interactive_setup():
    """Walk the user through first-time configuration."""
    print("\n" + "="*60)
    print("  🇮🇳  VISA SLOT TRACKER — SETUP WIZARD")
    print("="*60 + "\n")

    config = {
        "check_interval_seconds": 180,
        "max_concurrent": 2,
        "desktop_alerts": True,
        "browser": {"headless": True, "page_timeout": 30, "proxies": []},
        "email": {"enabled": False, "smtp_host": "smtp.gmail.com",
                  "smtp_port": 587, "sender": "", "password": "", "recipients": []},
        "telegram": {"bot_token": "", "chat_ids": []},
        "discord": {"webhook_url": ""},
        "webhook": {"url": ""},
        "instant_notify": True,
        "targets": [],
    }

    # ── Notification setup ──
    print("STEP 1: Notification Channels\n")

    email = input("  Enable email alerts? (y/n): ").strip().lower() == "y"
    if email:
        config["email"]["enabled"] = True
        config["email"]["sender"] = input("  Gmail address: ").strip()
        config["email"]["password"] = input("  Gmail App Password: ").strip()
        config["email"]["recipients"] = [input("  Recipient email: ").strip()]

    print()
    tg = input("  Enable Telegram alerts? (y/n): ").strip().lower() == "y"
    if tg:
        config["telegram"]["bot_token"] = input("  Bot token (from @BotFather): ").strip()
        config["telegram"]["chat_ids"] = [input("  Chat ID (from @userinfobot): ").strip()]

    print()
    disc = input("  Enable Discord alerts? (y/n): ").strip().lower() == "y"
    if disc:
        config["discord"]["webhook_url"] = input("  Webhook URL: ").strip()

    # ── Country selection ──
    print("\nSTEP 2: Which countries to monitor?\n")
    print("  Available countries:")

    all_countries = list_supported_countries()
    for i, c in enumerate(all_countries):
        # Annotate each line with the processor so users see what they're picking
        rec = COUNTRY_INDEX.get(c.strip().lower(), {})
        proc = rec.get("processor", "")
        proc_label = f" [{proc}]" if proc else ""
        print(f"    {i+1:2d}. {c}{proc_label}")

    print(f"\n  Enter country numbers separated by commas (e.g., 1,3,5)")
    print(f"  Or type 'all' for all {len(all_countries)} countries")
    selection = input("\n  Selection: ").strip()

    if selection.lower() == "all":
        selected = all_countries
    else:
        indices = [int(x.strip())-1 for x in selection.split(",") if x.strip().isdigit()]
        selected = [all_countries[i] for i in indices if 0 <= i < len(all_countries)]

    # ── City selection per country ──
    print("\nSTEP 3: Cities per country\n")
    # v4.4.0: "Bangalore" → "Bengaluru" to match centers.json / VFS naming
    cities = ["New Delhi", "Mumbai", "Chennai", "Bengaluru", "Hyderabad",
              "Kolkata", "Pune", "Ahmedabad", "Chandigarh"]
    print("  Available cities: " + ", ".join(cities))
    print("  (Press Enter for default: New Delhi, Mumbai, Chennai, Bengaluru, Hyderabad)\n")

    default_cities = ["New Delhi", "Mumbai", "Chennai", "Bengaluru", "Hyderabad"]
    city_input = input("  Cities (comma-separated, or Enter for default): ").strip()
    if city_input:
        chosen_cities = [c.strip() for c in city_input.split(",")]
    else:
        chosen_cities = default_cities

    # Build targets — carry processor + tier so tiered mode and dispatch
    # work the same as select-countries-generated configs (v4.4.0)
    for country in selected:
        rec = COUNTRY_INDEX.get(country.strip().lower(), {})
        config["targets"].append({
            "country": country,
            "cities": chosen_cities,
            "visa_types": ["Tourist", "Business", "Student"],  # safe defaults
            "processor": rec.get("processor", "unknown"),
            "tier": rec.get("tier", "cold"),
        })

    # ── Check interval ──
    print(f"\nSTEP 4: Check interval")
    interval = input("  Seconds between checks (default 180): ").strip()
    if interval.isdigit():
        config["check_interval_seconds"] = int(interval)

    # ── Save ──
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Config saved to config.json")
    print(f"  {len(selected)} countries, {len(chosen_cities)} cities each")
    print(f"\n  Next steps:")
    print(f"    1. python visa_tracker_v3.py calibrate --all")
    print(f"    2. python visa_tracker_v3.py run")
    print(f"{'='*60}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _first_run_disclaimer_check():
    """v4.2.1 — Show a one-time disclaimer on first CLI invocation.

    Writes a small acknowledgment marker to ~/.visa_tracker_acknowledged
    after the user accepts. Skipped on subsequent runs.

    The purpose is to (a) ensure every user reads the project's scope and
    intended-use statement at least once, (b) document downstream user
    accountability for compliance with portal terms of service and local
    law, and (c) shift contractual privity to the user — the maintainer
    publishes source code under MIT; the user runs it on their own
    infrastructure under their own responsibility. See LEGAL.md.

    Set environment variable VISA_TRACKER_NO_PROMPT=1 to skip (intended
    for CI/CD and automated GitHub Actions workflows where the operator
    is the same as the deployer and has already acknowledged).
    """
    import os as _os
    from pathlib import Path as _Path

    # CI/automation skip
    if _os.environ.get("VISA_TRACKER_NO_PROMPT") == "1":
        return
    if _os.environ.get("CI") or _os.environ.get("GITHUB_ACTIONS"):
        return

    marker_path = _Path.home() / ".visa_tracker_acknowledged"
    if marker_path.exists():
        return

    # Skip for one-shot informational commands that don't actually monitor
    skip_for_cmds = {"--help", "-h", "help", "version", "--version", "selftest"}
    if len(sys.argv) >= 2 and sys.argv[1] in skip_for_cmds:
        return

    print()
    print("=" * 72)
    print("  Visa Slot Tracker — First-Run Notice")
    print("=" * 72)
    print()
    print("  This is open-source RESEARCH AND EDUCATIONAL software.")
    print()
    print("  WHAT IT DOES:")
    print("    Read-only monitoring of publicly available visa-availability")
    print("    pages and US Department of State public wait-time data. Notifies")
    print("    you when the data changes. That is the entire scope.")
    print()
    print("  WHAT IT DOES NOT DO:")
    print("    Does NOT book, reschedule, or cancel appointments.")
    print("    Does NOT store or use any user credentials.")
    print("    Does NOT bypass CAPTCHAs or use proxy/VPN evasion.")
    print("    Does NOT collect personal data of any visa applicant.")
    print("    Has NO affiliation with VFS Global, BLS, TLScontact, CGI Federal,")
    print("    the US Department of State, or any embassy/consulate.")
    print()
    print("  YOUR RESPONSIBILITY:")
    print("    You are responsible for complying with the terms of service of")
    print("    any portal you choose to monitor and the laws of your jurisdiction.")
    print("    You are responsible for the consequences of any appointment you")
    print("    book using information surfaced by this tool. The booking action")
    print("    happens entirely OUTSIDE this software through official channels.")
    print()
    print("  IMPORTANT:")
    print("    The US Embassy in India announced in March 2025 the cancellation")
    print("    of ~2,000 appointments made by booking bots. This software does")
    print("    NOT auto-book and is not the kind of tool that announcement")
    print("    targeted. But applicants who manipulate any visa scheduling")
    print("    system (regardless of method) face appointment cancellation,")
    print("    visa refusal, or visa cancellation. Use information from this")
    print("    tool to manually book appointments through legitimate channels.")
    print()
    print("  Read DISCLAIMER.md and LEGAL.md before continuing.")
    print()
    print("=" * 72)
    print()
    try:
        response = input("  Type 'yes' to acknowledge and continue: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print("  Acknowledgment required. Exiting.")
        sys.exit(1)

    if response != "yes":
        print()
        print("  Acknowledgment declined. Exiting.")
        print("  (Run again and type 'yes' if you have read and understood")
        print("   the scope, limitations, and your responsibilities.)")
        sys.exit(1)

    # Write the marker so we don't prompt again
    try:
        marker_path.write_text(
            f"acknowledged at {datetime.now().isoformat()}\n"
            f"version: {__version__}\n"
            f"see DISCLAIMER.md and LEGAL.md in the repository\n"
        )
    except Exception as e:
        # Non-fatal — re-prompting is fine if we can't write the marker
        log.warning(f"Could not write acknowledgment marker: {e}")

    print()
    print("  Thank you. Acknowledgment recorded. Continuing...")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    # v4.2.1 — first-run disclaimer
    _first_run_disclaimer_check()

    def _sigint_handler(*_):
        log.info("Stopping...")
        # v4.4.0: stop trackers so the ThreadPoolExecutor's atexit join
        # doesn't hang the process on queued Selenium work.
        for t in _ACTIVE_TRACKERS:
            try:
                t.stop()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint_handler)

    if cmd == "setup":
        interactive_setup()

    elif cmd == "verify-urls":
        # v3.2.1 — Preflight every enabled center URL with a quick HEAD/GET
        # and report DNS errors, 404s, Cloudflare blocks. Runs in seconds and
        # saves you from a 90-minute calibration on broken URLs.
        #
        # This was added because v3.2 shipped 4 BLS URLs that were
        # pattern-generated (Portugal, Algeria, Tunisia, Mozambique) and
        # only discovered to be broken after a long calibration run.
        import socket
        from urllib.parse import urlparse as _urlparse

        if not CENTERS_REGISTRY:
            print("centers.json not loaded — nothing to verify.")
            return

        centers = [c for c in CENTERS_REGISTRY.get("centers", [])
                   if c.get("enabled") and c.get("appointment_url")]
        # Allow filtering: verify-urls --processor vfs_global
        proc_filter = None
        for i, arg in enumerate(sys.argv):
            if arg == "--processor" and i+1 < len(sys.argv):
                proc_filter = sys.argv[i+1]
        if proc_filter:
            centers = [c for c in centers if c.get("processor") == proc_filter]

        print("\n" + "="*72)
        print(f"  VISA TRACKER — URL PREFLIGHT  ({len(centers)} centers)")
        print("="*72)

        results = {"ok": [], "dns_fail": [], "cloudflare": [],
                   "client_error": [], "server_error": [], "timeout": []}

        for c in centers:
            url = c["appointment_url"]
            country = c["destination_country"]
            host = _urlparse(url).hostname or ""

            # Stage 1: DNS resolution
            try:
                socket.getaddrinfo(host, None)
            except socket.gaierror:
                print(f"  ❌ DNS    {country:<30} {url[:60]}")
                results["dns_fail"].append((country, url))
                continue
            except Exception as e:
                print(f"  ❌ NET    {country:<30} {str(e)[:50]}")
                results["dns_fail"].append((country, url))
                continue

            # Stage 2: HTTP probe — use streaming GET (not HEAD).
            # v3.2.2b fix: Cloudflare returns 404 to HEAD requests on SPA
            # root routes (very common pattern with "Cache Everything"
            # rules). v3.2.2a only fell back to GET on 405, which meant
            # 69/70 VFS Global URLs got reported as broken when they were
            # actually fine. Streaming GET reads only the first 4KB which
            # is enough for status code + Cloudflare challenge detection
            # without downloading the full SPA payload.
            try:
                r = requests.get(url, timeout=10, allow_redirects=True,
                                 stream=True,
                                 headers={"User-Agent": rand_ua()})
                code = r.status_code
                # Read just enough to detect CF challenge pages
                try:
                    chunk = next(r.iter_content(4096), b"")
                    snippet = chunk.decode("utf-8", errors="replace").lower()
                except Exception:
                    snippet = ""
                finally:
                    try: r.close()
                    except Exception: pass
                if "just a moment" in snippet or "challenge-platform" in snippet \
                        or "cf-chl" in snippet or "cf_chl_opt" in snippet:
                    results["cloudflare"].append((country, url))
                    print(f"  🛡 CF    {country:<30} (Cloudflare challenge)")
                    continue
                if 200 <= code < 400:
                    results["ok"].append((country, url))
                    print(f"  ✓ {code:<3}   {country:<30} {url[:60]}")
                elif 400 <= code < 500:
                    results["client_error"].append((country, url, code))
                    print(f"  ❌ {code}   {country:<30} {url[:60]}")
                else:
                    results["server_error"].append((country, url, code))
                    print(f"  ⚠ {code}   {country:<30} {url[:60]}")
            except requests.Timeout:
                results["timeout"].append((country, url))
                print(f"  ⏱ TIME  {country:<30} {url[:60]}")
            except Exception as e:
                results["server_error"].append((country, url, str(e)[:30]))
                print(f"  ⚠ ERR   {country:<30} {str(e)[:50]}")

        # Summary
        print("\n" + "-"*72)
        print(f"  Reachable:        {len(results['ok'])}")
        print(f"  Cloudflare wall:  {len(results['cloudflare'])}  (real, but bot-protected)")
        print(f"  DNS fail:         {len(results['dns_fail'])}  (URL is broken — fix in centers.json)")
        print(f"  4xx errors:       {len(results['client_error'])}  (URL probably wrong)")
        print(f"  5xx errors:       {len(results['server_error'])}  (server problem)")
        print(f"  Timeout:          {len(results['timeout'])}")
        print("="*72)
        if results["dns_fail"] or results["client_error"]:
            print("\n  ⚠ Action needed: fix the entries above in centers.json")
            print(f"  before running `calibrate --all`.")
        else:
            print("\n  ✓ Looks clean — safe to run calibrate.")
        print()

    elif cmd == "calibrate":
        config_path = "config.json"
        workers = 1
        for i, arg in enumerate(sys.argv):
            if arg == "--config" and i+1 < len(sys.argv):
                config_path = sys.argv[i+1]
            if arg == "--workers" and i+1 < len(sys.argv):
                try:
                    workers = max(1, min(8, int(sys.argv[i+1])))
                except ValueError:
                    print(f"Invalid --workers value, using 1")
                    workers = 1

        tracker = VisaTracker(config_path)

        if "--all" in sys.argv:
            countries = [t["country"] for t in tracker.config.get("targets", [])]
            if not countries:
                countries = list_supported_countries()
            tracker.calibrator.calibrate_all(countries, workers=workers)
        elif len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
            # Calibrate specific country
            country_query = " ".join(sys.argv[2:]).strip("-").strip()
            # Strip --workers N if present in tail
            country_query = re.sub(r"\s*--workers\s+\S+\s*", " ", country_query).strip()
            # Fuzzy match across all supported countries
            for name in list_supported_countries():
                if country_query.lower() in name.lower():
                    tracker.calibrator.calibrate_country(name)
                    break
            else:
                print(f"Country '{country_query}' not found")
        else:
            print("Usage: calibrate <country> | calibrate --all [--workers N]")

    elif cmd == "run":
        config_path = "config.json"
        for i, arg in enumerate(sys.argv):
            if arg == "--config" and i+1 < len(sys.argv):
                config_path = sys.argv[i+1]

        tracker = VisaTracker(config_path)

        # v3.2.2: --dry-run suppresses outbound notifications. Useful for
        # the first run after upgrading, in case the new delta classifier
        # still misfires on a country we haven't seen.
        if "--dry-run" in sys.argv:
            tracker.notifier.dry_run = True
            log.warning("⚠ DRY-RUN MODE: notifications will be logged, not sent.")

        # v4.0.0: --tiered uses the priority-queue scheduler instead of the
        # fixed-interval cycle. Each target is rescheduled per its tier
        # (hot=10min, warm=30min, cold=90min by default). Faster latency
        # for hot countries (UK/Germany/Ireland/Singapore/Canada) without
        # spawning extra processes or burning more CPU.
        use_tiered = "--tiered" in sys.argv

        if "--once" in sys.argv:
            asyncio.run(tracker.run_cycle())
        elif "--server" in sys.argv:
            asyncio.run(tracker.run_with_server())
        elif use_tiered:
            asyncio.run(tracker.run_monitor_tiered())
        else:
            asyncio.run(tracker.run_monitor())

    elif cmd == "server":
        config_path = "config.json"
        for i, arg in enumerate(sys.argv):
            if arg == "--config" and i+1 < len(sys.argv):
                config_path = sys.argv[i+1]
        tracker = VisaTracker(config_path)
        asyncio.run(tracker.run_server_only())

    elif cmd == "status":
        # Quick diagnostic: print DB stats, last cycle results, error breakdown.
        # Useful for cron jobs and answering "is it actually working?" without
        # tailing the log file.
        config_path = "config.json"
        for i, arg in enumerate(sys.argv):
            if arg == "--config" and i+1 < len(sys.argv):
                config_path = sys.argv[i+1]
        tracker = VisaTracker(config_path)
        s = tracker.db.stats()
        print("\n" + "="*60)
        print("  VISA TRACKER — STATUS")
        print("="*60)
        print(f"  Active slots:      {s['total_slots']}")
        print(f"  Countries w/slots: {s['countries']}")
        print(f"  Cities w/slots:    {s['cities']}")
        print(f"  Total checks:      {s['total_checks']}")
        print(f"  Error checks:      {s['error_checks']}")
        print(f"  Last check:        {s['last_check'] or 'never'}")
        print()
        # Status breakdown across last 100 checks
        recent = tracker.db.recent_checks(100)
        if recent:
            from collections import Counter
            status_counts = Counter(c["status"] for c in recent)
            print(f"  Last {len(recent)} checks by status:")
            for st, n in status_counts.most_common():
                pct = 100.0 * n / len(recent)
                print(f"    {st:<14s} {n:>4d}  ({pct:.1f}%)")
            # If everything is errors, surface the first error message
            errs = [c for c in recent if c["status"] == "error"]
            if errs and len(errs) >= len(recent) * 0.5:
                print(f"\n  ⚠ Majority of checks are errors. First error:")
                first_err = (errs[0].get("error") or "").split("\n")[0]
                print(f"    {first_err[:200]}")
        else:
            print(f"  No checks logged yet — run `python visa_tracker_v3.py run --once`")

        # v3.2.2: surface JWT health if any countries have tripped the breaker
        try:
            jwt_health = tracker.checker.vfs_jwt.health()
            open_circuits = jwt_health.get("open_circuits", [])
            if open_circuits:
                print()
                print(f"  ⚠ JWT circuit breakers open ({len(open_circuits)} countries):")
                for c in open_circuits[:10]:
                    print(f"    · {c}")
                print(f"    These countries will skip JWT replay until next calibration")
                print(f"    or successful harvest. Reduces silent VFS API failures.")
        except Exception:
            pass
        print("="*60 + "\n")

    elif cmd == "coverage":
        # Show what destinations and processors are currently loaded from
        # centers.json. Useful for verifying the registry is wired up and
        # for picking which countries to enable in config.json.
        from collections import Counter
        if not CENTERS_REGISTRY:
            print("No centers.json registry loaded — using legacy hard-coded URLs.")
            print(f"Legacy VFS countries: {len(VFS_COUNTRIES)}")
            print(f"Legacy BLS countries: {len(BLS_COUNTRIES)}")
            print(f"Legacy TLS countries: {len(TLS_COUNTRIES)}")
            return
        centers = CENTERS_REGISTRY.get("centers", [])
        procs = CENTERS_REGISTRY.get("processors", {})
        print("\n" + "="*60)
        print("  VISA TRACKER — COVERAGE")
        print("="*60)
        print(f"  Registry version:  {CENTERS_REGISTRY.get('version', '?')}")
        print(f"  Total centers:     {len(centers)}")
        print(f"  Enabled centers:   {sum(1 for c in centers if c.get('enabled'))}")
        print(f"  Processors:        {len(procs)}")
        print()
        proc_count = Counter(c["processor"] for c in centers)
        print("  By processor:")
        for p, n in proc_count.most_common():
            enabled = sum(1 for c in centers if c.get("processor") == p and c.get("enabled"))
            print(f"    {p:<22s} {enabled:>3d}/{n} enabled")
        print()
        prio_count = Counter(c.get("priority", "") for c in centers if c.get("enabled"))
        print("  Enabled by priority:")
        for p in ("high", "medium", "low"):
            n = prio_count.get(p, 0)
            if n: print(f"    {p:<10s} {n}")
        print()
        all_cities = set()
        for c in centers:
            if c.get("enabled"):
                all_cities.update(c.get("indian_cities", []))
        india_cities = sorted(ct for ct in all_cities if ct not in
            {"Atlanta", "Houston", "Chicago", "New-York", "San-Francisco"})
        print(f"  Indian cities covered ({len(india_cities)}):")
        for i in range(0, len(india_cities), 4):
            print(f"    {', '.join(india_cities[i:i+4])}")
        print()
        disabled = [c for c in centers if not c.get("enabled")]
        if disabled:
            print(f"  Disabled centers ({len(disabled)}):")
            for c in disabled[:8]:
                note = (c.get("notes") or "").split(".")[0] or "(no reason given)"
                print(f"    {c['destination_country']:<28s} [{c['processor']}] — {note[:60]}")
        print("="*60 + "\n")

    elif cmd == "selftest":
        # v3.2.2 — Offline integration check. Runs in ~30 seconds, no
        # network calls, no Selenium. Catches regressions in the
        # registry, page-change classifier, JWT class, DB migrations,
        # click-through XPath compilation, and notifier on edge inputs.
        # Goal: validate v3.2.x changes without a real calibration run.
        import tempfile
        passed = []
        failed = []
        def _try(name, fn):
            try:
                fn()
                passed.append(name)
                print(f"  ✓ {name}")
            except Exception as e:
                failed.append((name, str(e)[:200]))
                print(f"  ✗ {name}  →  {str(e)[:200]}")

        print("\n" + "="*60)
        print(f"  VISA TRACKER — SELFTEST (v{__version__})")
        print("="*60)

        # 1. Registry loads
        def _t_registry():
            global CENTERS_REGISTRY, COUNTRY_INDEX
            CENTERS_REGISTRY = {}
            COUNTRY_INDEX.clear()
            r = load_centers_registry()
            assert r, "centers.json not loaded"
            assert len(r.get("centers", [])) >= 80, f"Expected ≥80 centers, got {len(r.get('centers', []))}"
            # v4.0.0: accept both 3.2.x and 4.x.x versions (4.0 preserves all
            # v3.2.x schema invariants — added fields are additive only)
            ver = r.get("version", "")
            assert ver.startswith("3.2") or ver.startswith("4."), f"Bad version: {ver}"
            assert "vfs_global" in r["processors"]
            vfs = r["processors"]["vfs_global"]
            assert vfs.get("auth_method") == "jwt_via_selenium", "vfs_global missing JWT auth marker"
            assert vfs.get("known_api_endpoints"), "vfs_global missing known_api_endpoints"
        _try("registry load + processor metadata", _t_registry)

        # 2. URL routing for the v3.2.1-corrected countries
        def _t_routing():
            for country, expected_proc in [
                ("Portugal", "vfs"),
                ("Algeria", "embassy"),
                ("Tunisia", "embassy"),
                ("Mozambique", "embassy"),
                ("Spain", "bls"),
                ("Slovakia", "bls"),
                ("Czech Republic", "vfs"),
                ("United Kingdom", "vfs"),
            ]:
                url, portal = get_appointment_url(country)
                assert portal == expected_proc, f"{country}: got portal={portal}, expected {expected_proc}"
                assert url, f"{country}: empty URL"
        _try("URL routing for v3.2.1 corrected countries", _t_routing)

        # 3. Page-change classifier (v3.2.2 weighted + strict mode)
        def _t_classifier():
            from unittest.mock import MagicMock
            d = PageChangeDetector(MagicMock(), MagicMock())
            cases = [
                ("no appointments available at this time", False, "still_no_slots"),
                ("appointments available now! click to book your slot", False, "slots_likely"),
                ("available 24/7", False, "unknown_change"),
                ("book now for your visa appointment new dates available", False, "slots_likely"),
                # strict mode: 2 weak positives no longer enough
                ("book now select date", True, "unknown_change"),
                ("book now select date click to book", True, "slots_likely"),
                # strong negative beats anything
                ("currently no appointments. book now.", False, "still_no_slots"),
                ("© 2026 Visa Application Center. Cookies policy.", False, "unknown_change"),
            ]
            for text, strict, expected in cases:
                got = d._classify_change(text, strict_mode=strict)
                assert got == expected, f"classify({text[:30]!r}, strict={strict}): got {got}, expected {expected}"
        _try("page-change classifier (weighted + strict)", _t_classifier)

        # 4. Delta computation
        def _t_delta():
            from unittest.mock import MagicMock
            d = PageChangeDetector(MagicMock(), MagicMock())
            prev = "Welcome. Apply for visa. Book now. © 2026."
            curr = "Welcome. Apply for visa. Book now. New dates added! Available now. © 2026."
            delta = d._compute_delta(prev, curr)
            # Delta should contain the new sentence(s), not the unchanged ones
            assert "new dates" in delta.lower(), f"delta missing new content: {delta!r}"
            # Identical input → empty delta
            assert d._compute_delta(prev, prev).strip() == "", "identical input should diff to empty"
        _try("delta computation (difflib SequenceMatcher)", _t_delta)

        # 5. Noise stripping
        def _t_noise():
            from unittest.mock import MagicMock
            d = PageChangeDetector(MagicMock(), MagicMock())
            noisy = "© 2026 v3.2.1-abc Cookies Policy. Accept All. Last updated 12:34 PM."
            stripped = d._strip_noise(noisy)
            assert "©" not in stripped or "2026" not in stripped, f"copyright not stripped: {stripped!r}"
            assert "12:34" not in stripped, f"timestamp not stripped: {stripped!r}"
            assert "cookies" not in stripped.lower() or "policy" not in stripped.lower(), \
                f"cookie banner not stripped: {stripped!r}"
        _try("noise pattern stripping", _t_noise)

        # 6. VFSJWTSession instantiation + circuit breaker
        def _t_jwt_session():
            from unittest.mock import MagicMock
            sess = VFSJWTSession(MagicMock())
            # Initially closed circuits
            assert sess.health()["open_circuits"] == []
            # Force-trip the breaker
            for _ in range(VFSJWTSession.FAILURE_CIRCUIT_BREAKER):
                sess._failures["TestCountry"] = sess._failures.get("TestCountry", 0) + 1
            sess._failures["TestCountry"] = VFSJWTSession.FAILURE_CIRCUIT_BREAKER
            sess._circuit_open.add("TestCountry")
            assert "TestCountry" in sess.health()["open_circuits"]
            sess.reset_circuit("TestCountry")
            assert sess.health()["open_circuits"] == []
        _try("VFSJWTSession circuit breaker", _t_jwt_session)

        # 7. DB schema migration on a fresh sqlite file
        def _t_db_migration():
            import os
            tmpdir = tempfile.mkdtemp()
            dbpath = os.path.join(tmpdir, "selftest.db")
            db = Database(dbpath)
            # Verify v3.2.2 columns are present
            import sqlite3
            conn = sqlite3.connect(dbpath)
            ph_cols = [r[1] for r in conn.execute("PRAGMA table_info(page_hashes)").fetchall()]
            cal_cols = [r[1] for r in conn.execute("PRAGMA table_info(calibration)").fetchall()]
            conn.close()
            assert "consecutive_changes" in ph_cols, f"page_hashes missing column: {ph_cols}"
            assert "last_change_at" in ph_cols
            assert "confidence" in cal_cols, f"calibration missing column: {cal_cols}"
            # Test the new methods
            db.set_page_hash("k1", "h1", "preview text", mark_change=True)
            state = db.get_page_state("k1")
            assert state and state["hash"] == "h1"
            assert state["consecutive_changes"] == 1
            db.set_page_hash("k1", "h2", "more preview", mark_change=True)
            assert db.get_page_state("k1")["consecutive_changes"] == 2
            db.reset_page_noise("k1")
            assert db.get_page_state("k1")["consecutive_changes"] == 0
            try: os.remove(dbpath)
            except: pass
        _try("DB schema + page_hashes migration", _t_db_migration)

        # 8. Click-through XPath patterns compile
        def _t_xpaths():
            # The xpath strings live inline in calibrate_country; we mirror
            # them here to detect breakage. If the calibrator's list changes,
            # update both places.
            xpaths = [
                "//button[contains(translate(., 'BOOK', 'book'), 'book') and not(contains(translate(., 'LOGIN', 'login'), 'login'))]",
                "//a[contains(translate(., 'BOOK', 'book'), 'book')]",
                "//button[contains(@class, 'primary') or contains(@class, 'cta')]",
            ]
            # We can't fully validate XPath without lxml; do a basic sanity check
            for xp in xpaths:
                assert xp.startswith("//"), f"bad xpath: {xp}"
                assert xp.count("(") == xp.count(")"), f"unbalanced parens: {xp}"
                assert xp.count("[") == xp.count("]"), f"unbalanced brackets: {xp}"
        _try("click-through XPath syntax sanity", _t_xpaths)

        # 9. Notifier on empty + dry-run input
        def _t_notifier():
            n = Notifier({"notification_dry_run": True})
            n.send([])  # empty — no-op
            n.send([SlotInfo(country="Test", city="X", visa_type="T",
                            date="2026-06-01", time_slot="—",
                            confidence="medium")])  # dry-run, must not crash
            # Force rate-limit path with a clean notifier
            n2 = Notifier({"notification_dry_run": False, "desktop_alerts": False,
                          "email": {}, "telegram": {}, "discord": {}})
            many = [SlotInfo(country=f"C{i}", city="X", visa_type="T",
                             date="2026-06-01", time_slot="—",
                             confidence="medium")
                    for i in range(Notifier.NOTIFICATION_CAP + 5)]
            n2.send(many)  # should hit summary path
        _try("notifier (empty / dry-run / rate-limited)", _t_notifier)

        # 10. Default targets seed from registry
        def _t_default_targets():
            t = _default_targets_from_registry()
            assert len(t) >= 30, f"default targets too few: {len(t)}"
            countries = {x["country"] for x in t}
            assert "United Kingdom" in countries
            assert "Spain" in countries
            assert "Portugal" in countries  # v3.2.1 correction
            # Disabled BLS countries should NOT be in defaults
            assert "Algeria" not in countries
            assert "Tunisia" not in countries
            assert "Mozambique" not in countries
        _try("default targets seed (v3.2.1 corrections honored)", _t_default_targets)

        # 11. v4.4.0: US consulate cities merge into one target (was: first-only)
        def _t_us_cities_merged():
            t = _default_targets_from_registry()
            us = [x for x in t if x["country"] == "United States"
                  and x.get("processor") == "us_state_dept"]
            assert len(us) == 1, f"expected 1 merged US target, got {len(us)}"
            n_cities = len(us[0]["cities"])
            assert n_cities >= 5, (
                f"US target has only {n_cities} consulate(s) — city merge regressed"
            )
        _try("US consulate cities merged into one target (v4.4.0)", _t_us_cities_merged)

        # 12. v4.4.0: wait-time persistence round-trips (was 100% broken)
        def _t_wait_times():
            import os
            tmpdir = tempfile.mkdtemp()
            dbpath = os.path.join(tmpdir, "waittest.db")
            db = Database(dbpath)
            proc = USStateDeptProcessor(db)
            proc._store_current("us_waittime|Mumbai|B1/B2", 400)
            assert proc._get_previous("us_waittime|Mumbai|B1/B2") == 400, \
                "numeric wait time did not round-trip"
            proc._store_current("us_waittime|Chennai|C1/D", "Closed")
            assert proc._get_previous("us_waittime|Chennai|C1/D") == "Closed", \
                "status-string wait time did not round-trip"
            assert proc._get_previous("us_waittime|Nowhere|X") is None
            allw = db.get_all_wait_times()
            assert len(allw) == 2, f"expected 2 baselines, got {len(allw)}"
            # Drop detection actually works end-to-end now
            assert proc._is_significant_drop(400, 200) is True
            assert proc._is_significant_drop(200, 400) is False
            try: os.remove(dbpath)
            except: pass
        _try("US wait-time persistence round-trip (v4.4.0 fix)", _t_wait_times)

        # 13. v4.4.0: timestamps are valid RFC3339 (no '+00:00Z')
        def _t_timestamps():
            ts = utc_now_iso()
            assert "+00:00" not in ts, f"double offset in {ts}"
            assert ts.endswith("Z"), f"missing Z suffix: {ts}"
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")  # parseable
            s = SlotInfo(country="T", city="C", visa_type="V", date="2026-01-01")
            assert "+00:00Z" not in s.found_at, f"SlotInfo.found_at malformed: {s.found_at}"
        _try("timestamps are valid RFC3339 (v4.4.0 fix)", _t_timestamps)

        # 14. v4.4.0: telegram chunking stays under the 4096 limit
        def _t_telegram_chunks():
            header = "🎯 header"
            blocks = [f"block {i} " + "x" * 300 for i in range(30)]
            chunks = Notifier._telegram_chunks(header, blocks)
            assert len(chunks) > 1, "30 large blocks should split into multiple messages"
            for ch in chunks:
                assert len(ch) <= 4096, f"chunk exceeds Telegram limit: {len(ch)}"
            # Nothing lost in the packing
            joined = "\n".join(chunks)
            for i in range(30):
                assert f"block {i} " in joined, f"block {i} lost in chunking"
        _try("telegram chunking under 4096-char limit (v4.4.0)", _t_telegram_chunks)

        # 15. v4.4.0: state.gov wait table parses structurally
        def _t_state_gov_table():
            from unittest.mock import MagicMock
            proc = USStateDeptProcessor(MagicMock())
            html = """
            <html><body><table>
              <tr><th>City</th>
                  <th>Interview Required Visitors (B1/B2)</th>
                  <th>Interview Required Students/Exchange Visitors (F, M, J)</th>
                  <th>Interview Required Petition-Based Temporary Workers (H, L, O, P, Q)</th>
                  <th>Interview Required Crew and Transit (C1/D)</th>
                  <th>Interview Waiver Other Nonimmigrant Visas</th></tr>
              <tr><td>Chennai</td><td>44 Days</td><td>11 Days</td><td>217 Days</td><td>30 Days</td><td>90 Days</td></tr>
              <tr><td>Mumbai</td><td>437 Days</td><td>15 Days</td><td>Closed</td><td>22 Days</td><td>60 Days</td></tr>
            </table></body></html>
            """
            data = proc._parse_wait_table(html, "Mumbai")
            assert data.get("Visitor (B1/B2)") == 437, f"B1/B2 parse failed: {data}"
            assert data.get("Student/Exchange Visitor (F, M, J)") == 15, f"F/M/J parse failed: {data}"
            assert data.get("Petition-Based Temporary Workers (H, L, O, P, Q)") == "Closed", \
                f"status string not preserved: {data}"
            data2 = proc._parse_wait_table(html, "Chennai")
            assert data2.get("Crew/Transit (C1/D)") == 30, f"Chennai C1/D parse failed: {data2}"
            assert proc._parse_wait_table(html, "Hyderabad") == {}
        _try("state.gov wait-table structural parser (v4.4.0)", _t_state_gov_table)

        # ── Summary ──
        print("\n" + "-"*60)
        print(f"  Passed: {len(passed)}")
        print(f"  Failed: {len(failed)}")
        if failed:
            print(f"\n  Failures:")
            for name, err in failed:
                print(f"    ✗ {name}")
                print(f"      {err}")
            print("="*60 + "\n")
            sys.exit(1)
        else:
            print(f"\n  ✓ All checks passed — v{__version__} is wired up correctly.")
            print(f"  Next: `python visa_tracker_v3.py verify-urls` then calibrate.")
            print("="*60 + "\n")

    elif cmd == "list-countries":
        for name in list_supported_countries():
            rec = COUNTRY_INDEX.get(name.strip().lower(), {})
            proc = rec.get("processor", "legacy")
            enabled = rec.get("enabled", "?")
            print(f"  {name:<32s} {proc:<22s} enabled={enabled}")

    elif cmd == "setup-telegram":
        # v4.0.0 — interactive Telegram bot setup wizard. Uses the Bot API
        # directly to validate the token, auto-detect chat_id by polling
        # /getUpdates, send a test message, and write config.json. No new
        # dependencies — only `requests`.
        _cmd_setup_telegram()

    elif cmd == "select-countries":
        # v4.0.0 — interactive country picker. Replaces the "monitor all 42"
        # default with explicit opt-in. Presets cover common Indian outbound
        # use cases. Updates `enabled` flags in centers.json AND rewrites
        # the targets list in config.json.
        _cmd_select_countries()

    elif cmd == "set-tier":
        # v4.0.0 — promote a country to hot/warm/cold tier for tiered
        # scheduling (run --tiered). Examples:
        #   set-tier --country "United Kingdom" --tier hot
        #   set-tier --country "Germany" --tier hot
        #   set-tier --preset immigration   # UK/Canada/DE/IE/SG → hot
        _cmd_set_tier()

    elif cmd == "wait-times":
        # v4.4.0 — live US consulate wait-time table (state.gov + CGI
        # Federal, no auth). --all covers every us_state_dept center in
        # the registry; default is the 5 Indian consulates.
        _cmd_wait_times()

    elif cmd == "export":
        # v4.4.0 — dump active slots (+ checks/stats in JSON mode) to a
        # file for spreadsheets or your own tooling.
        _cmd_export()

    elif cmd == "doctor":
        # v4.4.0 — offline environment diagnostics: Python/deps/Chrome/
        # registry/config/DB integrity. Complements `selftest` (code-level
        # checks) with install-level checks.
        _cmd_doctor()

    elif cmd in ("version", "--version"):
        print(f"visa-tracker {__version__}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  v4.0.0 — NEW CLI COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cmd_setup_telegram():
    """Interactive Telegram setup. Validates token, finds chat_id, sends test."""
    print("\n" + "="*72)
    print("  TELEGRAM SETUP WIZARD (v4.0.0)")
    print("="*72)
    print()
    print("Why Telegram? Desktop toasts only fire when you're at your laptop")
    print("and Windows isn't in Do Not Disturb. Telegram pushes to your phone")
    print("24/7, free, works globally including India.")
    print()
    print("Prerequisites:")
    print("  1. Telegram app installed on your phone (free)")
    print("  2. ~5 minutes")
    print()
    print("─" * 72)
    print("STEP 1 — Create a bot")
    print("─" * 72)
    print("  • Open Telegram on your phone")
    print("  • Search for the user @BotFather (verified blue tick)")
    print("  • Send /newbot")
    print("  • Follow prompts: pick a name (any), then a username ending in 'bot'")
    print("  • BotFather replies with a bot token like 1234567890:ABCdef...")
    print()
    token = input("Paste your bot token here, then Enter: ").strip()
    if not token or ":" not in token:
        print("  ❌ That doesn't look like a Telegram bot token (should contain a colon).")
        print("     Try again: python visa_tracker_v3.py setup-telegram")
        return

    # Validate token via getMe
    print()
    print("  Validating token...")
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            print(f"  ❌ Telegram rejected the token: {data.get('description', 'unknown error')}")
            return
        bot = data["result"]
        print(f"  ✓ Bot validated: @{bot['username']} ({bot['first_name']})")
    except Exception as e:
        print(f"  ❌ Could not reach Telegram API: {e}")
        print("     Check your internet connection and try again.")
        return

    print()
    print("─" * 72)
    print("STEP 2 — Send a message TO your bot")
    print("─" * 72)
    print(f"  • In Telegram, search for your bot: @{bot['username']}")
    print("  • Tap Start (or send /start)")
    print("  • Send any message to it (e.g., 'hi' or anything)")
    print()
    input("Press Enter when done... ")

    # Poll getUpdates to find chat_id
    print()
    print("  Looking for your chat_id...")
    chat_id = None
    user_name = None
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            print(f"  ❌ Telegram error: {data.get('description', 'unknown')}")
            return
        updates = data.get("result", [])
        if not updates:
            print("  ❌ No messages found. Did you actually send a message to the bot?")
            print("     Send any message and re-run: python visa_tracker_v3.py setup-telegram")
            return
        # Most recent message wins
        for update in reversed(updates):
            msg = update.get("message") or update.get("edited_message")
            if msg and msg.get("chat", {}).get("id"):
                chat_id = str(msg["chat"]["id"])
                user_name = msg["chat"].get("first_name", "you")
                break
        if not chat_id:
            print("  ❌ Couldn't find a chat_id in recent messages.")
            return
        print(f"  ✓ Found chat_id {chat_id} (you: {user_name})")
    except Exception as e:
        print(f"  ❌ Failed to poll updates: {e}")
        return

    # Send test message
    print()
    print("─" * 72)
    print("STEP 3 — Test message")
    print("─" * 72)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": (
                    "🎯 <b>Visa Tracker</b> — Telegram is working!\n\n"
                    "If you can read this, the v4.0.0 setup wizard succeeded. "
                    "Future visa slot alerts will arrive in this chat.\n\n"
                    "Feel free to delete this test message."
                ),
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        if r.json().get("ok"):
            print("  ✓ Test message sent. Check Telegram on your phone now.")
        else:
            print(f"  ❌ Send failed: {r.json().get('description', 'unknown')}")
            return
    except Exception as e:
        print(f"  ❌ Could not send test message: {e}")
        return

    print()
    confirm = input("Did you receive the test message? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Hmm. Setup is technically complete (token+chat_id valid) but the message")
        print("  didn't arrive. Possible causes: blocked the bot, network issue, wrong chat.")
        print("  Re-run setup-telegram to retry.")
        return

    # Write to config.json
    config_path = "config.json"
    try:
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        tg = cfg.setdefault("telegram", {})
        tg["bot_token"] = token
        tg["chat_ids"] = [chat_id]
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print()
        print("─" * 72)
        print("  ✓ Telegram is configured. Wrote to config.json.")
        print("─" * 72)
        print()
        print(f"  Bot:        @{bot['username']}")
        print(f"  Chat ID:    {chat_id}")
        print(f"  Recipient:  {user_name}")
        print()
        print("Next: restart the tracker, or it'll pick up the new config on next cycle.")
        print("Both desktop toasts AND Telegram messages will fire on every alert.")
        print()
    except Exception as e:
        print(f"  ❌ Couldn't write config.json: {e}")
        print(f"     Manually add this to your config.json:")
        print(json.dumps({"telegram": {"bot_token": token, "chat_ids": [chat_id]}}, indent=2))


# Country presets for v4.0.0 select-countries / set-tier commands
_COUNTRY_PRESETS = {
    "immigration": [
        "United Kingdom", "Canada", "Germany", "Ireland", "Singapore",
    ],
    "schengen": [
        "France", "Germany", "Italy", "Spain", "Netherlands",
        "Switzerland", "Austria", "Belgium", "Greece", "Portugal",
        "Czech Republic", "Hungary", "Poland", "Sweden", "Norway",
        "Denmark", "Finland",
    ],
    "asia-pacific": [
        "Japan", "South Korea", "Singapore", "Australia", "New Zealand",
        "China", "Thailand", "Vietnam",
    ],
    "gulf": [
        "Saudi Arabia", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait", "Oman",
    ],
    "americas": [
        "Canada", "United States", "Mexico", "Brazil",
    ],
    "tier1-work-study": [
        "United Kingdom", "Canada", "Australia", "Germany", "Ireland",
        "New Zealand", "Singapore", "Netherlands",
    ],
}


def _cmd_select_countries():
    """Interactive country selection. Updates centers.json (enabled flags) and config.json (targets)."""
    print("\n" + "="*72)
    print("  COUNTRY SELECTION (v4.0.0)")
    print("="*72)
    print()
    print("Pick which countries the tracker should monitor.")
    print("Skip the long tail of 42 countries you'll never travel to —")
    print("smaller country list = faster cycles + lower Cloudflare exposure.")
    print()
    print("PRESETS:")
    for name, countries in _COUNTRY_PRESETS.items():
        print(f"  {name:<24s} ({len(countries)} countries: {', '.join(countries[:3])}...)")
    print(f"  {'all':<24s} (all enabled centers in centers.json)")
    print(f"  {'custom':<24s} (pick from list interactively)")
    print()
    choice = input("Pick a preset, 'custom', or 'all': ").strip().lower()

    if choice == "all":
        # Enable everything that isn't visa-free / e-visa
        registry = load_centers_registry()
        selected_countries = sorted(set(
            c["destination_country"] for c in registry.get("centers", [])
            if c.get("_indian_passport_status") not in ("visa_free", "evisa")
        ))
        if not selected_countries:
            # Fallback: registry doesn't have the flags yet (older centers.json)
            selected_countries = sorted(set(
                c["destination_country"] for c in registry.get("centers", [])
            ))
    elif choice == "custom":
        registry = load_centers_registry()
        all_countries = sorted(set(
            c["destination_country"] for c in registry.get("centers", [])
        ))
        print()
        print("Available countries (numbered):")
        for i, c in enumerate(all_countries, 1):
            rec = next((x for x in registry["centers"]
                       if x["destination_country"] == c), {})
            visa_free = rec.get("_indian_passport_status") in ("visa_free", "evisa")
            note = " [visa-free, no slots to track]" if visa_free else ""
            print(f"  {i:2d}. {c}{note}")
        print()
        sel = input("Enter numbers separated by commas (e.g., 1,3,5,12): ").strip()
        try:
            indices = [int(x.strip()) - 1 for x in sel.split(",") if x.strip().isdigit()]
            selected_countries = [all_countries[i] for i in indices if 0 <= i < len(all_countries)]
        except Exception as e:
            print(f"  ❌ Could not parse selection: {e}")
            return
    elif choice in _COUNTRY_PRESETS:
        selected_countries = list(_COUNTRY_PRESETS[choice])
    else:
        print(f"  ❌ Unknown preset: {choice}")
        print(f"     Available: {', '.join(_COUNTRY_PRESETS)}, all, custom")
        return

    if not selected_countries:
        print("  ❌ No countries selected — nothing to do.")
        return

    print()
    print(f"Selected ({len(selected_countries)}): {', '.join(selected_countries)}")
    confirm = input("Apply this selection? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    # ── Apply to centers.json (toggle enabled flags) ───────────────────
    selected_lower = {c.lower() for c in selected_countries}
    try:
        with open("centers.json", encoding="utf-8-sig") as f:
            registry = json.load(f)
    except Exception as e:
        print(f"  ❌ Could not read centers.json: {e}")
        return

    enabled_count = 0
    disabled_count = 0
    for center in registry.get("centers", []):
        country = center.get("destination_country", "")
        if country.lower() in selected_lower:
            # Don't enable if marked visa-free / e-visa — those have no slots
            if center.get("_indian_passport_status") in ("visa_free", "evisa"):
                center["enabled"] = False
                continue
            if not center.get("enabled"):
                enabled_count += 1
            center["enabled"] = True
        else:
            if center.get("enabled"):
                disabled_count += 1
            center["enabled"] = False

    with open("centers.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"  ✓ centers.json updated: {enabled_count} enabled, {disabled_count} disabled")

    # ── Refresh config.json targets to match ───────────────────────────
    if os.path.exists("config.json"):
        try:
            with open("config.json", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"  ⚠ Could not read config.json: {e}")
            cfg = {}
    else:
        cfg = {}

    # Reload registry (with new enabled flags) and rebuild targets
    global CENTERS_REGISTRY
    CENTERS_REGISTRY = registry
    cfg["targets"] = _default_targets_from_registry()

    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"  ✓ config.json updated: {len(cfg['targets'])} targets configured")

    print()
    print("Next:")
    print("  • Run calibration if you added new countries:")
    print("      python visa_tracker_v3.py calibrate --all")
    print("  • Optionally promote priorities to hot tier:")
    print("      python visa_tracker_v3.py set-tier --preset immigration")
    print("  • Start monitoring:")
    print("      python visa_tracker_v3.py run --tiered")
    print()


def _cmd_set_tier():
    """Set tier (hot/warm/cold) on countries. Modifies config.json targets list."""
    args = sys.argv
    tier = None
    country = None
    preset = None

    for i, arg in enumerate(args):
        if arg == "--tier" and i + 1 < len(args):
            tier = args[i + 1]
        elif arg == "--country" and i + 1 < len(args):
            country = args[i + 1]
        elif arg == "--preset" and i + 1 < len(args):
            preset = args[i + 1]

    if tier is None:
        if preset:
            tier = "hot"  # presets default to hot when used with --preset
        else:
            print("Usage:")
            print("  set-tier --country \"United Kingdom\" --tier hot")
            print("  set-tier --preset immigration            # promotes preset to hot")
            print("  set-tier --preset schengen --tier warm   # specific tier for preset")
            print()
            print("Tiers: hot (10min) | warm (30min) | cold (90min)")
            return

    if tier not in ("hot", "warm", "cold"):
        print(f"  ❌ Invalid tier: {tier!r}. Use: hot, warm, or cold")
        return

    # Resolve which countries to update
    if preset:
        if preset not in _COUNTRY_PRESETS:
            print(f"  ❌ Unknown preset: {preset}")
            print(f"     Available: {', '.join(_COUNTRY_PRESETS)}")
            return
        countries_to_update = list(_COUNTRY_PRESETS[preset])
    elif country:
        countries_to_update = [country]
    else:
        print("  ❌ Specify --country or --preset")
        return

    # Load config, update tiers in targets list
    if not os.path.exists("config.json"):
        print("  ❌ config.json not found. Run select-countries first.")
        return

    with open("config.json", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    targets = cfg.get("targets", [])
    if not targets:
        print("  ❌ No targets in config.json. Run select-countries first.")
        return

    matched = 0
    countries_lower = {c.lower() for c in countries_to_update}
    for target in targets:
        if target.get("country", "").lower() in countries_lower:
            target["tier"] = tier
            matched += 1

    if matched == 0:
        print(f"  ⚠ None of the requested countries are in your active targets list.")
        print(f"     Active countries: {', '.join(t['country'] for t in targets)}")
        print(f"     Run: python visa_tracker_v3.py select-countries")
        return

    # Make sure tier_intervals exists
    cfg.setdefault("tier_intervals", {
        "hot": 600, "warm": 1800, "cold": 5400,
    })

    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    tier_emoji = {"hot": "🔥", "warm": "🌤", "cold": "❄"}.get(tier, "?")
    print(f"  ✓ {tier_emoji} {matched} target(s) set to '{tier}' tier")
    for target in targets:
        if target.get("tier") == tier and target["country"].lower() in countries_lower:
            print(f"      {tier_emoji} {target['country']}")
    print()
    print(f"Tier intervals: {cfg['tier_intervals']}")
    print(f"To start tier-aware monitoring: python visa_tracker_v3.py run --tiered")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  v4.4.0 — NEW CLI COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cmd_wait_times():
    """Fetch and display current US visa wait times per consulate.

    Usage:
        wait-times                    # 5 Indian consulates
        wait-times --all              # every us_state_dept center in registry
        wait-times --city "Mumbai"    # one consulate
        wait-times --record           # also store values as DB baselines
    """
    args = sys.argv
    city_filter = None
    for i, a in enumerate(args):
        if a == "--city" and i + 1 < len(args):
            city_filter = args[i + 1]

    if city_filter:
        consulates = [city_filter]
    elif "--all" in args:
        consulates = []
        for c in CENTERS_REGISTRY.get("centers", []):
            if c.get("processor") == "us_state_dept" and c.get("enabled"):
                for city in c.get("indian_cities", []):
                    if city not in consulates:
                        consulates.append(city)
        if not consulates:
            consulates = list(USStateDeptProcessor.INDIAN_CONSULATES)
    else:
        consulates = list(USStateDeptProcessor.INDIAN_CONSULATES)

    record = "--record" in args
    db = Database()
    proc = USStateDeptProcessor(db)

    col_codes = ["B1/B2", "F/M/J", "H/L/O/P/Q", "C1/D", "Other"]
    print("\n" + "=" * 78)
    print(f"  US VISA WAIT TIMES — {len(consulates)} consulate(s)  (days; live fetch)")
    print("=" * 78)
    print(f"  {'Consulate':<22}" + "".join(f"{c:>11}" for c in col_codes))
    print("  " + "-" * 76)

    fetched = 0
    for consulate in consulates:
        data = proc._fetch_wait_times(consulate)
        if not data:
            print(f"  {consulate:<22}{'— fetch failed / no data —':>55}")
            continue
        fetched += 1
        by_code = {}
        for label, value in data.items():
            code = proc.VISA_TYPE_CODES.get(label, label[:10])
            by_code[code] = value
        row = f"  {consulate:<22}"
        for code in col_codes:
            v = by_code.get(code, "·")
            row += f"{str(v):>11}"
        print(row)
        if record:
            for code, value in by_code.items():
                db.set_wait_time(f"us_waittime|{consulate}|{code}", value)

    print("  " + "-" * 76)
    print(f"  Fetched {fetched}/{len(consulates)}."
          + ("  Baselines recorded to DB." if record and fetched else ""))
    print("  Sources: travel.state.gov (monthly) → ais.usvisa-info.com (fallback).")
    print("  A big DROP versus last month is the signal — see US_VISA_GUIDE.md.")
    print("=" * 78 + "\n")


def _cmd_export():
    """Export tracker data. Usage:
        export                          # JSON (slots+checks+stats) → visa_export.json
        export --format csv             # active slots → visa_slots.csv
        export --format json --out x.json
    """
    import csv as csv_mod
    args = sys.argv
    fmt = "json"
    out = None
    for i, a in enumerate(args):
        if a == "--format" and i + 1 < len(args):
            fmt = args[i + 1].lower()
        if a == "--out" and i + 1 < len(args):
            out = args[i + 1]

    if fmt not in ("json", "csv"):
        print(f"  ❌ Unknown format: {fmt}. Use json or csv.")
        return

    db = Database()
    slots = db.get_active_slots()

    if fmt == "csv":
        out = out or "visa_slots.csv"
        cols = ["uid", "country", "city", "visa_type", "date", "time_slot",
                "portal", "booking_url", "found_at", "detection_method",
                "confidence", "notified"]
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv_mod.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for s in slots:
                w.writerow({c: s.get(c, "") for c in cols})
        print(f"  ✓ {len(slots)} active slot(s) → {out}")
    else:
        out = out or "visa_export.json"
        payload = {
            "exported_at": utc_now_iso(),
            "version": __version__,
            "stats": db.stats(),
            "slots": slots,
            "checks": db.recent_checks(200),
            "wait_times": db.get_all_wait_times(),
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"  ✓ {len(slots)} slot(s), {len(payload['checks'])} check(s), "
              f"{len(payload['wait_times'])} wait-time baseline(s) → {out}")


def _cmd_doctor():
    """Offline environment diagnostics. Add --network for connectivity probes."""
    import shutil
    import importlib
    checks_passed = []
    checks_failed = []

    def _check(name, fn):
        try:
            detail = fn()
            checks_passed.append(name)
            print(f"  ✓ {name}" + (f"  — {detail}" if detail else ""))
        except Exception as e:
            checks_failed.append((name, str(e)[:160]))
            print(f"  ✗ {name}  →  {str(e)[:160]}")

    print("\n" + "=" * 72)
    print(f"  VISA TRACKER — DOCTOR (v{__version__})")
    print("=" * 72)

    def _t_python():
        if sys.version_info < (3, 10):
            raise RuntimeError(f"Python 3.10+ required, found {sys.version.split()[0]}")
        return f"Python {sys.version.split()[0]}"
    _check("python version", _t_python)

    def _t_deps():
        found = []
        for mod in ("requests", "bs4", "selenium", "aiohttp", "websockets",
                    "fake_useragent", "webdriver_manager"):
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            found.append(f"{mod} {ver}")
        return ", ".join(found[:4]) + ", …"
    _check("required modules importable", _t_deps)

    def _t_chrome():
        env_binary = os.environ.get("VISA_CHROME_BINARY", "").strip()
        if env_binary:
            if os.path.exists(env_binary):
                return f"{env_binary} (VISA_CHROME_BINARY)"
            raise RuntimeError(f"VISA_CHROME_BINARY set but not found: {env_binary}")
        candidates = ["google-chrome", "google-chrome-stable", "chromium",
                      "chromium-browser", "chrome"]
        for c in candidates:
            path = shutil.which(c)
            if path:
                return path
        win_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in win_paths:
            if os.path.exists(p):
                return p
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            return mac_path
        raise RuntimeError("Chrome/Chromium not found on PATH or standard locations "
                           "(Selenium layers will fail; page-change detection needs it). "
                           "Install Chrome, or point VISA_CHROME_BINARY at a browser binary")
    _check("chrome browser present", _t_chrome)

    def _t_registry():
        reg = load_centers_registry()
        if not reg:
            raise RuntimeError("centers.json missing or unparseable")
        n = len(reg.get("centers", []))
        enabled = sum(1 for c in reg.get("centers", []) if c.get("enabled"))
        return f"v{reg.get('version', '?')}, {n} centers ({enabled} enabled)"
    _check("centers.json registry", _t_registry)

    def _t_config():
        if not os.path.exists("config.json"):
            return "no config.json yet (created on first run)"
        with open("config.json", encoding="utf-8-sig") as f:
            cfg = json.load(f)
        targets = cfg.get("targets", [])
        channels = []
        if cfg.get("telegram", {}).get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN"):
            channels.append("telegram")
        if cfg.get("email", {}).get("enabled"):
            channels.append("email")
        if cfg.get("discord", {}).get("webhook_url"):
            channels.append("discord")
        if cfg.get("webhook", {}).get("url"):
            channels.append("webhook")
        if cfg.get("desktop_alerts", True):
            channels.append("desktop")
        return f"{len(targets)} targets, channels: {', '.join(channels) or 'NONE — you will miss alerts'}"
    _check("config.json", _t_config)

    def _t_db():
        db = Database()
        with db._lock:
            conn = db._conn()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            slot_cols = {r[1] for r in conn.execute("PRAGMA table_info(slots)").fetchall()}
            conn.close()
        if integrity != "ok":
            raise RuntimeError(f"integrity_check: {integrity}")
        required = {"slots", "checks", "page_hashes", "sessions", "calibration", "wait_times"}
        missing = required - tables
        if missing:
            raise RuntimeError(f"missing tables: {missing}")
        # Column check catches a foreign/partial DB dropped in the cwd —
        # CREATE TABLE IF NOT EXISTS won't repair a wrong-shaped table.
        required_cols = {"uid", "country", "city", "date", "notified", "expired"}
        missing_cols = required_cols - slot_cols
        if missing_cols:
            raise RuntimeError(
                f"slots table missing columns {missing_cols} — this is not a "
                f"visa-tracker DB; move/delete visa_slots.db and rerun"
            )
        return f"integrity ok, {len(tables)} tables"
    _check("database (visa_slots.db)", _t_db)

    def _t_writable():
        probe = ".doctor_write_probe"
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return "cwd writable (logs, screenshots, DB)"
    _check("filesystem writable", _t_writable)

    if "--network" in sys.argv:
        def _t_net_telegram():
            r = requests.head("https://api.telegram.org", timeout=8)
            return f"api.telegram.org HTTP {r.status_code}"
        _check("network: Telegram API reachable", _t_net_telegram)

        def _t_net_stategov():
            r = requests.get(USStateDeptProcessor.STATE_GOV_URL, timeout=10,
                             stream=True, headers={"User-Agent": rand_ua()})
            code = r.status_code
            r.close()
            return f"travel.state.gov HTTP {code}"
        _check("network: state.gov reachable", _t_net_stategov)

    print("\n" + "-" * 72)
    print(f"  Passed: {len(checks_passed)}   Failed: {len(checks_failed)}")
    if checks_failed:
        print("\n  Fix the items above, then re-run: python visa_tracker_v3.py doctor")
        print("=" * 72 + "\n")
        sys.exit(1)
    print("  ✓ Environment looks healthy. Next: selftest → verify-urls → run")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()