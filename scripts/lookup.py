"""Discover the value space of any FWD column (codes, names, and counts).

The FWD datasets use dozens of coded dimensions — occupational series, agencies,
pay plans, locality-pay areas, education levels. This helper aggregates one
column (and its `_code` sibling if present) for a given month so you can find
the exact codes to pass to netflow.py --series / --agency-code / --where.

Examples
--------
  lookup.py accessions 2026 5 occupational_series --top 30
  lookup.py separations 2026 5 agency --top 40
  lookup.py accessions 2026 5 age_bracket
  lookup.py accessions 2026 5 separation --top 20     # partial column match ok
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwd  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("dataset", choices=fwd.DATASETS)
    p.add_argument("year", type=int)
    p.add_argument("month", type=int)
    p.add_argument("column", help="Column name (or unique substring of one)")
    p.add_argument("--top", type=int, default=25)
    args = p.parse_args(argv)

    df = fwd.load(args.dataset, args.year, args.month)

    if args.column not in df.columns:
        matches = [c for c in df.columns if args.column.lower() in c.lower() and not c.endswith("_code")]
        if len(matches) == 1:
            args.column = matches[0]
        elif matches:
            sys.stderr.write(f"ambiguous column {args.column!r}; matches: {matches}\n")
            return 1
        else:
            sys.stderr.write(f"no column matching {args.column!r}\n")
            return 1

    code_col = f"{args.column}_code"
    group = [args.column] + ([code_col] if code_col in df.columns else [])
    agg = (
        df.groupby(group, dropna=False)["count"]
        .sum()
        .sort_values(ascending=False)
        .head(args.top)
    )
    total = int(df["count"].sum())
    print(f"{args.dataset} {args.year}-{args.month:02d}: top {args.top} of {args.column} (total count {total:,})\n")
    for key, cnt in agg.items():
        if isinstance(key, tuple):
            name, code = key[0], key[1]
            print(f"  {str(code):>8}  {int(cnt):>7,}  {name}")
        else:
            print(f"  {int(cnt):>7,}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
