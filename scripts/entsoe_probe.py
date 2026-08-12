# scripts/entsoe_probe.py
"""Probe three undocumented/contradictory ENTSO-E REST API behaviours.

Usage:
    .venv/bin/python scripts/entsoe_probe.py              # probes A + B, rate probe dry-run
    .venv/bin/python scripts/entsoe_probe.py --hard       # ...and actually trip the rate limit

Everything in docs/sources/entsoe-api-constraints.md is vendor documentation, not
measurement. This script measures the three things that file flags as
needing a live check:

  A. Case sensitivity. The docs say parameter names are case-sensitive, yet
     ENTSO-E's own Postman collection ships the same parameter spelled two
     ways (curveType/curvetype, contract_MarketAgreement.Type/.type). Both
     spellings cannot be right if the rule holds.
  B. `offset` pagination. Documented on 20 of 77 Postman endpoints, absent
     from the Zendesk parameter reference. If real, it turns the
     100-TimeSeries response cap into a pagination stride.
  C. The 400 req/min limit, its window shape, and the "approximately 10
     minutes" unban interval -- which is pasted support-ticket text, not spec.

Probe C is destructive to *our own* token: tripping the limit earns a
temporary ban (vendor says ~10 min, automatic). It therefore requires an
explicit --hard flag, and runs LAST so that a ban cannot invalidate A and B.
We hold exactly one token; a ban blocks every probe.

All three probes use 12.1.D Energy Prices or 6.1.A Actual Total Load, both
cheap. Raw per-request traces are written to the findings JSON before any
interpretation, so a mid-run ban still leaves evidence on disk.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

BASE = "https://web-api.tp.entsoe.eu/api"
TIMEOUT_S = 60.0
OUT = Path("outputs/entsoe_probe")

# 12.1.D Energy Prices. Ships contract_MarketAgreement.type (lowercase t),
# classificationSequence_...position (lowercase p), offset and curveType --
# three of the five casing conflicts plus the pagination parameter, on one
# endpoint. DE-LU is densely populated.
DE_LU = "10Y1001A1001A82H"
CZ = "10YCZ-CEPS-----N"

PRICE_BASE = {
    "documentType": "A44",
    "out_Domain": DE_LU,
    "in_Domain": DE_LU,
}

# Rate-probe defaults. 450 > 400 so the threshold lands inside the run.
RATE_N = 450
RATE_WORKERS = 12
UNBAN_POLL_S = 30
UNBAN_MAX_S = 1200


def api_key() -> str:
    key = os.environ.get("ENTSOE_API_KEY")
    if not key:
        sys.exit("ENTSOE_API_KEY not set -- source .env first")
    return key


def redact(text: str, key: str) -> str:
    """Strip the security token out of anything we print or persist."""
    return text.replace(key, "<TOKEN>") if key else text


def localname(tag: str) -> str:
    """'{urn:...}GL_MarketDocument' -> 'GL_MarketDocument'."""
    return tag.rsplit("}", 1)[-1]


@dataclass
class Reply:
    """Classified API response. The root element, not the status code, says
    whether a request was accepted: 'no matching data' comes back as HTTP 200
    carrying an Acknowledgement with reason 999."""

    status: int
    root: str = ""
    reason_code: str = ""
    reason_text: str = ""
    n_timeseries: int = 0
    n_zip_entries: int = 0
    mrids: list[str] = field(default_factory=list)
    intervals: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def accepted(self) -> bool:
        return (
            self.root.endswith("_MarketDocument")
            and self.root != "Acknowledgement_MarketDocument"
        )

    def summary(self) -> str:
        if self.error and not self.root:
            return f"HTTP {self.status} transport-error: {self.error}"
        if self.root == "Acknowledgement_MarketDocument":
            return f"HTTP {self.status} REJECTED ({self.reason_code}: {self.reason_text})"
        if self.root == "ZIP":
            return f"HTTP {self.status} ACCEPTED <ZIP> {self.n_zip_entries} XML documents"
        if self.accepted:
            return f"HTTP {self.status} ACCEPTED <{self.root}> {self.n_timeseries} TimeSeries"
        return f"HTTP {self.status} <{self.root or '?'}>"

    @property
    def size(self) -> int:
        """Whichever unit this endpoint's cap is expressed in."""
        return self.n_zip_entries if self.root == "ZIP" else self.n_timeseries


def call(client: httpx.Client, params: dict[str, str], key: str) -> Reply:
    """One GET. Never raises; classification lives in the returned Reply."""
    q = dict(params)
    q["securityToken"] = key
    try:
        r = client.get(BASE, params=q)
    except Exception as exc:  # noqa: BLE001 -- a probe must survive transport failures
        return Reply(status=0, error=type(exc).__name__)

    out = Reply(status=r.status_code)
    if r.status_code == 429:
        out.root = "RATE_LIMITED"
        return out

    # Outage endpoints answer with a ZIP of XML documents; their cap is
    # expressed in documents, not TimeSeries, so count entries.
    if r.content[:2] == b"PK":
        out.root = "ZIP"
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                out.n_zip_entries = len(zf.namelist())
        except zipfile.BadZipFile as exc:
            out.error = str(exc)[:200]
        return out

    body = r.text
    if not body.lstrip().startswith("<"):
        out.root = "NON_XML"
        return out

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        out.root = "PARSE_ERROR"
        out.error = str(exc)[:200]
        return out

    out.root = localname(root.tag)
    for el in root.iter():
        name = localname(el.tag)
        if name == "TimeSeries":
            out.n_timeseries += 1
            for child in el:
                if localname(child.tag) == "mRID" and child.text:
                    out.mrids.append(child.text.strip())
                    break
        elif name == "code" and not out.reason_code:
            out.reason_code = (el.text or "").strip()
        elif name == "text" and not out.reason_text:
            out.reason_text = (el.text or "").strip()[:200]

    # timeInterval start/end pairs, for the contiguity check in probe B.
    for el in root.iter():
        if localname(el.tag) == "timeInterval":
            start = end = ""
            for child in el:
                if localname(child.tag) == "start":
                    start = (child.text or "").strip()
                elif localname(child.tag) == "end":
                    end = (child.text or "").strip()
            if start or end:
                out.intervals.append(f"{start}/{end}")

    return out


def _clean(rep: Reply) -> dict:
    """Reply as a dict without the bulky mRID list."""
    return {k: v for k, v in asdict(rep).items() if k != "mrids"}


# --------------------------------------------------------------------------
# Probe A -- case sensitivity
# --------------------------------------------------------------------------

def probe_case(client: httpx.Client, key: str) -> dict:
    """Do the casing conflicts in ENTSO-E's own collection actually work?

    The docs say 'Parameter names are case sensitive.' If true, exactly one
    spelling of each conflicting pair should be accepted.

    The trap: an unknown parameter appears to be *silently ignored* rather
    than rejected. So "renamed param was accepted" is ambiguous on its own --
    it could mean the new spelling was understood, or that it was dropped and
    the request happened to still be valid. Two discriminators settle it:

      * DISCRIMINATOR-1 sends only `DocumentType` (no lowercase form). If the
        rename were ignored, the mandatory documentType would be missing and
        the request must be rejected. Acceptance proves the rename was read.
      * DISCRIMINATOR-2 sends `DocumentType=A65` (load) against price domains.
        If the rename is read, the response must change or fail; if it is
        dropped, we would fall back to the A44 in the lowercase key.
    """
    window = {"periodStart": "202406010000", "periodEnd": "202406020000"}
    base = PRICE_BASE | window
    no_doctype = {k: v for k, v in base.items() if k != "documentType"}

    variants = [
        ("baseline (no optional params)", base),
        ("curveType=A03  [Postman spelling A]", base | {"curveType": "A03"}),
        ("curvetype=A03  [Postman spelling B]", base | {"curvetype": "A03"}),
        (
            "contract_MarketAgreement.type=A01  [as shipped on 12.1.D]",
            base | {"contract_MarketAgreement.type": "A01"},
        ),
        (
            "contract_MarketAgreement.Type=A01  [Zendesk reference spelling]",
            base | {"contract_MarketAgreement.Type": "A01"},
        ),
        ("DISCRIMINATOR-1 DocumentType=A44 only, no lowercase form",
         no_doctype | {"DocumentType": "A44"}),
        ("DISCRIMINATOR-2 DocumentType=A65 (load) only, on price domains",
         no_doctype | {"DocumentType": "A65"}),
        ("documenttype=A44 only (all lowercase)", no_doctype | {"documenttype": "A44"}),
        ("CONTROL mandatory documentType omitted entirely", no_doctype),
        ("CONTROL unknown param bogusParam=xyz alongside valid query",
         base | {"bogusParam": "xyz"}),
        ("VALUE casing: documentType=a44 (lowercase value)", no_doctype | {"documentType": "a44"}),
    ]

    print("\n=== PROBE A: case sensitivity (12.1.D Energy Prices, DE-LU) ===")
    results = []
    for label, params in variants:
        rep = call(client, params, key)
        print(f"  {label}\n      -> {rep.summary()}")
        results.append({"variant": label, **_clean(rep)})
        time.sleep(0.3)
    return {"probe": "case_sensitivity", "results": results}


# --------------------------------------------------------------------------
# Probe B -- offset pagination
# --------------------------------------------------------------------------

def probe_offset(client: httpx.Client, key: str) -> dict:
    """How does `offset` actually behave?

    First run showed the documented "maximum 100 TimeSeries per response" does
    NOT bind on 12.1.D: omitting offset returned 732 TimeSeries for 2024,
    while offset=100 and offset=200 each returned exactly 100. So we test
    `offset` absent vs `offset=0` explicitly -- if they differ, the parameter
    does not merely paginate, it *switches on* the 100-item cap.
    """
    year = {"periodStart": "202401010000", "periodEnd": "202412310000"}
    base = PRICE_BASE | year

    print("\n=== PROBE B: offset pagination (12.1.D Energy Prices, DE-LU, 2024) ===")
    no_off = call(client, base, key)
    print(f"  offset absent   -> {no_off.summary()}")
    time.sleep(0.5)

    pages: dict[int, Reply] = {}
    for off in (0, 100, 200, 700):
        rep = call(client, base | {"offset": str(off)}, key)
        pages[off] = rep
        print(f"  offset={off:<4}     -> {rep.summary()}")
        time.sleep(0.5)

    findings: dict[str, object] = {
        "n_without_offset": no_off.n_timeseries,
        "n_with_offset_0": pages[0].n_timeseries,
    }
    findings["offset_switches_on_cap"] = (
        no_off.n_timeseries > 100 and pages[0].n_timeseries == 100
    )
    if findings["offset_switches_on_cap"]:
        print(
            f"    ! omitting offset returns ALL {no_off.n_timeseries} TimeSeries; "
            f"offset=0 returns {pages[0].n_timeseries}. The documented 100-cap "
            "binds only when offset is supplied."
        )

    # NB: TimeSeries mRID is a *document-local* counter ("1".."100"), reissued
    # from 1 on every page -- it is NOT a stable identifier and is useless for
    # dedup across pages. Key on timeInterval instead.
    p0 = pages[0]
    for off in (100, 200, 700):
        rep = pages[off]
        if not rep.accepted:
            findings[f"offset_{off}"] = "rejected"
            continue
        overlap = set(p0.intervals) & set(rep.intervals)
        findings[f"offset_{off}_n"] = rep.n_timeseries
        findings[f"offset_{off}_interval_overlap_with_page0"] = len(overlap)
        verdict = "DISJOINT from page0" if not overlap else f"OVERLAPS page0 on {len(overlap)}"
        print(f"    offset={off}: {rep.n_timeseries} TimeSeries, {verdict}")

    # Do the pages tile the full set, or is content duplicated/dropped?
    union = set(p0.intervals) | set(pages[100].intervals) | set(pages[200].intervals)
    findings["distinct_intervals_across_first_3_pages"] = len(union)
    print(f"    union of offsets 0/100/200 = {len(union)} distinct intervals")
    if no_off.intervals:
        covered = union <= set(no_off.intervals)
        findings["pages_are_subset_of_full_response"] = covered
        print(f"    all paged intervals present in the un-offset response: {covered}")
    # Tail check: last page should complete the set exactly.
    tail = pages[700]
    if tail.accepted:
        findings["tail_offset_plus_count"] = 700 + tail.n_timeseries
        findings["tail_matches_total"] = (700 + tail.n_timeseries) == no_off.n_timeseries
        print(
            f"    tail: offset=700 + {tail.n_timeseries} returned = "
            f"{700 + tail.n_timeseries} vs {no_off.n_timeseries} total "
            f"-> {'EXACT' if findings['tail_matches_total'] else 'MISMATCH'}"
        )

    # Contiguity: page 1 should begin where page 0 ended, not restart.
    if p0.intervals and pages[100].intervals:
        print(f"    page0 first interval : {p0.intervals[0]}")
        print(f"    page0 last  interval : {p0.intervals[-1]}")
        print(f"    page1 first interval : {pages[100].intervals[0]}")
        findings["page0_last_interval"] = p0.intervals[-1]
        findings["page1_first_interval"] = pages[100].intervals[0]

    # Negative case: is `offset` global, or only on the endpoints that document it?
    load = {
        "documentType": "A65",
        "processType": "A16",
        "outBiddingZone_Domain": CZ,
        "periodStart": "202406010000",
        "periodEnd": "202406020000",
    }
    plain = call(client, load, key)
    time.sleep(0.3)
    offset_on_load = call(client, load | {"offset": "100"}, key)
    print("\n  Negative case -- offset on 6.1.A, where Postman does NOT document it:")
    print(f"    without offset  -> {plain.summary()}")
    print(f"    with offset=100 -> {offset_on_load.summary()}")
    findings["undocumented_endpoint_plain"] = plain.summary()
    findings["undocumented_endpoint_with_offset"] = offset_on_load.summary()

    return {
        "probe": "offset",
        "pages": {str(o): _clean(r) for o, r in pages.items()},
        "findings": findings,
    }


# --------------------------------------------------------------------------
# Probe D -- does the offset/cap behaviour generalise beyond 12.1.D?
# --------------------------------------------------------------------------

def probe_cap_generality(client: httpx.Client, key: str) -> dict:
    """Is 'omitting offset lifts the cap' a rule, or a 12.1.D quirk?

    Probe B found 12.1.D returns all 732 TimeSeries when offset is omitted,
    despite a documented 100 cap. Two readings fit that single endpoint:
    (a) offset switches the cap on, generally; or (b) 12.1.D's cap was simply
    raised, and offset=0 returning 100 is ordinary pagination.

    Discriminate by repeating absent-vs-offset=0 on endpoints with a
    *different* documented cap unit: 13.1.A (100 TimeSeries, plain XML) and
    10.1.A&B (200 XML documents inside a ZIP).
    """
    year = {"periodStart": "202401010000", "periodEnd": "202412300000"}
    cases = [
        (
            "13.1.A Redispatching Internal, NL (doc cap: 100 TimeSeries)",
            {"documentType": "A63", "businessType": "A85",
             "out_Domain": "10YNL----------L", "in_Domain": "10YNL----------L"} | year,
            100,
        ),
        (
            "10.1.A&B Transmission Unavailability, FR>BE (doc cap: 200 documents)",
            {"documentType": "A78", "Out_Domain": "10YFR-RTE------C",
             "In_Domain": "10YBE----------2"} | year,
            200,
        ),
    ]

    print("\n=== PROBE D: does the cap behaviour generalise? ===")
    results = []
    for label, params, doc_cap in cases:
        absent = call(client, params, key)
        time.sleep(0.5)
        zero = call(client, params | {"offset": "0"}, key)
        time.sleep(0.5)
        print(f"  {label}")
        print(f"      offset absent -> {absent.summary()}")
        print(f"      offset=0      -> {zero.summary()}")

        verdict = "inconclusive"
        if absent.status == 200 and zero.status == 200:
            if absent.size > doc_cap and zero.size == doc_cap:
                verdict = "switch_on_confirmed"
            elif absent.size == doc_cap:
                verdict = "cap_binds_without_offset (12.1.D is an exception)"
            elif absent.size == zero.size:
                verdict = f"no_difference (both {absent.size}; set smaller than cap?)"
        print(f"      -> {verdict}")
        results.append({
            "endpoint": label, "documented_cap": doc_cap,
            "n_without_offset": absent.size, "n_with_offset_0": zero.size,
            "verdict": verdict,
            "status_absent": absent.status, "status_offset0": zero.status,
        })

    return {"probe": "cap_generality", "results": results}


# --------------------------------------------------------------------------
# Probe C -- rate limit (destructive: bans our own token)
# --------------------------------------------------------------------------

def probe_rate(client: httpx.Client, key: str, n: int, armed: bool) -> dict:
    """Find where the 400/min limit actually bites, and how long the ban lasts.

    Not run unless armed. A dry run prints the plan and sends nothing.
    """
    cheap = {
        "documentType": "A65",
        "processType": "A16",
        "outBiddingZone_Domain": CZ,
        "periodStart": "202406010000",
        "periodEnd": "202406010100",
    }

    print("\n=== PROBE C: rate limit ===")
    if not armed:
        print(
            f"  DRY RUN -- nothing sent.\n"
            f"  Would fire {n} requests at {RATE_WORKERS} workers against 6.1.A (1 MTU of CZ load),\n"
            f"  record (index, elapsed, status) per request, then poll every {UNBAN_POLL_S}s\n"
            f"  for up to {UNBAN_MAX_S // 60} min to measure the unban interval.\n"
            f"  This WILL temporarily ban the token (vendor: ~10 min, automatic).\n"
            f"  Arm it with:  .venv/bin/python scripts/entsoe_probe.py --hard"
        )
        return {"probe": "rate_limit", "mode": "dry_run", "planned_requests": n}

    print(f"  ARMED: firing {n} requests, {RATE_WORKERS} workers. Expect a ban.")
    t0 = time.monotonic()

    def one(i: int) -> dict:
        started = time.monotonic() - t0
        rep = call(client, cheap, key)
        return {
            "i": i,
            "t_start": round(started, 3),
            "t_end": round(time.monotonic() - t0, 3),
            "status": rep.status,
            "root": rep.root,
        }

    with ThreadPoolExecutor(max_workers=RATE_WORKERS) as pool:
        trace = list(pool.map(one, range(n)))

    trace.sort(key=lambda r: r["t_start"])
    # Persist the raw trace before interpreting anything -- a ban mid-run must
    # still leave evidence on disk.
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rate_trace.json").write_text(json.dumps(trace, indent=1))

    limited = [r for r in trace if r["status"] == 429]
    ok = [r for r in trace if r["status"] == 200]
    print(f"  sent={len(trace)}  ok={len(ok)}  429={len(limited)}")

    out: dict[str, object] = {
        "probe": "rate_limit",
        "mode": "armed",
        "n_sent": len(trace),
        "n_ok": len(ok),
        "n_429": len(limited),
        "trace_file": str(OUT / "rate_trace.json"),
    }

    if not limited:
        print(
            f"  No 429 in {len(trace)} requests over "
            f"{trace[-1]['t_end']:.1f}s -- limit not reached at this rate."
        )
        out["verdict"] = "limit_not_reached"
        return out

    first = limited[0]
    n_ok_before = sum(1 for r in ok if r["t_start"] < first["t_start"])
    print(
        f"  First 429 at request index {first['i']} "
        f"({n_ok_before} successful requests before it), t={first['t_start']:.2f}s"
    )
    out["first_429_index"] = first["i"]
    out["successes_before_first_429"] = n_ok_before
    out["first_429_elapsed_s"] = first["t_start"]
    # A fixed 60s window trips near 400 within the first minute; a rolling
    # window trips ~400 behind a moving cursor. The two imply different throttles.
    out["window_hint"] = (
        "consistent_with_fixed_60s_window"
        if first["t_start"] <= 60 and 380 <= n_ok_before <= 420
        else "does_not_match_naive_400_per_fixed_minute"
    )
    print(f"  window: {out['window_hint']}")

    print(f"  Polling every {UNBAN_POLL_S}s for unban (max {UNBAN_MAX_S // 60} min)...")
    ban_start = time.monotonic()
    while time.monotonic() - ban_start < UNBAN_MAX_S:
        time.sleep(UNBAN_POLL_S)
        rep = call(client, cheap, key)
        waited = time.monotonic() - ban_start
        print(f"    t+{waited:6.0f}s -> HTTP {rep.status}")
        if rep.status != 429:
            out["unban_after_s"] = round(waited, 1)
            out["unban_after_min"] = round(waited / 60, 2)
            print(f"  Unbanned after ~{waited / 60:.1f} min (vendor says ~10).")
            return out

    out["unban_after_s"] = f">{UNBAN_MAX_S}"
    print(f"  Still limited after {UNBAN_MAX_S // 60} min -- gave up polling.")
    return out


def write_findings(findings: list, key: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "findings.json"
    dest.write_text(redact(json.dumps(findings, indent=1), key))
    return dest


class Tee:
    """Mirror stdout into the durable run log -- the printed verdicts are the
    readable record, and job scratch dirs do not survive."""

    def __init__(self, stream, sink) -> None:
        self.stream, self.sink = stream, sink

    def write(self, s: str) -> int:
        self.stream.write(s)
        self.sink.write(s)
        return len(s)

    def flush(self) -> None:
        self.stream.flush()
        self.sink.flush()


def main() -> None:
    ap = argparse.ArgumentParser(description="Probe live ENTSO-E API behaviour.")
    ap.add_argument(
        "--hard",
        action="store_true",
        help="arm the rate-limit probe; WILL temporarily ban the token (~10 min)",
    )
    ap.add_argument("--n", type=int, default=RATE_N, help=f"rate-probe requests (default {RATE_N})")
    args = ap.parse_args()

    key = api_key()
    findings: list = []

    OUT.mkdir(parents=True, exist_ok=True)
    log = (OUT / "run.txt").open("w")
    sys.stdout = Tee(sys.__stdout__, log)  # type: ignore[assignment]

    with httpx.Client(timeout=TIMEOUT_S, follow_redirects=True) as client:
        # A and B first, always: they are ~11 requests and must not be
        # invalidated by a ban from C.
        findings.append(probe_case(client, key))
        findings.append(probe_offset(client, key))
        findings.append(probe_cap_generality(client, key))
        print(f"\n  probes A/B/D written to {write_findings(findings, key)}")

        findings.append(probe_rate(client, key, args.n, args.hard))

    print(f"\nFindings written to {write_findings(findings, key)}")
    print(f"Run log written to {OUT / 'run.txt'}")
    sys.stdout = sys.__stdout__  # type: ignore[assignment]
    log.close()


if __name__ == "__main__":
    main()
