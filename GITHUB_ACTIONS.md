# GitHub Actions Deployment (v4.0.0)

Run the visa tracker 24/7 in the cloud, free, with no laptop required. This is the right deployment for anyone whose machine sleeps, travels, or whose owner has a life.

## What you get

- **Cycles run every 30 minutes**, regardless of whether your laptop is on
- **Telegram notifications to your phone** the moment a slot is detected
- **Weekly automatic recalibration** to handle VFS endpoint rotations
- **Daily healthcheck ping** so you know the system's alive
- **Free tier sufficient** if you use a public repo
- **Full state persistence** — calibration data, JWT cache, page hashes survive between runs

The trade-offs:

- **Cron jitter**: GitHub Actions cron has 5-30 min jitter at peak times. A 30-min cron effectively fires every ~35-60 min. Don't expect 5-minute precision.
- **Limited tier system**: Tiered scheduling (`run --tiered`) needs a long-running process; Actions runs `run --once` per cron tick, so all targets are checked once per workflow run regardless of tier
- **JWT layer probably won't work**: VFS Cloudflare often serves 403s to Azure IP ranges (which Actions runners use). Page-change layer is the primary signal — same as v3.2.x production validation showed
- **2,000 minute/month free tier on private repos**. A monitor cycle is ~10-15 min; over a month at 30-min schedule that's ~17,000 min. **You need a public repo**, OR pay (~$140/month at full burn), OR cut cycle frequency drastically
- **No desktop toasts** (obviously — this runs on a server, not your laptop)

## Architecture

Three workflows in `.github/workflows/`:

| Workflow | Schedule | Purpose |
|---|---|---|
| `monitor.yml` | every 30 min | Main monitoring loop. Runs `run --once`, fires Telegram on alerts |
| `calibrate.yml` | Sunday 04:00 UTC | Weekly recalibration. Refreshes endpoints, JWT discovery |
| `healthcheck.yml` | daily 03:00 UTC | Sends a daily Telegram message confirming the tracker is alive |

State (`visa_slots.db`) persists between runs via [GitHub Actions cache](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows). Cache entries expire after 7 days of no access; with daily activity, your state stays alive indefinitely.

Notifications use Telegram (set up via `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` secrets — see "Setup" below).

## Setup — 15 minutes

### Step 1 — Create a Telegram bot

If you don't have one already, follow `TELEGRAM_SETUP.md` (or run `python visa_tracker_v3.py setup-telegram` locally first to auto-configure).

You need:
- Bot token (from `@BotFather`)
- Chat ID (from sending a message to your bot, or via `@userinfobot`)

### Step 2 — Create a public GitHub repository

```bash
# On your local machine, in the v4.0.0 folder
git init
git add .
git commit -m "Initial v4.0.0 deployment"

# Create a new public repo on GitHub (via web UI or gh CLI)
gh repo create visa-tracker --public --source=. --push
```

If you'd rather keep your code private:

- **Pay**: GitHub Actions on private repos = 2,000 min/month free, then $0.008/min on Linux. ~17K minutes ÷ free tier = need to cut by 8.5x or pay
- **Reduce frequency**: cron every 4 hours = ~125 min/month. Free tier covers this comfortably. But latency goes from 30 min to 4+ hours
- **Reduce country count**: with 5 countries × 3 cities, a cycle takes ~4 min instead of 12. 30-min cron = 4 min × 48/day = 192 min/day → too much. 2-hour cron = 4 min × 12/day = 48 min/day → fits

For most users, **public repo + free tier is the cleanest path**. Just don't commit personal info — use Secrets for everything sensitive.

### Step 3 — Add secrets

On GitHub, go to: **Settings → Secrets and variables → Actions → New repository secret**

Add two secrets:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID (or comma-separated list) |

Optional:

| Name | Value | When to set |
|---|---|---|
| `NOTIFICATION_DRY_RUN` | `true` | If you want to test the workflow without sending real Telegram messages |

After saving, the secrets are encrypted at rest. Even repo collaborators can't read them — only your workflows can.

### Step 4 — Run a manual test

Go to **Actions tab → Monitor Visa Slots → Run workflow → Run workflow**. The job runs immediately. Watch the logs.

Expected progression:
1. Checkout repo
2. Set up Python 3.12 (cached)
3. Install Chrome (~30s)
4. Restore tracker state (cache miss on first run → empty DB)
5. Install Python deps (~60-90s)
6. Run a single check cycle (`run --once`) — takes 10-15 min on Linux
7. Save tracker state to cache
8. (If failure) Send Telegram failure notice

If it succeeds: your monitor is live. Schedule will auto-trigger from now on.

If it fails: check the logs in the Actions tab. Most common issues:
- **`No targets in config.json`**: you didn't run `select-countries` before pushing. Either commit a config.json with targets, or have the workflow do it (see "Bootstrap config" below)
- **Chrome startup error**: usually transient, retry once
- **Network error to VFS**: Cloudflare may have blocked the runner. Manual retry, or accept it as expected (page-change layer still works)

### Step 5 — Verify the daily healthcheck

The next day, check Telegram. You should see a message like:

```
🤖 Visa Tracker Daily Healthcheck
Time: 2026-05-06T03:00:18Z
Checks (24h): 432
Active slots: 3
Errors (24h): 12

If you stop seeing these daily, the cron is broken.
```

If the daily message doesn't arrive, your cron is broken — check Actions tab. Usually a fixable issue (wrong secret name, syntax error in the YAML).

## Bootstrap config — first-time-only setup

The workflows expect a `config.json` to already exist with targets configured. If you push a fresh repo, you need to commit one. Easiest path:

### Option 1: Configure locally first, commit results

```powershell
# On your laptop
python visa_tracker_v3.py select-countries     # pick countries
python visa_tracker_v3.py set-tier --preset immigration  # optional
git add config.json centers.json
git commit -m "Configured monitoring targets"
git push
```

Now your repo has the config GitHub Actions needs.

### Option 2: Add a setup step to the workflow

Edit `.github/workflows/monitor.yml`. Before the "Run a single check cycle" step, add:

```yaml
      - name: Bootstrap config (first run only)
        run: |
          if [ ! -f config.json ]; then
            python -c "
            import json, sys
            sys.path.insert(0, '.')
            from visa_tracker_v3 import _default_targets_from_registry, load_centers_registry
            global CENTERS_REGISTRY
            import visa_tracker_v3 as m
            m.CENTERS_REGISTRY = load_centers_registry()
            cfg = {
                'check_interval_seconds': 5400,
                'tier_intervals': {'hot': 600, 'warm': 1800, 'cold': 5400},
                'desktop_alerts': False,
                'targets': m._default_targets_from_registry(),
            }
            json.dump(cfg, open('config.json', 'w'), indent=2)
            print(f'Wrote config.json with {len(cfg[\"targets\"])} targets')
            "
          fi
```

Now every workflow run checks for `config.json` and creates it if missing, with all enabled centers.

### Option 3: Commit a starter config.json

Hand-write a minimal config:

```json
{
  "check_interval_seconds": 5400,
  "desktop_alerts": false,
  "tier_intervals": {"hot": 600, "warm": 1800, "cold": 5400},
  "targets": [
    {
      "country": "United Kingdom",
      "cities": ["New Delhi", "Mumbai"],
      "visa_types": ["Standard Visitor", "Skilled Worker"],
      "tier": "cold"
    },
    {
      "country": "Germany",
      "cities": ["New Delhi", "Mumbai"],
      "visa_types": ["Schengen", "National"],
      "tier": "cold"
    }
  ]
}
```

Commit and push. Workflows pick it up.

## Cycle frequency tuning

The default `*/30 * * * *` cron is a balance between detection latency and free-tier consumption. Tighten or loosen based on your needs:

| Cron expression | Effective frequency | Min/day | Min/month | Public free? | Private free? |
|---|---|---|---|---|---|
| `*/15 * * * *` | every ~20-45 min | 480 | ~14,400 | yes | no (need ~$130/mo) |
| `*/30 * * * *` (default) | every ~35-60 min | 240 | ~7,200 | yes | no (need ~$60/mo) |
| `0 */1 * * *` | every ~1.5 hours | 80 | ~2,400 | yes | barely (1.2x free) |
| `0 */2 * * *` | every ~2.5 hours | 40 | ~1,200 | yes | yes (60% free tier) |
| `0 */4 * * *` | every ~4-5 hours | 20 | ~600 | yes | yes (30% free tier) |

For Indian outbound visa hunting where slots open and close in minutes, **`*/30` or `0 */1` is the sweet spot**. Tighter than 15-min cron just buys you the same effective interval at 2x the runner cost (because of Actions cron jitter).

To change: edit `.github/workflows/monitor.yml` line `- cron: '*/30 * * * *'`.

## Resource use estimates

A single monitor cycle on a `ubuntu-latest` runner:

| Phase | Time |
|---|---|
| Checkout + Python setup | ~30s (cached) |
| Chrome install | ~30s |
| Cache restore | ~5s |
| pip install | ~60-90s (cached partial) |
| Single cycle (40 targets × 4 cities × 14s/check) | ~10-12 min |
| Cache save | ~5s |
| Total | ~12-15 min |

For 30-min cron + 30 day month: 60 cycles/day × 13 min/cycle × 30 days = **23,400 minutes/month**.

That's far over the 2,000 min/month private repo free tier. **Public repos are necessary** unless you're paying.

## What you cannot do on Actions

- **Tiered scheduling (`run --tiered`).** The tiered scheduler needs a long-running process. Actions cron triggers `run --once` per cycle, which checks all targets sequentially regardless of tier. You can simulate tiering by running multiple workflows at different cron schedules (one for hot-tier countries every 15 min, one for cold every 90 min) but it's complex.
- **Real-time alerts.** Cron jitter means alerts arrive 0-30 min after the slot opens. For hot corridors (UK Skilled Worker), this matters. Consider running locally during active booking windows.
- **Server-side dashboard.** The web dashboard component (`visa-dashboard.jsx`) requires the WebSocket server, which doesn't fit Actions' short-lived job model.

## Hybrid deployment

The optimal setup for someone in active visa-hunting mode:

- **Local laptop**: Run `--tiered` mode for fast detection on hot countries. Telegram + desktop notifications both fire
- **GitHub Actions**: Background monitor for everything else, fires Telegram if you're not at your laptop or your laptop is off

Both can use the same Telegram bot/chat. You'll get duplicate notifications when both detect the same slot, which is fine — better duplicates than misses.

## Pausing without deleting

To temporarily disable monitoring without removing files:

1. Edit each workflow file (`.github/workflows/*.yml`)
2. Comment out the `schedule:` lines:
   ```yaml
   on:
     # schedule:
     #   - cron: '*/30 * * * *'
     workflow_dispatch:
   ```
3. Commit and push

Workflows can still be triggered manually but won't auto-run. Re-enable by uncommenting and pushing.

To pause for a week or two: simpler to just disable workflow files in **Settings → Actions → General → Disable Actions**.

## Troubleshooting

**"Workflow runs but no Telegram messages arrive"**

- Check secrets are correctly named (`TELEGRAM_BOT_TOKEN`, not `TELEGRAM_TOKEN`)
- Check the bot was actually started by you (send `/start` to it)
- Look at the workflow log; should see `Telegram: bot_token loaded from environment`

**"Cycle hangs and times out"**

- Increase `timeout-minutes` in monitor.yml (default 25). Real cycles usually take ~13 min on Actions, but Selenium startup can be slow on cold runners
- Check for VFS Cloudflare blocks — those produce 33s timeouts per affected city. With 40 cities all timing out, cycle exceeds 25 min

**"Cache misses every run, deps reinstall every time"**

- The pip cache is keyed by `requirements.txt` hash. If you're regenerating `requirements.txt` somehow, cache won't hit. Check it's stable.
- The state cache (`visa-state-`) is keyed by `${{ github.run_id }}`. First run after a long pause may miss restore but will save for next time. Subsequent runs hit. If state always misses → check the cache size limit (10 GB per repo)

**"All cycles fire 403 errors against VFS"**

- Cloudflare has flagged the runner IP range. This is partially expected — VFS detects cloud-based scrapers
- Page-change layer should still work (it doesn't use authenticated VFS APIs). Check if your alerts are coming from `page_change` method
- Consider running `verify-urls` to see exactly which sites are blocked. Can also try moving to self-hosted runners or other clouds (Hetzner, Vultr) where IPs aren't flagged

**"GitHub bills me unexpectedly"**

- You probably went private. Switch repo back to public, or pause workflows, or pay
- Check **Settings → Billing → Plans and usage → Actions usage** to see consumption

## Checklist before you push

Before committing a workflow setup that auto-runs every 30 min:

- [ ] Repo is public (or you've accepted private repo billing)
- [ ] `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` secrets configured
- [ ] `config.json` committed with at least 1 target
- [ ] Tested workflow manually via `workflow_dispatch` once and it succeeded
- [ ] Telegram test message received
- [ ] No personal info / API keys / passwords in any committed file
- [ ] You actually want this — turning it off later requires editing files; running 24/7 forever has a cost (electricity, GitHub free tier consumption, cognitive load of constant phone notifications)

If all checked → push, watch the next scheduled run, and you're live.
