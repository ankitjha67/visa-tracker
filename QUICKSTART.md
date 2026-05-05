# Quickstart — Visa Slot Tracker v4.0.0

Technical quick reference for developers. **For non-technical setup, read `USER_GUIDE.md` instead** — plain English walkthrough.

## Doc map

| File | For | Length |
|---|---|---|
| `USER_GUIDE.md` | Non-developers / first-time users | ~10 min |
| `QUICKSTART.md` (this file) | Developers / quick reference | ~5 min |
| `TIER_SYSTEM.md` | Tier scheduler internals + tuning | ~8 min |
| `TELEGRAM_SETUP.md` | Telegram bot setup | ~5 min |
| `GITHUB_ACTIONS.md` | Cloud deployment | ~12 min |
| `VISA_FREE_GUIDE.md` | `_indian_passport_status` flagging | ~5 min |
| `ADDING_COUNTRIES.md` | Expanding coverage + embassy reference | ~10 min |
| `SETUP_GUIDE.md` | Architecture deep-dive | ~20 min |
| `PROCESSORS.md` | Per-processor notes | ~8 min |

## Prerequisites

- Python 3.10+ (3.14 tested)
- Google Chrome
- Windows 10/11 (macOS/Linux work; desktop notification path differs)

## Install

```powershell
# UTF-8 console (every fresh PowerShell window)
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# Install deps
python -m pip install -r requirements.txt

# Smoke test (all 7 stages should pass)
.\smoke_test.ps1
```

## v4.0 setup flow (recommended order)

```powershell
# 1. Pick which countries to monitor (presets or custom)
python visa_tracker_v3.py select-countries

# 2. Configure Telegram for phone alerts (recommended)
python visa_tracker_v3.py setup-telegram

# 3. Promote priorities to hot tier (10-min polling)
python visa_tracker_v3.py set-tier --preset immigration
# OR target specific countries:
python visa_tracker_v3.py set-tier --country "United Kingdom" --tier hot

# 4. First-time calibration (15-17 min)
python visa_tracker_v3.py calibrate --all

# 5. Start monitoring with tier-aware scheduler
python visa_tracker_v3.py run --tiered
```

## CLI reference

### Lifecycle

```powershell
python visa_tracker_v3.py run                     # standard fixed-interval (v3.2.x compat)
python visa_tracker_v3.py run --tiered            # v4.0 priority-queue scheduler
python visa_tracker_v3.py run --once              # single cycle, exit (used by GitHub Actions)
python visa_tracker_v3.py run --dry-run           # log notifications, don't send
python visa_tracker_v3.py run --server            # WebSocket dashboard
```

### v4.0 commands

```powershell
# Country selection (interactive picker)
python visa_tracker_v3.py select-countries

# Tier management
python visa_tracker_v3.py set-tier --country "United Kingdom" --tier hot
python visa_tracker_v3.py set-tier --preset immigration               # → hot
python visa_tracker_v3.py set-tier --preset schengen --tier warm

# Telegram setup wizard
python visa_tracker_v3.py setup-telegram
```

Tier presets:

| Preset | Countries |
|---|---|
| `immigration` | UK, Canada, Germany, Ireland, Singapore |
| `schengen` | All 17 Schengen |
| `asia-pacific` | Japan, Korea, Singapore, AU, NZ, China, TH, VN |
| `gulf` | UAE, SA, Qatar, Bahrain, Kuwait, Oman |
| `americas` | Canada, USA, Mexico, Brazil |
| `tier1-work-study` | UK, CA, AU, DE, IE, NZ, SG, NL |

### Health & diagnostics

```powershell
python visa_tracker_v3.py status                  # JWT circuits, last cycle, DB stats
python visa_tracker_v3.py coverage                # all 82 centers + confidence + tier
python visa_tracker_v3.py verify-urls             # streaming GET against all URLs
python visa_tracker_v3.py selftest                # 10 offline integration checks
python visa_tracker_v3.py list-countries          # processor + enabled status
```

### Calibration

```powershell
python visa_tracker_v3.py calibrate --all
python visa_tracker_v3.py calibrate --country "United Kingdom"
python visa_tracker_v3.py calibrate --workers 4   # parallel
```

### Smoke test

```powershell
.\smoke_test.ps1                                  # PowerShell wrapper
python smoke_test.py                              # cross-platform direct
```

## Environment variables (v4.0 — for GitHub Actions)

| Var | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Overrides `config.telegram.bot_token` |
| `TELEGRAM_CHAT_ID` | Adds to `config.telegram.chat_ids` (comma-separated supported) |
| `NOTIFICATION_DRY_RUN` | `true` → suppress sends without changing config |

Read at `Notifier.__init__` time. Required for GitHub Actions where secrets can't live in committed config.

## Config defaults (v4.0)

```json
{
  "check_interval_seconds": 180,
  "tier_intervals": {"hot": 600, "warm": 1800, "cold": 5400},
  "max_concurrent": 2,
  "desktop_alerts": true,
  "telegram": {"bot_token": "", "chat_ids": []},
  "discord": {"webhook_url": ""},
  "email": {"enabled": false, ...},
  "targets": [
    {
      "country": "...",
      "cities": [...],
      "visa_types": [...],
      "processor": "...",
      "tier": "cold"
    }
  ]
}
```

## File layout

```
visa-tracker-v4/
├── visa_tracker_v3.py        # ~4,350 lines (v4.0 patches on v3.2.4 base)
├── centers.json              # v4.0.0 — 82 centers, 12 visa-free/evisa flagged, 64 active
├── requirements.txt          # pinned deps incl. windows-toasts
├── smoke_test.py             # 7-stage end-to-end verification
├── smoke_test.ps1            # PowerShell wrapper
│
├── USER_GUIDE.md             # plain-English walkthrough
├── QUICKSTART.md             # this file
├── TIER_SYSTEM.md            # tier scheduler details
├── TELEGRAM_SETUP.md         # bot setup
├── GITHUB_ACTIONS.md         # cloud deployment
├── VISA_FREE_GUIDE.md        # cleanup feature
├── ADDING_COUNTRIES.md       # expansion + embassy reference
├── SETUP_GUIDE.md            # architecture deep-dive
├── PROCESSORS.md             # per-processor notes
├── CHANGELOG.md              # version history
├── visa-dashboard.jsx        # optional React dashboard
│
└── .github/workflows/
    ├── monitor.yml           # every 30 min cron
    ├── calibrate.yml         # weekly Sunday 04:00 UTC
    └── healthcheck.yml       # daily 03:00 UTC alive ping
```

## Common operations

### Toggle live ↔ dry-run

```powershell
python -c "import json; cfg=json.load(open('config.json',encoding='utf-8-sig')); cfg['notification_dry_run']=not cfg.get('notification_dry_run', False); print('dry_run is now:', cfg['notification_dry_run']); json.dump(cfg, open('config.json','w',encoding='utf-8'), indent=2, ensure_ascii=False)"
```

### Inspect tier distribution

```powershell
python -c "import json; cfg=json.load(open('config.json',encoding='utf-8-sig')); from collections import Counter; print(Counter(t.get('tier','cold') for t in cfg['targets']))"
```

### Clean restart (preserves DB)

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "visa_tracker" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process -Name "chromedriver" -ErrorAction SilentlyContinue | Stop-Process -Force
python visa_tracker_v3.py run --tiered
```

### Wipe and start over

```powershell
Remove-Item visa_slots.db, config.json
python visa_tracker_v3.py select-countries
python visa_tracker_v3.py setup-telegram
python visa_tracker_v3.py set-tier --preset immigration
python visa_tracker_v3.py calibrate --all
python visa_tracker_v3.py run --tiered
```

### Re-enable a visa-free entry (for non-Indian passport)

```powershell
python -c @"
import json
with open('centers.json', encoding='utf-8-sig') as f: data = json.load(f)
target = 'Sri Lanka'
for c in data['centers']:
    if c['destination_country'] == target:
        c['enabled'] = True
        print(f'Re-enabled: {c[\"id\"]}')
with open('centers.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"@
```

See `VISA_FREE_GUIDE.md` for full flag reference.

## Verify v4.0 features are wired

```powershell
python -c "src=open('visa_tracker_v3.py', encoding='utf-8').read(); checks=[('tiered scheduler', 'run_monitor_tiered' in src), ('--tiered flag', '--tiered' in src), ('setup-telegram', '_cmd_setup_telegram' in src), ('select-countries', '_cmd_select_countries' in src), ('set-tier', '_cmd_set_tier' in src), ('TELEGRAM env', 'TELEGRAM_BOT_TOKEN' in src), ('country presets', '_COUNTRY_PRESETS' in src), ('priority queue', 'heappush' in src and 'heappop' in src), ('selftest v4.0', 'SELFTEST (v4.0.0)' in src)]; [print(f'  {chr(10003) if v else chr(10007)} {k}') for k,v in checks]"
```

All 9 should print `✓`.

## Diagnostics

| Symptom | Quick check | Fix |
|---|---|---|
| Smoke test stage 7 — no toast | Notification Center | Disable Focus / DND |
| `selftest` fails with import error | Deps not installed | `pip install -r requirements.txt` |
| Tracker logs `❌ <country>/<city>: error` | Selector wait timeout | Recalibrate that country |
| `select-countries all` enables ~64 not 82 | Visa-free / e-visa flagged correctly | Intentional; see VISA_FREE_GUIDE.md |
| `run --tiered` says "Queue empty" | No targets in config | Run `select-countries` first |
| Tiered mode: hot only, cold never | Hot saturating | Reduce hot count or interval |
| GH Actions hits 25min timeout | Cloudflare 403s | Increase `timeout-minutes` in monitor.yml |

## Architecture overview (one paragraph)

Three-layer detection per cycle (verbatim from v3.2.x): VFS JWT replay → anonymous API → delta page-change classifier with persistent-noise marker. v4.0 wraps these in a priority-queue scheduler (`--tiered`): each (country, city) target carries a `tier` field; after each check, target rescheduled at `now + tier_intervals[tier]`. Pending notifications batched, sent when queue idle (>30s) or buffer hits 5. Notifications via `Notifier.send()`: dry-run → email → Telegram → Discord → desktop, rate-limited at 25 (overflow → summary). Telegram credentials read from `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` env vars if present.

For deeper detail see `SETUP_GUIDE.md` and `TIER_SYSTEM.md`.
