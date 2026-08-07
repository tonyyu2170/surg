"""Download ERCOT annual load and RTM price archives.

Both are public: no API key, no quota. Verified 2026-08-07.

Load  : https://www.ercot.com/gridinfo/load/load_hist -> native_load_<YYYY>.zip
Price : GetReports.do?reportTypeId=13061             -> RTMLZHBSPP_<YYYY>.zip

Scope is narrower than the raw listings, per the plan ERRATA:

  * Load years >= 2017 (E2). ERCOT publishes four different schema families;
    only 2017 onward uses the zone names this project's ZONES constant
    expects. 2016 renames four zones and stores a Timestamp; 2015 and
    earlier are .xls needing xlrd, and pre-2003 files use 11 control areas.
  * Price years >= 2022 (E3). The panel discards everything before the
    DOM-matched window, so fetching 2010-2021 would download ~170 MB that
    no downstream step reads.

Filename case is inconsistent across years (`native_load_2017.zip`,
`Native_Load_2019.zip`), so the link regex is case-insensitive. Relying on
macOS's case-insensitive filesystem to paper over this would be an accident,
not correct code.

Usage: .venv/bin/python scripts/ercot_fetch.py
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import httpx

RAW = Path("data/raw/ercot")
LOAD_PAGE = "https://www.ercot.com/gridinfo/load/load_hist"
PRICE_LIST = "https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061"
DOWNLOAD = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"

FIRST_LOAD_YEAR = 2017
FIRST_PRICE_YEAR = 2022


def _get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url, timeout=300.0, follow_redirects=True)
    resp.raise_for_status()
    return resp


def fetch_load(client: httpx.Client, dest: Path) -> list[Path]:
    """Download each native_load_<YYYY>.zip from FIRST_LOAD_YEAR onward."""
    html = _get(client, LOAD_PAGE).text
    urls = sorted(set(re.findall(r'https://[^"]*?native_load_\d{4}\.zip', html, re.I)))
    if not urls:
        raise RuntimeError("no native_load zips found; ERCOT page layout changed")

    written = []
    for url in urls:
        year = int(re.search(r"(\d{4})\.zip$", url).group(1))
        if year < FIRST_LOAD_YEAR:
            continue
        out = dest / url.rsplit("/", 1)[-1]
        if not out.exists():
            out.write_bytes(_get(client, url).content)
        written.append(out)
        print(f"load  {out.name}")
    return written


def fetch_prices(client: httpx.Client, dest: Path) -> list[Path]:
    """Download RTMLZHBSPP_<YYYY>.zip archives from FIRST_PRICE_YEAR onward.

    The MIS listing pairs each filename with a doclookupId positionally.
    Pairing by proximity (e.g. `grep -B2`) mismatches rows, so both are
    extracted in document order and zipped together.
    """
    html = _get(client, PRICE_LIST).text
    names = re.findall(r"RTMLZHBSPP_(\d{4})\.zip", html)
    ids = re.findall(r"doclookupId=(\d+)", html)
    if len(names) != len(ids):
        raise RuntimeError(f"pairing mismatch: {len(names)} names vs {len(ids)} ids")

    written = []
    for year, doc_id in zip(names, ids):
        if int(year) < FIRST_PRICE_YEAR:
            continue
        out = dest / f"RTMLZHBSPP_{year}.zip"
        if not out.exists():
            out.write_bytes(_get(client, DOWNLOAD.format(doc_id)).content)
        written.append(out)
        print(f"price {out.name}")
    return written


def extract_all(paths: list[Path], dest: Path) -> None:
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            archive.extractall(dest)


def main() -> None:
    dest = RAW
    dest.mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        load_zips = fetch_load(client, dest)
        price_zips = fetch_prices(client, dest)
    extract_all(load_zips + price_zips, dest)
    print(f"\nextracted to {dest}")


if __name__ == "__main__":
    main()
