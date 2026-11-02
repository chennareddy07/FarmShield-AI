# Andhra Pradesh Agricultural Evidence Register

**Snapshot reviewed:** 2026-11-01  
**Scope:** Paddy and groundnut; Andhra Pradesh. Source verification, local applicability and expert approval are separate statuses. No evidence is expert-approved at this snapshot.

## Current evidence state

- Six short, source-linked knowledge records are seeded in `knowledge/metadata/seed_documents.json`: one meteorological source fact, three accessible agricultural sources needing expert review, and two inaccessible bibliography leads marked source-unverified.
- `knowledge/metadata/evidence_registry.json` records source access, dates, geographic scope, source-vs-interpretation distinctions, and crop-stage coverage. For the two seven-stage crop catalogues and eight configured risk concerns, it emits **107 explicit `insufficient_evidence` combinations**. The other five stage-concern entries are accessible experimental evidence but still require expert review; none is an operational rule.
- `knowledge/metadata/rule_validation_records.json` records each of the five configured rules and its source/input variable, unit and time-window compatibility. **All five remain disabled; zero operational and zero expert-approved crop-stage rules.**
- Expert decisions are pending in `knowledge/reviews/paddy-evidence-review.md` and `knowledge/reviews/groundnut-evidence-review.md`.

## Source facts and limits

| Record | Source-verified fact | FarmShield interpretation / limitation |
|---|---|---|
| IMD rainfall classes | [IMD press release, 2024-09-18](https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_e66343_PRESS%20RELEASE%2011%20dated%2018th%20%20September%202024.pdf) reports heavy 64.5–115.5 mm, very heavy 115.6–204.4 mm, and extremely heavy ≥204.5 mm rainfall classes. | Meteorological classes, not crop damage. The 24-hour observation ending 08:30 IST differs from Open-Meteo's local-calendar-day total. |
| Paddy flowering heat | [JIRCAS/JARQ (1977), pp. 190–191](https://www.jircas.go.jp/sites/default/files/publication/jarq/11-3-190-191_0.pdf) describes controlled IRRI phytotron exposures and variety-dependent fertility responses. It uses 35 °C for screening susceptible varieties and 38 °C for selecting tolerant varieties. | Screening values, not Andhra Pradesh field damage thresholds. Duration and variety matter; daily maximum temperature does not represent the reported controlled exposure. |
| Groundnut water stress | [ICAR Annals of Arid Zone abstract (published 2016-12-21)](https://epubs.icar.org.in/index.php/AAZ/article/view/66171) reports experimental treatment windows at flowering, pegging, pod formation and pod development (23–47, 33–55, 57–79 and 73–95 DAS). | Experimental DAS periods are not a local crop calendar or weather trigger. The full article download was unavailable from the page; expert review is needed. |
| Groundnut moisture management | [ICAR-IIGR Crop Production page](https://icar-iigr.org.in/crop-production/) reports several moisture-conservation approaches as promising at different locations and names Jagtial and Kadiri in some cropping-system recommendations. | Page has no publication/trial date and does not provide a stage-specific weather threshold or district-wide applicability. Kadiri is stored as a named location, not a district. |
| Paddy heat chapter lead | [Springer / Joint FAO-IAEA chapter](https://link.springer.com/chapter/10.1007/978-3-319-77338-4_2) returned HTTP 406. | No claims or numeric thresholds are extracted or used. |
| Groundnut heat chapter lead | [ICRISAT repository PDF](https://oar.icrisat.org/1009/1/62806.pdf) redirected to login and returned HTTP 401. | The previous seed's >34 °C claim is unverified and excluded from assistant grounding. |

The [IMD Amaravati bulletin](https://mausam.imd.gov.in/amaravati/mcdata/APvaf.pdf) issued 2026-10-30 was checked as a dated, one-page five-day district forecast. It is an expiring forecast product, not reusable crop-risk evidence, and was not seeded. ANGRAU resources were not verified in this research pass; TNAU's general index was accessible, but guessed crop pages returned 404 and Tamil Nadu sources alone would not establish Andhra Pradesh applicability. IRRI's Rice Knowledge Bank could not be retrieved.

PDFs were downloaded temporarily only to inspect the JIRCAS paper, the IMD rainfall press release and the current IMD bulletin; temporary copies were deleted and none is vendored. Reuse/license terms for the JIRCAS document were not confirmed. The ICAR article was checked through its abstract page only.

## Rule validation

| Rule IDs | Source fact | Compatibility / limitation | Status |
|---|---|---|---|
| `IMD-RAIN-HEAVY`, `IMD-RAIN-VERYHEAVY`, `IMD-RAIN-EXTREME` | Verified IMD meteorological amount classes | Units are mm, but source 24-hour 08:30 interval differs from provider local-day total; not crop-impact thresholds; severity mapping is FarmShield-defined. | Disabled |
| `PADDY-HEAT-FLOWERING` | Verified controlled-study screening value | The selected 35 °C candidate is not an AP field threshold; duration and variety matter; provider daily maximum is a different exposure window. | Disabled |
| `GNUT-HEAT-REPRO` | Cited source is inaccessible; candidate >34 °C claim unverified | No source window or verified exposure claim; daily maximum does not establish duration. | Disabled |

`ALLOW_UNVERIFIED_RULES=true` cannot override an unverified temporal window. See the per-rule records for required work before any enablement.

## Required expert work

1. Review paddy stage definitions, local varieties and whether the controlled study has any local application.
2. Obtain accessible ANGRAU/ICAR field guidance and district/season crop calendars for both crops.
3. Review the full ICAR groundnut study before interpreting the abstract for Andhra Pradesh.
4. Establish validated weather variable, units, exposure period, crop stage and local impact for every proposed rule.
5. Review Telugu terminology and all farmer-facing recommendations.

Until that review is recorded, no source is expert-approved, the assistant cannot use inaccessible leads as evidence, and all uncovered category/stage pairs remain insufficient rather than receiving invented thresholds or advice.
