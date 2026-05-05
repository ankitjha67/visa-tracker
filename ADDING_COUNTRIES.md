# Adding Countries, Cities, and Embassies

This guide shows you how to expand the tracker's coverage. Three scenarios, ranked by difficulty:

1. **Easy** — Add an Indian city to a country already on the tracker (1 minute)
2. **Easy** — Add a new VFS Global country (5 minutes)
3. **Medium** — Add a non-VFS country with an embassy direct URL (10 minutes)
4. **Hard** — Add a country that uses CGI Federal, BLS, TLS, or another non-VFS portal (requires code changes — see "Custom processors" at the end)

Plus a reference table of common visa portals at the end.

---

## Related v4.0 docs

- **`VISA_FREE_GUIDE.md`** — explains the `_indian_passport_status` flagging system (visa-free / e-visa entries kept in centers.json but disabled by default). Read this before re-enabling any flagged entry.
- **`TIER_SYSTEM.md`** — how to use the `tier` field on each center for priority scheduling.

When you add a new country in v4.0, it inherits `tier: cold` by default. Promote with `set-tier` once added.

---

## How the tracker decides what to watch

Everything the tracker monitors is defined in **`centers.json`**. It's a plain text file you can open in any text editor (Notepad works). Each "center" describes one **(destination country × Indian city)** combination.

Open `centers.json` and you'll see the structure:

```json
{
  "version": "3.2.4",
  "schema": "centers-registry",
  "processors": [...],          // List of processors (VFS, BLS, TLS, etc.)
  "indian_cities": [...],       // Default list of Indian cities to monitor
  "centers": [
    {
      "id": "vfs_gbr",
      "destination_country": "United Kingdom",
      "destination_iso2": "gb",
      "destination_iso3": "gbr",
      "processor": "vfs_global",
      "appointment_url": "https://visa.vfsglobal.com/ind/en/gbr/",
      "indian_cities": ["New Delhi", "Mumbai", "Bengaluru", ...],
      "visa_types": ["Visitor", "Business", "Student", "Work", "Family"],
      "priority": "high",
      "confidence": "medium",
      "enabled": true
    },
    ...
  ]
}
```

There are 82 centers covering 42 countries and 7 different processors.

### Field reference

| Field | What it means | How to set |
|---|---|---|
| `id` | Unique identifier — anything you want, but stick to lowercase + underscores | e.g., `vfs_gbr`, `embassy_rus` |
| `destination_country` | Display name shown in notifications | e.g., `"United Kingdom"`, `"Russia"` |
| `destination_iso2` | 2-letter country code | Lookup at [iso.org](https://www.iso.org/obp/ui/#search) |
| `destination_iso3` | 3-letter country code (used in VFS URLs) | Same source |
| `processor` | Which visa processor handles this country | Must match an entry in the `processors` array (typically `vfs_global`, `bls_international`, `tls_contact`, `cgi_federal`, `embassy_direct`) |
| `appointment_url` | URL the tracker visits | Get from the actual visa portal |
| `indian_cities` | List of Indian application centers for this country | See full list below |
| `visa_types` | Visa categories handled (informational only) | e.g., `["Visitor", "Business", "Student"]` |
| `priority` | Subjective importance — `high`/`medium`/`low` | Affects nothing functional yet |
| `confidence` | How reliable the tracker is for this country — `high`/`medium`/`low` | Set by calibration; you can leave as `medium` initially |
| `enabled` | `true` to monitor, `false` to skip | Use `false` to temporarily disable a country |
| `tier` (v4.0) | Polling priority — `hot` / `warm` / `cold` | Default `cold`. Promote with `set-tier` CLI command |
| `_indian_passport_status` (v4.0) | Optional: `visa_free` / `evisa` if no slots exist for Indians | See `VISA_FREE_GUIDE.md` |
| `_status_note` (v4.0) | Optional: human-readable explanation when `_indian_passport_status` is set | Free text |
| `_status_alternative_url` (v4.0) | Optional: real e-visa portal URL when not appointment-based | URL or note |

### Available Indian cities

Cities currently used across the registry:

```
New Delhi, Mumbai, Bengaluru, Chennai, Hyderabad, Kolkata, Ahmedabad,
Chandigarh, Pune, Cochin, Goa, Jaipur, Jalandhar, Bhubaneswar, Puducherry
```

You can add others if a visa center exists there. Common additions: Lucknow, Indore, Coimbatore, Surat, Bhopal, Nagpur, Trivandrum.

---

## Scenario 1 — Add an Indian city to an existing country

The simplest case. Say you live in Lucknow and the UK VFS center in Lucknow opened recently.

1. Open `centers.json` in Notepad (or any editor).

2. Find the United Kingdom entry. Its `indian_cities` field looks like:

   ```json
   "indian_cities": ["New Delhi", "Mumbai", "Bengaluru", "Chennai",
                     "Hyderabad", "Kolkata", "Ahmedabad", "Chandigarh",
                     "Pune", "Cochin", "Goa", "Jaipur", "Jalandhar",
                     "Bhubaneswar", "Puducherry"]
   ```

3. Add `"Lucknow"` to the list:

   ```json
   "indian_cities": ["New Delhi", "Mumbai", "Bengaluru", "Chennai",
                     "Hyderabad", "Kolkata", "Ahmedabad", "Chandigarh",
                     "Pune", "Cochin", "Goa", "Jaipur", "Jalandhar",
                     "Bhubaneswar", "Puducherry", "Lucknow"]
   ```

4. Save the file. **Important:** Make sure your text editor saved as UTF-8. Notepad on Windows 11 does this by default; older versions might add a BOM, which the tracker handles correctly since v3.2.3.

5. Recalibrate just that country:

   ```powershell
   python visa_tracker_v3.py calibrate --country "United Kingdom"
   ```

6. Restart the tracker. The next cycle will include UK/Lucknow.

That's it. Takes 1 minute.

---

## Scenario 2 — Add a new VFS Global country

VFS Global handles ~30 countries from India and they all use the same URL pattern: `https://visa.vfsglobal.com/ind/en/<iso3>/`. Adding a new VFS country is mostly copy-paste.

Example: add Slovakia (a Schengen country not currently on the tracker).

1. Find Slovakia's ISO codes:
   - ISO2: `sk`
   - ISO3: `svk`

2. Verify the URL works: open `https://visa.vfsglobal.com/ind/en/svk/` in your browser. If it loads (not 404), VFS handles Slovakia from India.

3. Open `centers.json`. Find the `centers` array.

4. Pick any existing VFS country to copy from. The Czech Republic entry is a good template (similar Schengen tier). Find the entry with `"id": "vfs_cze"` and copy the entire object, including the `{` and `}`.

5. Paste the copied object after another center (don't forget to add a comma after the previous closing `}`).

6. Edit the pasted entry:

   ```json
   {
     "id": "vfs_svk",
     "destination_country": "Slovakia",
     "destination_iso2": "sk",
     "destination_iso3": "svk",
     "processor": "vfs_global",
     "appointment_url": "https://visa.vfsglobal.com/ind/en/svk/",
     "indian_cities": ["New Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata"],
     "visa_types": ["Visitor", "Business", "Student"],
     "priority": "medium",
     "confidence": "medium",
     "enabled": true
   }
   ```

   Adjust `indian_cities` to match what Slovakia actually offers (check the VFS site after clicking through). Most smaller Schengen countries only have 5-7 Indian centers, not all 15.

7. Save the file.

8. Validate the JSON is well-formed:

   ```powershell
   python -c "import json; json.load(open('centers.json', encoding='utf-8-sig')); print('OK')"
   ```

   If you see `OK`, the file parses. If you see an error, you probably forgot a comma or quote somewhere — most JSON errors are like that.

9. Calibrate the new country:

   ```powershell
   python visa_tracker_v3.py calibrate --country "Slovakia"
   ```

10. Restart the tracker. New country is now monitored.

---

## Scenario 3 — Add a non-VFS country (embassy direct)

For countries that don't use VFS but have a direct booking URL on their consulate website. Example: Russia. (Russia-India is currently handled differently, but the pattern works for any direct booking page.)

1. Find the actual booking URL. Visit the embassy or consulate site for the country in India and find the appointment booking page. Common patterns:

   - `https://<country>embassy.org/book-appointment`
   - `https://india.<country>visa.gov/`
   - `https://<country>.gov.in/` (rare — usually Indian embassies abroad, not foreign embassies in India)

2. Open `centers.json`. Find the `processors` array near the top. Make sure `embassy_direct` is listed:

   ```json
   "processors": [
     {"id": "vfs_global", "name": "VFS Global", ...},
     {"id": "bls_international", "name": "BLS International", ...},
     {"id": "embassy_direct", "name": "Embassy Direct", ...}
   ]
   ```

   If `embassy_direct` isn't there, you can add it, but most installs already include it.

3. Add a new center:

   ```json
   {
     "id": "embassy_<iso3>",
     "destination_country": "Country Name",
     "destination_iso2": "xx",
     "destination_iso3": "xxx",
     "processor": "embassy_direct",
     "appointment_url": "https://full-direct-url-here/",
     "indian_cities": ["New Delhi"],
     "visa_types": ["Visitor"],
     "priority": "medium",
     "confidence": "low",
     "enabled": true
   }
   ```

4. Use `confidence: "low"` for embassy direct entries. The tracker can only do page-change detection on these (no API monitoring), so reliability is lower than VFS countries.

5. Save, validate JSON, calibrate.

---

## Embassy / portal reference table

Common visa portals for India outbound. Use this when adding a country.

### Already on the tracker (VFS Global, 30 destinations)

These work out of the box:

| Country | ISO3 | URL |
|---|---|---|
| United Kingdom | gbr | https://visa.vfsglobal.com/ind/en/gbr/ |
| Canada | can | https://visa.vfsglobal.com/ind/en/can/ |
| Australia | aus | https://visa.vfsglobal.com/ind/en/aus/ |
| Germany | deu | https://visa.vfsglobal.com/ind/en/deu/ |
| France | fra | https://visa.vfsglobal.com/ind/en/fra/ |
| Italy | ita | https://visa.vfsglobal.com/ind/en/ita/ |
| Netherlands | nld | https://visa.vfsglobal.com/ind/en/nld/ |
| Switzerland | che | https://visa.vfsglobal.com/ind/en/che/ |
| Austria | aut | https://visa.vfsglobal.com/ind/en/aut/ |
| Belgium | bel | https://visa.vfsglobal.com/ind/en/bel/ |
| Sweden | swe | https://visa.vfsglobal.com/ind/en/swe/ |
| Norway | nor | https://visa.vfsglobal.com/ind/en/nor/ |
| Denmark | dnk | https://visa.vfsglobal.com/ind/en/dnk/ |
| Finland | fin | https://visa.vfsglobal.com/ind/en/fin/ |
| Ireland | irl | https://visa.vfsglobal.com/ind/en/irl/ |
| Czech Republic | cze | https://visa.vfsglobal.com/ind/en/cze/ |
| Hungary | hun | https://visa.vfsglobal.com/ind/en/hun/ |
| Poland | pol | https://visa.vfsglobal.com/ind/en/pol/ |
| Greece | grc | https://visa.vfsglobal.com/ind/en/grc/ |
| Croatia | hrv | https://visa.vfsglobal.com/ind/en/hrv/ |
| Bulgaria | bgr | https://visa.vfsglobal.com/ind/en/bgr/ |
| New Zealand | nzl | https://visa.vfsglobal.com/ind/en/nzl/ |
| Japan | jpn | https://visa.vfsglobal.com/ind/en/jpn/ |
| South Korea | kor | https://visa.vfsglobal.com/ind/en/kor/ |
| Singapore | sgp | https://visa.vfsglobal.com/ind/en/sgp/ |
| Saudi Arabia | sau | https://visa.vfsglobal.com/ind/en/sau/ |
| Qatar | qat | https://visa.vfsglobal.com/ind/en/qat/ |
| South Africa | zaf | https://visa.vfsglobal.com/ind/en/zaf/ |
| Russia | rus | https://visa.vfsglobal.com/ind/en/rus/ |
| Israel | isr | https://visa.vfsglobal.com/ind/en/isr/ |

### VFS-handled but not on tracker yet (easy to add)

| Country | ISO3 | URL | Notes |
|---|---|---|---|
| Slovakia | svk | https://visa.vfsglobal.com/ind/en/svk/ | Schengen completion |
| Slovenia | svn | https://visa.vfsglobal.com/ind/en/svn/ | Schengen |
| Romania | rou | https://visa.vfsglobal.com/ind/en/rou/ | Schengen since 2024 |
| Lithuania | ltu | https://visa.vfsglobal.com/ind/en/ltu/ | Schengen |
| Latvia | lva | https://visa.vfsglobal.com/ind/en/lva/ | Schengen |
| Estonia | est | https://visa.vfsglobal.com/ind/en/est/ | Schengen |
| Cyprus | cyp | https://visa.vfsglobal.com/ind/en/cyp/ | Joining Schengen |
| Iceland | isl | https://visa.vfsglobal.com/ind/en/isl/ | Schengen |
| Malta | mlt | https://visa.vfsglobal.com/ind/en/mlt/ | Schengen |
| Luxembourg | lux | https://visa.vfsglobal.com/ind/en/lux/ | Schengen |
| Bahrain | bhr | https://visa.vfsglobal.com/ind/en/bhr/ | Gulf |
| Kuwait | kwt | https://visa.vfsglobal.com/ind/en/kwt/ | Gulf |
| Oman | omn | https://visa.vfsglobal.com/ind/en/omn/ | Gulf |

Verify each URL before adding — VFS occasionally moves countries in/out of the India service.

### NOT on VFS — needs custom handling

These require code changes (see "Custom processors" below) or aren't worth tracking:

| Country | Portal | Notes |
|---|---|---|
| **United States** | https://ais.usvisa-info.com/en-in/niv/ | CGI Federal — **highest demand for Indians**, would be the biggest win to add. Requires custom processor (auth-gated). |
| **China** | https://bio.visaforchina.cn/ | China Visa Application Service Center. Different system. Worth adding for business travelers. |
| **Spain** | https://blsspainvisa.com/ | BLS handles Spain. Already on tracker via BLS processor with low confidence. |
| **UAE** | https://gdrfad.gov.ae/ | Direct e-visa, no appointment needed. **Skip — no slots to track.** |
| **Hong Kong** | (visa-free 14 days for Indians) | **Skip — no visa needed.** |
| **Taiwan** | https://niaspeedy.immigration.gov.tw/nia_southeast/ | E-visa, instant approval. Skip. |
| **Iran** | https://evisatraveller.mfa.ir/ | E-visa, instant. Skip. |
| **Egypt** | https://visa2egypt.gov.eg/ | E-visa for some categories. Skip. |
| **Turkey** | https://www.evisa.gov.tr/ | E-visa instant. Already on tracker via VFS for sticker visas; e-visa doesn't need monitoring. |

### Visa-free / on-arrival — DO NOT add

These have no slots to monitor because Indians don't book appointments:

```
Sri Lanka    Thailand     Malaysia     Maldives     Bhutan
Nepal        Indonesia    Mauritius    Fiji         Cambodia
Myanmar      Iran (eVisa) Egypt (eVisa) Vietnam (eVisa)
Hong Kong    Taiwan (eVisa)
```

Adding any of these wastes ~30 seconds per cycle and never produces a useful alert. The current `centers.json` should not include them. If you find one in your registry, set `"enabled": false` to skip it.

---

## Validating your edits

After editing `centers.json`, before restarting the tracker:

### 1. Check the JSON parses

```powershell
python -c "import json; d=json.load(open('centers.json',encoding='utf-8-sig')); print('OK,', d['version'], len(d['centers']), 'centers')"
```

Should print: `OK, 3.2.4 N centers` where N is your new count. If you see a JSON error, find and fix it (most common: missing comma, extra comma, mismatched quotes).

### 2. Verify URLs are reachable

```powershell
python visa_tracker_v3.py verify-urls
```

This visits every URL with a 4KB streaming GET. Any country that returns a real 4xx/5xx error is flagged. Cloudflare 404s on HEAD are correctly handled — don't worry if a URL works in browser but the test reports the response. Look for connection errors and DNS failures.

### 3. Calibrate the new countries

```powershell
python visa_tracker_v3.py calibrate --all
```

Or for just the new ones:

```powershell
python visa_tracker_v3.py calibrate --country "Slovakia"
python visa_tracker_v3.py calibrate --country "Latvia"
```

If calibration sets confidence to `low`, the country is monitored only via page-change detection. If `medium`, both API monitoring (when JWT works) and page-change. If `high`, all three layers.

### 4. Run a single cycle to verify

```powershell
python visa_tracker_v3.py run --once --dry-run
```

Watch the log. Each new country should appear with its cities and a `no_change` or `classified as ...` result. If you see `❌ <Country>/<City>: error`, that center has a problem — recalibrate or check the URL.

---

## Disabling a country temporarily

You don't have to delete entries to stop monitoring them. Set `enabled` to `false`:

```json
{
  "id": "vfs_lka",
  "destination_country": "Sri Lanka",
  ...
  "enabled": false
}
```

The tracker skips disabled centers entirely. Good for visa-free countries you accidentally added, or for temporarily reducing cycle time when you only care about specific destinations.

---

## Custom processors (advanced)

Some visa portals (US, China, BLS-Spain) need custom code, not just a centers.json entry. This is because:

- They have authentication that VFS doesn't (US requires login + DS-160 form)
- Their URL pattern is different from VFS
- Their slot data lives in a different page structure

Adding a new processor requires writing a Python class in `visa_tracker_v3.py`. It's a 100-200 line change. Out of scope for this guide, but the existing `VFSJWTSession` and `BLSScraper` classes are good templates.

If you have a specific country you'd like supported and you're comfortable with Python, see the architecture section in `SETUP_GUIDE.md` for where to plug in. If you're not comfortable with code: ask whoever set up the tracker for you.

---

## Quick reference: minimum edits to add a country

```json
{
  "id": "vfs_<iso3>",
  "destination_country": "Country Name",
  "destination_iso2": "xx",
  "destination_iso3": "xxx",
  "processor": "vfs_global",
  "appointment_url": "https://visa.vfsglobal.com/ind/en/<iso3>/",
  "indian_cities": ["New Delhi", "Mumbai", "Bengaluru"],
  "visa_types": ["Visitor"],
  "priority": "medium",
  "confidence": "medium",
  "tier": "cold",
  "enabled": true
}
```

Drop into `centers.json` → save → `select-countries` → calibrate. Done.

To make this country a hot priority after adding:

```powershell
python visa_tracker_v3.py set-tier --country "Country Name" --tier hot
```
