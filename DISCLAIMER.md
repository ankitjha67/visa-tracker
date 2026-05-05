# Disclaimer

**Read this before using this software.**

## What this project is

Visa Slot Tracker is an **open-source research and educational tool** that monitors **publicly available** information about visa appointment availability and consular wait times. It is published under the MIT License for personal, educational, journalistic, and research use.

It is built and maintained as a **personal side project by an independent developer** in India. It has **no affiliation with, endorsement from, or partnership with**:

- VFS Global Services PLC or any VFS Global subsidiary
- BLS International Services Ltd. or any BLS subsidiary
- TLScontact / Teleperformance
- CGI Federal Inc. or CGI Inc.
- The U.S. Department of State, U.S. embassies, or U.S. consulates
- Any other country's foreign ministry, embassy, consulate, or visa application center
- Any commercial visa-tracking service (CheckVisaSlots, VisaCatcher, Visasoon, Atlys, etc.)

The software is "as-is," with no warranty, no guarantee of accuracy, and no guarantee of continued operation if any monitored portal changes its structure.

## What this project does

This software performs **read-only** monitoring of three categories of publicly accessible data:

1. **Public landing pages** of visa application centers — hashes visible page text and detects changes (the same operation a human would perform by refreshing a browser tab and noticing different text).
2. **Anonymous appointment-availability endpoints** that issue tokens to any visitor without requiring user login or account creation.
3. **U.S. Department of State public wait-time data** at `travel.state.gov`, which is a U.S. federal government publication and, under 17 U.S.C. § 105, is statutorily in the public domain.

When availability changes, the software notifies the user via desktop toast, Telegram, email, or Discord — channels the user has configured on their own infrastructure.

## What this project explicitly does NOT do

This is a deliberate architectural commitment. The software does not:

- ❌ **Submit, book, reschedule, or cancel any appointment.** It does not interact with form-submission endpoints. It is a notifier, not an actor.
- ❌ **Store, transmit, or use any user credentials.** No DS-160 numbers, no CGI Federal logins, no usvisa-info.com logins, no VFS account credentials, no passwords.
- ❌ **Solve, bypass, or circumvent CAPTCHAs.** No 2Captcha, no DeathByCaptcha, no anti-Cloudflare libraries beyond what is required to read public pages.
- ❌ **Use VPN rotation, proxy networks, or IP masking** to evade rate limits or access controls.
- ❌ **Collect, aggregate, or distribute personal data** of any visa applicant, including the user.
- ❌ **Operate as a paid service** of any kind. The code is free; the developer is unpaid; no marketplace exists.
- ❌ **Function as an "agent," "fixer," or "consultant"** in the visa application process. It does not represent applicants to any consulate or center.

If you need a feature in any of the above categories, this is not the right software. Please do not request such features. They will not be added.

## Important: who is responsible for what

When you run this software:

- **You** are responsible for reviewing and complying with the terms of service of any portal you choose to monitor.
- **You** are responsible for setting polling rates appropriate to the destinations you select. Default settings prioritize gentle traffic (5,400-second cold tier, 1,800-second warm tier, 600-second hot tier) but you can change them.
- **You** are responsible for the lawfulness of your use under the laws of your jurisdiction.
- **You** are responsible for the consequences of any appointment you book using information surfaced by this tool. The tool only tells you something has changed; the booking decision and action are entirely yours and happen outside this software.
- **The maintainer** is responsible for publishing source code that does what this disclaimer describes, and for honestly documenting its limitations and risks.

## Prohibited uses

The MIT License permits use, modification, and redistribution. However, the following uses are **inconsistent with the stated purpose** of this project, and the maintainer expressly disclaims any endorsement of them:

- Operating the software as a **commercial visa-booking service** for paying clients
- Using the software as part of a **fraud scheme**, including but not limited to selling appointments, posing as an agent, or circumventing consular accountability
- Modifying the software to add **auto-booking, credential storage, or CAPTCHA bypass**, then redistributing the modified version under this project's name
- Using the software in a way that produces **abusive request volume** against any portal (defined as polling rates lower than the project's defaults, run from many concurrent IPs, or coordinated across multiple users targeting the same center)

If you fork the project to add any of the above, please **rename the fork** and remove references to this project. The original project's reputation should not be associated with such modifications.

## The U.S. Embassy India March 2025 announcement

In March 2025, the U.S. Embassy in India announced the cancellation of approximately 2,000 appointments made by booking bots and the suspension of the associated user accounts' scheduling privileges. This action specifically targeted:

- **Auto-booking automation** — software that creates appointments
- **Commercial agents and fixers** charging fees to book slots
- **User accounts** on the U.S. visa scheduling system

This software does **none** of the above. It does not auto-book, it does not act as an agent, and it does not maintain accounts on `ais.usvisa-info.com`, `ustraveldocs.com`, or any U.S. visa scheduling system. Users of this software remain responsible for booking their own appointments through legitimate channels.

The U.S. Embassy's announcement and similar guidance from the U.S. Embassy in the Dominican Republic ("any applicant who seeks to manipulate the appointment system will face consequences. Potential consequences include: appointment cancellation, visa refusal, and visa cancellation") is consistent with this software's design — applicants who use *legitimate notification* and book *manually through official channels* are not the target of these enforcement actions.

## Educational and research purpose

This project is published for the following purposes, each of which has well-established precedent in academic, journalistic, and consumer-information contexts:

- **Software architecture research** — comparative study of consular booking system designs across multiple countries and processors
- **Transparency in consumer markets** — making publicly available appointment-availability data more accessible to applicants who would otherwise need to refresh portals manually
- **Open-source software engineering** — demonstrating production-grade Python patterns for distributed monitoring, multi-channel notification, tier-based scheduling, and graceful degradation
- **Legal and regulatory research** — providing a real-world reference point for ongoing scholarly and policy discussion about web scraping, public data access, and TOS enforcement (see `LEGAL.md`)

The project is not intended to substitute for legal advice, immigration counsel, or government-issued visa application guidance.

## If you have a concern

If you are a representative of a visa application center, consulate, or government agency and have a specific concern about this project:

- For technical concerns (unexpected load, malformed requests, etc.): please open a GitHub issue describing the concern. The maintainer commits to responding within 5 business days.
- For legal concerns: please send a written notice to the GitHub repository. The maintainer will respond promptly through GitHub's notice-and-response process. See `LEGAL.md` for the project's posture on the relevant case law.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

The MIT License does not grant any trademark rights to "VFS Global," "BLS International," "TLScontact," "CGI Federal," or any consulate or embassy name appearing in the code or documentation. All such names are the property of their respective owners and are referenced only as factual identifiers of the portals being monitored.
