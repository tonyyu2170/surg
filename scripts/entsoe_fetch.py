# scripts/entsoe_fetch.py
"""Pull ENTSO-E 6.1.A load and 12.1.D day-ahead price into data/raw/entsoe/.

Constraints that shape this script live in docs/entsoe-api-constraints.md and
docs/plans/2026-08-12-entsoe-ireland-design.md. The four that matter:

  * "No data" is HTTP 200 + reason 999. Every body must be parsed; the status
    code alone cannot distinguish data from emptiness.
  * Over-cap is HTTP 400 carrying an exact count, never a silent truncation.
    The response to a 400 is to halve the window, not to paginate -- offset is
    honoured on only 20 of 77 endpoints and is silently ignored elsewhere.
  * The rate limit is 400 req/min PER TOKEN and tripping it earns a temporary
    ban; the vendor also reserves the right to revoke. We pace at ~5 req/s
    (the docs' own recommendation is 6-7) and STOP on 429 rather than retry.
    The token took 3 working days to obtain and gates this whole thread.
  * Raw storage is parsed-but-UNEXPANDED, so A03 expansion can be re-run and
    re-tested without re-pulling.

Idempotent: re-runs skip any target already on disk. Partial writes go to
.part and are renamed only on success.

Usage: .venv/bin/python scripts/entsoe_fetch.py [--items load,price] [--zones IE_CTA,NL]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surg.acquisition.entsoe_parse import parse_response
from surg.preprocessing.entsoe_zones import YEARS, zones_for

API = "https://web-api.tp.entsoe.eu/api"
RAW = Path("data/raw/entsoe")
MANIFEST = RAW / "manifest.csv"
SLEEP_S = 0.2  # ~5 req/s, under the documented 6-7 rec.
TIMEOUT_S = 300.0  # vendor request timeout is 5 minutes

ITEM_PARAMS = {
    "load": {"documentType": "A65", "processType": "A16"},
    "price": {"documentType": "A44"},
    # 14.1.A Installed Generation Capacity per Type, psrType B16 = Solar.
    # This is the H_solar DOSE. It is deliberately NOT 16.1.B&C actual solar
    # generation (A75): measured 2026-08-12, the Dutch A75 feed peaks at 204 MW
    # on a June day against 27,980 MW of A68 installed capacity, because most
    # Dutch PV is distributed and invisible to the TSO -- while the German A75
    # peaks at 24,393 MW against 77,016 MW installed and clearly does include
    # distributed PV. A75 solar is therefore NOT comparable across countries,
    # and using it as the dose would score the Netherlands, one of the densest
    # PV fleets on earth, as a near-zero-solar market. A68 matches the national
    # figure and is the only ENTSO-E series here that includes behind-the-meter.
    "capacity": {"documentType": "A68", "processType": "A33", "psrType": "B16"},
}

# A68 is one ANNUAL document. A multi-year window is rejected with HTTP 400 and
# fetch_year's halving splitter is meaningless on it, so it gets its own window.
ANNUAL_ITEMS = frozenset({"capacity"})


def api_key() -> str:
    for line in Path(".env").read_text().splitlines():
        if line.startswith("ENTSOE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ENTSOE_API_KEY not found in .env")


def domain_params(item: str, eic: str) -> dict[str, str]:
    if item == "load":
        return {"outBiddingZone_Domain": eic}
    if item == "capacity":
        # A68 takes in_Domain alone; sending out_Domain too is a different query.
        return {"in_Domain": eic}
    return {"in_Domain": eic, "out_Domain": eic}


def fetch_window(
    client: httpx.Client, item: str, eic: str, start: str, end: str
) -> tuple[str, list[dict], str]:
    """Fetch one window. Returns (outcome, period_records, note).

    outcome is one of: "data", "no_data", "over_cap", "error".
    """
    params = {
        **ITEM_PARAMS[item],
        **domain_params(item, eic),
        "periodStart": start,
        "periodEnd": end,
    }
    resp = client.get(API, params=params, timeout=TIMEOUT_S)
    time.sleep(SLEEP_S)

    if resp.status_code == 429:
        sys.exit(
            "HTTP 429 -- rate limited. STOPPING rather than retrying: the "
            "vendor reserves the right to revoke a misused token. Wait ~10 "
            "minutes and re-run; the pull is idempotent."
        )
    if resp.status_code == 400:
        return "over_cap", [], resp.text[:300].replace("\n", " ")
    if resp.status_code != 200:
        return "error", [], f"HTTP {resp.status_code}: {resp.text[:200]}"

    result = parse_response(resp.text)
    if result.kind == "no_data":
        return "no_data", [], f"reason {result.reason_code}: {result.reason_text}"
    return "data", result.periods, ""


def fetch_year(
    client: httpx.Client, item: str, eic: str, year: int
) -> tuple[str, list[dict], str]:
    """Fetch one calendar year, halving the window if the API rejects on size."""
    if item in ANNUAL_ITEMS:
        # One annual document: no size cap to hit, and nothing to split.
        outcome, periods, detail = fetch_window(
            client, item, eic, f"{year}01010000", f"{year}12310000"
        )
        return outcome, periods, detail

    windows = [(f"{year}01010000", f"{year + 1}01010000")]
    collected: list[dict] = []
    note = ""
    while windows:
        start, end = windows.pop(0)
        outcome, periods, detail = fetch_window(client, item, eic, start, end)
        if outcome == "over_cap":
            mid = (
                pd.Timestamp(start, tz="UTC")
                + (pd.Timestamp(end, tz="UTC") - pd.Timestamp(start, tz="UTC")) / 2
            ).floor("D")
            mid_s = mid.strftime("%Y%m%d%H%M")
            if mid_s in (start, end):
                return "error", collected, f"cannot split further: {detail}"
            windows[:0] = [(start, mid_s), (mid_s, end)]
            note = "split on over-cap"
            continue
        if outcome == "error":
            return "error", collected, detail
        if outcome == "no_data":
            note = note or detail
            continue
        collected.extend(periods)
    if not collected:
        return "no_data", [], note
    return "data", collected, note


def to_frame(periods: list[dict], zone_key: str, item: str) -> pd.DataFrame:
    rows = []
    for p in periods:
        for position, value in p["points"]:
            rows.append(
                {
                    "zone": zone_key,
                    "item": item,
                    "doc_start": p["doc_start"],
                    "doc_end": p["doc_end"],
                    "resolution": p["resolution"],
                    "curve_type": p["curve_type"],
                    "position": position,
                    "value": value,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="load,price")
    ap.add_argument("--zones", default="", help="comma-separated zone keys; default all")
    ap.add_argument("--years", default="", help="comma-separated years; default all")
    args = ap.parse_args()

    items = args.items.split(",")
    year_list = [int(y) for y in args.years.split(",")] if args.years else list(YEARS)
    manifest_rows = []

    client = httpx.Client(params={"securityToken": api_key()}, follow_redirects=True)
    for item in items:
        candidates = zones_for(item)
        if args.zones:
            wanted = set(args.zones.split(","))
            candidates = [z for z in candidates if z.key in wanted]
        for zone in candidates:
            dest_dir = RAW / item / zone.key
            dest_dir.mkdir(parents=True, exist_ok=True)
            for year in year_list:
                dest = dest_dir / f"{year}.parquet"
                if dest.exists():
                    print(f"  skip (exists): {item}/{zone.key}/{year}")
                    continue
                outcome, periods, note = fetch_year(client, item, zone.eic, year)
                frame = to_frame(periods, zone.key, item)
                if outcome == "data" and not frame.empty:
                    part = dest.with_suffix(".parquet.part")
                    frame.to_parquet(part, index=False)
                    part.rename(dest)
                resolutions = sorted(frame["resolution"].unique()) if not frame.empty else []
                print(f"  {item}/{zone.key}/{year}: {outcome} rows={len(frame)} {resolutions}")
                manifest_rows.append(
                    {
                        "item": item,
                        "zone": zone.key,
                        "eic": zone.eic,
                        "year": year,
                        "outcome": outcome,
                        "n_rows": len(frame),
                        "resolutions": ";".join(resolutions),
                        "note": note,
                    }
                )
    client.close()

    if manifest_rows:
        new = pd.DataFrame(manifest_rows)
        if MANIFEST.exists():
            new = pd.concat([pd.read_csv(MANIFEST), new], ignore_index=True)
            new = new.drop_duplicates(subset=["item", "zone", "year"], keep="last")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        new.to_csv(MANIFEST, index=False)
        print(f"\nmanifest -> {MANIFEST} ({len(new)} rows)")


if __name__ == "__main__":
    main()
