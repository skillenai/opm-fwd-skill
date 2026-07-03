"""Build a federal-workforce net-flow time series from the OPM FWD API.

Net flow = accessions (hires) - separations (departures), the cleanest single
measure of whether the federal workforce is growing or shrinking. This script
sweeps a month range, optionally filters and/or groups by any column, and emits
a tidy long CSV plus a printed summary.

Examples
--------
  # Total workforce net flow, Jan 2024 - May 2026
  netflow.py --start 2024-01 --end 2026-05

  # Tech/data occupational series only, broken out by series
  netflow.py --start 2024-01 --end 2026-05 \
      --series 2210,1550,1560,1515,1530 --by occupational_series

  # STEM occupations at one department
  netflow.py --start 2025-01 --end 2026-05 --stem --agency-code VA

  # Net flow by age bracket (is the rebound entry-level or senior?)
  netflow.py --start 2025-01 --end 2026-05 --by age_bracket --out age.csv

Filters (--series, --agency-code, --stem, --where COL=VAL) are applied to both
accessions and separations before aggregation. `--by COL` produces one row per
(month, COL value); omit it for a single net number per month.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd  # noqa: E402


def month_range(start: str, end: str) -> list[tuple[int, int]]:
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def apply_filters(df, args):
    if args.series:
        codes = {c.strip().zfill(4) for c in args.series.split(",")}
        df = df[df["occupational_series_code"].isin(codes)]
    if args.agency_code:
        df = df[df["agency_code"] == args.agency_code]
    if args.stem:
        df = df[df.get("stem_occupation") == "STEM OCCUPATIONS"]
    for clause in args.where or []:
        col, _, val = clause.partition("=")
        df = df[df[col] == val]
    return df


def aggregate_month(dataset, y, m, args) -> dict:
    """Return {group_value: count} for one month/dataset after filtering."""
    df = fwd.load(dataset, y, m)
    df = apply_filters(df, args)
    if args.by:
        g = df.groupby(args.by)["count"].sum()
        return {str(k): int(v) for k, v in g.items()}
    return {"__all__": int(df["count"].sum())}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--start", required=True, help="YYYY-MM inclusive")
    p.add_argument("--end", required=True, help="YYYY-MM inclusive")
    p.add_argument("--by", help="Column to group by (e.g. occupational_series, agency, age_bracket)")
    p.add_argument("--series", help="Comma-separated occupational_series_code filter")
    p.add_argument("--agency-code", help="Filter to one agency_code (e.g. VA, TR, HE)")
    p.add_argument("--stem", action="store_true", help="STEM occupations only")
    p.add_argument("--where", action="append", metavar="COL=VAL", help="Extra equality filter (repeatable)")
    p.add_argument("--out", type=Path, help="Write tidy long CSV here")
    args = p.parse_args(argv)

    months = month_range(args.start, args.end)
    records = []
    for y, m in months:
        acc = aggregate_month("accessions", y, m, args)
        sep = aggregate_month("separations", y, m, args)
        keys = set(acc) | set(sep)
        for k in keys:
            a, s = acc.get(k, 0), sep.get(k, 0)
            records.append(
                {
                    "month": f"{y}-{m:02d}",
                    "group": None if k == "__all__" else k,
                    "accessions": a,
                    "separations": s,
                    "net": a - s,
                }
            )
        tot_a = sum(acc.values())
        tot_s = sum(sep.values())
        sys.stderr.write(f"  {y}-{m:02d}: hires {tot_a:>7,}  seps {tot_s:>7,}  net {tot_a - tot_s:>+8,}\n")

    import pandas as pd

    out_df = pd.DataFrame.from_records(records)
    if args.by:
        out_df = out_df.sort_values(["month", "net"], ascending=[True, False])
    else:
        out_df = out_df.drop(columns=["group"]).sort_values("month")

    if args.out:
        out_df.to_csv(args.out, index=False)
        sys.stderr.write(f"\nwrote {args.out} ({len(out_df)} rows)\n")

    with pd.option_context("display.max_rows", 400, "display.width", 160):
        print(out_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
