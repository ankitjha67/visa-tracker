# User Guide — Visa Slot Tracker (current version: v4.4.0)

This guide is for **non-technical users**. No coding background required. If you can install software and follow recipes, you can run this tool.

---

## What is this?

A small program that watches **visa application websites** for India outbound travellers and pops up a notification the moment a new appointment slot opens up. You can then race to the booking website and grab the slot before someone else does.

That's it. It's a tireless watcher.

### Why use it?

Visa appointments at popular destinations (UK, Canada, Schengen countries) frequently have **zero availability for months**. When a slot does open up — often when someone cancels — it disappears within minutes. Without a tool like this, you'd have to refresh the booking page manually every few minutes, all day. With it, you carry on with your life and your laptop tells you the second something opens.

### What's new in v4.0.0

Three big additions over v3.2.4:

1. **Tier system** — Hot-priority countries (the ones you're actively trying to book) check every 10 minutes; the rest stay at 90 minutes. Fast detection on what matters, no waste on what doesn't.

2. **Telegram setup wizard** — A 60-second guided setup gets your phone receiving alerts. So you catch slots even when away from your laptop.

3. **GitHub Actions deployment** — Run the tracker 24/7 in the cloud (free) instead of on your laptop. Catches slots while you sleep.

Plus: **`select-countries`** to choose what to monitor (instead of monitoring all 82 by default), and a smarter `centers.json` that automatically skips visa-free destinations.

### What it can NOT do

- It cannot **book** the slot for you. You still have to log in and complete the booking yourself.
- It cannot find slots that VFS Global has marked as private/login-only.
- It cannot work for visa-free countries (Sri Lanka, Thailand, Malaysia, Maldives, Bhutan, Nepal, Indonesia, Mauritius, etc.) — those visas are issued instantly online or on arrival, no slots to monitor. v4.0.0 automatically skips these.
- It cannot work without your computer being on (unless you deploy to GitHub Actions).

---

## Before you start: 3 things you need

### 1. A Windows computer

Tested on Windows 11. Should also work on Windows 10. Mac and Linux work but the desktop notification setup is slightly different.

### 2. Python 3.10 or newer (free)

1. Go to https://www.python.org/downloads/
2. Click "Download Python 3.x.x"
3. Open the downloaded file
4. **Important:** Check the box "Add python.exe to PATH" on the first install screen
5. Click "Install Now"

Verify by opening PowerShell and typing `python --version`. You should see `Python 3.x.x`.

### 3. Google Chrome (free)

If not already installed: https://chrome.google.com.

---

## Setup — 10 minutes

### Step 1 — Make a folder and unzip

Create a folder like `D:\Visa Tracker`. Right-click `visa-tracker-v4.zip` → Extract All → choose your folder → Extract.

You should see these files:

```
Visa Tracker/
├── visa_tracker_v3.py        (the program)
├── centers.json              (list of countries it can watch)
├── requirements.txt          (helper libraries)
├── smoke_test.py             (verifies install)
├── smoke_test.ps1            (one-click test launcher)
├── USER_GUIDE.md             (this file)
├── QUICKSTART.md             (technical reference)
├── ADDING_COUNTRIES.md       (how to expand coverage)
├── TIER_SYSTEM.md            (priority tier details)
├── TELEGRAM_SETUP.md         (Telegram bot guide)
├── GITHUB_ACTIONS.md         (cloud deployment)
├── VISA_FREE_GUIDE.md        (how to manage visa-free entries)
├── CHANGELOG.md              (version history)
├── SETUP_GUIDE.md            (architecture reference)
├── PROCESSORS.md             (visa processor notes)
└── visa-dashboard.jsx        (optional web dashboard)
```

### Step 2 — Open PowerShell in that folder

Right-click on the folder while holding **Shift**, then click "Open PowerShell window here".

### Step 3 — Install helper libraries

Paste this into PowerShell:

```powershell
chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
python -m pip install -r requirements.txt
```

Takes 30-90 seconds. Ignore any "pip out of date" warnings.

### Step 4 — Run the smoke test

```powershell
.\smoke_test.ps1
```

Seven stages run, each ending with "OK" in green. The last stage pops up a Windows notification saying "Visa Slot Alert / Smoke Test." If all 7 stages pass, you're ready.

### Step 5 — **Pick which countries to monitor** (NEW in v4.0.0)

Instead of watching all 82 countries (overkill, slow, more risk of website blocking), pick what you care about:

```powershell
python visa_tracker_v3.py select-countries
```

You'll see preset options:

| Preset | What's included |
|---|---|
| `immigration` | UK, Canada, Germany, Ireland, Singapore (5 countries) |
| `schengen` | All 17 Schengen countries |
| `asia-pacific` | Japan, Korea, Singapore, Australia, NZ, China, Thailand, Vietnam |
| `gulf` | UAE, Saudi Arabia, Qatar, Bahrain, Kuwait, Oman |
| `americas` | Canada, USA, Mexico, Brazil |
| `tier1-work-study` | UK, Canada, Australia, Germany, Ireland, NZ, Singapore, Netherlands |
| `all` | Everything except visa-free destinations (~64 countries) |
| `custom` | Pick numbered countries from a list |

Type the preset name (e.g., `immigration`) and confirm. The tracker now monitors only those countries.

### Step 6 — **Promote priorities to hot tier** (NEW in v4.0.0)

If you have specific countries you really want fast detection on, mark them as "hot":

```powershell
# Promote a single country
python visa_tracker_v3.py set-tier --country "United Kingdom" --tier hot

# Or promote a whole preset
python visa_tracker_v3.py set-tier --preset immigration
```

Hot-tier countries get checked every 10 minutes. The rest every 90 minutes. Big difference if a slot opens at 11:31 — hot detects it by 11:41, cold by 13:00.

### Step 7 — Set up Telegram (recommended)

Desktop notifications only fire when you're at your laptop. For 24/7 phone alerts:

```powershell
python visa_tracker_v3.py setup-telegram
```

A wizard walks you through:
1. Create a Telegram bot via `@BotFather` (~2 min)
2. Paste your bot token (wizard validates it)
3. Send any message to your bot from Telegram
4. Wizard auto-detects your chat ID
5. Wizard sends a test message — you confirm you got it
6. Saved to config.json

5 minutes total. You now get visa alerts on your phone.

If you want to skip this for now: desktop toasts still work, you just won't get phone alerts.

### Step 8 — First-time calibration

Calibration teaches the tracker the structure of each visa website. Required once on first install, then every 3 weeks.

```powershell
python visa_tracker_v3.py calibrate --all
```

Takes 15-17 minutes. Just leave it running.

### Step 9 — Start monitoring

Two options:

**Standard mode** (every country checked at 90-min intervals):

```powershell
python visa_tracker_v3.py run
```

**Tiered mode** (hot countries every 10 min, others slower) — RECOMMENDED if you used set-tier:

```powershell
python visa_tracker_v3.py run --tiered
```

Either way, leave the PowerShell window open. Closing it stops the tracker. To stop cleanly: press `Ctrl + C`.

---

## What a real notification looks like

When a slot opens:

1. **Windows toast** in the bottom-right:
   > 🎯 Visa Slot Alert
   > 1 visa slot(s): United Kingdom

2. **Telegram message** on your phone (if configured):
   > 🎯 Visa Slot Alert! (1 slot)
   > 🟢 United Kingdom — New Delhi
   > 📋 Standard Visitor
   > 📅 2026-05-08
   > 🔗 [Book Now]

3. **Log line** in PowerShell showing detection method and confidence

### What to do when you get one

The moment a notification fires:

1. **Open the visa booking website**: e.g., `https://visa.vfsglobal.com/ind/en/gbr/` for UK
2. **Log in** or proceed without account
3. **Pick your city and visa type**
4. **If you see "Earliest available slot is: <date>"** → click through and book it
5. **If you see "No appointments available"** → you missed it; the slot was taken in the seconds between notification and your click. Better luck next time.

For UK Skilled Worker, Canada Express Entry, Germany National visa — the popular corridors — slots get snapped within minutes. Have your visa documents ready in a folder so you don't fumble.

---

## Stopping, restarting, and pausing

### Stop the tracker

Press `Ctrl + C` in the PowerShell window. The tracker shuts down cleanly.

### Restart later

```powershell
python visa_tracker_v3.py run         # or with --tiered
```

It picks up where it left off. The database persists.

### Pause for weeks or months

Just stop the tracker. Files stay in place. To resume, run `calibrate --all` first (websites change), then `run`.

If pausing for very long, see GITHUB_ACTIONS.md for cloud deployment that runs without your laptop.

---

## Recommended setups for different situations

### "I'm actively trying to book a UK Skilled Worker slot"

```powershell
python visa_tracker_v3.py select-countries     # pick: immigration
python visa_tracker_v3.py setup-telegram       # phone alerts critical
python visa_tracker_v3.py set-tier --preset immigration   # hot tier
python visa_tracker_v3.py calibrate --all      # one-time
python visa_tracker_v3.py run --tiered         # 10-min UK polling
```

Run it for 1-2 weeks during your active booking window. Stop when you've booked.

### "I want to keep an eye on Schengen for an upcoming Europe trip"

```powershell
python visa_tracker_v3.py select-countries     # pick: schengen
python visa_tracker_v3.py setup-telegram
python visa_tracker_v3.py set-tier --country "France" --tier warm
python visa_tracker_v3.py set-tier --country "Italy" --tier warm
python visa_tracker_v3.py calibrate --all
python visa_tracker_v3.py run --tiered
```

Warm tier (30-min checks) is enough — Schengen tourist slots aren't typically as competitive as work visas.

### "I want set-and-forget cloud monitoring"

See `GITHUB_ACTIONS.md`. ~30 minutes setup, then runs forever for free.

### "I want broad coverage to spot interesting opportunities"

```powershell
python visa_tracker_v3.py select-countries     # pick: all
python visa_tracker_v3.py setup-telegram
python visa_tracker_v3.py calibrate --all
python visa_tracker_v3.py run                 # standard mode, no tiers
```

64 countries, 90-min cycles. Lots of broad visibility, no urgency.

---

## Useful commands cheat sheet

| What you want | Command |
|---|---|
| Pick countries to monitor | `python visa_tracker_v3.py select-countries` |
| Promote country to hot tier | `python visa_tracker_v3.py set-tier --country "Germany" --tier hot` |
| Promote preset to hot | `python visa_tracker_v3.py set-tier --preset immigration` |
| Set up Telegram | `python visa_tracker_v3.py setup-telegram` |
| First-time calibration | `python visa_tracker_v3.py calibrate --all` |
| Recalibrate one country | `python visa_tracker_v3.py calibrate --country "United Kingdom"` |
| Start monitoring (tiered) | `python visa_tracker_v3.py run --tiered` |
| Start monitoring (standard) | `python visa_tracker_v3.py run` |
| Test mode (no real alerts) | `python visa_tracker_v3.py run --dry-run` |
| Single check then exit | `python visa_tracker_v3.py run --once` |
| Check current status | `python visa_tracker_v3.py status` |
| List all available countries | `python visa_tracker_v3.py coverage` |
| Verify all URLs work | `python visa_tracker_v3.py verify-urls` |
| Run smoke test | `.\smoke_test.ps1` |
| Stop the tracker | Ctrl+C in PowerShell |

---

## Adding more countries or cities

If a country you care about isn't on the list, see `ADDING_COUNTRIES.md`. You can add:

- **A new Indian city** to an existing country (1 minute)
- **A new VFS Global country** (5 minutes)
- **A new embassy-direct country** (10 minutes)

Plus an embassy URL reference table covering ~30 destinations.

## Visa-free destinations (Sri Lanka, Thailand, etc.)

These don't have appointment slots — Indian passport holders enter without booking. v4.0.0 automatically skips them. See `VISA_FREE_GUIDE.md` for which countries are flagged and how to re-enable them if your situation differs.

---

## Troubleshooting

### Smoke test stage 7 — no notification appears

Three possibilities:
1. **Focus / Do Not Disturb is on.** Settings → System → Focus → turn off
2. **App-level notifications blocked for Python.** Settings → System → Notifications → enable for Python
3. **Master notification toggle is off.** Same Settings page, top toggle

The toast might also be sitting silently in Notification Center (the icon next to the date). Check there.

### "python is not recognized"

Python wasn't added to PATH on install. Reinstall and check the PATH box.

### "The tracker keeps showing errors for one country"

The website probably changed. Recalibrate just that country:

```powershell
python visa_tracker_v3.py calibrate --country "Country Name"
```

### "I missed a slot — what went wrong?"

Most likely cause: cycle interval was too long for that country. If a slot opens at 11:31 and your last check was 11:00 with the next at 12:30, you'd see it 60 minutes too late.

Solutions:
- Promote that country to **hot tier** (`set-tier --country X --tier hot`) → 10-min checks
- Set up **Telegram** so you get phone alerts even when away from laptop
- Consider **GitHub Actions deployment** for 24/7 monitoring

### "I'm getting too many notifications"

Check what's firing:

```powershell
python visa_tracker_v3.py status
```

If the tracker is alerting on noise (false positives), open an issue or recalibrate. Real alerts should be 0-5 per day for active corridors.

---

## How long should I run this?

Same advice as before: **run when you actually need a slot, pause otherwise.**

Visa tracking is a tool, not a service. Set it up before a known booking window (usually 2-4 weeks before a deadline), let it run, stop after you've booked. Running for 6 months continuously isn't useful — if no slots have appeared in 6 months, the constraint is upstream and a tool can't help.

For long-term passive monitoring (e.g., "tell me whenever Czech Republic opens"), GitHub Actions deployment is better than running a local laptop forever.

---

## Plain-English summary of v4.0.0

You install Python and Chrome, unzip the tracker, run `pip install -r requirements.txt` once, run `select-countries` to pick what to monitor, run `setup-telegram` for phone alerts, run `set-tier` to promote priorities, run `calibrate --all` to teach the websites, then run `run --tiered` for fast monitoring. Slots open → Windows toast + Telegram message. You race to the booking site.

Pause when you've booked. Resume when you need it again. Or set up GitHub Actions for cloud monitoring.

Welcome to less manual refreshing.
