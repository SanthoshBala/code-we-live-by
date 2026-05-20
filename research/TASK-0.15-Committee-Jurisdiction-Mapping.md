# Task 0.15: Congressional Committee Jurisdiction Mapping

**Task**: Map House/Senate committees to US Code titles and chapters for the "CODEOWNERS" metaphor
**Status**: Complete
**Date**: 2026.05.19
**GitHub Issue**: #302

---

## Executive Summary

Congressional committees have jurisdiction over specific areas of federal law, making them the natural analogue for CODEOWNERS in the CWLB version-control metaphor. This document maps House and Senate committees to all 54 US Code titles, answers key design questions about granularity and overlap, and proposes a CODEOWNERS file format for the platform.

**Key findings:**
- Most titles have clear **Title-level** jurisdiction assigned to a single committee pair
- **Title 21, 31, and 42** require **Chapter-level** splits due to program-type differences
- **Title 50** has an additional Intelligence committee layer for FISA and intelligence community chapters
- **Title 52** and **Title 2** involve House/Senate Administration committees in addition to Judiciary/Rules
- Overlapping jurisdiction is handled by convention (primary/secondary designations) and formal referral procedures

**Important data model implications (discovered during research):**
1. **Committee assignments are per-Congress.** Rule X is re-adopted at the start of each Congress and committees are renamed, merged, or restructured (e.g., Homeland Security added in 109th Congress; Intelligence moved from rule XLVIII to rule X clause 11 in 106th). Any data model must key committee records to a congress number.
2. **Rule X does not reference the US Code.** Jurisdictions are expressed as legislative topics ("adulteration of seeds, insect pests", "commodity exchanges") — never as US Code title or section numbers. The mapping from Rule X language → US Code paths is a **human-authored curation layer** that must be maintained separately. See the [Data Model](#data-model-implications) section below.

---

## Design Questions Answered

### Q1: Is jurisdiction at Title level or Chapter level?

**Mostly Title level, with three significant exceptions.**

| Title | Granularity | Reason for split |
|-------|-------------|-----------------|
| 21 — Food and Drugs | Chapter | FDA (Energy and Commerce / HELP) vs. USDA food safety (Agriculture / Agriculture) |
| 31 — Money and Finance | Chapter | Treasury/currency operations (Financial Services / Banking) vs. debt/fiscal policy (Ways and Means / Finance) |
| 42 — Public Health and Welfare | Chapter | Medicare/Medicaid (Ways and Means / Finance) vs. public health agencies (Energy and Commerce / HELP) vs. civil rights (Judiciary / Judiciary) |
| 50 — War and National Defense | Title + chapter overrides | Armed Services primary; Intelligence committees for FISA (Ch. 36) and National Security Act (Ch. 44) |

All other titles can be mapped at the Title level with a single primary committee pair.

### Q2: How to handle overlapping jurisdiction?

Three patterns appear in practice:

**Pattern A — Primary/Secondary designation** (most common)
One committee is clearly primary; a second may claim secondary authority. Display the primary committee as the OWNER, list the secondary as a reviewer. Example: Title 18 criminal justice reform may also be referred to Homeland Security, but Judiciary is the clear primary.

**Pattern B — Sequential referral** (Titles 21, 31, 42)
When a bill amends chapters under different committee jurisdictions, Congress refers it sequentially (or simultaneously) to each committee. The CODEOWNERS file reflects this by mapping at Chapter granularity.

**Pattern C — Intelligence oversight overlay** (Title 50)
Intelligence committees maintain oversight authority over chapters governing surveillance and intelligence community authorities, in addition to Armed Services. Model this as a secondary owner at the chapter level.

**Recommended display convention:** When multiple committees are listed for the same path, render the first as "Primary" and subsequent entries as "Also reviews."

### Q3: What metadata to include?

| Field | Example | Notes |
|-------|---------|-------|
| `committee_id` | `house-judiciary` | Stable slug for linking |
| `full_name` | `House Committee on the Judiciary` | Official name |
| `chamber` | `House` | House or Senate |
| `jurisdiction_type` | `primary` | primary / secondary / oversight |
| `authority_rule` | `House Rule X, Clause 1(l)` | Formal rule citation |
| `website` | `https://judiciary.house.gov/` | Current URL |
| `codeowners_path` | `/title-17/` | Path pattern this entry covers |

**Do not hardcode chair/membership data** — it changes each Congress. Link to `congress.gov/committees/<id>` for current membership.

---

## Complete CODEOWNERS Format

```
# CODEOWNERS — Congressional Committee Jurisdiction
# Format: <path pattern>  <house-committee>  <senate-committee>
# Multiple owners listed left-to-right: primary first, then secondary/oversight

# ── Government Operations ──────────────────────────────────────────────────
/title-1/     @house/judiciary                              @senate/judiciary
/title-2/     @house/administration                         @senate/rules-and-administration
/title-3/     @house/oversight-and-accountability           @senate/homeland-security-governmental-affairs
/title-4/     @house/judiciary                              @senate/judiciary
/title-5/     @house/oversight-and-accountability           @senate/homeland-security-governmental-affairs
/title-6/     @house/homeland-security                      @senate/homeland-security-governmental-affairs
/title-13/    @house/oversight-and-accountability           @senate/homeland-security-governmental-affairs
/title-39/    @house/oversight-and-accountability           @senate/homeland-security-governmental-affairs
/title-40/    @house/transportation-and-infrastructure      @senate/environment-and-public-works
/title-41/    @house/oversight-and-accountability           @senate/homeland-security-governmental-affairs
/title-44/    @house/administration                         @senate/rules-and-administration

# ── Judiciary and Law ──────────────────────────────────────────────────────
/title-8/     @house/judiciary                              @senate/judiciary
/title-9/     @house/judiciary                              @senate/judiciary
/title-11/    @house/judiciary                              @senate/judiciary
/title-17/    @house/judiciary                              @senate/judiciary
/title-18/    @house/judiciary                              @senate/judiciary
/title-27/    @house/judiciary @house/energy-and-commerce   @senate/judiciary @senate/commerce
/title-28/    @house/judiciary                              @senate/judiciary
/title-34/    @house/judiciary                              @senate/judiciary
/title-35/    @house/judiciary                              @senate/judiciary
/title-36/    @house/judiciary                              @senate/judiciary

# ── Armed Forces and National Defense ─────────────────────────────────────
/title-10/    @house/armed-services                         @senate/armed-services
/title-32/    @house/armed-services                         @senate/armed-services
/title-37/    @house/armed-services                         @senate/armed-services
/title-50/    @house/armed-services                         @senate/armed-services
/title-50/chapter-36/   @house/intelligence @house/judiciary    @senate/intelligence @senate/judiciary
/title-50/chapter-44/   @house/intelligence                  @senate/intelligence

# ── Agriculture and Food ───────────────────────────────────────────────────
/title-7/     @house/agriculture                            @senate/agriculture-nutrition-forestry
/title-21/    @house/energy-and-commerce @house/agriculture  @senate/help @senate/agriculture-nutrition-forestry
/title-21/chapter-1/    @house/agriculture                   @senate/agriculture-nutrition-forestry
/title-21/chapter-9/    @house/energy-and-commerce           @senate/help
/title-21/chapter-13/   @house/energy-and-commerce @house/judiciary  @senate/help @senate/judiciary

# ── Commerce, Banking, and Trade ──────────────────────────────────────────
/title-12/    @house/financial-services                     @senate/banking-housing-urban-affairs
/title-15/    @house/energy-and-commerce                    @senate/commerce-science-transportation
/title-19/    @house/ways-and-means                         @senate/finance
/title-47/    @house/energy-and-commerce                    @senate/commerce-science-transportation

# ── Taxation and Finance ───────────────────────────────────────────────────
/title-26/    @house/ways-and-means                         @senate/finance
/title-31/    @house/financial-services @house/ways-and-means  @senate/banking-housing-urban-affairs @senate/finance
/title-31/chapter-3/    @house/ways-and-means               @senate/finance
/title-31/chapter-5/    @house/financial-services            @senate/banking-housing-urban-affairs
/title-31/chapter-31/   @house/ways-and-means                @senate/finance

# ── Foreign Affairs ────────────────────────────────────────────────────────
/title-22/    @house/foreign-affairs                        @senate/foreign-relations

# ── Education and Labor ────────────────────────────────────────────────────
/title-20/    @house/education-and-workforce                 @senate/help
/title-29/    @house/education-and-workforce                 @senate/help

# ── Public Health and Welfare — Chapter-level split ───────────────────────
/title-42/                  @house/energy-and-commerce           @senate/help
/title-42/chapter-6a/       @house/energy-and-commerce           @senate/help
/title-42/chapter-7/        @house/ways-and-means                @senate/finance
/title-42/chapter-8/        @house/financial-services            @senate/banking-housing-urban-affairs
/title-42/chapter-21/       @house/judiciary                     @senate/judiciary

# ── Natural Resources and Environment ─────────────────────────────────────
/title-16/    @house/natural-resources                      @senate/energy-and-natural-resources
/title-25/    @house/natural-resources                      @senate/indian-affairs
/title-30/    @house/natural-resources                      @senate/energy-and-natural-resources
/title-43/    @house/natural-resources                      @senate/energy-and-natural-resources
/title-48/    @house/natural-resources                      @senate/energy-and-natural-resources
/title-54/    @house/natural-resources                      @senate/energy-and-natural-resources

# ── Transportation and Infrastructure ─────────────────────────────────────
/title-14/    @house/transportation-and-infrastructure       @senate/commerce-science-transportation
/title-23/    @house/transportation-and-infrastructure       @senate/environment-and-public-works
/title-33/    @house/transportation-and-infrastructure       @senate/environment-and-public-works
/title-45/    @house/transportation-and-infrastructure       @senate/commerce-science-transportation
/title-46/    @house/transportation-and-infrastructure       @senate/commerce-science-transportation
/title-49/    @house/transportation-and-infrastructure       @senate/commerce-science-transportation

# ── Veterans ───────────────────────────────────────────────────────────────
/title-24/    @house/veterans-affairs @house/energy-and-commerce  @senate/veterans-affairs @senate/help
/title-38/    @house/veterans-affairs                        @senate/veterans-affairs

# ── Space and Science ─────────────────────────────────────────────────────
/title-51/    @house/science-space-technology                @senate/commerce-science-transportation

# ── Elections and Voting ──────────────────────────────────────────────────
/title-52/    @house/administration @house/judiciary          @senate/rules-and-administration @senate/judiciary
```

---

## Complete Title-by-Title Reference Table

| # | Title | House Primary | Senate Primary | Granularity | Notes |
|---|-------|--------------|----------------|-------------|-------|
| 1 | General Provisions | Judiciary | Judiciary | Title | |
| 2 | The Congress | House Administration | Rules and Administration | Title | Internal rules and operations |
| 3 | The President | Oversight and Accountability | Homeland Security and Governmental Affairs | Title | Executive branch oversight |
| 4 | Flag and Seal | Judiciary | Judiciary | Title | |
| 5 | Government Organization and Employees | Oversight and Accountability | Homeland Security and Governmental Affairs | Title | Civil service, FOIA, APA |
| 6 | Domestic Security | Homeland Security | Homeland Security and Governmental Affairs | Title | DHS-enabling legislation |
| 7 | Agriculture | Agriculture | Agriculture, Nutrition, and Forestry | Title | Farm bill, SNAP, crop insurance |
| 8 | Aliens and Nationality | Judiciary | Judiciary | Title | Immigration law |
| 9 | Arbitration | Judiciary | Judiciary | Title | Federal Arbitration Act |
| 10 | Armed Forces | Armed Services | Armed Services | Title | NDAA annual vehicle |
| 11 | Bankruptcy | Judiciary | Judiciary | Title | Bankruptcy Code |
| 12 | Banks and Banking | Financial Services | Banking, Housing, and Urban Affairs | Title | |
| 13 | Census | Oversight and Accountability | Homeland Security and Governmental Affairs | Title | |
| 14 | Coast Guard | Transportation and Infrastructure | Commerce, Science, and Transportation | Title | |
| 15 | Commerce and Trade | Energy and Commerce | Commerce, Science, and Transportation | Title | FTC, antitrust, consumer protection |
| 16 | Conservation | Natural Resources | Energy and Natural Resources | Title | Wildlife, fisheries, endangered species |
| 17 | Copyrights | Judiciary | Judiciary | Title | IP subcommittees in each chamber |
| 18 | Crimes and Criminal Procedure | Judiciary | Judiciary | Title | |
| 19 | Customs Duties | Ways and Means | Finance | Title | Tariffs and trade remedies |
| 20 | Education | Education and the Workforce | Health, Education, Labor and Pensions (HELP) | Title | ESEA, HEA reauthorizations |
| 21 | Food and Drugs | Energy and Commerce / Agriculture | HELP / Agriculture, Nutrition, and Forestry | **Chapter** | FDA (E&C/HELP) vs. USDA food (Agriculture) |
| 22 | Foreign Relations and Intercourse | Foreign Affairs | Foreign Relations | Title | |
| 23 | Highways | Transportation and Infrastructure | Environment and Public Works | Title | Highway bills (IIJA) |
| 24 | Hospitals and Asylums | Veterans' Affairs + Energy and Commerce | Veterans' Affairs + HELP | Title | Primarily VA facilities; secondary: public hospitals |
| 25 | Indians | Natural Resources | Indian Affairs | Title | Senate has a standing committee; House uses Natural Resources |
| 26 | Internal Revenue Code | Ways and Means | Finance | Title | House has Art. I §7 origination authority |
| 27 | Intoxicating Liquors | Judiciary + Energy and Commerce | Judiciary + Commerce, Science, and Transportation | Title | Primary: Judiciary; secondary: E&C/Commerce for TTB regulation |
| 28 | Judiciary and Judicial Procedure | Judiciary | Judiciary | Title | Federal courts, DOJ, marshals |
| 29 | Labor | Education and the Workforce | HELP | Title | NLRA, OSHA, FLSA, FMLA |
| 30 | Mineral Lands and Mining | Natural Resources | Energy and Natural Resources | Title | |
| 31 | Money and Finance | Financial Services + Ways and Means | Banking, Housing, and Urban Affairs + Finance | **Chapter** | Treasury/currency ops (Financial Services/Banking) vs. fiscal policy (Ways/Finance) |
| 32 | National Guard | Armed Services | Armed Services | Title | |
| 33 | Navigation and Navigable Waters | Transportation and Infrastructure | Environment and Public Works | Title | Corps of Engineers, Clean Water Act, harbors |
| 34 | Crime Control and Law Enforcement | Judiciary | Judiciary | Title | |
| 35 | Patents | Judiciary | Judiciary | Title | IP subcommittees; AIA was major recent revision |
| 36 | Patriotic and National Observances, Ceremonies, and Organizations | Judiciary | Judiciary | Title | |
| 37 | Pay and Allowances of the Uniformed Services | Armed Services | Armed Services | Title | |
| 38 | Veterans' Benefits | Veterans' Affairs | Veterans' Affairs | Title | VA healthcare, disability compensation, GI Bill |
| 39 | Postal Service | Oversight and Accountability | Homeland Security and Governmental Affairs | Title | |
| 40 | Public Buildings, Property, and Works | Transportation and Infrastructure | Environment and Public Works | Title | GSA, federal buildings |
| 41 | Public Contracts | Oversight and Accountability | Homeland Security and Governmental Affairs | Title | Federal procurement |
| 42 | The Public Health and Welfare | Energy and Commerce / Ways and Means / Judiciary | HELP / Finance / Judiciary | **Chapter** | See detailed mapping below |
| 43 | Public Lands | Natural Resources | Energy and Natural Resources | Title | BLM, federal land management |
| 44 | Public Printing and Documents | House Administration | Rules and Administration | Title | GPO, Federal Register, NARA |
| 45 | Railroads | Transportation and Infrastructure | Commerce, Science, and Transportation | Title | Amtrak, FRA |
| 46 | Shipping | Transportation and Infrastructure | Commerce, Science, and Transportation | Title | Maritime law, USCG authority |
| 47 | Telecommunications | Energy and Commerce | Commerce, Science, and Transportation | Title | FCC, spectrum, broadband |
| 48 | Territories and Insular Possessions | Natural Resources | Energy and Natural Resources | Title | |
| 49 | Transportation | Transportation and Infrastructure | Commerce, Science, and Transportation | Title | DOT, FAA, NHTSA |
| 50 | War and National Defense | Armed Services (+Intelligence for Ch. 36, 44) | Armed Services (+Intelligence for Ch. 36, 44) | Title + overrides | |
| 51 | National and Commercial Space Program | Science, Space, and Technology | Commerce, Science, and Transportation | Title | NASA authorization, commercial launch |
| 52 | Voting and Elections | House Administration + Judiciary | Rules and Administration + Judiciary | Title | Voting rights under Judiciary; election administration under Administration |
| 54 | National Park Service and Related Programs | Natural Resources | Energy and Natural Resources | Title | |

---

## Chapter-Level Split Details

### Title 21 — Food and Drugs

| Chapter | Subject | House | Senate |
|---------|---------|-------|--------|
| Chapter 1 (§§ 1–24) | Federal Food and Drugs Act (original) / USDA food commodity standards | Agriculture | Agriculture, Nutrition, and Forestry |
| Chapter 9 (§§ 301–399f) | Federal Food, Drug, and Cosmetic Act (FDA primary authority) | Energy and Commerce | HELP |
| Chapter 13 (§§ 801–971) | Drug Abuse Prevention and Control (Controlled Substances Act) | Energy and Commerce + Judiciary | HELP + Judiciary |
| Chapter 22 (§§ 1501–1509) | Dietary Supplement Health and Education Act | Energy and Commerce | HELP |

### Title 31 — Money and Finance

| Chapter | Subject | House | Senate |
|---------|---------|-------|--------|
| Chapter 3 (§§ 301–339) | Department of the Treasury | Ways and Means | Finance |
| Chapter 5 (§§ 501–535) | Office of Management and Budget; government financial management | Oversight and Accountability | Homeland Security and Governmental Affairs |
| Chapter 31 (§§ 3101–3132) | Public Debt (debt ceiling) | Ways and Means | Finance |
| Chapter 51 (§§ 5101–5119) | Coins and currency | Financial Services | Banking, Housing, and Urban Affairs |
| Chapter 53 (§§ 5301–5340) | Monetary transactions (Bank Secrecy Act, AML) | Financial Services | Banking, Housing, and Urban Affairs |

### Title 42 — The Public Health and Welfare

| Chapter | Subject | House | Senate |
|---------|---------|-------|--------|
| Chapter 6A (§§ 201–300mm-61) | Public Health Service Act — CDC, NIH, HRSA, SAMHSA, FDA authorities | Energy and Commerce | HELP |
| Chapter 7 (§§ 301–1397mm) | Social Security Act — Medicare (Title XVIII), Medicaid (Title XIX), CHIP (Title XXI), TANF (Title IV) | Ways and Means | Finance |
| Chapter 8 (§§ 1401–1440) | Low-Income Housing | Financial Services | Banking, Housing, and Urban Affairs |
| Chapter 21 (§§ 1981–2000h-6) | Civil Rights Act provisions | Judiciary | Judiciary |
| Chapter 21B (§§ 2000aa–2000aa-12) | Privacy Protection Act | Judiciary | Judiciary |
| Chapter 23 (§§ 2101–2106) | Development Disabilities | Energy and Commerce | HELP |
| Chapters 67–136 (misc. welfare, community programs) | Block grants, community services, various | Energy and Commerce / Oversight | HELP / Governmental Affairs |

### Title 50 — War and National Defense (chapter overrides)

| Chapter | Subject | Additional Committees Beyond Armed Services |
|---------|---------|---------------------------------------------|
| Chapter 36 (§§ 1801–1885) | Foreign Intelligence Surveillance Act (FISA) | House: Intelligence + Judiciary; Senate: Intelligence + Judiciary |
| Chapter 44 (§§ 3001–3236) | National Security Act — intelligence community organization | House: Intelligence (Select); Senate: Intelligence (Select) |
| Chapter 45 (§§ 3301–3320) | Atomic Energy Defense Programs | House: Armed Services + Energy/Commerce; Senate: Armed Services + Energy/Natural Resources |

---

## Phase 1 Detailed Committee Profiles

### Title 10 — Armed Forces

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Armed Services | Committee on Armed Services |
| **Rule** | House Rule X, Clause 1(c) | Senate Rule XXV, Clause 1(d) |
| **Key subcommittee** | Military Personnel; Readiness; Strategic Forces; Cyber | Personnel; Readiness and Management Support |
| **Annual vehicle** | National Defense Authorization Act (NDAA) | National Defense Authorization Act (NDAA) |
| **Website** | armedservices.house.gov | armed-services.senate.gov |

### Title 17 — Copyrights

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Rule** | House Rule X, Clause 1(l) — patents, copyrights, trademarks | Senate Rule XXV, Clause 1(j) — patents, copyrights |
| **Key subcommittee** | Courts, Intellectual Property, Artificial Intelligence, and the Internet | Intellectual Property Subcommittee |
| **Note** | Revenue bills for copyright fees originate in House (Art. I §7) | |
| **Website** | judiciary.house.gov | judiciary.senate.gov |

### Title 18 — Crimes and Criminal Procedure

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Rule** | House Rule X, Clause 1(l) | Senate Rule XXV, Clause 1(j) |
| **Key subcommittee** | Crime, Terrorism and Homeland Security | Crime and Counterterrorism (oversees DOJ, FBI, DEA, ATF) |
| **Secondary referral** | Homeland Security (terrorism-related amendments) | Homeland Security (terrorism-related amendments) |
| **Website** | judiciary.house.gov | judiciary.senate.gov |

### Title 20 — Education

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Education and the Workforce | Committee on Health, Education, Labor & Pensions (HELP) |
| **Rule** | House Rule X, Clause 1(f) | Senate Rule XXV, Clause 1(g) |
| **Key subcommittee** | Higher Education and Workforce Development | Education Subcommittee |
| **Annual vehicle** | Reauthorizations (ESEA, HEA) | Reauthorizations (ESEA, HEA) |
| **Website** | edworkforce.house.gov | help.senate.gov |

### Title 22 — Foreign Relations and Intercourse

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Foreign Affairs | Committee on Foreign Relations |
| **Rule** | House Rule X, Clause 1(i) | Senate Rule XXV, Clause 1(h) |
| **Key subcommittee** | East Asia and Pacific; Western Hemisphere; Europe | Regional subcommittees |
| **Special authority** | Oversees executive war powers | Ratifies treaties (2/3 majority required) |
| **Website** | foreignaffairs.house.gov | foreign.senate.gov |

### Title 26 — Internal Revenue Code

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Ways and Means | Committee on Finance |
| **Rule** | House Rule X, Clause 1(s) + Art. I §7 | Senate Rule XXV, Clause 1(f) |
| **Key subcommittee** | Tax Subcommittee | Taxation and IRS Oversight Subcommittee |
| **Special authority** | Constitutional origination — all revenue bills must begin in House | Senate amends or substitutes House-passed bills |
| **Website** | waysandmeans.house.gov | finance.senate.gov |

### Title 42 — The Public Health and Welfare

**Medicare, Medicaid, CHIP, TANF (Chapter 7 — Social Security Act)**

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Ways and Means | Committee on Finance |
| **Key sections** | §§ 1395–1396 (Medicare/Medicaid); § 601 (TANF) | Same |
| **Website** | waysandmeans.house.gov | finance.senate.gov |

**Public health agencies — CDC, NIH, FDA, ACA market rules (Chapter 6A)**

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Energy and Commerce | Committee on Health, Education, Labor & Pensions (HELP) |
| **Key sections** | §§ 201–300 (Public Health Service Act) | Same |
| **Website** | energycommerce.house.gov | help.senate.gov |

**Civil rights provisions (Chapter 21)**

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Website** | judiciary.house.gov | judiciary.senate.gov |

### Title 50 — War and National Defense

| | House | Senate |
|-|-------|--------|
| **Primary committee** | Committee on Armed Services | Committee on Armed Services |
| **Rule** | House Rule X, Clause 1(c) | Senate Rule XXV, Clause 1(d) |

**Intelligence chapter overrides**

| Chapter | Additional Oversight Committees |
|---------|--------------------------------|
| Ch. 36 (FISA, §§ 1801–1885) | House: Intelligence + Judiciary; Senate: Intelligence + Judiciary |
| Ch. 44 (National Security Act, §§ 3001–3236) | House: Intelligence (Select); Senate: Intelligence (Select) |

---

## Committee Cross-Reference Index

Use this to look up which US Code titles a given committee owns.

### House Committees

| Committee | Titles (primary) | Titles (secondary/shared) |
|-----------|-----------------|--------------------------|
| Agriculture | 7 | 21 (Ch. 1) |
| Armed Services | 10, 32, 37, 50 | — |
| Education and the Workforce | 20, 29 | — |
| Energy and Commerce | 15, 47 | 21 (Ch. 9, 13), 24, 27, 42 (Ch. 6A) |
| Financial Services | 12 | 31, 42 (Ch. 8) |
| Foreign Affairs | 22 | — |
| Homeland Security | 6 | — |
| House Administration | 2, 44 | 52 |
| Intelligence (Select) | — | 50 (Ch. 44), 50 (Ch. 36) |
| Judiciary | 1, 4, 8, 9, 11, 17, 18, 28, 34, 35, 36 | 21 (Ch. 13), 27, 42 (Ch. 21), 50 (Ch. 36), 52 |
| Natural Resources | 16, 25, 30, 43, 48, 54 | — |
| Oversight and Accountability | 3, 5, 13, 39, 41 | 40 (shared) |
| Science, Space, and Technology | 51 | — |
| Transportation and Infrastructure | 14, 23, 33, 40, 45, 46, 49 | — |
| Veterans' Affairs | 38 | 24 |
| Ways and Means | 19, 26 | 31 (fiscal), 42 (Ch. 7) |

### Senate Committees

| Committee | Titles (primary) | Titles (secondary/shared) |
|-----------|-----------------|--------------------------|
| Agriculture, Nutrition, and Forestry | 7 | 21 (Ch. 1) |
| Armed Services | 10, 32, 37, 50 | — |
| Banking, Housing, and Urban Affairs | 12 | 31 (monetary), 42 (Ch. 8) |
| Commerce, Science, and Transportation | 14, 15, 45, 46, 47, 49, 51 | 27 |
| Energy and Natural Resources | 16, 30, 43, 48, 54 | — |
| Environment and Public Works | 23, 33, 40 | — |
| Finance | 19, 26 | 31 (fiscal), 42 (Ch. 7) |
| Foreign Relations | 22 | — |
| Health, Education, Labor and Pensions (HELP) | 20, 29 | 21 (Ch. 9, 13), 24, 42 (Ch. 6A) |
| Homeland Security and Governmental Affairs | 3, 5, 6, 13, 39, 41 | — |
| Indian Affairs | 25 | — |
| Intelligence (Select) | — | 50 (Ch. 44), 50 (Ch. 36) |
| Judiciary | 1, 4, 8, 9, 11, 17, 18, 28, 34, 35, 36 | 21 (Ch. 13), 27, 42 (Ch. 21), 50 (Ch. 36), 52 |
| Rules and Administration | 2, 44 | 52 |
| Veterans' Affairs | 38 | 24 |

---

## Granularity Recommendation

For the CWLB CODEOWNERS implementation:

1. **Start at Title level** for all titles — correct for 51 of 54 and provides a clean initial mapping
2. **Add Chapter-level entries for Titles 21, 31, and 42** from day one — the splits are significant enough that users will expect accurate attribution for Medicare vs. public health, FDA vs. USDA, Treasury vs. debt ceiling
3. **Add Chapter-level entries for Title 50, Chapters 36 and 44** — FISA and the National Security Act are high-profile and politically sensitive; accurate attribution matters
4. **Defer subcommittee-level granularity to Phase 2** — subcommittees shift frequently and add complexity without proportional user value in Phase 1

---

## Data Model Implications

### Problem: two separate concerns

The CODEOWNERS metaphor requires resolving two distinct questions:

1. **What does each committee claim jurisdiction over?** (Rule X text — per-Congress, prose format)
2. **Which US Code paths correspond to those claims?** (Curated mapping — stable, structured)

These must be stored separately. Conflating them creates a mess when Rule X changes or when committees are renamed.

### Proposed schema

```sql
-- One row per committee per Congress.
-- Committee names and jurisdiction claims change with each Congress adoption of rules.
CREATE TABLE congressional_committee (
    id              SERIAL PRIMARY KEY,
    congress        INTEGER NOT NULL,           -- 106, 107, …, 119
    chamber         TEXT NOT NULL,              -- 'house' | 'senate'
    committee_id    TEXT NOT NULL,              -- stable slug, e.g. 'judiciary'
    full_name       TEXT NOT NULL,              -- official name for that Congress
    rule_citation   TEXT,                       -- 'House Rule X, Clause 1(l)'
    jurisdiction_text TEXT,                     -- raw prose from Rule X / Rule XXV
    source_url      TEXT,                       -- GovInfo HTM URL for this Congress
    UNIQUE (congress, chamber, committee_id)
);

-- Human-curated mapping from a committee → US Code path.
-- This is the bridge between Rule X prose and the code tree.
CREATE TABLE committee_usc_mapping (
    id                  SERIAL PRIMARY KEY,
    committee_id        TEXT NOT NULL,          -- FK slug into congressional_committee
    congress_start      INTEGER NOT NULL,       -- first Congress this mapping applies
    congress_end        INTEGER,                -- NULL = still current
    usc_title           INTEGER NOT NULL,
    usc_chapter         TEXT,                   -- NULL = Title-level; e.g. '6a', '7'
    jurisdiction_type   TEXT NOT NULL,          -- 'primary' | 'secondary' | 'oversight'
    notes               TEXT                    -- reason for this mapping / split
);
```

### Data pipeline

Rule X is available as parsed HTM for every Congress from 106 onward:

```
https://www.govinfo.gov/content/pkg/HMAN-{congress}/html/HMAN-{congress}-houserules.htm
```

The HTM is parseable but the jurisdiction text is **prose** — not structured data. A pipeline approach:

1. **Fetch** the HMAN HTM for each Congress from GovInfo (available 106–119)
2. **Extract** each committee's numbered jurisdiction items by parsing the `(a) Committee on X` sections under Rule X
3. **Store** raw jurisdiction text in `congressional_committee.jurisdiction_text` — no interpretation yet
4. **Curate** `committee_usc_mapping` manually (or with LLM assistance) for each new Congress, diffing against the prior Congress to identify changed/added jurisdictions
5. **Audit** by cross-referencing against `LawChange` bill-referral data from the Congress.gov API

Step 4 is inherently a human judgment call. The mapping from "adulteration of seeds, insect pests, and protection of birds and animals in forest reserves" → `Title 7` requires interpreting legislative intent that no automated system can resolve cleanly. The curated table is the authoritative artifact.

### Change cadence

Rule X changes are infrequent between Congresses for most committees. Based on historical patterns:
- **Stable** (rarely changed): Agriculture, Judiciary, Ways and Means, Foreign Affairs, Armed Services, Veterans' Affairs, Natural Resources
- **Occasionally restructured**: Energy and Commerce, Transportation and Infrastructure
- **Frequently renamed/reorganized**: Oversight (renamed multiple times), Science/Space/Technology, Homeland Security (added 109th Congress)

A diff of `committee_usc_mapping` between consecutive Congresses is the right tool for tracking what changed.

---

## Data Sources

| Source | Type | Notes |
|--------|------|-------|
| GovInfo HMAN HTM | **Authoritative, machine-readable** | `govinfo.gov/content/pkg/HMAN-{congress}/html/HMAN-{congress}-houserules.htm` — available for all Congresses 106–119 |
| rules.house.gov prior Congresses | Index page | `rules.house.gov/resources/rules-and-manuals-house-prior-congresses` — links to PDFs and GovInfo |
| Senate Rule XXV | Authoritative — Senate jurisdiction rules | `senate.gov/pagelayout/reference/two_column_table/Senate_Rules.htm` |
| Congress.gov Committees | Reference — current membership and subcommittees | congress.gov/committees |
| Congress.gov API — bill committees | Empirical validation source | `/bill/{congress}/{type}/{number}/committees` — which committees received each bill |
| CRS Report R46251 | Background — referral procedures in the House | congress.gov/crs-product/R46251 |
| CRS Report R46815 | Background — referral procedures in the Senate | congress.gov/crs-product/R46815 |

**Rule X text sample (119th Congress, Committee on Agriculture):**

```
(a) Committee on Agriculture.
  (1) Adulteration of seeds, insect pests, and protection of birds and animals in forest reserves.
  (2) Agriculture generally.
  (3) Agricultural and industrial chemistry.
  ...
  (14) Inspection of livestock, poultry, meat products, and seafood and seafood products.
  (15) Forestry in general and forest reserves other than those created from the public domain.
  ...
```

This is the raw form of the data — topic descriptions only, no US Code citations. The `committee_usc_mapping` table is the authored layer that translates these into paths like `/title-7/`.

**Note on chair/membership:** Committee chairs change each Congress and sometimes mid-Congress. Never hardcode them. Link to `congress.gov/committees/<committee-id>` for live data.

---

## Implementation Notes

### OWNERS file placement

```
/CODEOWNERS                  ← root-level: all title paths (Title-level defaults)
/title-21/CODEOWNERS         ← Chapter-level overrides for Food and Drugs
/title-31/CODEOWNERS         ← Chapter-level overrides for Money and Finance
/title-42/CODEOWNERS         ← Chapter-level overrides for Public Health and Welfare
/title-50/CODEOWNERS         ← Chapter-level overrides for War and National Defense
```

### UI display

When rendering a US Code section, the "Owners" panel should show:
- Committee name with link to `congress.gov/committees/<id>`
- Chamber badge (House / Senate)
- Jurisdiction type (Primary / Secondary / Oversight)

For sections under split jurisdiction (e.g., 42 USC § 1395 — Medicare), show Finance/Ways and Means as primary and suppress HELP/Energy and Commerce unless they have specific subcommittee authority.

### Phase 2 enhancements

- **Subcommittee mapping** for high-traffic titles (17, 18, 26, 42)
- **Historical jurisdiction** — committees are renamed and restructured between Congresses; track historical names for accurate attribution on older laws
- **Bill referral data** — Congress.gov API exposes which committees received each bill; use this to validate and refine the mapping empirically

---

*Document prepared as part of CWLB Phase 0 Research & Validation*
