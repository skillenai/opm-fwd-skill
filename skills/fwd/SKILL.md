---
name: fwd
description: Query US federal workforce data (hires, separations, headcount) from the OPM Federal Workforce Data API — no API key required
user-invocable: true
argument-hint: [latest|list|schema|netflow|lookup|download] <details>
allowed-tools: Bash, Read, Write, Glob, Grep
---

# OPM Federal Workforce Data (FWD) Skill

Invoke as `/opm-fwd:fwd` (when installed via `/plugin install opm-fwd@labor-data-skills`).

This skill queries the **U.S. Office of Personnel Management's Federal Workforce Data (FWD) API** — an open, **no-authentication** REST service at `https://data.opm.gov` covering the federal civilian workforce.

## What the API provides

Three person-level monthly datasets, delivered as Parquet:

| Dataset | What it is | Grain |
|---------|-----------|-------|
| `employment` | Headcount snapshots — who is on the rolls | Monthly, back to 2005 |
| `accessions` | **Hires** / onboarding events | Monthly, back to 2015 |
| `separations` | **Departures** / offboarding events | Monthly, back to 2015 |

Each accession/separation record carries **68 columns**: agency & department, occupational series/group/category, STEM flag, pay (`annualized_adjusted_basic_pay`), grade & pay plan, work schedule, supervisory status, duty-station geography (state / city / county / CBSA), age bracket, education level, length of service, veteran status, appointment type, and a `count` field.

**`accessions − separations = net flow`** — the cleanest measure of whether the federal workforce (or any slice of it) is growing or shrinking.

## No credentials required

The FWD API is public. There is nothing to configure, no key, no signup. The helper scripts cache downloaded Parquet under `~/.cache/opm-fwd/` (override with `$OPM_FWD_CACHE`).

## Setup

Python deps (once):

```bash
pip install -r "$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"   # requests, pandas, pyarrow
```

All scripts live in `$CLAUDE_PLUGIN_ROOT/scripts/`. When running outside the plugin, use the repo's `scripts/` path.

## Core flows

### 1. Orient — what's the latest data?

```bash
python3 scripts/fwd.py latest accessions      # e.g. "accessions: 2026-05 (version 1)"
python3 scripts/fwd.py list accessions --year 2026 --current-only
```

### 2. Inspect the schema / sample rows

```bash
python3 scripts/fwd.py schema accessions 2026 5     # all 68 columns + dtypes
python3 scripts/fwd.py head   accessions 2026 5 -n 5
```

### 3. Net-flow time series (the headline capability)

```bash
# Whole federal workforce, monthly net flow
python3 scripts/netflow.py --start 2023-01 --end 2026-05

# Tech/data occupational series, broken out by series
python3 scripts/netflow.py --start 2024-01 --end 2026-05 \
    --series 2210,1550,1560,1515,1530 --by occupational_series --out netflow_tech.csv

# STEM occupations at one department
python3 scripts/netflow.py --start 2025-01 --end 2026-05 --stem --agency-code VA

# Is the trend entry-level or senior? Break out by age bracket
python3 scripts/netflow.py --start 2025-01 --end 2026-05 --by age_bracket
```

`--by COL` gives one row per (month, value); omit it for one net number per month. Filters (`--series`, `--agency-code`, `--stem`, `--where COL=VAL`) apply to both hires and separations before aggregation.

### 4. Discover codes (series, agencies, categories)

```bash
python3 scripts/lookup.py accessions 2026 5 occupational_series --top 30
python3 scripts/lookup.py separations 2026 5 separation --top 20     # separation_category codes
python3 scripts/lookup.py accessions 2026 5 agency --top 40
```

### 5. Custom analysis in Python

```python
import sys; sys.path.insert(0, "scripts")
import fwd
df = fwd.load("accessions", 2026, 5)     # DataFrame; `count` numeric, series code zero-padded
df.groupby("occupational_series")["count"].sum().sort_values(ascending=False).head()
```

## Data gotchas (learned the hard way — read before analyzing)

- **`count` is stored as a string.** `fwd.load()` coerces it to numeric; if you read the Parquet directly with pandas, do `pd.to_numeric(df["count"])` first or `sum()` will string-concatenate.
- **Strong seasonality.** May–July accessions are dominated by seasonal hiring at Interior/USDA (wildland fire management `0456`, forestry technician `0462`, park ranger `0025`). **Never compare raw month-over-month** — compare year-over-year, or use the full series. Single-month snapshots mislead.
- **Occupational series codes are 4-char zero-padded** (`0610` Nurse, `2210` IT Management, `1560` Data Science, `0456` Wildland Fire). `fwd.load()` zero-pads `occupational_series_code`.
- **Separation categories** (`separation_category_code`): `SC` quit, `SD` voluntary retirement, `SJ` termination/expired appt, `SA` transfer out, `SH` **reduction in force (RIF)**, `SE` early-out retirement. Use these to distinguish voluntary attrition from involuntary cuts.
- **Multiple versions per month.** Each file has a `version`; the row flagged `current: true` is the canonical release. `fwd.py` resolves `current` automatically. Older months tend to top out at v2, recent months at v1.
- **Watch for reporting-driven spikes.** Large administrative events (e.g. fiscal-year-end mass separations tied to deferred-resignation programs) can put a huge outlier in a single month. Inspect `separation_category` before attributing a spike to organic attrition.
- **`employment` is a snapshot, not a flow.** Don't difference two employment months and expect it to equal net accessions−separations; coverage and as-of timing differ.
- **This is federal civilian employment only** — not the whole US labor market, not the military, not federal contractors. For private-sector or macro comparisons, pair it with another source (e.g. BLS).

## Reference

- [docs/getting-started.md](../../docs/getting-started.md) — first request, cache, deps
- [docs/data-dictionary.md](../../docs/data-dictionary.md) — key columns and coded fields
- Official API: <https://data.opm.gov/get-data/api-access>
- FWD platform: <https://data.opm.gov>
