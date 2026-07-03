# OPM Federal Workforce Data Skill

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill and Python toolkit for the **[OPM Federal Workforce Data (FWD) API](https://data.opm.gov/get-data/api-access)** — open, monthly, person-level data on the U.S. federal civilian workforce. **No API key required.**

## What it covers

The U.S. Office of Personnel Management publishes three federal-workforce datasets as monthly Parquet files:

- **`employment`** — headcount snapshots (who is on the rolls), back to 2005
- **`accessions`** — hires / onboarding events, back to 2015
- **`separations`** — departures / offboarding events, back to 2015

Each hire/departure record has **68 columns** — agency, occupational series, pay, grade, STEM flag, duty-station geography, age, education, veteran status, and more. Subtract separations from accessions and you get **net flow**: how the federal workforce is growing or shrinking, sliceable every which way.

## Install (Claude Code)

This skill is distributed through the **[`skillenai/labor-data-skills`](https://github.com/skillenai/labor-data-skills)** marketplace — a family of labor-market data skills. Add the marketplace, then install this plugin:

```
/plugin marketplace add skillenai/labor-data-skills
```

```
/plugin install opm-fwd@labor-data-skills
```

Run those as two separate slash commands, then restart Claude Code (or `/reload-plugins`). The plugin registers one skill:

- **`/opm-fwd:fwd`** — query federal workforce hires, separations, headcount, and net flow

Ask things like *"What's the net flow of the federal IT workforce over the last two years?"* or *"How many nurses did the VA hire last month?"*

## Use standalone (no Claude Code)

Everything here is just files. Clone it and run the scripts directly:

```bash
git clone https://github.com/skillenai/opm-fwd-skill.git
cd opm-fwd-skill
pip install -r scripts/requirements.txt        # requests, pandas, pyarrow

python3 scripts/fwd.py latest accessions
python3 scripts/netflow.py --start 2024-01 --end 2026-05
```

## Helper scripts

| Script | Purpose |
|--------|---------|
| `scripts/fwd.py` | API client + local Parquet cache. `list` / `latest` / `download` / `schema` / `head`. Importable (`fwd.load(dataset, year, month)`). |
| `scripts/netflow.py` | Build an accessions−separations net-flow time series over a month range, with filters and group-by. |
| `scripts/lookup.py` | Discover the codes/values of any column (occupational series, agencies, separation categories) for a month. |
| `scripts/pay.py` | Count-weighted pay percentiles (`annualized_adjusted_basic_pay`) by any grouping — role, agency, age. |
| `scripts/rates.py` | Separation-rate time series by category — voluntary quits vs involuntary RIF vs retirements, as annualized % of headcount. |

Run any script with `--help`. Downloads are cached under `~/.cache/opm-fwd/` (override with `$OPM_FWD_CACHE`).

## Quick example

```bash
# Federal tech/data workforce net flow, by occupational series
python3 scripts/netflow.py --start 2024-01 --end 2026-05 \
    --series 2210,1550,1560,1515,1530 --by occupational_series
```

## Documentation

- [docs/getting-started.md](docs/getting-started.md) — first request, caching, dependencies
- [docs/data-dictionary.md](docs/data-dictionary.md) — key columns and coded fields
- [skills/fwd/SKILL.md](skills/fwd/SKILL.md) — the full skill instructions, common flows, and data gotchas

## Data source & attribution

Data is published by the U.S. Office of Personnel Management at [data.opm.gov](https://data.opm.gov). This project is an independent open-source client and is not affiliated with or endorsed by OPM. Federal workforce data is in the public domain; this wrapper code is MIT-licensed.

## Part of the Labor Data Skills family

This is one of several labor-market data skills curated by [Skillenai](https://skillenai.com) under [`skillenai/labor-data-skills`](https://github.com/skillenai/labor-data-skills). Others cover the Skillenai Data Products API and (planned) BLS and workforce-movement data.

## License

MIT — see [LICENSE](LICENSE).
