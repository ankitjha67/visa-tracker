# Internationalization Guide (v4.2.0)

This repo was built for India-outbound visa tracking, but the architecture is **passport-agnostic**. The schema in `centers.json`, the URL patterns, the detection layers — none of them assume your origin country is India. They just *default* to India because that's the maintainer's use case.

This guide shows how to adapt the repo for any origin country.

## TL;DR

What's India-specific:
- The default `centers.json` has Indian VFS URLs (`/ind/en/...`) and Indian application cities
- The country presets in `select-countries` lean toward Indian-popular destinations
- The `_indian_passport_status` field is named for Indians

What's NOT India-specific:
- The detection pipeline (VFS JWT replay, page-change classifier, US wait-time tracker)
- The tier system (hot/warm/cold)
- The notification system (Telegram, desktop, email, Discord)
- The GitHub Actions deployment
- The schema for adding centers

To adapt for another origin country: replace VFS URL prefixes with your country code, swap application cities, optionally rename the passport-status flags. Total work: ~30 minutes for a basic adapted setup.

---

## Worked example 1 — Bangladesh → multi-country

A Bangladeshi traveler applying for UK + Schengen + USA visas.

**Step 1: Identify VFS URL pattern for Bangladesh**

VFS Global URL format is `https://visa.vfsglobal.com/<origin_iso3>/<lang>/<destination_iso3>/`. For Bangladesh:

- `https://visa.vfsglobal.com/bgd/en/gbr/` (Bangladesh → UK)
- `https://visa.vfsglobal.com/bgd/en/can/` (Bangladesh → Canada)
- `https://visa.vfsglobal.com/bgd/en/deu/` (Bangladesh → Germany)
- etc.

Test the URL in your browser before committing. If it 404s, that origin-destination pair isn't on VFS — check the destination embassy's website for alternative paths.

**Step 2: Edit `centers.json`**

Open `centers.json` in your editor. For each center you want to track, change the `appointment_url` from `/ind/en/` to `/bgd/en/`. Update `indian_cities` to your local cities — for Bangladesh that might be:

```json
"indian_cities": ["Dhaka", "Chittagong", "Sylhet"]
```

The field is named `indian_cities` for legacy reasons; just treat it as "application cities in your origin country." (Or rename it to `application_cities` and update the code — see "Renaming the schema" below.)

**Step 3: For US visa, no changes needed**

The `us_state_dept` processor is country-agnostic. State.gov publishes wait times for all 200+ US consulates worldwide. To track Dhaka's US embassy:

```json
{
  "id": "us_bd_dhaka",
  "destination_country": "United States",
  "destination_iso3": "usa",
  "processor": "us_state_dept",
  "appointment_url": "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html",
  "indian_cities": ["Dhaka"],
  "visa_types": ["Visitor (B1/B2)", "Student/Exchange Visitor (F, M, J)"],
  "tier": "cold",
  "enabled": true
}
```

The processor's accent-handling kicks in automatically — it'll find "Dhaka" in the state.gov page regardless.

**Step 4: Update `_indian_passport_status` flags if applicable**

For Bangladesh, the visa-free destinations differ slightly from India:
- Bangladesh-visa-free: most South Asian neighbors, some ASEAN
- Bangladesh-evisa: somewhat similar list to India but not identical

Search `centers.json` for `_indian_passport_status` entries and update them based on Bangladesh's visa policy. Or keep the field as-is but understand it's documenting Indian status — for your case, you'd consult Bangladesh-specific resources.

**Step 5: Run as normal**

```bash
python visa_tracker_v3.py select-countries     # pick what you want
python visa_tracker_v3.py setup-telegram       # phone alerts
python visa_tracker_v3.py calibrate --all
python visa_tracker_v3.py run --tiered
```

Same workflow as Indian users.

---

## Worked example 2 — UK → Schengen tourism

A UK resident wanting to monitor Schengen tourist visa availability for an upcoming Europe trip.

UK residents already have visa-free access to Schengen for short tourism — but not always. Some travelers (UK residents on non-British passports, e.g., Indian-passport-holders on UK student visas) DO need Schengen visas. This example covers that case.

**Step 1: VFS URLs for UK**

VFS in UK uses the path `/gbr/en/<destination>/`:

- `https://visa.vfsglobal.com/gbr/en/fra/` (UK → France)
- `https://visa.vfsglobal.com/gbr/en/deu/` (UK → Germany)
- `https://visa.vfsglobal.com/gbr/en/ita/` (UK → Italy)

**Step 2: Application cities in UK**

UK Schengen VFS centers exist in:

```json
"indian_cities": ["London", "Manchester", "Edinburgh", "Birmingham", "Belfast", "Cardiff"]
```

(Yes, the field name is misleading. See "Renaming the schema.")

**Step 3: Replace the existing centers**

You can either:

- **Edit in place** — open `centers.json`, find/replace `/ind/en/` with `/gbr/en/` for the Schengen entries you want, update cities
- **Add new entries** — keep the Indian entries, add UK-specific entries with new IDs (`vfs_gbr_to_fra`, etc.)

The cleanest approach: fork the repo, make a `centers.uk.json`, point the tracker at it via `--config centers.uk.json` (you'd add this CLI flag — see "Multi-region setup" below).

---

## Worked example 3 — Pakistan → Canada Express Entry

A Pakistani applicant pursuing Canadian PR via Express Entry.

VFS URL: `https://visa.vfsglobal.com/pak/en/can/`
Application cities: Islamabad, Karachi, Lahore (Pakistan's main VFS centers)

```json
{
  "id": "vfs_pak_can",
  "destination_country": "Canada",
  "destination_iso2": "ca",
  "destination_iso3": "can",
  "processor": "vfs_global",
  "appointment_url": "https://visa.vfsglobal.com/pak/en/can/",
  "indian_cities": ["Islamabad", "Karachi", "Lahore"],
  "visa_types": ["Visitor", "Study Permit", "Work Permit", "Permanent Resident"],
  "priority": "high",
  "confidence": "medium",
  "tier": "hot",
  "enabled": true
}
```

For US visa wait times in Pakistan: state.gov has Islamabad consulate. Add similarly to the Bangladesh example.

---

## Worked example 4 — A US citizen tracking visas to other countries

US citizens have visa-free access to many countries, but some destinations require visas regardless of passport (Russia, China, India long-stay, Nigeria, Saudi tourist visas before 2019, etc.).

For US → India visa: India uses Cox & Kings Global Services (CKGS), not VFS. Their portal is at `https://www.in.ckgs.us/`. Adding this requires a new `ckgs` processor — already exists in `centers.json` but currently disabled. See `PROCESSORS.md` for the existing CKGS notes.

For US → Russia: Russia uses VHS Russia from US. URL `https://russia.blsspainglobal.com/USA/`.

For US → China: CVASC (China Visa Application Service Center) at `https://bio.visaforchina.cn/USA/`.

**These all require custom processors.** They're outside the VFS pattern. See "Adding non-VFS processors" below.

---

## Renaming the schema (optional)

If the `indian_cities` field name bothers you, here's how to rename it to something neutral like `application_cities`:

**1. Update centers.json** — find/replace `"indian_cities"` with `"application_cities"` throughout:

```bash
# Linux/Mac
sed -i 's/"indian_cities"/"application_cities"/g' centers.json

# Windows PowerShell
(Get-Content centers.json) -replace '"indian_cities"', '"application_cities"' | Set-Content centers.json
```

**2. Update code references** — the tracker code reads `c.get("indian_cities", ["New Delhi"])`. Find these references:

```bash
grep -n "indian_cities" visa_tracker_v3.py
```

You'll see ~5-10 references. Find/replace them:

```bash
sed -i 's/indian_cities/application_cities/g' visa_tracker_v3.py
```

**3. Update the default fallback values** — in `_default_targets_from_registry()` and similar, the fallback `["New Delhi"]` is India-specific. Replace with whatever's appropriate for your origin (e.g., `["Dhaka"]` for Bangladesh, `["London"]` for UK).

**4. Run smoke test** to verify nothing broke:

```bash
python smoke_test.py
```

After this, your fork is fully neutral. Consider opening a PR upstream if you think the rename should land in the main repo.

---

## Adapting visa-free flags for non-Indian passports

The `_indian_passport_status` field is specifically about Indian passport holders. For other origin passports:

**Option A — Keep the existing flags, ignore them**

Visa-free entries are pre-disabled. If you're, say, Pakistani, then Sri Lanka isn't visa-free for you (Pakistanis need a visa to Sri Lanka), but the flag won't actively harm you — just `enabled: true` for Sri Lanka and the tracker monitors it normally.

```bash
# Re-enable Sri Lanka for Pakistani users
python -c "
import json
with open('centers.json', encoding='utf-8-sig') as f: data = json.load(f)
for c in data['centers']:
    if c['destination_country'] == 'Sri Lanka':
        c['enabled'] = True
        # Optionally clear the misleading flag
        c.pop('_indian_passport_status', None)
        c.pop('_status_note', None)
with open('centers.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"
```

**Option B — Rename and re-flag for your passport**

Add a `_pakistani_passport_status` (or whatever) field. Keep `_indian_passport_status` as historical data. The tracker doesn't read these fields — they're documentation only. Your `select-countries` choices control what's actually monitored.

**Option C — Generalize to `_passport_visa_status` with a config-driven origin**

Larger refactor. Add an `origin_passport` field at the top of `config.json`:

```json
{
  "origin_passport": "pak",
  "tier_intervals": {...}
}
```

Then change the visa-free flag system to be a dict keyed by passport ISO code:

```json
"_passport_visa_status": {
  "ind": {"status": "visa_free", "note": "Free 30-day ETA"},
  "pak": {"status": "appointment_required", "note": "Standard visa"},
  "gbr": {"status": "visa_free", "note": "Visa-free 30 days"}
}
```

This is the cleanest long-term solution but requires code changes. PRs welcome.

---

## Country-specific URL patterns

VFS Global URL pattern: `https://visa.vfsglobal.com/<origin_iso3>/<lang>/<destination_iso3>/`

Common origin codes:

| Origin country | ISO3 |
|---|---|
| India | ind |
| Bangladesh | bgd |
| Pakistan | pak |
| Sri Lanka | lka |
| Nepal | npl |
| United Kingdom | gbr |
| United States | usa |
| Canada | can |
| Australia | aus |
| UAE | are |
| Saudi Arabia | sau |
| Singapore | sgp |
| Malaysia | mys |
| Indonesia | idn |
| Philippines | phl |
| Vietnam | vnm |
| Thailand | tha |
| Hong Kong | hkg |
| Taiwan | twn |
| China | chn |
| Japan | jpn |
| South Africa | zaf |
| Nigeria | nga |
| Kenya | ken |
| Egypt | egy |
| Turkey | tur |
| Russia | rus |

For destinations: same ISO3 codes, used in the URL after the language code.

---

## Multi-region setup (run multiple origin configs)

If you're tracking visas for multiple origin countries simultaneously (e.g., you live between India and UK and need both VFS portals tracked), the cleanest approach is:

**Method 1 — separate `centers.json` per origin**

- `centers.india.json` — India VFS URLs, Indian cities
- `centers.uk.json` — UK VFS URLs, UK cities

The tracker doesn't natively support this; you'd add a CLI flag `--registry centers.uk.json` and update the load_centers_registry path. Small code change. See `load_centers_registry()` in `visa_tracker_v3.py`.

**Method 2 — separate database per origin**

Run two instances of the tracker in different folders, each with its own `centers.json` and `visa_slots.db`. Telegram credentials can be shared (same bot, both instances send to same chat).

**Method 3 — tag entries with origin**

Add an `origin_country` field to each center entry. The tracker would group/filter by this. Requires schema and code changes. Larger refactor but cleanest UX.

For most users, Method 2 (two folders) is simplest.

---

## What you cannot easily adapt

Some things are India-deep enough that adaptation requires real work:

- **VFS JWT replay path**. The endpoint at `lift-api.vfsglobal.com/appointment/slots` accepts a `countryCode=ind` parameter. Other origins have different country codes (`gbr`, `usa`, `pak`, etc.). The processor metadata in `centers.json` hardcodes `"countryCode": "ind"` in the JWT replay payload. Easy fix — find this in `visa_tracker_v3.py`'s `UnifiedChecker.check()` and parameterize, OR fork and replace globally.

- **Country presets in `select-countries`**. The `_COUNTRY_PRESETS` dict in `visa_tracker_v3.py` lists destinations relevant to Indians (immigration: UK/Canada/DE/IE/SG). For UK or Pakistani users, the popular destinations differ. Add new presets to this dict or replace existing.

- **CGI Federal & state.gov processor**. Already country-agnostic in v4.2.0 — works for any origin. No change needed.

- **Documentation tone**. README and docs are India-focused. If you're forking and publishing your adapted version publicly, do a pass through these docs.

---

## Schengen — read this carefully

Schengen visa monitoring is a popular request from international users. **The current architecture handles Schengen well via the existing VFS layer**, but expectations need calibrating.

**What works:**
- VFS Global handles 17 of the 27 Schengen members from most origin countries
- Page-change detection on VFS country landing pages catches new appointment availability
- Real-time-ish detection: 5-90 minutes from slot opening to your notification
- Validated for Indian → Czech Republic May 2026 (real slot detection confirmed)

**What doesn't work (and why):**
- There is NO equivalent of state.gov for Schengen wait times. Each Schengen member publishes (or doesn't) their own wait time data. France publishes some; Germany publishes some on consulate websites; Italy mostly doesn't.
- A unified "Schengen wait-time tracker" would require scraping 17+ different consulate websites, each with different formats. Fragile and maintenance-heavy.
- Some Schengen countries (Switzerland in some regions) use TLS Contact instead of VFS. Different API, different page structures.

**Recommendation:**
- Use the VFS layer (already implemented) for Schengen monitoring. Set Schengen countries to `tier: warm` for 30-min checking — fast enough to catch real slot openings.
- Don't build a Schengen-specific wait-time tracker unless you have a specific consulate website with structured data and you commit to maintaining the parser.
- If you do build a Schengen consulate scraper for your specific case, the pattern from `USStateDeptProcessor` is reusable. Add a `_fetch_<consulate>` method, return wait days dict, plug into the existing alert logic.

---

## Contributing your adaptation back

If you build a working configuration for a non-Indian origin (Bangladesh, Pakistan, UK, etc.), consider opening a PR:

1. Fork the repo on GitHub
2. Make your changes in a branch (e.g., `bangladesh-support`, `uk-residents`)
3. Keep the changes additive where possible — don't break Indian users' configs
4. Open a PR with:
   - A new file like `centers.bangladesh.json` (or whatever fits)
   - Documentation explaining how to use it
   - Notes on what was tested vs theoretical

The architecture is meant to support multiple origin countries. The current default just happens to be India because that's the maintainer's use case.

---

## Quick checklist for adapting

For an X → Y visa tracking setup (origin X, destination Y):

- [ ] Verify VFS URL works in browser: `https://visa.vfsglobal.com/<X_iso3>/en/<Y_iso3>/`
- [ ] If non-VFS, find the actual booking portal
- [ ] Edit `centers.json`: update `appointment_url`, `indian_cities` (= application cities)
- [ ] Optionally: rename `indian_cities` → `application_cities` schema-wide
- [ ] Optionally: update `_indian_passport_status` flags to reflect your passport
- [ ] Run `select-countries` and pick your destinations
- [ ] Run `setup-telegram` for phone alerts
- [ ] Run `calibrate --all` (15-17 min)
- [ ] Run `run --tiered`

The same workflow as Indian users. The architecture doesn't care where you're applying from.
