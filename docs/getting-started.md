# Getting Started

The OPM Federal Workforce Data (FWD) API is public — no account, no key, no rate-limit signup.

## 1. Make a request by hand

List available accessions files:

```bash
curl -s "https://data.opm.gov/api/v1/files/accessions" | python3 -m json.tool | head
```

Each entry looks like:

```json
{"filename": "accessions_202605_1", "publishDate": "…", "version": 1, "current": true, "month": "05", "year": "2026"}
```

Download one month (Parquet):

```bash
curl -sL "https://data.opm.gov/api/v1/files/accessions/2026/05/1/download" -o accessions_202605.parquet
```

The path is `/api/v1/files/{dataset}/{year}/{month}/{version}/download`, where `{version}` is the integer version (use the one flagged `current: true` in the file listing).

## 2. Use the helper scripts (recommended)

```bash
pip install -r scripts/requirements.txt     # requests, pandas, pyarrow

python3 scripts/fwd.py latest accessions     # newest available month
python3 scripts/fwd.py schema accessions 2026 5
python3 scripts/netflow.py --start 2024-01 --end 2026-05
```

`fwd.py` resolves the `current` version for you, downloads to a local cache, and (via `fwd.load`) hands back a pandas DataFrame with `count` already numeric.

## 3. Caching

Downloaded Parquet is cached under `~/.cache/opm-fwd/` so multi-month sweeps and repeat runs don't re-download. Override the location:

```bash
export OPM_FWD_CACHE=/path/to/cache
```

A full 2015→present accessions+separations sweep is a few hundred MB; individual months are 60 KB–1 MB each.

## 4. Datasets at a glance

| Dataset | Meaning | Earliest |
|---------|---------|----------|
| `employment` | Headcount snapshot | 2005 |
| `accessions` | Hires | 2015 |
| `separations` | Departures | 2015 |

For net flow, use `accessions` and `separations`. `employment` is a stock (level); the other two are flows.
