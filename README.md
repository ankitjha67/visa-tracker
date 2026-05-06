# Visa Slot Tracker

> **⚠️ Important — please read before using:**
>
> This is an **open-source research and educational project**. It is a **read-only monitor** that watches publicly available visa-availability information and notifies you when it changes. **It does not book appointments. It does not store credentials. It does not bypass CAPTCHAs. It does not act as an agent or fixer.**
>
> The project has **no affiliation** with VFS Global, BLS International, TLScontact, CGI Federal, the U.S. Department of State, or any embassy or consulate.
>
> **You** are responsible for complying with the terms of service of any portal you choose to monitor and the laws of your jurisdiction. **Please read [`DISCLAIMER.md`](DISCLAIMER.md) before installing.** For the project's legal posture and architectural commitments, see [`LEGAL.md`](LEGAL.md).

---

A personal-use, MIT-licensed Python project that watches visa appointment websites and notifies you when their public availability pages change. Built primarily as a research artifact and consumer-information tool for Indian travellers tracking competitive visa corridors (UK Skilled Worker, Canada Express Entry, Schengen, U.S. wait times) — but the architecture is **passport-agnostic** and can be adapted for any origin country (see [INTERNATIONALIZATION_GUIDE.md](INTERNATIONALIZATION_GUIDE.md)).

**Version:** v4.3.0
**Status:** production-validated against real VFS Global traffic. Two confirmed real Czech Republic slot detection events: May 5 2026 (4 slots, all 4 cities) and May 6 2026 (16 slots across multiple cycles, 6h continuous run). Page-change classifier achieved 0 false positives across 2,677 classification decisions in the May 6 6-hour window.
**Platform:** Windows 10/11 (primary), macOS/Linux (secondary), GitHub Actions (cloud)
**License:** MIT
**Purpose:** research, education, transparency, consumer information

## What it does

This project performs **read-only** monitoring of three categories of **publicly accessible** data:

1. **Public landing pages** of visa application centres — hashes visible page text and detects changes (the same operation a human would perform by refreshing a browser tab).
2. **Anonymous availability endpoints** that issue tokens to any visitor without requiring login or account creation.
3. **U.S. Department of State public wait-time data** at `travel.state.gov` — federal government data that, under 17 U.S.C. § 105, is statutorily in the public domain.

When the data changes, the tool notifies the user via desktop toast, Telegram, email, or Discord — channels the user configures on their own infrastructure.

Coverage at v4.3.0: **118 visa application centres** across **45+ destination countries**, including 5 Indian US consulates and 31 third-country US consulates (Mexico, Canada, UAE, Saudi Arabia, etc.). Tier-based polling (hot/warm/cold) keeps default request volume comparable to a single human user actively monitoring a site. False-positive noise from v3.2.0 (1,968 cosmetic events) is fully suppressed.

## What it does NOT do

These are deliberate architectural commitments documented in [`LEGAL.md`](LEGAL.md). The software does not, and will not be modified to:

- ❌ Submit, book, reschedule, or cancel any appointment
- ❌ Store, transmit, or use any user credentials (no DS-160, no CGI Federal login, no usvisa-info.com login, no VFS account credentials)
- ❌ Solve, bypass, or circumvent CAPTCHAs (no 2Captcha, no DeathByCaptcha, no anti-Cloudflare bypass libraries)
- ❌ Use VPN rotation, proxy networks, or IP masking to evade rate limits or access controls
- ❌ Collect, aggregate, or distribute personal data of any visa applicant
- ❌ Operate as a paid service or commercial booking agent of any kind

If you need any of the above, **this is not the right software** and the maintainer will not implement those features. See [`DISCLAIMER.md`](DISCLAIMER.md) for the full scope statement.

## What's new in v4.3.0

**Instant notifications on detection** — when the page-change classifier fires `🎯 PAGE CHANGED`, the toast/Telegram/email/Discord alert fires immediately rather than waiting for cycle completion. Driven by the May 6 2026 production cycle: real Czech Republic detection at 03:17, but notification didn't fire until 03:43 (26-minute lag) because the cycle walked sequentially through all 269 country/city pairs before the batch notify ran. v4.3.0 closes that gap. Cycle-end batch dedupes against already-sent slots, so users never get duplicate alerts. Disable via `{"instant_notify": false}` in `config.json`.

**Log noise suppression** — silenced the `fake_useragent` library's "fallback used" WARNING that fires on every browser-string request when its CDN is slow or rate-limited. The fallback works fine; we observed ~1,500 of these warnings in a 6h run (25% of all log volume). Logger level set to ERROR so real failures stay visible.

**Bytecode caching disabled** — set `sys.dont_write_bytecode = True`. Stale `__pycache__/.pyc` files masked the v4.2.0→v4.2.1 disclaimer prompt on Windows until the cache was manually nuked, because Windows file copies preserve the source's original mtime. Trading 50ms startup for guaranteed source-file accuracy is correct for a CLI tool that users upgrade by overwriting files.

## What was new in v4.2.1

**Disclaimer hardening and legal transparency.** Added [`DISCLAIMER.md`](DISCLAIMER.md), [`LEGAL.md`](LEGAL.md), and CLI first-run notice documenting the project's research-and-education purpose, architectural commitments, and good-faith analysis of relevant case law (hiQ Labs v. LinkedIn, Van Buren v. United States, Section 43/66 of India's IT Act 2000, GDPR scope). No functional code changes; v4.2.0 features remain.

## What was new in v4.2.0

**Third-country US consulate tracking** — extended `USStateDeptProcessor` to 30 US consulates worldwide where Indians (or anyone) might pursue the "third-country interview" workaround when domestic queues are years long. Mexico (10 consulates), Canada (7), UAE/Saudi Arabia (4), plus Singapore, Thailand, UK, France, Germany, Australia, Japan. All disabled by default — opt in via `select-countries`.

**Internationalization** — new [INTERNATIONALIZATION_GUIDE.md](INTERNATIONALIZATION_GUIDE.md) showing how non-Indian users (Bangladesh, Pakistan, UK residents, etc.) can adapt the schema and URL patterns. Worked examples for 4 origin/destination combinations, country code reference table, and honest notes on what's adaptable vs what needs code changes.

**Schengen documentation** — clarified the architecture for Schengen monitoring. The VFS layer (already implemented and production-validated) IS the right mechanism. There is no equivalent of state.gov for Schengen, so a unified Schengen wait-time tracker isn't built — and shouldn't be. Set Schengen countries to `tier: warm` for 30-min polling.

**Stale reference cleanup** — comprehensive sweep of all version references across docs.

## What was new in v4.1.0

🇺🇸 **US visa wait-time tracker** — first non-VFS, non-Selenium processor. Monitors official US Department of State + CGI Federal public pages. Detects significant drops in wait time which strongly correlate with new appointment slot batches being released. Honest caveat: trend tracker, not real-time slot scraper. Latency is days to weeks (state.gov updates monthly), not minutes like VFS. Direct slot scraping at CGI Federal requires DS-160 + login and is intentionally NOT implemented (account-lock risk). See [`US_VISA_GUIDE.md`](US_VISA_GUIDE.md) for full scope.

## What was new in v4.0.0

- **Tier system** — promote priority countries to a 10-min polling interval; let the long tail stay at 90 min
- **Telegram setup wizard** — `setup-telegram` CLI auto-detects your chat ID and sends a test message in 60 seconds
- **GitHub Actions deployment** — three workflows for cloud monitoring, weekly recalibration, daily healthcheck
- **Country selection** — pick what to monitor instead of scaffolding all centres
- **Visa-free cleanup** — 12 destinations (Sri Lanka, Thailand, Malaysia, etc.) flagged and disabled by default

See [CHANGELOG.md](CHANGELOG.md) for the full history.

## Quickstart (5 minutes for non-developers)

```powershell
# 1. Install Python 3.10+ from python.org (check "Add to PATH")
# 2. Unzip this repo into a folder
# 3. Open PowerShell in that folder

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
python -m pip install -r requirements.txt
.\smoke_test.ps1                              # verify install (7 stages)

# 4. Pick countries
python visa_tracker_v3.py select-countries     # interactive picker

# 5. Promote priorities to hot tier (10-min checks)
python visa_tracker_v3.py set-tier --preset immigration

# 6. Set up Telegram for phone alerts
python visa_tracker_v3.py setup-telegram       # 60-second wizard

# 7. Calibrate (one-time, 15 min)
python visa_tracker_v3.py calibrate --all

# 8. Start monitoring
python visa_tracker_v3.py run --tiered
```

For non-technical step-by-step, see [USER_GUIDE.md](USER_GUIDE.md).

## Documentation

| Document | Audience | What's in it |
|---|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | Non-developers | Plain-English setup walkthrough, troubleshooting |
| [QUICKSTART.md](QUICKSTART.md) | Developers | CLI reference, common operations |
| [TIER_SYSTEM.md](TIER_SYSTEM.md) | Anyone using v4.0+ | How hot/warm/cold tiers work, tuning advice |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Anyone wanting phone alerts | Bot creation, env vars, group chats |
| [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) | Cloud deployers | 24/7 monitoring on free tier, cost analysis |
| [US_VISA_GUIDE.md](US_VISA_GUIDE.md) | US visa applicants | What v4.1.0+ US tracking does and doesn't do, honest scope |
| [INTERNATIONALIZATION_GUIDE.md](INTERNATIONALIZATION_GUIDE.md) | Non-Indian users | Adapt the repo for any origin country (Bangladesh, UK, Pakistan, etc.) |
| [ADDING_COUNTRIES.md](ADDING_COUNTRIES.md) | Anyone expanding coverage | Schema reference, embassy URL table for ~30 destinations |
| [VISA_FREE_GUIDE.md](VISA_FREE_GUIDE.md) | Curious about disabled entries | Why Sri Lanka is flagged off, how to re-enable |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Architecture deep-dive | 3-layer detection, JWT replay, calibration internals |
| [PROCESSORS.md](PROCESSORS.md) | Developers extending support | VFS / BLS / TLS / embassy_direct / us_state_dept implementation notes |
| [CHANGELOG.md](CHANGELOG.md) | Anyone | Release history with reasoning |

## Architecture (at 30,000 ft)

Three detection layers per check, run by a single Python process:

1. **VFS JWT replay** — Headless Chrome harvests authorization tokens from VFS portal network logs, replays against `lift-api.vfsglobal.com/appointment/slots`. Cached 25 min. Circuit breaker after 6 consecutive failures.
2. **Anonymous API** — For non-VFS portals or VFS endpoints discovered during calibration. Plain `requests.get`. Date extractor is key-aware and plausibility-filtered.
3. **Delta page-change** — SPA hydration → SHA hash of visible text. On change: compute SequenceMatcher delta, classify ONLY the delta, suppress if <30 chars or pure noise. Persistent-noise marker escalates to strict mode after 2+ consecutive change events.

v4.0 adds a **priority-queue scheduler** on top: each (country, city, tier) is rescheduled at a tier-specific interval after each check. Hot countries get checked 9× more frequently than cold.

## Limitations

- Cannot book slots for you — it just notifies. You still need to log in and complete the booking.
- Cannot find login-gated slots. Sees only what an anonymous visitor sees.
- Cannot work for visa-free destinations (no slots to monitor — Sri Lanka, Thailand, Malaysia, etc. are flagged off).
- VFS Global occasionally rotates endpoints — periodic recalibration required.
- GitHub Actions cron has 5–30 min jitter at peak; tiered scheduling needs a long-running process.
- Cloudflare may flag cloud-runner IPs (Azure, AWS) and serve 403s. Page-change layer still works in that case.

## Security & privacy

- **Don't commit `config.json`** — it contains your Telegram bot token. The `.gitignore` excludes it; commit `config.example.json` instead.
- **Don't commit `visa_slots.db`** — it caches JWTs and personal queries. Also gitignored.
- **GitHub Actions secrets are encrypted at rest.** Use `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` repo secrets for cloud deployment.
- **The bot can only send messages**, never read your chats. Telegram API restricts bots to their own conversations.

## Contributing

This is a personal project, but PRs are welcome. The high-impact areas:

- **New processors** — CGI Federal (US), CVASC (China), TLS Contact (Slovakia) require custom Python classes. See `PROCESSORS.md`.
- **New countries** — most VFS countries can be added by editing `centers.json`. See `ADDING_COUNTRIES.md`.
- **Embassy reference table** — corrections welcome if any URLs in `ADDING_COUNTRIES.md` have rotted.

## Disclaimer & legal posture

This project is unaffiliated with VFS Global, BLS International, TLScontact, CGI Federal, or any embassy or consulate. It is published as **open-source research and educational software** for personal, journalistic, and academic use.

**Before installing, please read [`DISCLAIMER.md`](DISCLAIMER.md)** for the full scope statement, prohibited-use guidance, and user responsibility breakdown.

**For the project's posture on relevant case law** (hiQ Labs v. LinkedIn, Van Buren v. United States, Section 43/66 of India's IT Act 2000, GDPR scope, the U.S. Embassy India March 2025 announcement), see [`LEGAL.md`](LEGAL.md).

The maintainer commits to the architectural choices documented in `LEGAL.md` — no auto-booking, no credential storage, no CAPTCHA bypass, no proxy rotation, no personal-data collection. Departing from any of these would change the legal analysis materially and is not contemplated.

**If you have a concern** (technical or legal) as a representative of any monitored entity, please open a GitHub issue or send a written notice to this repository. The maintainer commits to responding within 5 business days for technical concerns and through GitHub's notice-and-response process for formal legal notices.

## License

MIT. See [LICENSE](LICENSE).

The MIT License does not grant trademark rights to "VFS Global," "BLS International," "TLScontact," "CGI Federal," or any consulate or embassy name appearing in this code. Such names are the property of their respective owners and are referenced only as factual identifiers.

---

Built and maintained by [@ankitjha67](https://github.com/ankitjha67). Issues and PRs welcome.
