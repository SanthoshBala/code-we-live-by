# Task 0.15: Congressional Committee Jurisdiction Mapping

**Task**: Map House/Senate committees to US Code titles/chapters for the "CODEOWNERS" metaphor
**Status**: Complete
**Date**: 2026.05.19
**GitHub Issue**: #302

---

## Executive Summary

Congressional committees have jurisdiction over specific areas of federal law, making them the natural analogue for CODEOWNERS in the CWLB version-control metaphor. This document maps House and Senate committees to the 8 Phase 1 US Code titles, answers key design questions about granularity and overlap, and proposes a CODEOWNERS file format for the platform.

**Key findings:**
- 7 of 8 Phase 1 titles have clear **Title-level** jurisdiction assigned to a single primary committee pair
- **Title 42 (Public Health and Welfare)** is the significant exception — jurisdiction splits at the **Chapter level** across three committees per chamber
- **Title 50** has an additional **Intelligence committee** layer for chapters covering surveillance and intelligence authorities
- Overlapping jurisdiction is handled by convention (primary/secondary designations) and formal referral procedures

---

## Recommended CODEOWNERS Format

Using a path structure that mirrors the US Code hierarchy (`/title-NN/chapter-NN/section-NNNN`), the OWNERS mapping for Phase 1 titles would look like:

```
# CODEOWNERS — Congressional Committee Jurisdiction
# Format: <path pattern>  <house-committee>  <senate-committee>
# Overlapping jurisdiction listed left-to-right: primary first

/title-10/    @house/armed-services          @senate/armed-services
/title-17/    @house/judiciary               @senate/judiciary
/title-18/    @house/judiciary               @senate/judiciary
/title-20/    @house/education-and-workforce  @senate/help
/title-22/    @house/foreign-affairs          @senate/foreign-relations
/title-26/    @house/ways-and-means           @senate/finance

# Title 42 splits at chapter level — overrides follow general rule
/title-42/                      @house/energy-and-commerce        @senate/help
/title-42/chapter-6a/           @house/energy-and-commerce        @senate/help
/title-42/chapter-7/            @house/ways-and-means             @senate/finance
/title-42/chapter-8/            @house/ways-and-means             @senate/finance

# Title 50 — Armed Services primary; Intel committees have oversight authority
/title-50/                      @house/armed-services             @senate/armed-services
/title-50/chapter-44/           @house/intelligence               @senate/intelligence
/title-50/chapter-36/           @house/intelligence @house/judiciary  @senate/intelligence @senate/judiciary
```

---

## Design Questions Answered

### Q1: Is jurisdiction at Title level or Chapter level?

**Mostly Title level, with one major exception.**

For 7 of 8 Phase 1 titles, a single committee pair holds comprehensive jurisdiction and no meaningful Chapter-level splits exist:

| Title | Granularity | Notes |
|-------|-------------|-------|
| 10 — Armed Forces | Title | Armed Services has complete authority |
| 17 — Copyrights | Title | Judiciary handles all IP law |
| 18 — Crimes | Title | Judiciary handles all criminal law |
| 20 — Education | Title | Education & Workforce / HELP |
| 22 — Foreign Relations | Title | Foreign Affairs / Foreign Relations |
| 26 — Internal Revenue Code | Title | Ways and Means / Finance (with House origination authority under Constitution Art. I §7) |
| 50 — War and National Defense | Title (with chapter carve-outs) | Armed Services primary; Intelligence committees for Chapters 36 and 44 |

**Title 42 requires Chapter-level mapping** because it contains fundamentally different program types with separate funding mechanisms, which Congress has historically assigned to different committees:

| Title 42 Chapter | Subject | House | Senate |
|-----------------|---------|-------|--------|
| Chapter 6A | Public Health Service Act (CDC, NIH, FDA) | Energy and Commerce | HELP |
| Chapter 7 | Social Security Act (Medicare, Medicaid, CHIP, TANF) | Ways and Means | Finance |
| Chapter 8 | Housing programs | Financial Services | Banking |
| Chapter 21 (Civil Rights) | Civil rights enforcement | Judiciary | Judiciary |
| Chapters 67–136 (misc.) | Welfare, community, environment programs | Energy and Commerce / Oversight | HELP / Finance (split) |

### Q2: How to handle overlapping jurisdiction?

Three patterns appear in practice:

**Pattern A — Primary/Secondary designation** (most common for Phase 1 titles)
One committee is clearly primary; a second committee may claim secondary authority. Display the primary committee as the OWNER, list the secondary committee as a reviewer. Example: Title 18 criminal justice reform may also be referred to Homeland Security committee, but Judiciary is the clear primary.

**Pattern B — Sequential referral** (Title 42 / complex legislation)
When a bill amends multiple chapters under different committee jurisdictions, Congress refers it sequentially (or simultaneously) to each committee. The CODEOWNERS file reflects this by mapping at Chapter granularity.

**Pattern C — Intelligence oversight overlay** (Title 50)
Intelligence committees (Select Committee on Intelligence in both chambers) maintain oversight authority over Title 50 chapters governing surveillance and intelligence community authorities, in addition to Armed Services. Model this as a secondary owner at the chapter level.

**Recommended display convention:** When multiple committees are listed for the same path, render the first as "Primary" and subsequent entries as "Also reviews." This matches how GitHub renders CODEOWNERS when multiple teams are listed.

### Q3: What metadata to include?

For each committee entry, the recommended metadata fields:

| Field | Example | Notes |
|-------|---------|-------|
| `committee_id` | `house-judiciary` | Stable slug for linking |
| `full_name` | `House Committee on the Judiciary` | Official name |
| `chamber` | `House` | House or Senate |
| `jurisdiction_type` | `primary` | primary / secondary / oversight |
| `authority_rule` | `House Rule X, Clause 1(l)` | Formal rule citation |
| `website` | `https://judiciary.house.gov/` | Current URL |
| `codeowners_path` | `/title-17/` | Path pattern this entry covers |

Chair/membership data changes each Congress; **do not hardcode** in the mapping table. Link to `congress.gov/committees/<id>` for current membership.

---

## Phase 1 Committee Mapping Table

### Title 10 — Armed Forces

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Armed Services | Committee on Armed Services |
| **Rule** | House Rule X, Clause 1(c) | Senate Rule XXV, Clause 1(d) |
| **Key subcommittee** | Military Personnel; Readiness; Strategic Forces | Personnel; Readiness and Management Support |
| **Jurisdiction level** | Title | Title |
| **Annual vehicle** | National Defense Authorization Act (NDAA) | National Defense Authorization Act (NDAA) |
| **Website** | armedservices.house.gov | armed-services.senate.gov |

### Title 17 — Copyrights

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Rule** | House Rule X, Clause 1(l) — patents, copyrights, trademarks | Senate Rule XXV, Clause 1(j) — patents, copyrights |
| **Key subcommittee** | Courts, Intellectual Property, Artificial Intelligence, and the Internet | Intellectual Property Subcommittee |
| **Jurisdiction level** | Title | Title |
| **Note** | Revenue bills for copyright fees originate in House (Art. I §7) | |
| **Website** | judiciary.house.gov | judiciary.senate.gov |

### Title 18 — Crimes and Criminal Procedure

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Rule** | House Rule X, Clause 1(l) — criminal law, administration of justice | Senate Rule XXV, Clause 1(j) — federal courts, criminal law |
| **Key subcommittee** | Crime, Terrorism and Homeland Security | Crime and Counterterrorism (oversees DOJ, FBI, DEA, ATF) |
| **Jurisdiction level** | Title | Title |
| **Secondary referral** | Homeland Security (for terrorism-related amendments) | Homeland Security (for terrorism-related amendments) |
| **Website** | judiciary.house.gov | judiciary.senate.gov |

### Title 20 — Education

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Education and the Workforce | Committee on Health, Education, Labor & Pensions (HELP) |
| **Rule** | House Rule X, Clause 1(f) | Senate Rule XXV, Clause 1(g) |
| **Key subcommittee** | Higher Education and Workforce Development | Education Subcommittee |
| **Jurisdiction level** | Title | Title |
| **Annual vehicle** | Reauthorizations (ESEA, HEA) | Reauthorizations (ESEA, HEA) |
| **Website** | edworkforce.house.gov | help.senate.gov |

### Title 22 — Foreign Relations and Intercourse

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Foreign Affairs | Committee on Foreign Relations |
| **Rule** | House Rule X, Clause 1(i) — foreign affairs, foreign assistance | Senate Rule XXV, Clause 1(h) — foreign relations, treaties |
| **Key subcommittee** | East Asia and the Pacific; Western Hemisphere; Europe | Regional subcommittees |
| **Jurisdiction level** | Title | Title |
| **Special authority** | Foreign Affairs oversees executive war powers; Foreign Relations ratifies treaties (2/3 majority) | |
| **Website** | foreignaffairs.house.gov | foreign.senate.gov |

### Title 26 — Internal Revenue Code

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Ways and Means | Committee on Finance |
| **Rule** | House Rule X, Clause 1(s) + Art. I §7 (all revenue bills originate in House) | Senate Rule XXV, Clause 1(f) |
| **Key subcommittee** | Tax Subcommittee | Taxation and IRS Oversight Subcommittee |
| **Jurisdiction level** | Title | Title |
| **Special authority** | Constitutional origination — the House always drafts the initial revenue bill | Senate amends or replaces House-passed bills |
| **Website** | waysandmeans.house.gov | finance.senate.gov |

### Title 42 — The Public Health and Welfare *(Chapter-level split)*

This title encompasses programs with fundamentally different funding mechanisms, historically divided across committees:

#### Programs financed by trust funds / appropriations (Medicare, Medicaid, CHIP, TANF)

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Ways and Means | Committee on Finance |
| **Primary chapters** | Chapter 7 (Social Security Act) | Chapter 7 (Social Security Act) |
| **Key sections** | §§ 1395–1396 (Medicare/Medicaid), § 601 (TANF) | Same |
| **Website** | waysandmeans.house.gov | finance.senate.gov |

#### Public health agencies and health regulation (CDC, NIH, FDA, ACA marketplace)

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on Energy and Commerce | Committee on Health, Education, Labor & Pensions (HELP) |
| **Primary chapters** | Chapter 6A (Public Health Service Act) | Chapter 6A (Public Health Service Act) |
| **Key sections** | §§ 201–300 (PHS Act), ACA Title I market rules | Same |
| **Website** | energycommerce.house.gov | help.senate.gov |

#### Civil rights and anti-discrimination provisions

| | House | Senate |
|-|-------|--------|
| **Committee** | Committee on the Judiciary | Committee on the Judiciary |
| **Primary chapters** | Chapter 21 (Civil Rights Act provisions) | Chapter 21 |

#### Summary — Title 42 CODEOWNERS paths

| Path | House Primary | Senate Primary |
|------|--------------|----------------|
| `/title-42/` (default) | Energy and Commerce | HELP |
| `/title-42/chapter-7/` | Ways and Means | Finance |
| `/title-42/chapter-6a/` | Energy and Commerce | HELP |
| `/title-42/chapter-21/` | Judiciary | Judiciary |

### Title 50 — War and National Defense

| | House | Senate |
|-|-------|--------|
| **Primary committee** | Committee on Armed Services | Committee on Armed Services |
| **Rule** | House Rule X, Clause 1(c) — national security, defense policy | Senate Rule XXV, Clause 1(d) |
| **Jurisdiction level** | Title (with chapter carve-outs for intelligence) | Title (with chapter carve-outs) |

**Intelligence committee overlay:**

| Chapter | Subject | Additional Oversight |
|---------|---------|---------------------|
| Chapter 36 (§§ 1801–1885, FISA) | Foreign Intelligence Surveillance | House & Senate Intelligence committees + Judiciary |
| Chapter 44 (§§ 3001–3236, National Security Act) | Intelligence community organization | House & Senate Intelligence committees (Select) |

The Select Intelligence committees in both chambers have exclusive jurisdiction over intelligence community programs and budgets. Armed Services maintains primary authority over defense programs and war powers.

---

## Granularity Recommendation for Phase 1

For the CWLB CODEOWNERS implementation:

1. **Start at Title level** for all 8 titles — this is correct for 7 of 8 and provides a clean initial mapping
2. **Add Chapter-level entries for Title 42** from day one — the split is significant enough that users will expect it
3. **Add Chapter-level entries for Title 50 Chapters 36 and 44** — FISA and the National Security Act are high-profile enough to warrant precise attribution
4. **Defer subcommittee-level granularity** to Phase 2 — subcommittees shift more frequently and add complexity without proportional user value

---

## Data Sources and Authority References

| Source | Type | URL |
|--------|------|-----|
| House Rule X | Authoritative — committee jurisdiction rules | govinfo.gov/content/pkg/HMAN-119 |
| Senate Rule XXV | Authoritative — committee jurisdiction rules | senate.gov/pagelayout/reference/two_column_table/Senate_Rules.htm |
| Congress.gov Committees | Reference — current membership and subcommittees | congress.gov/committees |
| House.gov Committees | Reference — committee websites and jurisdiction descriptions | house.gov/committees |
| CRS Report R46251 | Background — committee referral procedures in the House | congress.gov/crs-product/R46251 |
| CRS Report R46815 | Background — committee referral procedures in the Senate | congress.gov/crs-product/R46815 |

**Note on chair/membership data:** Committee chairs and membership change each Congress (and sometimes mid-Congress). Do not store chair names in the mapping table; instead link to `congress.gov/committees/<committee-id>` for live data. The jurisdiction rules (House Rule X, Senate Rule XXV) are far more stable.

---

## Implementation Notes for Phase 1

### OWNERS file placement

Following the CWLB repository metaphor where titles are directories, place CODEOWNERS-style files as:

```
/CODEOWNERS              ← root-level: maps all title paths
/title-42/CODEOWNERS     ← chapter-level overrides for Title 42
/title-50/CODEOWNERS     ← chapter-level overrides for Title 50
```

### Display in UI

When rendering a US Code section (e.g., 17 USC § 106), the "Owners" panel should show:
- Committee name with link to `congress.gov/committees/<id>`
- Chamber badge (House / Senate)
- Jurisdiction type (Primary / Secondary / Oversight)

For sections under split jurisdiction (Title 42 Chapter 7), show both Finance (primary) and HELP (secondary, if applicable to that specific section's subject matter).

### Future work (Phase 2+)

- **Subcommittee mapping**: Map specific subcommittees to US Code chapters for deeper attribution
- **Historical jurisdiction**: Committees are renamed and restructured between Congresses; track historical names for accurate attribution on older laws
- **Bill referral data**: Congress.gov API exposes which committees received each bill — use this to validate and refine the mapping empirically rather than relying solely on formal jurisdiction rules

---

*Document prepared as part of CWLB Phase 0 Research & Validation*
