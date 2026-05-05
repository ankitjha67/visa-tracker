# Legal Notes

This document records the maintainer's good-faith analysis of the legal posture of this project. It is **not** legal advice, **not** a representation that the project is free from legal risk in any jurisdiction, and **not** a substitute for counsel.

It exists for three reasons:

1. To document **dual-use research and consumer-information intent** for any GitHub Trust & Safety review (see GitHub Acceptable Use Policies, "dual-use security technologies and content related to research").
2. To document **good-faith awareness of controlling case law**, which is relevant to claims requiring fraudulent or willful intent (e.g., Section 66 of India's Information Technology Act 2000, the Computer Fraud and Abuse Act in the United States).
3. To give legal counsel approaching this repository — whether the maintainer's, a complainant's, or GitHub's — a starting point for evaluating the actual architecture against the relevant legal doctrine, rather than relying on assumptions about what "visa scrapers" do generically.

## Architecture summary

The project consists of three independent data-acquisition layers, each of which interacts with public information through different technical and legal frames:

### Layer 1: Public-page hashing

The software periodically retrieves publicly accessible HTML pages of visa application centers (the same pages any browser user can load without authentication) and computes hashes of visible text content. When the hash changes, the software triggers a notification.

This is functionally identical to a human user refreshing a browser tab and noting that the displayed text has changed. No authentication is bypassed; no rate limit is circumvented; no CAPTCHA is solved; no proxy or VPN is used to evade access controls.

### Layer 2: Anonymous JWT replay

Some VFS Global landing pages issue a short-lived JSON Web Token (JWT) to **any visitor**, with no login or account creation required. This token authenticates subsequent calls to a documented availability endpoint that returns slot-count data.

The software harvests the JWT issued to its own anonymous request and uses that token to query the availability endpoint at a low frequency. It does not impersonate another user, does not store credentials, and does not attempt to forge or extend tokens beyond their natural lifetime. The "gate" — to use the controlling Ninth Circuit terminology — opens automatically for any visitor and the software passes through it the same way every browser does.

### Layer 3: U.S. State Department wait-time data

The software reads publicly published wait-time data from `travel.state.gov`, a U.S. federal government website. Under 17 U.S.C. § 105, "Copyright protection under this title is not available for any work of the United States Government." This data is statutorily in the public domain in the United States. The software's processing of this data — reading, parsing, and notifying on changes — is consistent with the data's published purpose of informing the public about consular processing times.

## Relevant authorities

The maintainer has reviewed, in good faith, the following authorities and believes the project's architecture is consistent with them. This list is not exhaustive and is offered for orientation, not as a legal conclusion.

### United States — Computer Fraud and Abuse Act

**hiQ Labs, Inc. v. LinkedIn Corp., 31 F.4th 1180 (9th Cir. 2022)** — The Ninth Circuit held that scraping public-facing web pages does not violate the CFAA's "without authorization" prohibition where the website "has erected no gates to lift or lower in the first place." The decision draws a clean line between credentialed access (potentially CFAA-actionable) and public, anonymous access (not CFAA-actionable on a "without authorization" theory alone).

**Van Buren v. United States, 593 U.S. ___ (2021)** — The Supreme Court narrowed "exceeds authorized access" under the CFAA to a "gates-up-or-down" inquiry. Improper purpose alone does not convert authorized access into unauthorized access for CFAA purposes.

**Sandvig v. Barr, 451 F. Supp. 3d 73 (D.D.C. 2020)** — Constraining the use of CFAA to criminalize academic and journalistic research that violates a website's terms of service.

This project does not interact with any credentialed gate (no login is required for any monitored endpoint), does not bypass any technical access control, and does not collect personal data.

### United States — Copyright

**17 U.S.C. § 105** — Works of the U.S. federal government are not subject to copyright protection. `travel.state.gov` content prepared by federal employees in the course of their duties is therefore in the public domain in the United States.

**Feist Publications, Inc. v. Rural Telephone Service Co., 499 U.S. 340 (1991)** — Facts and data are not copyrightable. The arrangement of facts may be copyrightable only if it shows a minimal degree of creativity. A list of consular wait times is a list of facts.

GitHub's official guidance on DMCA notices explicitly states: "**facts (including data) are generally not copyrightable. Words and short phrases are generally not copyrightable. URLs and domain names are generally not copyrightable.**" This project contains no copyrighted code, text, logos, or branded materials of any monitored entity.

### United States — TOS-based contract claims

**Power Ventures, Inc. v. Facebook, Inc., 844 F.3d 1058 (9th Cir. 2016)** — Establishes that *individualized revocation of authorization* (e.g., a cease-and-desist letter combined with IP blocks) can support CFAA liability where continued access occurs after notice. Absent such revocation, ordinary public-data access is not CFAA-actionable.

**Craigslist Inc. v. 3Taps Inc., 942 F. Supp. 2d 962 (N.D. Cal. 2013)** — Liability turned on the defendant's use of "different IP addresses and proxy servers" to evade Craigslist's blocks after receiving a cease-and-desist letter.

This project has not received any individualized revocation, and it explicitly does not use proxy rotation, VPN evasion, or IP-masking techniques.

### India — Information Technology Act, 2000

**Section 43** (civil liability for unauthorized access) and **Section 66** (criminal liability where access is "dishonest or fraudulent") together constitute the primary Indian regulatory framework for unauthorized access to computer systems.

Section 66 criminal liability requires proof of dishonest or fraudulent intent. This project's published purpose (research, transparency, consumer information), its open-source posture, its absence of monetization, and its explicit exclusion of fraud-adjacent features (auto-booking, agent functionality, credential storage) are inconsistent with the mens rea requirement for Section 66.

The maintainer has reviewed the Centre for Internet & Society's commentary, S.S. Rana & Co.'s legal-issues analysis, and academic SSRN literature on data scraping under Indian law. No reported Indian decision has held that anonymous monitoring of publicly available consular appointment availability constitutes "unauthorized access" within the meaning of Section 43.

### India — Digital Personal Data Protection Act, 2023

The DPDP Act applies to the processing of *personal data* of natural persons. This project does not process personal data of any kind. It does not collect applicant names, passport numbers, DS-160 numbers, contact information, payment information, or any other personal identifier. The project is therefore outside the material scope of the DPDP Act.

### European Union — GDPR

GDPR applies to the processing of personal data of EU data subjects. This project does not process personal data. Recent GDPR enforcement against scrapers (Clearview AI, Kaspr, the 2024 Polish data broker case, the 2024 Italian directory case) all involved the processing of identifiable personal data — names, photographs, contact information, telephone numbers. Slot-availability data is operational data about a system, not personal data about an identified or identifiable natural person.

### United Kingdom — Computer Misuse Act 1990

UK legal commentary (Bird & Bird, Sprintlaw UK, Eversheds Sutherland) consistently holds that scraping of publicly accessible pages is unlikely to constitute unauthorized access under the CMA. No CMA prosecution of a visa-monitor author has been reported. This project's UK-relevant operations (VFS UK, BLS UK) are constrained by the same hiQ-style logic.

## Architectural commitments

The maintainer commits to the following architectural choices, which are central to the legal posture described above. Departing from any of these would change the legal analysis materially and is not contemplated:

1. **No credentialed access** — the software does not log into any user account on any visa portal, and does not store, transmit, or use any user credentials.
2. **No CAPTCHA solving** — no integration with 2Captcha, DeathByCaptcha, or any similar service. No machine-learning models for CAPTCHA defeat.
3. **No proxy or VPN evasion** — the software runs from the user's own IP address. It does not include proxy-rotation libraries, VPN integrations, or any mechanism designed to evade IP-based access controls.
4. **No auto-booking** — the software does not POST, PUT, PATCH, or otherwise mutate state on any portal. It does not submit appointment forms. It does not interact with any "book" or "schedule" endpoint.
5. **No personal-data collection** — the software does not collect applicant identifiers of any kind. The notification destinations (Telegram, email, Discord) are configured by the user and are not transmitted back to the maintainer.
6. **Tier-based polling with conservative defaults** — the software's default polling intervals (cold: 5,400 seconds; warm: 1,800 seconds; hot: 600 seconds) are designed to produce request volume comparable to a single human user actively monitoring a site.
7. **Graceful failure** — when a monitored portal changes its response format or introduces new technical controls, the software is designed to fail closed (no false alerts) rather than aggressively retry or attempt circumvention.

## Response to formal legal notices

If a formal legal notice is delivered to the GitHub repository:

1. **DMCA takedown notices** — the maintainer will evaluate each notice on its merits. Where the underlying material is not subject to copyright (facts, data, URLs, public-domain government works, or the maintainer's own original code), the maintainer will file a counter-notice through GitHub's published process. Per GitHub's DMCA Counter Notice procedure, content is restored within 10–14 business days unless the original notifier files suit during that window.

2. **Cease-and-desist letters from VFS Global, BLS International, CGI Federal, or any consulate or embassy** — the maintainer will consult with qualified legal counsel before responding. The maintainer will not auto-comply with non-binding correspondence that overclaims rights, but will engage in good faith to address legitimate technical concerns (e.g., specific requests to lower polling rates against a particular portal).

3. **Government inquiries** — the maintainer will cooperate with lawful inquiries from Indian, U.S., or other government authorities through appropriate legal counsel.

4. **GitHub Trust & Safety reviews** — the maintainer will provide full architectural documentation, including this `LEGAL.md`, the `DISCLAIMER.md`, the `CHANGELOG.md`, and any other context Trust & Safety requires.

## Sources of further information

For users and counsel seeking further context:

- **Electronic Frontier Foundation** (eff.org) — open-source author defense
- **Software Freedom Law Center** (softwarefreedom.org) — open-source legal services
- **GitHub Site Policy** (docs.github.com/site-policy) — DMCA, Acceptable Use, Trust & Safety
- **Centre for Internet & Society India** (cis-india.org) — Indian IT Act analysis
- **Privacy World blog** (privacyworld.blog) — GDPR enforcement tracking

## Versioning of this document

This document was first added to the project at v4.2.1. Material changes to the architectural commitments above will be reflected here; minor documentation improvements will be tracked in `CHANGELOG.md` without separate notice.

If you are reviewing this project at a version later than v4.2.1, check the git history of this file (`git log LEGAL.md`) to confirm whether the architectural commitments have been amended since this document was first published.

---

**Maintainer:** independent open-source developer, India
**Repository:** https://github.com/ankitjha67/visa-tracker
**License:** MIT
**First published:** May 5, 2026
**This document last reviewed:** May 5, 2026
