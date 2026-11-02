# Paddy evidence review — Andhra Pradesh

**Status:** Pending qualified agronomist review. No evidence in this document is expert-approved.  
**Registry snapshot:** 2026-11-01  
**Scope:** Evidence provenance and limits for the current paddy stage catalogue and risk categories. This is not a cultivation prescription.

## What was independently checked

| Source | Verified material | What it supports | What it does not support |
|---|---|---|---|
| [JIRCAS/JARQ TARC Notes (1977), pp. 190–191](https://www.jircas.go.jp/sites/default/files/publication/jarq/11-3-190-191_0.pdf) | The two-page PDF was downloaded temporarily and its text checked. It describes controlled IRRI phytotron experiments with three varieties/selections, temperatures from 26 to 41 °C and 2, 4 or 8 hours of exposure per day over five days. | Rice flowering fertility response is affected by temperature, exposure duration and variety. The paper describes 35 °C for screening susceptible varieties and 38 °C for selecting tolerant ones. | Neither number is a general field damage threshold, an Andhra Pradesh recommendation, or a direct match for a daily maximum forecast. Source reuse terms were not confirmed; the PDF is not retained in the repository. |
| [Springer / Joint FAO-IAEA chapter](https://link.springer.com/chapter/10.1007/978-3-319-77338-4_2) | Publisher returned HTTP 406 in this review. | Bibliography lead only. | No claim, including any numeric threshold, is treated as verified or used for assistant grounding. |
| [IMD rainfall amount classes (2024-09-18)](https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_e66343_PRESS%20RELEASE%2011%20dated%2018th%20%20September%202024.pdf) | Official four-page PDF and class text checked. | Heavy, very heavy and extremely heavy are meteorological rainfall classes. | They are not paddy damage thresholds; the source's 24-hour observation interval ending at 08:30 IST does not match the provider's local-calendar-day total. |

The current [IMD Amaravati forecast bulletin](https://mausam.imd.gov.in/amaravati/mcdata/APvaf.pdf) was checked as a one-page issue dated 2026-10-30. It is an expiring forecast product, not crop-risk evidence, and was not seeded.

## Stage and concern coverage

The current configured stages are `nursery`, `transplanting_establishment`, `tillering`, `panicle_initiation`, `flowering`, `grain_filling`, and `maturity_harvest`. This stage catalogue itself remains `needs_review`; no durations are inferred.

Only `flowering` / `high_temperature` has a directly accessible crop-stage source in the registry, and that item is still `expert_review_required`. The registry emits an explicit `insufficient_evidence` row for each of the other stage/concern pairs, including rainfall, excess rainfall, dry spell, low temperature, humidity, wind and severe weather.

## Interpretation and safety decisions

- Keep `PADDY-HEAT-FLOWERING` disabled. Its candidate 35 °C value is not a validated local damage threshold, and the controlled exposure window is not represented by daily maximum temperature.
- Keep all three IMD rainfall rules disabled. Meteorological classes do not establish paddy impact, and provider/source windows differ.
- Do not infer stage durations, sowing dates, or district-wide recommendations from the sources above.
- No crop-specific recommendation is approved by this review record.

## Required reviewer decision

- Confirm source interpretation and whether the controlled study is relevant to local varieties and field conditions.
- Identify suitable Andhra Pradesh field studies or ANGRAU/ICAR district advisories for stage-specific rainfall, flooding, dry spell, heat, cold, disease and wind impacts.
- Define the measurement window, variable and unit needed for any candidate rule; separately validate local forecast-provider compatibility.
- Review paddy stage names and Telugu agricultural terms.

**Reviewer name / affiliation:** Not assigned  
**Review date:** Not reviewed  
**Decision:** Pending — no evidence or risk rule approved  
**Approved rule IDs:** None
