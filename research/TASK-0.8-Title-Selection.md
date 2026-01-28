# Task 0.8: Phase 1 Title Selection

**Task**: Finalize 5-10 titles for Phase 1
**Status**: Complete
**Date**: 2026.01.28

---

## Executive Summary

This document provides the rationale for selecting **8 titles** for CWLB Phase 1 coverage. The selection balances public interest, data quality (positive vs non-positive law status), and legislative activity volume to create a compelling MVP while managing complexity.

### Final Selection

| Title | Subject | Positive Law | Selection Rationale |
|-------|---------|--------------|---------------------|
| **10** | Armed Forces | ✅ Yes (1956) | High public interest, positive law, moderate activity |
| **17** | Copyright | ✅ Yes (1976) | High public interest, positive law, excellent for demos |
| **18** | Crimes & Criminal Procedure | ✅ Yes (1948) | High public interest, positive law, frequent updates |
| **20** | Education | ❌ No | High public interest, affects families nationwide |
| **22** | Foreign Relations | ❌ No | Current events relevance, moderate activity |
| **26** | Internal Revenue Code | ❌ No | Highest public interest, very high activity |
| **42** | Public Health & Welfare | ❌ No | Extremely high interest (ACA, Medicare, Social Security) |
| **50** | War & National Defense | ❌ No | Current events relevance, national security interest |

---

## Selection Criteria

### 1. Public Interest and Relevance

**Scoring (1-5, 5 = highest public interest):**

| Title | Score | Rationale |
|-------|-------|-----------|
| Title 26 (Tax) | 5 | Affects every taxpayer; constant media coverage |
| Title 42 (Health/Welfare) | 5 | ACA, Medicare, Medicaid, Social Security - affects millions |
| Title 18 (Crimes) | 5 | Criminal law; high media visibility |
| Title 20 (Education) | 4 | Student loans, K-12 policy, affects families |
| Title 17 (Copyright) | 4 | Tech industry, creators, DMCA debates |
| Title 10 (Armed Forces) | 4 | Defense spending, military policy |
| Title 50 (War/Defense) | 3 | Intelligence, national security |
| Title 22 (Foreign Relations) | 3 | Diplomacy, foreign aid, treaties |

### 2. Data Availability and Quality

**Positive Law Status Impact:**

| Status | Implication for CWLB |
|--------|---------------------|
| **Positive Law** | US Code text is authoritative; simpler attribution model |
| **Non-Positive Law** | Statutes at Large is authoritative; requires disclaimers |

**Selected Titles by Status:**

- **Positive Law (3)**: Titles 10, 17, 18
- **Non-Positive Law (5)**: Titles 20, 22, 26, 42, 50

**Rationale for Including Non-Positive Law Titles:**

While positive law titles offer cleaner data attribution, excluding non-positive law titles would omit the most publicly relevant content (taxes, healthcare, education). The CWLB UI will clearly distinguish between positive and non-positive law sections with appropriate disclaimers.

### 3. Legislative Activity Volume

**Activity Assessment (based on recent Congressional sessions):**

| Title | Activity Level | Characteristics |
|-------|---------------|-----------------|
| Title 26 (Tax) | Very High | Major revisions with each Congress; Tax Cuts and Jobs Act, IRA |
| Title 42 (Health) | Very High | ACA amendments, COVID legislation, Medicare updates |
| Title 18 (Crimes) | High | Regular criminal justice reforms, new offense definitions |
| Title 10 (Armed Forces) | High | Annual NDAA brings consistent updates |
| Title 50 (War/Defense) | Moderate-High | Intelligence authorization acts, FISA updates |
| Title 20 (Education) | Moderate | Periodic reauthorizations (ESEA, HEA) |
| Title 17 (Copyright) | Moderate | Periodic updates (DMCA, MMA); stable core |
| Title 22 (Foreign Relations) | Moderate | Sanctions, aid programs, State Dept authorizations |

**Balance Achieved:**
- High-activity titles (26, 42, 18, 10) showcase CWLB's change-tracking capabilities
- Moderate-activity titles (17, 20, 22, 50) demonstrate historical depth without overwhelming volume

---

## Title-by-Title Analysis

### Title 10: Armed Forces ✅ SELECTED

**Subject Matter:** Organization and administration of the armed forces, military justice (UCMJ), personnel policies, procurement.

**Why Selected:**
- **Public Interest**: Defense spending debates, military policy, veteran affairs
- **Positive Law**: Enacted 1956; authoritative text simplifies attribution
- **Activity**: Consistent annual updates via National Defense Authorization Act (NDAA)
- **Demo Value**: NDAA amendments show clear year-over-year changes

**Scope Considerations:**
- ~1,800 sections across 25+ chapters
- Well-structured with clear hierarchies
- Good balance of stable provisions and annual amendments

---

### Title 17: Copyrights ✅ SELECTED

**Subject Matter:** Copyright protection, exclusive rights, fair use, DMCA, licensing.

**Why Selected:**
- **Public Interest**: Tech industry debates, creator rights, streaming, AI training data
- **Positive Law**: Enacted 1976; clean attribution model
- **Activity**: Moderate; stable core with periodic significant amendments
- **Demo Value**: Excellent for demonstrating blame view (§106, §107 are iconic)

**Scope Considerations:**
- ~600 sections; manageable size
- Clear structure with well-known sections
- Ideal for tutorials and onboarding examples

**Historical Significance:**
- Copyright Act of 1976 is a landmark recodification
- DMCA (1998), MMA (2018) show modern amendment patterns

---

### Title 18: Crimes and Criminal Procedure ✅ SELECTED

**Subject Matter:** Federal criminal offenses, sentencing, criminal procedure, prisons.

**Why Selected:**
- **Public Interest**: Criminal justice reform, new offense definitions, sentencing debates
- **Positive Law**: Enacted 1948; authoritative text
- **Activity**: High; regular updates for new crimes, sentencing reforms
- **Media Relevance**: Federal prosecutions frequently in news

**Scope Considerations:**
- ~2,500 sections; larger title but high value
- Clear organization by offense type
- Frequent cross-references to sentencing guidelines

---

### Title 20: Education ✅ SELECTED

**Subject Matter:** Federal education programs, student loans, K-12 policy, higher education.

**Why Selected:**
- **Public Interest**: Student debt crisis, school funding, FAFSA, Pell Grants
- **Activity**: Moderate; periodic reauthorizations (Every Student Succeeds Act, Higher Education Act)
- **Demographic Reach**: Affects students, parents, educators nationwide

**Non-Positive Law Considerations:**
- Requires disclaimer: "Compilation - Statutes at Large is authoritative"
- Attribution shows law that modified Statutes at Large
- Clear UI indicators for non-positive law status

**Scope Considerations:**
- ~1,200 sections
- Major programs (ESEA, HEA) well-documented

---

### Title 22: Foreign Relations and Intercourse ✅ SELECTED

**Subject Matter:** State Department, diplomacy, foreign aid, treaties, sanctions.

**Why Selected:**
- **Current Events**: Sanctions programs, foreign aid debates, diplomatic relations
- **Activity**: Moderate; tied to geopolitical events
- **Diversity**: Adds international affairs dimension to coverage

**Non-Positive Law Considerations:**
- Same disclaimers as Title 20
- Generally less contentious legally than domestic policy titles

**Scope Considerations:**
- ~1,500 sections
- Includes important sanctions authorities (IEEPA references)

---

### Title 26: Internal Revenue Code ✅ SELECTED

**Subject Matter:** Federal tax law - income, estate, gift, excise taxes; IRS administration.

**Why Selected:**
- **Public Interest**: Highest possible - affects every taxpayer
- **Activity**: Very high; major tax legislation each Congress
- **Media Coverage**: Tax reform constantly in political discourse
- **Demo Value**: Shows CWLB handling massive, complex legislation

**Non-Positive Law Considerations:**
- Critical to include despite compilation status
- Most users won't care about positive law distinction for tax questions
- Clear disclaimers in UI

**Scope Considerations:**
- **Largest title**: ~10,000+ sections
- Most complex hierarchical structure
- May require phased ingestion or section prioritization
- Consider starting with Subtitle A (Income Taxes) as sub-scope

**Risk Mitigation:**
- Implement title-level pagination in Phase 1
- Prioritize frequently-accessed sections
- Consider async loading for deep sections

---

### Title 42: The Public Health and Welfare ✅ SELECTED

**Subject Matter:** Social Security, Medicare, Medicaid, ACA, public health, civil rights.

**Why Selected:**
- **Public Interest**: Highest tier - healthcare affects everyone
- **Activity**: Very high; ACA amendments, Medicare updates, COVID legislation
- **Landmark Laws**: Social Security Act, ACA, Civil Rights Act provisions
- **Political Relevance**: Healthcare constantly debated

**Non-Positive Law Considerations:**
- Same disclaimers as other non-positive law titles
- Statutes at Large citations provided

**Scope Considerations:**
- **Second largest title**: ~8,000+ sections
- Very deep nesting in some areas (Medicare regulations)
- Similar phasing approach as Title 26

---

### Title 50: War and National Defense ✅ SELECTED

**Subject Matter:** National security, intelligence agencies, war powers, FISA.

**Why Selected:**
- **Current Events**: Intelligence debates, surveillance law, war powers
- **Activity**: Moderate-high; annual intelligence authorizations
- **Complements Title 10**: Covers civilian national security vs military organization

**Non-Positive Law Considerations:**
- Standard disclaimers apply

**Scope Considerations:**
- ~1,000 sections; manageable
- Includes sensitive topics (some provisions classified/omitted)
- FISA amendments are high-profile

---

## Titles Considered but Not Selected

### Title 8: Aliens and Nationality
- **Why Considered**: High public interest (immigration policy)
- **Why Deferred**: Can be added in Phase 2; Title 42 already covers some immigration-adjacent topics

### Title 11: Bankruptcy
- **Why Considered**: Positive law, moderate interest
- **Why Deferred**: More specialized audience; lower priority than selected titles

### Title 21: Food and Drugs
- **Why Considered**: FDA policy, drug regulation
- **Why Deferred**: Can be added in Phase 2; partially overlaps with Title 42 health topics

### Title 29: Labor
- **Why Considered**: Employment law, OSHA, labor unions
- **Why Deferred**: Phase 2 candidate; moderate public interest

### Title 35: Patents
- **Why Considered**: Positive law, tech industry relevance
- **Why Deferred**: More specialized than copyright; Phase 2 candidate

---

## Implementation Considerations

### Ingestion Priority Order

Based on complexity and demo value:

1. **Title 17** (Copyright) - Smallest, cleanest; ideal for initial development
2. **Title 18** (Crimes) - Medium size, positive law, high value
3. **Title 10** (Armed Forces) - Medium size, positive law
4. **Title 20** (Education) - Medium size, test non-positive law handling
5. **Title 22** (Foreign Relations) - Medium size
6. **Title 50** (War/Defense) - Medium size
7. **Title 26** (Tax) - Large; requires pagination/phasing
8. **Title 42** (Health) - Largest; requires pagination/phasing

### Estimated Section Counts

| Title | Est. Sections | Est. USCodeLine Records | Notes |
|-------|---------------|------------------------|-------|
| 17 | ~600 | ~15,000 | Ideal starting point |
| 18 | ~2,500 | ~75,000 | Positive law, high value |
| 10 | ~1,800 | ~54,000 | Positive law |
| 20 | ~1,200 | ~36,000 | First non-positive law test |
| 22 | ~1,500 | ~45,000 | |
| 50 | ~1,000 | ~30,000 | |
| 26 | ~10,000 | ~300,000 | Largest; phase carefully |
| 42 | ~8,000 | ~240,000 | Second largest |
| **Total** | **~26,600** | **~795,000** | Phase 1 scope |

### Risk Assessment

| Risk | Mitigation |
|------|------------|
| Large titles (26, 42) overwhelming | Implement pagination; prioritize high-traffic sections |
| Non-positive law complexity | Clear UI disclaimers; link to Statutes at Large |
| Parser edge cases in complex titles | Manual review queue; iterative parser improvements |
| Historical depth varies by title | Document coverage clearly; backfill incrementally |

---

## Success Criteria

Phase 1 title selection will be considered successful if:

1. ✅ All 8 titles have current US Code sections ingested
2. ✅ Positive law vs non-positive law status correctly displayed
3. ✅ At least 20 years of historical depth for Title 17 (demo title)
4. ✅ Blame view functional for all ingested sections
5. ✅ Search returns results across all 8 titles
6. ✅ Performance acceptable (<2s load time) even for large titles

---

## Appendix: US Code Title Reference

For context, here is the complete list of US Code titles with positive law status:

| # | Title | Positive Law |
|---|-------|--------------|
| 1 | General Provisions | ✅ |
| 2 | The Congress | ❌ |
| 3 | The President | ✅ |
| 4 | Flag and Seal | ✅ |
| 5 | Government Organization | ✅ |
| 6 | Domestic Security | ❌ |
| 7 | Agriculture | ❌ |
| 8 | Aliens and Nationality | ❌ |
| 9 | Arbitration | ✅ |
| **10** | **Armed Forces** | **✅ SELECTED** |
| 11 | Bankruptcy | ✅ |
| 12 | Banks and Banking | ❌ |
| 13 | Census | ✅ |
| 14 | Coast Guard | ✅ |
| 15 | Commerce and Trade | ❌ |
| 16 | Conservation | ❌ |
| **17** | **Copyrights** | **✅ SELECTED** |
| **18** | **Crimes and Criminal Procedure** | **✅ SELECTED** |
| 19 | Customs Duties | ❌ |
| **20** | **Education** | **❌ SELECTED** |
| 21 | Food and Drugs | ❌ |
| **22** | **Foreign Relations** | **❌ SELECTED** |
| 23 | Highways | ✅ |
| 24 | Hospitals and Asylums | ❌ |
| 25 | Indians | ❌ |
| **26** | **Internal Revenue Code** | **❌ SELECTED** |
| 27 | Intoxicating Liquors | ❌ |
| 28 | Judiciary and Procedure | ✅ |
| 29 | Labor | ❌ |
| 30 | Mineral Lands and Mining | ❌ |
| 31 | Money and Finance | ✅ |
| 32 | National Guard | ✅ |
| 33 | Navigation and Waters | ❌ |
| 34 | Crime Control | ✅ |
| 35 | Patents | ✅ |
| 36 | Patriotic Societies | ✅ |
| 37 | Pay and Allowances | ✅ |
| 38 | Veterans' Benefits | ✅ |
| 39 | Postal Service | ✅ |
| 40 | Public Buildings | ✅ |
| 41 | Public Contracts | ✅ |
| **42** | **Public Health and Welfare** | **❌ SELECTED** |
| 43 | Public Lands | ❌ |
| 44 | Public Printing | ✅ |
| 45 | Railroads | ❌ |
| 46 | Shipping | ✅ |
| 47 | Telecommunications | ❌ |
| 48 | Territories | ❌ |
| 49 | Transportation | ✅ |
| **50** | **War and National Defense** | **❌ SELECTED** |
| 51 | National and Commercial Space | ✅ |
| 52 | Voting and Elections | ✅ |
| 54 | National Park Service | ✅ |

---

*Document prepared as part of CWLB Phase 0 Research & Validation*
