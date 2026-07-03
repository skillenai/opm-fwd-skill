"""Count-weighted pay percentiles for federal workforce data, by any grouping.

`annualized_adjusted_basic_pay` is base pay including locality adjustment (it
excludes bonus, TSP match, and incentives). Each row carries a `count`, so
percentiles must be count-weighted — this helper does that correctly.

Examples
--------
  # Pay percentiles for one occupational series (incumbents)
  pay.py employment 2026 5 --series 1560

  # New-hire pay by series (accessions), several series at once
  pay.py accessions 2026 5 --series 2210,1550,1560 --by occupational_series

  # Pay by agency for US duty stations, custom percentiles
  pay.py employment 2026 5 --by agency --country US --percentiles 10,50,90
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd  # noqa: E402

PAY_COL = "annualized_adjusted_basic_pay"


def weighted_percentiles(df, col, pcts, weight="count"):
    df = df.dropna(subset=[col])
    df = df[(df[weight] > 0) & (df[col] > 0)]
    if df.empty:
        return {p: None for p in pcts}
    a = df.sort_values(col)
    cum = a[weight].cumsum()
    total = a[weight].sum()
    return {p: float(a.loc[cum >= p / 100 * total, col].iloc[0]) for p in pcts}


def main(argv=None) -> int:
    import pandas as pd

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset", choices=fwd.DATASETS)
    p.add_argument("year", type=int)
    p.add_argument("month", type=int)
    p.add_argument("--by", help="Column to group by (e.g. occupational_series, agency, age_bracket)")
    p.add_argument("--series", help="Comma-separated occupational_series_code filter")
    p.add_argument("--agency-code", help="Filter to one agency_code")
    p.add_argument("--country", help="Filter duty_station_country_code (e.g. US)")
    p.add_argument("--percentiles", default="25,50,75", help="Comma-separated (default 25,50,75)")
    args = p.parse_args(argv)

    df = fwd.load(args.dataset, args.year, args.month)
    df[PAY_COL] = pd.to_numeric(df[PAY_COL], errors="coerce")
    if args.series:
        codes = {c.strip().zfill(4) for c in args.series.split(",")}
        df = df[df["occupational_series_code"].isin(codes)]
    if args.agency_code:
        df = df[df["agency_code"] == args.agency_code]
    if args.country:
        df = df[df["duty_station_country_code"] == args.country]
    pcts = [int(x) for x in args.percentiles.split(",")]

    rows = []
    if args.by:
        for key, g in df.groupby(args.by):
            wp = weighted_percentiles(g, PAY_COL, pcts)
            rows.append({args.by: key, "n": int(g["count"].sum()), **{f"p{p}": wp[p] for p in pcts}})
        out = pd.DataFrame(rows).sort_values("n", ascending=False)
    else:
        wp = weighted_percentiles(df, PAY_COL, pcts)
        out = pd.DataFrame([{"n": int(df["count"].sum()), **{f"p{p}": wp[p] for p in pcts}}])

    with pd.option_context("display.max_rows", 200, "display.width", 160):
        print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
