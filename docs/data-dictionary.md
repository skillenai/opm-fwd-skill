# Data Dictionary (key fields)

The accessions and separations datasets share the same 68-column schema. This is a practical subset — the fields you'll actually filter and group on. OPM publishes a complete **FWD Data Dictionary** (downloadable from [data.opm.gov](https://data.opm.gov)); consult it for the full code lists.

Most dimensions come as a **name + `_code` pair** (e.g. `occupational_series` = `NURSE`, `occupational_series_code` = `0610`). Filter on whichever is more stable — codes don't change, names occasionally get relabeled.

## The measure

| Field | Notes |
|-------|-------|
| `count` | Number of employees in this cell. **Stored as a string** — coerce to numeric before summing (`fwd.load` does this). |

## Who / where they work

| Field | Example | Notes |
|-------|---------|-------|
| `agency` / `agency_code` | `DEPARTMENT OF VETERANS AFFAIRS` / `VA` | Employing agency. |
| `department` / `department_code` | | Cabinet-level parent. |
| `agency_subelement` / `_code` | `VETERANS HEALTH ADMINISTRATION` | Sub-agency. |
| `cfo_act_agency_indicator` | `CFO ACT AGENCY` | Flags the 24 large CFO Act agencies. |
| `duty_station_state` / `_abbreviation` | `CALIFORNIA` / `CA` | Work location. |
| `duty_station_city`, `_county`, `core_based_statistical_area` | | Metro-level geography via CBSA. |
| `locality_pay_area` / `_code` | `SAN DIEGO-CHULA VISTA-CARLSBAD, CA` | Locality-pay region. |

## What they do

| Field | Example | Notes |
|-------|---------|-------|
| `occupational_series` / `_code` | `INFORMATION TECHNOLOGY MANAGEMENT` / `2210` | The OPM occupational series. Codes are 4-char zero-padded. |
| `occupational_group` / `_code` | | Broad family the series rolls up to. |
| `occupational_category` / `_code` | `PROFESSIONAL` / `P` | PATCO: Professional / Administrative / Technical / Clerical / Other. |
| `stem_occupation` / `stem_occupation_type` | `STEM OCCUPATIONS` / `SCIENCE OCCUPATIONS` | STEM flag + sub-type. |
| `supervisory_status` / `_code` | `ALL OTHER POSITIONS` | Supervisor vs manager vs non-supervisory. |

### Handy occupational series codes

| Code | Series |
|------|--------|
| `2210` | Information Technology Management |
| `1550` | Computer Science |
| `1560` | Data Science |
| `1515` | Operations Research |
| `1529` / `1530` | Mathematical Statistics / Statistics |
| `0854` | Computer Engineering |
| `0610` | Nurse |
| `0456` | Wildland Fire Management (heavily seasonal) |
| `0462` | Forestry Technician (seasonal) |
| `0025` | Park Ranger (seasonal) |

## Pay & grade

| Field | Notes |
|-------|-------|
| `annualized_adjusted_basic_pay` | Annualized adjusted basic pay (numeric; `0` appears for some intermittent/other pay bases). |
| `pay_plan` / `_code` | `GENERAL SCHEDULE` / `GS`, plus SES, wage-grade, etc. |
| `grade` | GS grade (`05`, `11`, `13`…). |
| `pay_basis` / `_code` | `PER ANNUM` / `PA`, per-hour, etc. |
| `step_or_rate_type` / `_code` | Within-grade step. |

## Person attributes

| Field | Example | Notes |
|-------|---------|-------|
| `age_bracket` | `45-49` | 5-year brackets. Useful for entry-level vs senior cuts. |
| `education_level` / `education_level_bracket` / `_code` | `MASTER'S DEGREE` / `MASTERS OR PROFESSIONAL DEGREE` | |
| `length_of_service_years` | `12.4` | Tenure at the event. |
| `veteran_indicator` | `Y` / `N` | |
| `pathways_group` | | Federal early-career / internship programs (often null outside those hires). |

## Event type

| Field | Notes |
|-------|-------|
| `accession_category` / `_code` (accessions) | Type of onboarding, e.g. `AC` New Hire – Competitive Service, `AD` New Hire – Excepted Service, plus transfers-in and reinstatements. |
| `separation_category` / `_code` (separations) | Type of departure — see below. |
| `appointment_type` / `_code` | Career-conditional, term, temporary, etc. |
| `work_schedule` / `_code` | `FULL-TIME` / `F`, part-time, intermittent, seasonal. |
| `tenure` / `tenure_code` | Tenure group (career vs conditional). |
| `personnel_action_effective_date_yyyymm` | Month of the action. |

### Separation category codes (verified)

| Code | Meaning |
|------|---------|
| `SC` | Quit |
| `SD` | Retirement — Voluntary |
| `SE` | Retirement — Early Out |
| `SG` | Retirement — Other |
| `SJ` | Termination (expired appointment / other) |
| `SA` | Transfer Out — Individual |
| `SB` | Transfer Out — Mass Transfer |
| `SH` | **Reduction in Force (RIF)** |
| `SL` | Other Separation |

Distinguishing **voluntary** (`SC`, `SD`) from **involuntary** (`SH` RIF, some `SJ`) separations is often the analytically interesting split. Use `lookup.py separations <year> <month> separation` to see the current-month distribution.
