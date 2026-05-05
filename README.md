# Visa Slot Tracker

Personal automation that watches India-outbound visa appointment websites and notifies you the moment a slot opens up. Built for Indian travellers chasing UK Skilled Worker, Canada Express Entry, Schengen, and other competitive visa corridors where slots disappear in minutes.

**Version:** v4.0.0
**Status:** production-validated against real VFS Global traffic (22+ hours, 1,972 page-change events, 4 confirmed real slot detections in Czech Republic May 2026)
**Platform:** Windows 10/11 (primary), macOS/Linux (secondary), GitHub Actions (cloud)

## What it does

- Monitors **64 visa application centres** across **42 destination countries** every 10–90 minutes
- Detects new appointment slots via three layers (VFS JWT API replay, anonymous API discovery, page-change classifier)
- Notifies via **desktop toast + Telegram + email + Discord** (all configurable)
- Suppresses 100% of cosmetic noise that crashed v3.2.0 (validated across 1,968 false-positive events)
- Runs on your laptop or in **GitHub Actions** for 24/7 cloud monitoring

## What's new in v4.0.0

- **Tier system** — promote priority countries to a 10-min polling interval; let the long tail stay at 90 min
- **Telegram setup wizard** — `setup-telegram` CLI auto-detects your chat ID and sends a test message in 60 seconds
- **GitHub Actions deployment** — three workflows for cloud monitoring, weekly recalibration, daily healthcheck
- **Country selection** — pick what to monitor instead of scaffolding all 82 centres
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
| [TIER_SYSTEM.md](TIER_SYSTEM.md) | Anyone using v4.0 | How hot/warm/cold tiers work, tuning advice |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Anyone wanting phone alerts | Bot creation, env vars, group chats |
| [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) | Cloud deployers | 24/7 monitoring on free tier, cost analysis |
| [ADDING_COUNTRIES.md](ADDING_COUNTRIES.md) | Anyone expanding coverage | Schema reference, embassy URL table for ~30 destinations |
| [VISA_FREE_GUIDE.md](VISA_FREE_GUIDE.md) | Curious about disabled entries | Why Sri Lanka is flagged off, how to re-enable |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Architecture deep-dive | 3-layer detection, JWT replay, calibration internals |
| [PROCESSORS.md](PROCESSORS.md) | Developers extending support | VFS / BLS / TLS / embassy_direct implementation notes |
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

## Disclaimer

This project is unaffiliated with VFS Global, BLS International, TLS Contact, or any embassy/consulate. It only reads publicly visible content from official appointment portals. Use at your own risk; respect the terms of service of any site you point it at.

## License

MIT. See [LICENSE](LICENSE).

---

Built and maintained by [@ankitjha67](https://github.com/ankitjha67). Issues and PRs welcome.
