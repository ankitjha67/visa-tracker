# Tier System (v4.0.0)

The tier system lets you check important countries every 10 minutes while leaving the long tail at 90 minutes — without spawning extra processes or burning more CPU. It's the answer to the original v3.2.x problem: when you only really care about UK/Germany/Singapore, why are you waiting 70 minutes for the cycle to come around to them?

## TL;DR

Three tiers:

| Tier | Default interval | What goes here |
|---|---|---|
| **🔥 hot** | 10 min | Immigration priorities — countries you're actively trying to book |
| **🌤 warm** | 30 min | Active interest — Schengen for an upcoming trip, etc. |
| **❄ cold** | 90 min | The long tail — countries you'd be happy to know about but aren't urgent |

By default, every country is in the cold tier and the system behaves identically to v3.2.x. You opt into faster polling per-country.

## Three commands you'll use

### Pick which countries to monitor

```powershell
python visa_tracker_v3.py select-countries
```

Interactive picker. Pick a preset (`immigration`, `schengen`, `asia-pacific`, `gulf`, `americas`, `tier1-work-study`, `all`) or `custom` to choose individually.

### Promote countries to hot tier

```powershell
# Single country
python visa_tracker_v3.py set-tier --country "United Kingdom" --tier hot

# Whole preset to hot
python visa_tracker_v3.py set-tier --preset immigration

# Schengen group to warm
python visa_tracker_v3.py set-tier --preset schengen --tier warm
```

### Run with tier-aware scheduling

```powershell
python visa_tracker_v3.py run --tiered
```

Without `--tiered`, the run loop is the v3.2.x fixed-interval cycle (still works fine). With `--tiered`, the new priority-queue scheduler kicks in.

## How it works under the hood

### Standard run loop (v3.2.x style, still default)

```
[ Cycle 1: 70 min ] [ idle 20 min ] [ Cycle 2: 70 min ] [ idle 20 min ] ...
```

Every cycle checks every target. UK might be checked at minute 5 of cycle 1, then again at minute 5 of cycle 2 — 90 minutes apart. Slot opening at minute 7 of cycle 1 → detected at minute 5 of cycle 2 → 88-minute latency.

### Tiered run loop (v4.0.0 with `--tiered`)

```
[Hot UK] [Hot DE] [Cold AU] [Hot UK] [Hot IE] [Hot DE] [Hot CA] [Cold MY] ...
   ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓
  10min   10min     90min     10min   10min    10min   10min     90min
  later   later     later     later   later    later   later     later
```

Each target carries a tier. After being checked, it's rescheduled at `now + tier_interval`. The scheduler always picks the next-due target. Hot countries get checked 6-9 times per hour; cold countries once every ~90 min. UK slot opening latency drops from 88 min to ~7 min.

### Why this isn't 42 concurrent Chrome instances

Earlier in this project you proposed "1 agent per country, parallel polling." That hits hard limits:

- 42 Chrome instances × 200 MB RAM = 8.4 GB just for browsers
- VFS Cloudflare flags concurrent requests from the same IP within hours
- SQLite write contention with 42 writers

The tier system gets ~95% of the latency benefit with 5% of the resource cost: **one Chrome worker, one Python process**, intelligent scheduling. Concurrent VFS request count is unchanged from v3.2.x — the only difference is *which* targets get checked when.

## Resource cost analysis

A worked example with sensible tiering:

```
Hot tier:  5 countries × 3 cities × every 10min  = 90 checks/hour
Warm tier: 10 countries × 3 cities × every 30min = 60 checks/hour
Cold tier: 30 countries × 4 cities × every 90min = 80 checks/hour
                                          Total ≈ 230 checks/hour
```

For comparison, v3.2.x default (290 city-checks every 90min) = ~193 checks/hour. So tiered is +20% checks/hour for ~7x faster hot-tier latency. Trade-off worth making if your priority countries actually matter.

If you want lower resource use, narrow the hot tier:

```
Hot:  3 cities total (UK Delhi, UK Mumbai, Germany Delhi) × every 10min = 18/hour
Warm: 5 countries × 2 cities × every 30min                              = 20/hour
Cold: 25 countries × 3 cities × every 90min                             = 50/hour
                                                                  Total = 88/hour
```

Less than half of v3.2.x baseline check rate, with sub-15-minute latency on the 3 things you actually care about.

## Config layout

After running `select-countries` and `set-tier`, your `config.json` looks like:

```json
{
  "check_interval_seconds": 5400,
  "tier_intervals": {
    "hot":  600,
    "warm": 1800,
    "cold": 5400
  },
  "max_concurrent": 2,
  "desktop_alerts": true,
  "telegram": {
    "bot_token": "...",
    "chat_ids": ["..."]
  },
  "targets": [
    {
      "country": "United Kingdom",
      "cities": ["New Delhi", "Mumbai", "Bengaluru"],
      "visa_types": ["Standard Visitor", "Skilled Worker"],
      "processor": "vfs_global",
      "tier": "hot"
    },
    {
      "country": "Germany",
      "cities": ["New Delhi", "Mumbai", "Bengaluru"],
      "tier": "hot"
    },
    ...
    {
      "country": "Brazil",
      "cities": ["New Delhi"],
      "tier": "cold"
    }
  ]
}
```

You can edit `tier_intervals` directly to customize the polling cadence. Defaults are sensible but feel free to tighten or loosen.

## Choosing tier values

### Hot tier (`hot`)

Use for **countries you're actively trying to book a slot for, right now**. Examples:

- You have a UK Skilled Worker offer with a CoS deadline — UK Delhi/Mumbai → hot
- You have an Express Entry ITA — Canada Delhi/Mumbai/Chandigarh → hot
- You're trying to attend a conference in Germany next month — Germany Mumbai → hot

Don't put more than ~5 countries × 2-3 cities each in hot. Past that, you spend so much time checking hot targets that cold and warm starve.

### Warm tier (`warm`)

For **active but flexible interest**. Examples:

- General Schengen interest for upcoming holiday — France/Italy/Spain → warm
- Work travel might come up next quarter — Singapore/UAE → warm
- A 6-month booking horizon, not a same-week scramble

Warm can hold 10-20 countries comfortably.

### Cold tier (`cold`)

The default. **Everything you'd be happy to know about but isn't pressing.** Travel enthusiasts watching for spontaneous Schengen availability for instance. The 90-min interval is plenty fast for non-urgent monitoring.

## Migration from v3.2.x

If you have an existing v3.2.4 install:

```powershell
# Drop in v4.0 files (visa_tracker_v3.py, centers.json, requirements.txt)
# Your existing config.json and visa_slots.db work as-is

# Add the tier_intervals key to config.json (one-liner):
python -c "import json; cfg=json.load(open('config.json',encoding='utf-8-sig')); cfg.setdefault('tier_intervals',{'hot':600,'warm':1800,'cold':5400}); json.dump(cfg, open('config.json','w',encoding='utf-8'), indent=2, ensure_ascii=False); print('OK')"

# Promote your priorities
python visa_tracker_v3.py set-tier --preset immigration

# Switch to tiered run mode
python visa_tracker_v3.py run --tiered
```

Without `set-tier`, all targets stay cold and tiered behaves identically to non-tiered. So you can adopt v4.0 without changing behavior, then opt into tiered scheduling when ready.

## When NOT to use tiered

Stick with the v3.2.x non-tiered run loop if:

- **You don't have any actual priorities** — if you'd be equally happy hearing about any of 42 countries, the regular cycle is simpler
- **You're running on GitHub Actions** — Actions cron has 5-30 min jitter, so tier intervals shorter than 30 min don't help. Actions deployment uses `run --once` per cron tick, not the long-running tiered scheduler
- **You're concerned about VFS detection** — tier system slightly increases request rate to hot domains. If you've gotten 403s before, stay on the slower default cycle
- **Your hot list is empty** — without any hot/warm assignments, tiered is exactly equivalent to non-tiered (both run cold-only)

## Inspecting the queue

To see what's queued and tier distribution:

```powershell
python visa_tracker_v3.py status
```

This shows last-run-time per target plus next-due-time for tiered runs.

To force a full rebuild of the queue:

```powershell
# Stop tracker (Ctrl+C), then start again — queue rebuilds from config.json
python visa_tracker_v3.py run --tiered
```

The queue is in-memory only; restarting always re-reads `config.json`.

## Troubleshooting

**"Tiered mode says 'Queue empty — exiting'"**
Your config.json has no targets. Run `python visa_tracker_v3.py select-countries` first.

**"Hot tier targets are checked, but warm/cold never are"**
This means hot target count × 1/hot_interval > 1 check per minute. The scheduler always picks the next-due target, and if hot targets accumulate enough to fill all available time, warm/cold queue indefinitely. Solution: reduce hot tier count, or raise hot interval.

**"I get 403 errors after switching to tiered"**
Cloudflare is rate-limiting. Raise hot interval to 900 or 1200 seconds, or drop hot tier count. The trade-off is latency vs. detection — at some point VFS notices. Don't go below 5 minutes per check on any single URL.

**"Want to monitor 50+ countries with tiered"**
Possible but understand the math: with 50 cold-tier countries × 3 cities × 14.5s/check, one full pass takes ~37 min. So cold targets effectively check every max(90, 37) = 90 min. No degradation. Adding hot targets pushes this longer for cold.
