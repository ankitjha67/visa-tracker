# Indian Visa Processor Landscape — May 2026 (v3.2.1)

This document explains who actually processes visa applications for Indians traveling abroad. The tracker's `centers.json` registry codifies all of this; this doc explains the *why* so you can decide what to enable, what to leave disabled, and what's outside the tracker's reach.

> **v3.2.1 corrections to v3.2:** Portugal moved BLS → VFS Global (Embassy of Portugal mandates VFS). Algeria, Tunisia, Mozambique moved BLS → embassy_direct (no online portal exists for any of the three; v3.2 had pattern-generated `india.bls{country}visa.com` URLs that don't resolve). See the misclassification audit at the bottom.

## The companies that actually matter

There are three real visa processing companies operating from India for outbound applications: VFS Global, BLS International, and CGI Federal (the latter only for US visas). Everything else (Y-Axis, Akbar Travels, BTW, Thomas Cook, etc.) is a travel agent that submits through one of these three — they don't hold government contracts.

### 1. VFS Global — the giant

By far the biggest. Handles ~70 destination countries from India and operates VACs in 15 Indian cities: Ahmedabad, Bengaluru, Bhubaneswar (opened April 2026, Odisha's first), Chandigarh, Chennai, Cochin, Goa, Hyderabad, Jaipur, Jalandhar, Kolkata, Mumbai, New Delhi, Puducherry, Pune.

**URL pattern**: `https://visa.vfsglobal.com/ind/en/{iso3}/` where `{iso3}` is the lowercase ISO 3166-1 alpha-3 code for the destination country (e.g. `gbr`, `fra`, `deu`, `aus`, `sgp`, `prt`).

**Stack**: Nuxt 3 SPA. Heavy client-side hydration — must wait for the loader to clear before scraping (this is what `wait_for_spa()` handles). Cloudflare in front. Headless Chrome works fine; aggressive scraping will eventually trip Bot Management.

**API backend (NEW in v3.2.1)**: `https://lift-api.vfsglobal.com/appointment/{centerwithearliestslot,slots}`. JWT-protected — anonymous fetch returns 403. The tracker harvests a JWT via headless Selenium (network log + localStorage scan), caches for 25 min, and replays with country-specific params: `countryCode=ind`, `missionCode=<iso3>`, `languageCode=en-US`, `applicantsCount=1`, `days=90`, `slotType=2`.

**What VFS handles from India**:
- **UK, Schengen majority** (France, Germany, Italy, Netherlands, Switzerland, Austria, Belgium, Sweden, Norway, Denmark, Finland, Greece, Czech, Hungary, Poland, Croatia, Bulgaria, **Portugal** ← v3.2.1 correction)
- **Australia, Canada, New Zealand**
- **GCC** (UAE, Saudi Arabia, Qatar, Bahrain, Kuwait, Oman)
- **East Asia** (Japan, South Korea, China, Singapore, Thailand, Vietnam, Malaysia, Philippines)
- **Russia, Israel, Turkey, South Africa, Egypt, Brazil, Mexico, Argentina**, and many more

### 2. BLS International — the Indian challenger

Indian-origin (Forbes Asia "Best Under a Billion"). Smaller than VFS but holds significant Schengen contracts.

**v3.2.1 correction:** v3.2 listed Portugal, Algeria, Tunisia, Mozambique under BLS based on a guessed `india.bls{country}visa.com` URL pattern. Verified May 2026: **none of those four use BLS.** Portugal is VFS. The other three have no online portal at all.

**What BLS actually handles from India** (verified):
- **Spain** — exclusive (8 Indian cities). Don't try VFS for Spain. URL: `https://india.blsspainvisa.com/`
- **Slovakia** — exclusive (5 Indian cities). URL: `https://blsslovakiavisa.com/india/` (note the inverted pattern)

That's it. If you see other "BLS [country]" suggestions online, verify the URL actually resolves before adding to the registry. URL conventions vary per contract — there's no single template.

**Stack**: ASP.NET classic (no SPA hydration wait needed, just `document.readyState === complete`). Login required for booking on most BLS portals.

### 3. CGI Federal (USTravelDocs / usvisascheduling.com)

The only path for US non-immigrant visas (B1/B2, F1, H1B, L1, O1, J1, etc.) from India.

**Indian Consulates**: New Delhi (Embassy), Mumbai, Chennai, Hyderabad, Kolkata. **OFCs** (Offsite Facilitation Centers) for biometrics: New Delhi, Mumbai, Chennai, Hyderabad, Kolkata, **Bengaluru** (OFC only — no consular interview).

**Disabled by default in the registry.** CGI has aggressive bot detection, account-lock-on-failed-CAPTCHA, and Terms of Service that explicitly prohibit automated access. Enabling without proxy rotation, human-in-the-loop CAPTCHA solving, and a clear understanding of the account-lock risk is asking for trouble. The flag is there for completeness, not for casual use.

### 4. TLScontact — currently dormant in India

Owned by Teleperformance. Larger globally (90 countries, 150 VACs) but has minimal active India operations as of May 2026. Most Schengen work that previously routed through TLS in India has shifted to VFS.

**URL pattern**: `https://visas-{iso2}.tlscontact.com/en-in/`. React SPA.

The processor is included in the registry map for completeness; no active India centers are configured.

### 5. Cox & Kings Global Services (CKGS)

Used to handle India outbound for some destinations. Now mostly handles **inbound to India** services — Indian passport renewal, OCI cards, renunciation — for Indians living abroad (US, Canada, etc.).

For India-outbound tracking, CKGS is largely out of scope. In the registry for completeness, disabled.

## Embassy direct (no outsourced VAC)

A handful of countries process applications without an outsourced visa application center. v3.2.1 added Algeria, Tunisia, and Mozambique to this group after the BLS audit.

| Country | Indian visa needed? | How to apply | Tracker enabled |
|---|---|---|---|
| Bhutan | No (free travel) | — | No |
| Nepal | No | — | No |
| Maldives | Visa on arrival | At airport | No |
| Sri Lanka | Yes (online ETA) | https://eta.gov.lk | Yes (only enabled embassy_direct) |
| Iran | Yes | Embassy direct, intermittent | No |
| **Algeria** (v3.2.1) | Yes | Embassy of Algeria, New Delhi (in-person only) | No |
| **Tunisia** (v3.2.1) | Tourism: visa-free up to 90 days. Business: yes | Tunisian Embassy New Delhi | No |
| **Mozambique** (v3.2.1) | Yes (eVisa for >30 days) | https://evisa.gov.mz/ (launched Feb 2026) | No |

For Mozambique specifically: the new `evisa.gov.mz` portal was launched 11 February 2026, replacing previous BLS speculation. Indians can either use the eVisa portal (for stays >30 days) or rely on the visa-free 30-day allowance for tourism.

## What the tracker can do per processor (v3.2.1)

| Processor | Public landing | Click-through | JWT API replay | Confidence default |
|-----------|----------------|---------------|----------------|--------------------|
| vfs_global | ✓ Page hydrates | ✓ Discovers gated APIs | ✓ Real-time slots via lift-api | medium → high after good calibration |
| bls_international | ✓ Static HTML | ✓ Some workflows | ✗ Not implemented (no known endpoint) | medium |
| tls_contact | ✓ Public | ✓ Some workflows | ✗ Not implemented | medium |
| cgi_federal | Limited | ✗ Don't try | ✗ Don't try (account-lock risk) | low |
| ckgs | Inverse direction | n/a | n/a | low |
| embassy_direct | Varies | Varies | n/a | low |
| indian_visa_online | Inverse direction | n/a | n/a | low |

The tracker's three layers — JWT replay (VFS only), anonymous API replay, and page-change detection — work best for VFS portals because of the lift-api JWT path. BLS portals gate slot data behind login, which the tracker doesn't perform automatically (no credential storage). What the tracker *can* see for BLS:
- Page-change signals when a portal's status banner changes
- Site-wide announcements
- Any selector-discoverable content the calibrator surfaces

For real-time logged-in slot polling on BLS, you need credentialed automation — out of scope by design.

## Confidence semantics

Each center starts with a default confidence (set in `centers.json`):
- **VFS Global** entries → `medium` (will upgrade to `high` after a successful calibration with API capture + click-through, or stay `medium` if click-through hits a login wall)
- **BLS International** → `medium` (selectors usually work)
- **TLScontact** → `medium` (unused but reserved)
- **CGI/CKGS/embassy_direct/indian_visa_online** → `low` (either disabled, doesn't apply, or no portal)

Calibration overrides this with the actually-observed quality:
- `high` = real API endpoint discovered (or known on processor) AND click-through worked AND/OR selectors worked
- `medium` = working DOM selectors only, OR a known API but no surface to verify
- `low` = page-change fallback only — high false-positive risk (cookie banners, A/B variants, news ticker)

The dashboard groups slots by confidence so low-trust alerts don't drown out high-trust ones.

## Recently announced changes (track these)

These have happened in the past few months and the registry reflects them:

- **April 2026** — VFS Global opened Bhubaneswar (Odisha's first VAC, 10 destinations initially)
- **April 2026** — VFS Global opened Singapore-specific centers in Chandigarh and Chennai
- **2025–26** — VFS launched Bulgaria long-term visa services across 6 Indian cities
- **January 2026** — France VFS Delhi center relocated; French long-stay language requirement raised B1 → B2
- **February 2026** — Mozambique launched evisa.gov.mz, replacing previous embassy-direct workflow

## Cities where each processor operates

**VFS** (15 cities): Ahmedabad, Bengaluru, Bhubaneswar, Chandigarh, Chennai, Cochin, Goa, Hyderabad, Jaipur, Jalandhar, Kolkata, Mumbai, New Delhi, Puducherry, Pune

**BLS** (10 cities): New Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Hyderabad, Ahmedabad, Pune, Chandigarh, Jalandhar

**TLS in India**: N/A (no live India contracts)

**CGI / US Embassy** (5 consular cities + 6 OFCs): New Delhi, Mumbai, Chennai, Hyderabad, Kolkata, plus OFC in Bengaluru

## How to use the registry

```bash
# v3.2.1: preflight URLs FIRST, before calibrating
python visa_tracker_v3.py verify-urls

# See what's loaded
python visa_tracker_v3.py coverage

# Dump every supported country
python visa_tracker_v3.py list-countries

# Calibrate one
python visa_tracker_v3.py calibrate "United Kingdom"

# Calibrate all enabled, parallel
python visa_tracker_v3.py calibrate --all --workers 3

# Check current status
python visa_tracker_v3.py status
```

To add a destination: open `centers.json`, add a new center entry following the schema, set `enabled: true`, restart the tracker. The `_default_targets_from_registry` function picks up enabled high-priority and medium-priority entries automatically; for low-priority you also need to add them to `targets` in `config.json`.

To disable a destination without deleting: set `enabled: false` in `centers.json` or remove from `targets` in `config.json`.

## What NOT to expect

- The tracker won't bypass any login wall. If a portal requires credentials before showing slots, you'll only get public-page change detection — except for VFS, where the JWT replay path can sometimes reach lift-api anonymously. (Anonymous reach depends on whether the portal exposes a public landing JWT — varies by country and time.)
- The tracker won't solve CAPTCHAs. Cloudflare, hCaptcha, and reCAPTCHA all gate content — when a portal interjects, the check fails (logged as `captcha`).
- The tracker won't book slots. Slot detection ≠ slot booking.
- The tracker won't tell you about visa rules, fees, or document requirements — only appointment availability changes.

## Verifying coverage is correct

The registry is hand-curated against public processor websites. Government contracts shift — VFS or BLS may take over a country we haven't updated, or lose one. To verify a specific country is using the right processor:

1. Search `"{country} visa from India"` and look at the official embassy page recommendations
2. Check `https://visa.vfsglobal.com/ind/en/{iso3}/` — if it loads, VFS handles it
3. **Don't pattern-generate BLS URLs.** The `india.bls{country}visa.com` template was the v3.2 trap. Verify each BLS site individually by searching for it.
4. If both VFS and BLS load: VFS usually takes priority (registry favors the higher-priority entry)
5. If neither loads: check the destination embassy's India page for the current outsourcing partner (or no partner — embassy_direct)

Then run `python visa_tracker_v3.py verify-urls` after edits to catch typos before the next calibration.

## v3.2 misclassification audit (post-mortem)

For the historical record, here's what v3.2 got wrong and why:

| Country | v3.2 (wrong) | v3.2.1 (correct) | Root cause |
|---|---|---|---|
| Portugal | `bls_international`, `india.blsportugalvisa.com` (DNS fail) | `vfs_global`, `visa.vfsglobal.com/ind/en/prt/` | Embassy of Portugal explicitly mandates VFS. URL was pattern-generated from a non-existent BLS naming convention. |
| Algeria | `bls_international`, `india.blsalgeriavisa.com` (DNS fail) | `embassy_direct`, disabled | Embassy of Algeria New Delhi handles applications in-person; no online portal exists. |
| Tunisia | `bls_international`, `india.blstunisiavisa.com` (DNS fail) | `embassy_direct`, disabled | Indian citizens are visa-free for Tunisian tourism (90 days). Business visas via embassy in-person. |
| Mozambique | `bls_international`, `india.blsmozambiquevisa.com` (DNS fail) | `embassy_direct`, redirected to `evisa.gov.mz`, disabled | Mozambique launched its own eVisa portal Feb 2026. No BLS site exists. Indians visa-free for 30-day tourism. |

The lesson: **don't pattern-generate URLs.** Verify each entry against the actual live URL. The new `verify-urls` CLI command (v3.2.1) catches this in seconds.
