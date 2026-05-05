# Visa-Free Destinations Guide (v4.0.0)

This guide covers the `_indian_passport_status` flagging system added in v4.0.0. Some destinations on the tracker don't actually need monitoring because **Indian passport holders enter visa-free or via instant e-visa**. Watching their websites produces no useful signal — the tracker can't find slots that don't exist.

v4.0.0 marks these destinations explicitly with a `_indian_passport_status` field, sets `enabled: false`, and keeps them in `centers.json` with explanatory metadata. They're skipped by default but easy to re-enable if your situation differs (different passport, policy change, etc.).

## Why this matters

Before v4.0.0, monitoring Sri Lanka cost ~30 seconds per cycle. Across 90+ cycles per day, that's 45 minutes of wasted time monitoring a country where slots don't exist. Multiply by 8 visa-free destinations, you're looking at ~6 hours of CPU per day on pointless monitoring.

The cleanup is purely additive — nothing is deleted, just filtered out by default.

## What got flagged

### Visa-free for Indian passports (7 destinations)

These have `_indian_passport_status: visa_free`:

| Country | Status | Note |
|---|---|---|
| Sri Lanka | Free 30-day double-entry ETA | Confirmed permanent in 2026 by Sri Lankan High Commissioner; no appointment, no fee |
| Thailand | Visa-free 60 days | Effective since 2024 |
| Malaysia | Visa-free 30 days | Active since 2024 |
| Bhutan | No visa needed for Indians | Free entry permit at the border |
| Nepal | Visa-free | Indian citizens can enter freely by air or land |
| Maldives | Visa-on-arrival | 30 days, free |
| Indonesia | Visa-on-arrival | 30 days, ~$35 USD fee but no appointment booking |

### E-visa only (5 destinations)

These have `_indian_passport_status: evisa`:

| Country | Portal | Note |
|---|---|---|
| Vietnam | https://evisa.xuatnhapcanh.gov.vn | E-visa, instant approval |
| Iran | https://evisatraveller.mfa.ir | E-visa, instant |
| Egypt | https://visa2egypt.gov.eg | E-visa for tourism |
| Kenya | https://etakenya.go.ke | eTA replaced eVisa in 2024 |
| Taiwan | https://niaspeedy.immigration.gov.tw | E-visa or VOA for Indians with US/UK/Schengen visa |

### What's still being monitored

Everything else (~70 entries across 64 countries, considering some country-processor pairs). All require an actual appointment slot at a VFS / BLS / consulate location, which is exactly what the tracker is designed for.

## How to inspect the flags

Open `centers.json` in any text editor. A flagged entry looks like:

```json
{
  "id": "vfs_lka",
  "destination_country": "Sri Lanka",
  "destination_iso2": "lk",
  "destination_iso3": "lka",
  "processor": "vfs_global",
  "appointment_url": "https://visa.vfsglobal.com/ind/en/lka/",
  "indian_cities": ["New Delhi", "Mumbai", ...],
  "visa_types": ["Visitor", "Business"],
  "priority": "low",
  "confidence": "low",
  "tier": "cold",
  "_indian_passport_status": "visa_free",
  "_status_note": "Free 30-day double-entry ETA, confirmed permanent in 2026 by Sri Lankan High Commissioner",
  "_status_alternative_url": "see _status_note for actual application path",
  "enabled": false
}
```

The fields prefixed with underscore (`_indian_passport_status`, `_status_note`, `_status_alternative_url`) are metadata — the tracker doesn't act on them, they're documentation. The functional change is `enabled: false`.

## How to re-enable a flagged entry

Three reasons you might want to:

1. **You don't have an Indian passport.** The flags are specifically for Indian passport holders. If you're an Indian-resident foreigner using the tracker, the rules differ.

2. **Policy changed.** Visa-free agreements come and go. If Sri Lanka announces a fee or appointment requirement next year, you'll want to re-enable.

3. **You want to track for someone else** with a different passport.

To re-enable:

### Option A — manual edit

Open `centers.json` in a text editor. Find the entry. Change:

```json
"enabled": false
```

to:

```json
"enabled": true
```

Save. Run `python visa_tracker_v3.py select-countries` to refresh `config.json`. Calibrate. Done.

### Option B — quick PowerShell one-liner

```powershell
python -c @"
import json
with open('centers.json', encoding='utf-8-sig') as f: data = json.load(f)
target = 'Sri Lanka'  # change to whichever country
for c in data['centers']:
    if c['destination_country'] == target:
        c['enabled'] = True
        # Optional: also clear the visa_free flag if you want it monitored permanently
        # c.pop('_indian_passport_status', None)
        print(f'Re-enabled: {c[\"id\"]}')
with open('centers.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"@
```

### Option C — the select-countries CLI (custom mode)

```powershell
python visa_tracker_v3.py select-countries
# Pick: custom
# In the numbered list, pick the visa-free country you want
```

The select-countries command knows about the flag — it'll show "[visa-free, no slots to track]" next to flagged entries so you don't accidentally re-enable. But it does let you re-enable if you ask explicitly.

## How to add new flags (if you find more visa-free entries)

If a future Indian-government policy makes another country visa-free, flag it:

1. Open `centers.json`
2. Find the relevant entry
3. Add the metadata fields:

```json
"_indian_passport_status": "visa_free",
"_status_note": "Visa-free since YYYY-MM-DD, see [source URL]",
"_status_alternative_url": "<actual application URL or null>",
"enabled": false
```

4. Save. Run `select-countries` to refresh config.json.

The `_indian_passport_status` legend at the top of `centers.json` documents the four valid values:

```json
"_indian_passport_status_legend": {
  "visa_free": "...",
  "evisa": "...",
  "appointment_required": "...",
  "null_or_missing": "Default; treat as appointment_required."
}
```

## Why this isn't deletion

Three reasons we keep flagged entries instead of deleting them:

1. **Metadata is useful.** The `_status_note` field documents *why* the entry is disabled. Future-you (or anyone forking this) doesn't need to re-research "wait, does Sri Lanka require a visa?"

2. **Policy changes.** Visa rules between India and other countries get renegotiated regularly. If Thailand reintroduces visa requirements, you flip `enabled: true` instead of having to find ISO codes and rebuild the entry.

3. **Multi-passport users.** Not everyone using this tracker is Indian. The flags are specific to Indian passports — someone with a different nationality might genuinely need to track these.

Deleting would lose all that. Flagging preserves it.

## What about destinations not in the registry?

If you want to monitor a destination that isn't in `centers.json` at all, see `ADDING_COUNTRIES.md`. The flagging system only applies to entries that already exist.

For visa-free destinations not in the registry: don't add them. There's no slot to monitor.

## Cleanup checklist

If you're auditing your install and want to verify the cleanup landed correctly:

```powershell
# Should report 12 flagged entries (7 visa-free + 5 evisa)
python -c "
import json
with open('centers.json', encoding='utf-8-sig') as f: data = json.load(f)
visa_free = [c for c in data['centers'] if c.get('_indian_passport_status') == 'visa_free']
evisa = [c for c in data['centers'] if c.get('_indian_passport_status') == 'evisa']
print(f'Visa-free: {len(visa_free)} ({sorted(set(c[\"destination_country\"] for c in visa_free))})')
print(f'E-visa: {len(evisa)} ({sorted(set(c[\"destination_country\"] for c in evisa))})')
print(f'All flagged are disabled: {all(not c.get(\"enabled\") for c in visa_free + evisa)}')
"
```

Expected output:

```
Visa-free: 7 (['Bhutan', 'Indonesia', 'Maldives', 'Malaysia', 'Nepal', 'Sri Lanka', 'Thailand'])
E-visa: 5 (['Egypt', 'Iran', 'Kenya', 'Taiwan', 'Vietnam'])
All flagged are disabled: True
```

## Common mistakes

**"I re-enabled Sri Lanka but no slots are detected."**
Correct — there are no slots because the visa is free and instant. The tracker checks the page, sees no appointment widget, returns `no_change`. Forever. Re-disable it.

**"I disabled all visa-free entries manually but new ones might appear."**
The flags travel with `centers.json`. Future versions of the tracker will pre-flag new visa-free destinations. You don't need to re-audit unless you customize the registry.

**"I want to add Mauritius but it's flagged."**
Mauritius is visa-on-arrival for Indians. Same logic — there's nothing to monitor. If you're going there, just go.

**"I'm not Indian, so all these flags are wrong for me."**
Open `centers.json`, search for `_indian_passport_status`, set all `enabled` fields back to `true`. Or write a one-line script to do it programmatically. The flags don't actively harm — they just default to disabled.
