"""Separation-rate time series by category (quits, RIF, retirements) as % of headcount.

Net flow (accessions - separations) tells you if a workforce is growing. This
tells you *how* people leave — the split between voluntary mobility (quits),
involuntary loss (reduction in force), and retirements — as an annualized rate
against a headcount base. That distinction is the difference between "stable"
and "stuck", and between "secure" and "laid off".

Separation category codes: SC quit · SD retirement (voluntary) · SE early-out
retirement · SG other retirement · SJ termination · SA/SB transfer out ·
SH reduction-in-force (RIF) · SL other.

Examples
--------
  # Quit vs RIF rate for tech series, monthly, over two years
  rates.py --start 2024-01 --end 2026-05 --series 2210,1550,1560 --categories SC,SH

  # Retirement rate for one agency
  rates.py --start 2025-01 --end 2026-05 --agency-code VA --categories SD,SE

Headcount base defaults to the employment snapshot at --base-month (default the
range's first month); pass a fixed month to hold the denominator constant.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd  # noqa: E402


def month_range(start, end):
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out, y, m = [], sy, sm
    while (y, m) <= (ey, em):
        out.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def filtered(df, series, agency):
    if series:
        codes = {c.strip().zfill(4) for c in series.split(",")}
        df = df[df["occupational_series_code"].isin(codes)]
    if agency:
        df = df[df["agency_code"] == agency]
    return df


def main(argv=None) -> int:
    import pandas as pd

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", required=True, help="YYYY-MM")
    p.add_argument("--end", required=True, help="YYYY-MM")
    p.add_argument("--series", help="Comma-separated occupational_series_code filter")
    p.add_argument("--agency-code", help="Filter to one agency_code")
    p.add_argument("--categories", default="SC,SH,SD", help="Separation category codes (default SC,SH,SD)")
    p.add_argument("--base-month", help="YYYY-MM for the fixed headcount denominator (default: first month)")
    p.add_argument("--out", type=Path, help="Write CSV here")
    args = p.parse_args(argv)

    months = month_range(args.start, args.end)
    cats = [c.strip() for c in args.categories.split(",")]
    by, bm = (args.base_month or args.start).split("-")
    base_df = filtered(fwd.load("employment", int(by), int(bm)), args.series, args.agency_code)
    base = int(base_df["count"].sum())
    if base == 0:
        sys.stderr.write("error: headcount base is 0 for this filter\n")
        return 1

    rows = []
    for y, m in months:
        d = filtered(fwd.load("separations", y, m), args.series, args.agency_code)
        rec = {"month": f"{y}-{m:02d}"}
        for c in cats:
            n = int(d[d["separation_category_code"] == c]["count"].sum())
            rec[f"{c}_n"] = n
            rec[f"{c}_rate_ann_pct"] = 100 * n * 12 / base
        rows.append(rec)
    out = pd.DataFrame(rows)
    if args.out:
        out.to_csv(args.out, index=False)
        sys.stderr.write(f"wrote {args.out}\n")
    sys.stderr.write(f"(headcount base {int(by)}-{int(bm):02d} = {base:,})\n")
    with pd.option_context("display.max_rows", 400, "display.width", 160):
        print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
