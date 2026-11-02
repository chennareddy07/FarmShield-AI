# Groundnut evidence review — Andhra Pradesh

**Status:** Pending qualified agronomist review. No evidence in this document is expert-approved.  
**Registry snapshot:** 2026-11-02  
**Scope:** Evidence provenance and limits for the current groundnut stage catalogue and risk categories. This is not a cultivation prescription.

## What was independently checked

| Source | Verified material | What it supports | What it does not support |
|---|---|---|---|
| [ICAR Annals of Arid Zone article abstract (published 2016-12-21)](https://epubs.icar.org.in/index.php/AAZ/article/view/66171) | The article page and abstract were accessible; the page says article downloads are not available. The abstract describes experimental water-stress cycles at flowering (23–47 DAS), pegging (33–55 DAS), pod formation (57–79 DAS), and pod development (73–95 DAS). | In that experiment, imposed water stress affected yield/reproductive measures; pod development was reported as sensitive for pod yield and shelling percentage, and pegging for haulm yield. | The DAS windows are not local crop calendars or rainfall/dry-spell triggers. The abstract alone does not establish an Andhra Pradesh action threshold. |
| [ICAR-IIGR Crop Production page](https://icar-iigr.org.in/crop-production/) | Official page text was accessible; no publication or trial date was shown. It reports several groundnut moisture-conservation approaches as promising at different locations and names Jagtial and Kadiri in some groundnut-based system recommendations. | A traceable lead for moisture-management review and for practices reported at named locations. | It does not provide a crop-risk threshold, stage-specific weather rule, current district-wide eligibility or enough trial detail to approve a prescription. Kadiri is retained as a named location, not mislabeled as a district. |
| [ICAR-IIGR Package of Practices PDF (2018 metadata; publication year not printed)](https://icar-iigr.org.in/wp-content/uploads/2018/12/Package-of-Practices.pdf) | The official 17-page PDF was directly accessible; Andhra Pradesh content was checked on PDF pages 1–3. The title states “Package of practices (PoP’s)of groundnut for different states”; 2018 is indicated by the PDF creation metadata and upload path, not printed as a publication date. | Five source facts are registered for Andhra Pradesh: sowing seasons and duration/harvest, the source's variety list, soil-test-based nutrient management, critical irrigation stages including pegging, and selected non-chemical weed/field-management practices. | The document is historical and does not identify Guntur as a separate applicability area. Chemical prescriptions and numerical fertilizer doses are excluded. None of the records is expert-approved, a current district prescription, or a weather-risk rule. |
| [ICRISAT / University of Reading repository record](https://oar.icrisat.org/1009/1/62806.pdf) | URL redirected to login and returned HTTP 401. | Bibliography lead only. | The former seed paraphrase and >34 °C figure are unverified and excluded from assistant grounding. |
| [IMD rainfall amount classes (2024-09-18)](https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_e66343_PRESS%20RELEASE%2011%20dated%2018th%20%20September%202024.pdf) | Official four-page PDF and class text checked. | Heavy, very heavy and extremely heavy are meteorological rainfall classes. | They are not groundnut damage thresholds; the source's 24-hour observation interval ending at 08:30 IST does not match the provider's local-calendar-day total. |

The current [IMD Amaravati forecast bulletin](https://mausam.imd.gov.in/amaravati/mcdata/APvaf.pdf) was checked as a one-page issue dated 2026-10-30. It is an expiring forecast product, not crop-risk evidence, and was not seeded.

## Stage and concern coverage

The configured stages are `emergence_seedling`, `vegetative`, `flowering`, `pegging`, `pod_formation`, `pod_development`, and `maturity_harvest`. The stage catalogue remains `needs_review`.

The accessible ICAR abstract provides stage-specific *experimental evidence* for water stress at flowering, pegging, pod formation and pod development. All four entries remain `expert_review_required`; none supplies an operational weather trigger. The registry emits an explicit `insufficient_evidence` row for each remaining stage/concern pair, including rainfall, excess rainfall, heat, cold, humidity, wind and severe weather. The inaccessible ICRISAT record does not count as evidence.

The newly registered Package of Practices material is general agricultural guidance, not validated crop-risk evidence. Its irrigation record is linked to the `pegging` workflow because the source explicitly names peg penetration as a critical irrigation stage; its quoted schedule remains a historical source statement requiring local review.

## Interpretation and safety decisions

- Keep `GNUT-HEAT-REPRO` disabled. The cited ICRISAT source was inaccessible; its previous >34 °C claim is not verified.
- Keep all three IMD rainfall rules disabled. Meteorological classes do not establish groundnut impact, and provider/source windows differ.
- Do not convert experimental DAS ranges to an Andhra Pradesh sowing calendar or weather threshold.
- Keep all five ICAR-IIGR Package of Practices records at `expert_review_required`; the source is old and not Guntur-specific.
- Review the sowing calendar, cultivar list, irrigation schedule and cultural practices against current ANGRAU/KVK advice before presenting them as current local recommendations.
- Do not expose chemical pest-control prescriptions or numerical fertilizer rates from the source in the assistant.
- No crop-specific recommendation is approved by this review record.

## Required reviewer decision

- Review the full ICAR groundnut water-stress paper and assess whether findings generalize to local varieties, soils and production systems.
- Verify current ICAR-IIGR/ANGRAU advice for the named locations and identify district and season scope.
- Locate accessible field evidence for heat, excess rainfall/waterlogging, low temperature, disease and wind impacts.
- Define the measurement window, weather variable and unit before any rule proposal; validate it against the actual provider data.
- Review stage names and Telugu agricultural terms.

**Reviewer name / affiliation:** Not assigned  
**Review date:** Not reviewed  
**Decision:** Pending — no evidence or risk rule approved  
**Approved rule IDs:** None
