"""Client + local cache for the OPM Federal Workforce Data (FWD) API.

The FWD API is a public, **no-authentication** REST service published by the
U.S. Office of Personnel Management at https://data.opm.gov. It exposes three
person-level federal-civilian-workforce datasets as Parquet files, one file per
month (employment is also available monthly):

  employment   headcount snapshots (who is on the rolls)
  accessions   hires / onboarding events
  separations  departures / offboarding events

Accessions minus separations is a clean *net-flow* measure of how the federal
workforce is growing or shrinking, sliceable by agency, occupational series,
grade, pay, geography, age, education, and more (68 columns).

CLI
---
  fwd.py list accessions [--year 2026] [--current-only]
  fwd.py latest accessions
  fwd.py download accessions 2026 5 [--version current|N] [--out PATH] [--force]
  fwd.py schema accessions 2026 5
  fwd.py head accessions 2026 5 [-n 5]

Importable API
--------------
  from fwd import list_files, latest, download, load
  df = load("accessions", 2026, 5)          # -> pandas.DataFrame, `count` numeric
  path = download("separations", 2026, 5)    # -> cached local Parquet path

Files are cached under $OPM_FWD_CACHE (default ~/.cache/opm-fwd/) so repeated
runs and multi-month sweeps don't re-download.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://data.opm.gov/api/v1/files"
DATASETS = ("employment", "accessions", "separations")
USER_AGENT = "opm-fwd-skill/0.1 (+https://github.com/skillenai/opm-fwd-skill)"


def cache_dir() -> Path:
    d = Path(os.environ.get("OPM_FWD_CACHE", Path.home() / ".cache" / "opm-fwd"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get(url: str, *, stream: bool = False, retries: int = 4) -> requests.Response:
    """GET with polite retry/backoff. The API is unauthenticated and generally
    fast, but transient 5xx / connection resets happen on large sweeps."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                url, stream=stream, timeout=120, headers={"User-Agent": USER_AGENT}
            )
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:  # noqa: PERF203
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError(f"GET {url} failed after {retries} attempts")


def list_files(dataset: str) -> list[dict]:
    """Return the raw file listing for a dataset.

    Each entry: {filename, publishDate, version:int, current:bool, month:str, year:str}
    """
    _check_dataset(dataset)
    return _get(f"{BASE_URL}/{dataset}").json()


def _check_dataset(dataset: str) -> None:
    if dataset not in DATASETS:
        raise ValueError(f"dataset must be one of {DATASETS}, got {dataset!r}")


def resolve_version(dataset: str, year: int, month: int, version="current") -> int:
    """Resolve a concrete integer version for (dataset, year, month).

    version="current" -> the row flagged current==true (the canonical release).
    version=N (int/str) -> that exact version.
    """
    rows = [
        r
        for r in list_files(dataset)
        if int(r["year"]) == int(year) and int(r["month"]) == int(month)
    ]
    if not rows:
        raise LookupError(f"No {dataset} file for {year}-{int(month):02d}")
    if version == "current":
        cur = [r for r in rows if r.get("current")]
        chosen = cur[0] if cur else max(rows, key=lambda r: int(r["version"]))
        return int(chosen["version"])
    want = int(version)
    for r in rows:
        if int(r["version"]) == want:
            return want
    raise LookupError(
        f"No {dataset} {year}-{int(month):02d} version {want} "
        f"(available: {sorted(int(r['version']) for r in rows)})"
    )


def latest(dataset: str) -> tuple[int, int, int]:
    """Return (year, month, version) of the most recent *current* file."""
    rows = [r for r in list_files(dataset) if r.get("current")]
    if not rows:
        rows = list_files(dataset)
    r = max(rows, key=lambda x: (int(x["year"]), int(x["month"]), int(x["version"])))
    return int(r["year"]), int(r["month"]), int(r["version"])


def download(
    dataset: str,
    year: int,
    month: int,
    version="current",
    *,
    out: Path | None = None,
    force: bool = False,
) -> Path:
    """Download one month of a dataset to the local cache and return its path."""
    _check_dataset(dataset)
    ver = resolve_version(dataset, year, month, version)
    dest = out or (cache_dir() / f"{dataset}_{int(year)}{int(month):02d}_v{ver}.parquet")
    dest = Path(dest)
    if dest.exists() and not force and dest.stat().st_size > 0:
        return dest
    url = f"{BASE_URL}/{dataset}/{int(year)}/{int(month):02d}/{ver}/download"
    resp = _get(url, stream=True)
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if chunk:
                fh.write(chunk)
    tmp.replace(dest)
    return dest


def load(dataset: str, year: int, month: int, version="current"):
    """Download (if needed) and read one month into a pandas DataFrame.

    The API stores `count` as a string; it is coerced to a numeric column here
    so callers can sum it directly. `occupational_series_code` is zero-padded to
    4 chars for stable joins/filters.
    """
    import pandas as pd

    path = download(dataset, year, month, version)
    df = pd.read_parquet(path)
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
    if "occupational_series_code" in df.columns:
        df["occupational_series_code"] = (
            df["occupational_series_code"].astype(str).str.zfill(4)
        )
    return df


# --------------------------------------------------------------------------- CLI


def _cmd_list(args) -> None:
    rows = list_files(args.dataset)
    if args.year:
        rows = [r for r in rows if int(r["year"]) == args.year]
    if args.current_only:
        rows = [r for r in rows if r.get("current")]
    rows.sort(key=lambda r: (int(r["year"]), int(r["month"]), int(r["version"])))
    for r in rows:
        flag = "current" if r.get("current") else ""
        print(f"{r['year']}-{int(r['month']):02d}  v{r['version']:<2} {flag:8} {r['filename']}")
    print(f"\n{len(rows)} file(s)")


def _cmd_latest(args) -> None:
    y, m, v = latest(args.dataset)
    print(f"{args.dataset}: {y}-{m:02d} (version {v})")


def _cmd_download(args) -> None:
    path = download(
        args.dataset, args.year, args.month, args.version, out=args.out, force=args.force
    )
    size = path.stat().st_size
    print(f"{path}  ({size:,} bytes)")


def _cmd_schema(args) -> None:
    df = load(args.dataset, args.year, args.month, args.version)
    print(f"{args.dataset} {args.year}-{args.month:02d}: {df.shape[0]:,} rows, {df.shape[1]} cols\n")
    for c in df.columns:
        print(f"  {c:<45} {str(df[c].dtype)}")


def _cmd_head(args) -> None:
    df = load(args.dataset, args.year, args.month, args.version)
    import pandas as pd

    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df.head(args.n).to_string())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="List available files for a dataset")
    pl.add_argument("dataset", choices=DATASETS)
    pl.add_argument("--year", type=int)
    pl.add_argument("--current-only", action="store_true")
    pl.set_defaults(func=_cmd_list)

    pt = sub.add_parser("latest", help="Show the most recent available month")
    pt.add_argument("dataset", choices=DATASETS)
    pt.set_defaults(func=_cmd_latest)

    pd_ = sub.add_parser("download", help="Download one month to the local cache")
    pd_.add_argument("dataset", choices=DATASETS)
    pd_.add_argument("year", type=int)
    pd_.add_argument("month", type=int)
    pd_.add_argument("--version", default="current")
    pd_.add_argument("--out", type=Path)
    pd_.add_argument("--force", action="store_true")
    pd_.set_defaults(func=_cmd_download)

    ps = sub.add_parser("schema", help="Print columns + dtypes for one month")
    ps.add_argument("dataset", choices=DATASETS)
    ps.add_argument("year", type=int)
    ps.add_argument("month", type=int)
    ps.add_argument("--version", default="current")
    ps.set_defaults(func=_cmd_schema)

    ph = sub.add_parser("head", help="Print the first N rows of one month")
    ph.add_argument("dataset", choices=DATASETS)
    ph.add_argument("year", type=int)
    ph.add_argument("month", type=int)
    ph.add_argument("-n", type=int, default=5)
    ph.add_argument("--version", default="current")
    ph.set_defaults(func=_cmd_head)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (LookupError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
