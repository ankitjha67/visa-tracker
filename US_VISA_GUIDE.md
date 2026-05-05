# US Visa Wait-Time Tracker (v4.1.0)

This guide covers the US-specific tracking introduced in v4.1.0. **Read this before getting excited** — the US is fundamentally different from VFS countries, and what's possible without breaking US government terms of service is more limited than you might hope.

## TL;DR — read this first

The US tracker is a **wait-time trend tracker**, not a real-time slot scraper.

- Latency: days to weeks, not minutes
- What it detects: significant drops in published wait time (signals new slot batches were released)
- What it does NOT do: scrape live slots from CGI Federal's calendar (that requires login + DS-160)

If you saw "US support added" and assumed it meant the same minute-level detection that works for VFS countries — it doesn't. Read the rest of this guide to set expectations correctly.

## Why US is different from VFS

For VFS countries (UK, Canada, Schengen, etc.), the slot calendar is visible to anonymous visitors. The tracker can hit the public booking page, parse the calendar widget, and detect new slot openings within minutes.

US visa appointments work differently:

1. You complete the **DS-160** form online (separate from any tracker)
2. You **pay the visa fee** at a designated bank or via online payment, getting a receipt number
3. You **create an account** on `ais.usvisa-info.com` linked to your DS-160 confirmation number
4. **Only then** can you log in and see the appointment calendar
5. The slot calendar lives behind authentication. There's no public-facing slot list

So a public, unauthenticated tool **cannot see live US slots**. Anyone telling you otherwise is either:
- Using your account with credentials you provided (auth-mode tools — different category)
- Scraping a third-party aggregator like checkvisaslots.com (paid, ToS-questionable)
- Lying

This tracker takes a different, fully legal approach: monitor the **official US Department of State wait-time data** plus the public CGI Federal info page, and detect significant drops that strongly correlate with new appointment batches being released.

## What the v4.1.0 tracker does

Two data sources, both 100% public and unauthenticated:

### Source 1 — US Department of State (authoritative, monthly)

URL: `https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html`

The State Department publishes "estimated wait time until next available appointment" for every US embassy/consulate worldwide, broken down by visa category. For India, that's 5 consulates × 5 visa categories = 25 data points.

**Update cadence: monthly.** The page is updated by State Department staff; the timestamp on the page tells you when. So even if a slot opens up the day after the monthly publication, you won't see it reflected here for ~30 days.

This is still useful — when "Mumbai Visitor (B1/B2)" drops from 437 days to 219 days month-over-month, that's a strong signal that the consulate has been releasing fresh appointments. Race to your CGI Federal account to grab one.

### Source 2 — CGI Federal public wait times (unofficial, more frequent)

URL: `https://ais.usvisa-info.com/en-in/niv/information/visa_wait_times`

CGI Federal (the contractor running the actual appointment system) also publishes wait times on a public page. This data updates more frequently than state.gov (operational changes, batch releases) and tends to lead state.gov by a few days to weeks.

**Update cadence: irregular, typically weekly.** Less authoritative — sometimes shows wait times that seem inconsistent with what users report. Treat as a leading indicator, confirmed by state.gov.

### How alerts fire

The tracker stores the last observed wait time per (consulate, visa_type) in your `visa_slots.db`. On each cycle, it fetches the current value and compares. An alert fires when:

- Wait time **drops by ≥10%** (e.g., 400 → 360 days, or 50 → 45 days), OR
- Wait time **drops by ≥20 absolute days** even if the % is below threshold (catches cases like 50 → 30), OR
- The status **transitions from non-numeric to numeric** (e.g., "Closed" → "120 days", or "Interview Waiver" → "Interview Required")

Alerts include the projected appointment date (today + new wait days) so you know what window opened up.

### The five Indian consulates

| Consulate | Indian city | CGI Federal code |
|---|---|---|
| US Embassy New Delhi | New Delhi | IND-NDL |
| US Consulate Mumbai | Mumbai | IND-MUM |
| US Consulate Chennai | Chennai | IND-CHE |
| US Consulate Hyderabad | Hyderabad | IND-HYD |
| US Consulate Kolkata | Kolkata | IND-KOL |

All 5 are tracked by default in v4.1.0. Visa categories tracked at each: B1/B2 (visitor), F/M/J (student/exchange), H/L/O/P/Q (work/petition-based), C1/D (crew/transit), Other Nonimmigrant.

## Setup

If you've already installed v4.1.0:

```powershell
# US consulates are added to centers.json automatically.
# To enable them in your active monitoring:
python visa_tracker_v3.py select-countries
# Pick: 'all' (or 'americas', or 'custom' and select United States)

# Optional — promote to warm/hot tier for faster checking:
python visa_tracker_v3.py set-tier --country "United States" --tier warm

# Run as usual:
python visa_tracker_v3.py run --tiered
```

That's it. No US-specific configuration needed. The processor handles itself.

## What an alert looks like

```
🇺🇸 US/Mumbai/B1/B2: WAIT TIME DROP 437 → 219 days (projected appointment: 2026-12-09)
```

In Telegram:

```
🎯 Visa Slot Alert! (1 slot)
🟡 United States — Mumbai
   📋 B1/B2
   📅 2026-12-09
   🔍 us_wait_time_drop (medium)
   🔗 Book Now
```

The "Book Now" link goes to `https://ais.usvisa-info.com/en-in/niv/users/sign_in` — your CGI Federal login. From there you'd log in (assuming you've completed DS-160 and paid the fee) and check the calendar for actual available slots.

## What to do when an alert fires

1. **Don't panic.** Wait-time drops ≠ instant slots. They mean appointments are *being released*, not that one is available right now.

2. **Log into ais.usvisa-info.com immediately.** Your DS-160 confirmation + paid receipt should already be linked to your account. The actual slot calendar is post-login.

3. **Check the calendar for your consulate.** Look for available dates. The wait-time signal is correlated but not deterministic — sometimes consulates open and close the booking window quickly.

4. **If a slot is available, book it.** Confirm via email. If your travel plans change, you can usually move the appointment within the system.

5. **If no slot is visible despite the alert:** the wait time data lagged or the slots filled before you arrived. Common, especially for hot consulates. Don't despair — when a consulate is releasing slots, they often release more in the following days. Keep monitoring.

## Limitations to set expectations

**1. Latency is days, not minutes.** State.gov updates monthly. CGI Federal page updates roughly weekly. So even a "fresh" alert is at least 1-7 days behind reality. For comparison, VFS detection latency is 5-90 minutes.

**2. False negatives possible.** A consulate might open and close a slot batch within a single update cycle, leaving the wait time unchanged. You wouldn't get an alert. The tracker only catches drops that survive long enough to be published.

**3. Cannot replace ais.usvisa-info.com checking.** Even with this tracker, **you should still log into your CGI Federal account regularly** (daily if possible during active hunt periods). The wait time is a leading indicator, not a substitute for checking your actual calendar.

**4. State.gov format may change.** The wait times page is server-rendered HTML; the parser uses regex to extract values. If State Department redesigns the page, the parser will break and need updating. The tracker handles this gracefully (returns no data, no false alerts) but you'd silently lose US monitoring until the parser is fixed.

**5. Not a slot scraper.** Cannot tell you "Mumbai has a slot on 2026-08-15 at 10am." It can only tell you "Mumbai's wait time dropped substantially, go check."

## What the tracker deliberately does NOT do

These are out of scope by design, not because they're impossible:

- **Authenticated CGI Federal scraping.** Logging into your account, scraping the calendar widget, detecting actual available slots. This works technically but: (a) violates CGI Federal ToS, (b) carries account-lock risk, (c) requires storing your credentials. There are paid services that do this — use them at your own risk if you choose. This tracker won't.

- **Mexico / Canada US-visa monitoring.** Some Indians strategize by interviewing at third-country consulates (Ciudad Juárez, Vancouver) where wait times are shorter. The US has discouraged this and many consulates have stopped accepting third-country nationals. Tracking those consulates would be possible (state.gov publishes their data too) but isn't currently implemented. PRs welcome.

- **Interview waiver eligibility tracking.** Some Indians qualify for "interview waiver" (drop box) which has different and often shorter wait times. The state.gov page sometimes shows this; v4.1.0 does NOT currently parse it separately. Future enhancement.

- **Dropbox vs in-person distinction.** Treated as the same data point. Could be improved.

- **Email/SMS to your CGI Federal account.** Out of scope; that's CGI Federal's job.

## When to NOT use this tracker

- You haven't completed DS-160 yet. The wait time data is meaningless without the prerequisites for booking.
- You're applying for an immigrant visa (green card category). The state.gov "global wait times" page covers nonimmigrant visas. For immigrant visas use the [IV Scheduling Tool](https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/iv-wait-times.html) directly.
- You only need a single appointment in the next 30+ days at a non-bottleneck consulate. The current US wait times are dynamic enough that monthly checking via state.gov directly may be sufficient for casual planning.

## Comparison to VFS countries

| Feature | VFS (UK, Schengen, etc.) | US (state.gov + CGI Federal) |
|---|---|---|
| Detection latency | 5–90 minutes | 1–30 days |
| Data source | Live slot calendar (anonymous) | Published wait times |
| What it detects | Actual available slots | Significant wait time drops |
| What you do on alert | Book within minutes | Check CGI Federal account |
| Reliability | High (validated production) | Medium (correlation, not direct) |
| Auth required | None | Account login on US side |

US monitoring should complement, not replace, your manual checking on `ais.usvisa-info.com`.

## Frequently asked questions

**"Does this work better than checkvisaslots.com?"**
Different category. checkvisaslots.com (and similar paid services) scrape authenticated CGI Federal data using either user-supplied credentials or shared accounts. They have higher latency-to-detection (minute level) but operate in a legally gray area and charge ~$10-30/month. v4.1.0 is free, public-data-only, and has higher latency (day-to-week level). Use whichever fits your risk tolerance and budget.

**"Why monthly state.gov updates? Why not daily?"**
State Department staff manually compile and review the data. They explicitly say "We update visa wait time information monthly" on the page. Not technical limitation — policy choice.

**"Can I add interview waiver tracking?"**
Yes — the state.gov page does sometimes mark "Interview Waiver" eligibility per visa category. The current v4.1.0 parser doesn't extract that field separately. Look at `USStateDeptProcessor._fetch_state_gov` in the code; you'd add another regex pattern for "Interview Waiver" status and treat its appearance as a separate alert. PR welcome.

**"What about expedited / emergency appointments?"**
State.gov mentions an "expedited appointment" process for emergencies (medical, business, education deadlines). This is a per-applicant manual request to the consulate, not a slot category. The tracker doesn't and can't help with this.

**"What if I need a real-time US tracker right now?"**
You have three options: (a) pay for a service like checkvisaslots.com or visa-tracker.com, (b) use Telegram channels run by individuals (search "US visa slots India Telegram"), (c) write your own authenticated scraper. v4.1.0 isn't trying to compete with (a) — it's giving you a free, legal trend signal that complements those tools.

**"Will future versions add real-time US slot tracking?"**
Possibly, with explicit user-supplied credentials (encrypted, opt-in, never committed to GitHub). That would be a significant feature addition with significant risk. Not on the v4.x roadmap; might come in v5.

## Architecture notes (for developers)

The processor lives in `visa_tracker_v3.py` as `USStateDeptProcessor`. Dispatch happens in `UnifiedChecker.check()` at the very top, before the VFS/JWT layer:

```python
if rec_for_proc.get("processor") == "us_state_dept":
    return self.us_state_dept.check(country, city, visa_types)
```

The processor is pure HTTP — no Selenium, no browser, no calibration. Each check is ~2–5 seconds (single GET, regex parse, DB compare). 5 consulates × 1 cycle = ~15 seconds. Tier system applies normally; default is `cold` (90 min) which is reasonable given the underlying data updates monthly.

Wait time history is stored in `visa_slots.db` in the existing `slots` table, with a synthetic `id` like `us_waittime|Mumbai|B1/B2`. The `metadata` JSON column carries the actual wait_days value. This avoids a schema migration.

To extend with new visa categories: add to `USStateDeptProcessor.VISA_TYPE_CODES`. The regex extractors auto-pick up anything in that map.

To add a third data source (e.g., a state-specific announcements RSS): add a method `_fetch_<source>(consulate)` and chain it after `_fetch_cgi_federal` in `_fetch_wait_times`.

## Disclaimer

This project is unaffiliated with the US Department of State, US embassies and consulates, CGI Federal, or any visa application service. It only reads publicly visible data from official US government and contractor websites. No login, no scraping of authenticated content, no credential handling.

Use of this tracker does not improve or guarantee the success of your visa application. It only helps you spot wait-time trends. The US visa process is governed by US law and consular discretion, and a wait-time alert tells you nothing about whether your individual application will be approved.
