"""Pull Pecan Street static bundles from JupyterHub into data/raw/pecanstreet/.

One-off acquisition (2026-08-13): the University Free tier stages the
2019/2021 static release plus a Sept-2023 Puerto Rico power-quality set
on JupyterHub at /shared/Dataport-Data. This fetches the csv.gz bundles
and small top-level files plus (second pull, same day) the Austin/NY
1-second series and the PR home metadata. Still skipped: the
.sqlite3/.tar.gz duplicates of the same data, and the pr_homes
per-metric files (byte-identical to the ones pulled above).

Idempotent: files whose local size matches the server manifest are
skipped, partial downloads resume via HTTP Range.

Usage: .venv/bin/python scripts/pecanstreet_fetch.py
"""
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

HUB = "https://jupyterhub.pecanstreet.org"  # per-user base is HUB/user/<JUPYTER_USER>
ROOT = "shared/Dataport-Data"
DEST = Path(__file__).resolve().parent.parent / "data" / "raw" / "pecanstreet"

# (relative path under Dataport-Data, expected bytes from contents API 2026-08-13)
MANIFEST = [
    ("README.txt", 286),
    ("audits_and_surveys.zip", 512535),
    ("ev_and_weather.zip", 6139119),
    ("indoor_temp_data.zip", 359109593),
    ("metadata.csv", 615582),
    ("metadata.sqlite3", 561152),
    ("project_specific_datasets.zip", 3652),
    ("electricity_data/Austin/15minute_data_austin.csv.gz", 23474368),
    ("electricity_data/Austin/1minute_data_austin.csv.gz", 263212725),
    ("electricity_data/California/15minute_data_california.csv.gz", 13987111),
    ("electricity_data/California/1minute_data_california.csv.gz", 171568626),
    ("electricity_data/New_York/15minute_data_newyork.csv.gz", 11931813),
    ("electricity_data/New_York/1minute_data_newyork.csv.gz", 126687335),
    ("electricity_data/puerto_rico/pr_15min/pr_angle_09-2023_15min.csv.gz", 1299312),
    ("electricity_data/puerto_rico/pr_15min/pr_apparentpower_09-2023_15min.csv.gz", 457970),
    ("electricity_data/puerto_rico/pr_15min/pr_current_09-2023_15min.csv.gz", 706176),
    ("electricity_data/puerto_rico/pr_15min/pr_realpower_09-2023_15min.csv.gz", 1010511),
    ("electricity_data/puerto_rico/pr_15min/pr_thd_09-2023_15min.csv.gz", 1265579),
    ("electricity_data/puerto_rico/pr_1min/pr_angle_09-2023_1min.csv.gz", 20441072),
    ("electricity_data/puerto_rico/pr_1min/pr_apparentpower_09-2023_1min.csv.gz", 5730643),
    ("electricity_data/puerto_rico/pr_1min/pr_current_09-2023_1min.csv.gz", 9826214),
    ("electricity_data/puerto_rico/pr_1min/pr_realpower_09-2023_1min.csv.gz", 13326123),
    ("electricity_data/puerto_rico/pr_1min/pr_thd_09-2023_1min.csv.gz", 19506553),
    # pr_angle 1sec is 20 bytes on the server (broken upload) -- pulled anyway to record the fact
    ("electricity_data/puerto_rico/pr_1sec/pr_angle_09-2023_1sec.csv.gz", 20),
    ("electricity_data/puerto_rico/pr_1sec/pr_apparentpower_09-2023_1sec.csv.gz", 270544640),
    ("electricity_data/puerto_rico/pr_1sec/pr_current_09-2023_1sec.csv.gz", 478394706),
    ("electricity_data/puerto_rico/pr_1sec/pr_realpower_09-2023_1sec.csv.gz", 524039308),
    ("electricity_data/puerto_rico/pr_1sec/pr_thd_09-2023_1sec.csv.gz", 539445918),
    # Extension 2026-08-13 (second pull): PR home metadata (identical copy exists in all
    # three pr_homes/* dirs; the rest of pr_homes duplicates the per-metric files above)
    ("electricity_data/puerto_rico/pr_homes/pr_15min/metadata.csv", 582590),
    # Extension 2026-08-13 (second pull): Austin + NY 1-second series
    ("electricity_data/Austin/1s_data_austin_file1.csv.gz", 3365429465),
    ("electricity_data/Austin/1s_data_austin_file2.csv.gz", 3543066220),
    ("electricity_data/Austin/1s_data_austin_file3.csv.gz", 3588052813),
    ("electricity_data/Austin/1s_data_austin_file4.csv.gz", 3415998855),
    ("electricity_data/New_York/1s_data_newyork_file1.csv.gz", 3408209546),
    ("electricity_data/New_York/1s_data_newyork_file2.csv.gz", 1165678682),
    ("electricity_data/New_York/1s_data_newyork_file3.csv.gz", 1119490960),
    ("electricity_data/New_York/1s_data_newyork_file4.csv.gz", 1086523215),
]


def pull(rel: str, expected: int, client: httpx.Client, headers: dict, base: str) -> str:
    dest = DEST / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == expected:
        return "skip (already complete)"
    part = dest.with_suffix(dest.suffix + ".part")
    offset = part.stat().st_size if part.exists() else 0
    req_headers = dict(headers)
    if offset:
        req_headers["Range"] = f"bytes={offset}-"
    url = f"{base}/files/{ROOT}/{rel}"
    mode = "ab" if offset else "wb"
    with client.stream("GET", url, headers=req_headers) as r:
        if offset and r.status_code != 206:
            # server ignored Range; restart from scratch
            mode = "wb"
        r.raise_for_status()
        with open(part, mode) as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    got = part.stat().st_size
    if got != expected:
        return f"SIZE MISMATCH: got {got}, expected {expected} (kept .part for resume)"
    part.rename(dest)
    return f"ok ({got:,} bytes)"


def main() -> int:
    load_dotenv()
    key = os.environ.get("JUPYTER_API_KEY")
    if not key:
        sys.exit("JUPYTER_API_KEY not set -- add it to .env first")
    user = os.environ.get("JUPYTER_USER")
    if not user:
        sys.exit("JUPYTER_USER not set -- the Dataport login email with punctuation stripped")
    base = f"{HUB}/user/{user}"
    headers = {"Authorization": f"token {key}"}
    total = len(MANIFEST)
    failures = 0
    with httpx.Client(timeout=httpx.Timeout(30.0, read=300.0), follow_redirects=True) as client:
        for i, (rel, expected) in enumerate(MANIFEST, 1):
            t0 = time.time()
            for attempt in (1, 2, 3):
                try:
                    status = pull(rel, expected, client, headers, base)
                    break
                except Exception as e:  # noqa: BLE001 - one-off script, log and retry
                    status = f"ERROR attempt {attempt}: {e!r}"
                    time.sleep(5 * attempt)
            if not status.startswith(("ok", "skip")):
                failures += 1
            print(f"[{i}/{total}] {rel}: {status} ({time.time() - t0:.0f}s)", flush=True)
    print(f"DONE failures={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
