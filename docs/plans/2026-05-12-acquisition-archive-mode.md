# Acquisition archive-mode — implementation plan (Plan 1.5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `src/surg/acquisition/pull.py` to support PJM Data Miner 2 **Historic-tier** queries, enabling backfill of `rt_hrl_lmps` to before the 731-day archive cutoff. Then run the bulk historic pulls for the 9 EHV+ZONE target pnodes covering 2022-10-02 → 2024-05-11, fill the 13-day Standard-tier gap (2024-05-12 → 2024-05-25), and extend the reserve feeds to 2022-10-02 via the existing (non-archive) code path. End state: `data/raw/` has the full 3.6y joint analysis window populated (for 9 of 11 pnodes; Ashburn TX1/TX2 remain at the existing 2y by design — see `docs/decisions.md` 2026-05-12 § "Coverage choice (1a)").

**Architecture:** Three small extensions to existing modules — Pnode dataclass gains a `subtype` field, FeedSpec gains `supports_archive` flag, `_build_params` branches on an `archive_mode` arg (drops `pnode_id`, adds `type=<subtype>`, drops `sort/order`). Post-fetch client-side filter narrows historic results to the locked target pnode set. CLI gains `--archive-tier` and `--archive-subtype <EHV|ZONE|LOAD|...>` flags. The existing `date_chunks` helper already enforces calendar-year boundaries — no change needed there.

**Tech Stack:** Python 3.11+, pytest, httpx (existing). No new dependencies.

**Prerequisites:**
- Plan 1 ("acquisition reserve feeds extension") complete — current `_FEED_SPECS` covers six feeds; CLI accepts `--subzone` and `--locale`.
- 66 existing acquisition tests passing.
- `/etc/hosts` workaround for `api.pjm.com` is in place (`feedback_nu_dns_pjm.md`) so live API is reachable.
- `PJM_API_KEY` set in `.env` (verified by existing `surg-pull` runs).

**Prerequisite reading:**
- `docs/sources/pjm-api-constraints.md` § "Archived (Historic) data" — particularly the `type=pnode_subtype` clarification (2026-05-12) and the empirical Historic-tier volumes table.
- `docs/decisions.md` § "2026-05-12 — Window extension to 3.6y post-cap".

**Test discipline:** TDD throughout. Mock httpx transport for unit/integration tests (no live API in test suite). End-to-end live verification only in the bulk-pull tasks.

---

## File structure

```
src/surg/acquisition/
├── pull.py          # modify: FeedSpec, _build_params, pull_feed, CLI
├── targets.py       # modify: Pnode dataclass + pnode_ids_by_subtype helper

tests/acquisition/
├── test_targets.py        # modify: new tests for subtype helper
├── test_pull.py           # modify: new tests for _build_params + pull_feed archive branch
└── test_cli.py            # modify: new tests for --archive-tier flag
```

---

## Task 1: Add `subtype` to `Pnode` + `pnode_ids_by_subtype` helper

**Files:**
- Modify: `src/surg/acquisition/targets.py`
- Modify: `tests/acquisition/test_targets.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/acquisition/test_targets.py`:

```python
def test_pnode_has_subtype_field():
    from surg.acquisition.targets import PNODES
    # Every Pnode now carries a subtype matching the LMP feed's `type` column.
    for p in PNODES:
        assert hasattr(p, "subtype")
        assert p.subtype in {"EHV", "LOAD", "ZONE"}


def test_pnode_ids_by_subtype_ehv():
    from surg.acquisition.targets import pnode_ids_by_subtype
    ids = pnode_ids_by_subtype("EHV")
    assert set(ids) == {
        35010365, 35010371, 1356178195, 1356178171, 1356178181, 1356178201,
        35010369, 62871513,
    }


def test_pnode_ids_by_subtype_load():
    from surg.acquisition.targets import pnode_ids_by_subtype
    assert set(pnode_ids_by_subtype("LOAD")) == {34886139, 34886141}


def test_pnode_ids_by_subtype_zone():
    from surg.acquisition.targets import pnode_ids_by_subtype
    assert pnode_ids_by_subtype("ZONE") == [34964545]


def test_pnode_ids_by_subtype_unknown_returns_empty():
    from surg.acquisition.targets import pnode_ids_by_subtype
    assert pnode_ids_by_subtype("AGGREGATE") == []
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_targets.py -v
```

Expected: AttributeError / ImportError on `pnode_ids_by_subtype`.

- [ ] **Step 3: Implement**

Modify `src/surg/acquisition/targets.py`:

```python
Subtype = Literal["EHV", "LOAD", "ZONE"]


@dataclass(frozen=True, slots=True)
class Pnode:
    pnode_id: int
    name: str
    tier: Tier
    subtype: Subtype


PNODES: tuple[Pnode, ...] = (
    # Primary nodal — Loudoun-area transmission cluster (500 KV EHV)
    Pnode(35010365,   "LOUDOUN",            "primary_transmission", "EHV"),
    Pnode(35010371,   "PLEASANT VIEW",      "primary_transmission", "EHV"),
    Pnode(1356178195, "GOOSECRE",           "primary_transmission", "EHV"),
    Pnode(1356178171, "BRAMBLET",           "primary_transmission", "EHV"),
    Pnode(1356178181, "MOSBY",              "primary_transmission", "EHV"),
    Pnode(1356178201, "SKFFSCRK",           "primary_transmission", "EHV"),
    # Primary nodal — Ashburn distribution (35 KV LOAD)
    Pnode(34886139,   "ASHBURN 35 KV TX1",  "primary_distribution", "LOAD"),
    Pnode(34886141,   "ASHBURN 35 KV TX2",  "primary_distribution", "LOAD"),
    # Control / outside the Loudoun cluster
    Pnode(35010369,   "OX",                 "control", "EHV"),
    Pnode(62871513,   "BRISTERS",           "control", "EHV"),
    # DOM zonal baseline
    Pnode(34964545,   "DOM",                "zonal", "ZONE"),
)


def pnode_ids_by_subtype(subtype: str) -> list[int]:
    """Return pnode IDs for all targets matching the LMP-feed `type` value.

    Subtype is the `pnode_subtype` value as it appears in the
    rt_hrl_lmps response's `type` column. Used by Plan 1.5's
    archive-mode pull to client-side filter Historic-tier results.
    """
    return [p.pnode_id for p in PNODES if p.subtype == subtype]
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/acquisition/test_targets.py -v
```

Expected: All targets tests passing (existing + 5 new).

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 71 passed (66 + 5 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/targets.py tests/acquisition/test_targets.py
git commit -m "feat(acquisition): add Pnode subtype field and pnode_ids_by_subtype"
```

---

## Task 2: Extend `FeedSpec` with `supports_archive` flag

**Files:**
- Modify: `src/surg/acquisition/pull.py`
- Modify: `tests/acquisition/test_pull.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/acquisition/test_pull.py`:

```python
def test_feed_specs_mark_archive_support_correctly():
    from surg.acquisition.pull import _FEED_SPECS
    # Only the three LMP feeds support archive-tier queries.
    archive_feeds = {f for f, s in _FEED_SPECS.items() if s.supports_archive}
    assert archive_feeds == {"rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps"}


def test_feedspec_default_supports_archive_is_false():
    from surg.acquisition.pull import FeedSpec
    spec = FeedSpec("datetime_beginning_ept", "zone", False)
    assert spec.supports_archive is False
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_pull.py -k feed_spec -v
```

Expected: AttributeError on `supports_archive`.

- [ ] **Step 3: Implement**

In `src/surg/acquisition/pull.py`:

```python
@dataclass(frozen=True, slots=True)
class FeedSpec:
    """Per-feed metadata for API parameter construction.

    - date_field: column name used for range filter and sort
    - geo_filter_key: name of the geographic filter param (None means
      the feed has no geographic dimension)
    - is_lmp: True for LMP feeds (adds row_is_current=true to params)
    - supports_archive: True if the feed has a documented archive cutoff
      and Historic-tier queries with `type=<pnode_subtype>` work
    """
    date_field: str
    geo_filter_key: str | None
    is_lmp: bool
    supports_archive: bool = False


_FEED_SPECS: dict[str, FeedSpec] = {
    "rt_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),
    "da_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),
    "rt_fivemin_hrl_lmps":    FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),
    "hrl_load_metered":       FeedSpec("datetime_beginning_ept", "zone", False),
    "sync_reserve_events":    FeedSpec("event_start_ept", "synchronized_sub_zone", False),
    "reserve_market_results": FeedSpec("datetime_beginning_ept", "locale", False),
}
```

> Note: `rt_fivemin_hrl_lmps` is flagged `supports_archive=True` because PJM has an archive tier for it, but per `pjm-api-constraints.md` the `type` filter is **rejected** on Historic 5-min LMP. Plan 1.5 will not attempt 5-min archive pulls; the flag is for future-completeness only. Task 6's CLI validation rejects archive mode for `rt_fivemin_hrl_lmps`.

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/acquisition/test_pull.py -k feed_spec -v
```

Expected: 2 new tests passing.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 73 passed (71 + 2 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_pull.py
git commit -m "feat(acquisition): FeedSpec.supports_archive flag"
```

---

## Task 3: Branch `_build_params` for archive-mode

**Files:**
- Modify: `src/surg/acquisition/pull.py`
- Modify: `tests/acquisition/test_pull.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/acquisition/test_pull.py`:

```python
def test_build_params_archive_drops_pnode_id_and_sort():
    from datetime import date
    from surg.acquisition.pull import _build_params

    params = _build_params(
        "rt_hrl_lmps",
        date(2023, 1, 1), date(2023, 12, 31),
        geo_value=None,
        archive_mode=True,
        archive_subtype="EHV",
    )
    assert "pnode_id" not in params
    assert "sort" not in params
    assert "order" not in params
    assert params["type"] == "EHV"
    assert params["datetime_beginning_ept"].startswith("2023-01-01")
    assert params["row_is_current"] == "true"


def test_build_params_archive_requires_subtype_for_lmp():
    from datetime import date
    import pytest
    from surg.acquisition.pull import _build_params

    with pytest.raises(ValueError, match="archive_subtype is required"):
        _build_params(
            "rt_hrl_lmps",
            date(2023, 1, 1), date(2023, 12, 31),
            geo_value=None,
            archive_mode=True,
            archive_subtype=None,
        )


def test_build_params_archive_rejected_on_non_archive_feed():
    from datetime import date
    import pytest
    from surg.acquisition.pull import _build_params

    with pytest.raises(ValueError, match="does not support archive"):
        _build_params(
            "hrl_load_metered",
            date(2023, 1, 1), date(2023, 12, 31),
            geo_value="DOM",
            archive_mode=True,
            archive_subtype="LOAD",
        )


def test_build_params_standard_unchanged_when_archive_mode_false():
    """Regression: existing callers (archive_mode default False) get the
    same params they did before this task."""
    from datetime import date
    from surg.acquisition.pull import _build_params

    params = _build_params(
        "rt_hrl_lmps",
        date(2025, 6, 1), date(2025, 6, 30),
        geo_value=[35010365, 35010371],
    )
    assert params["pnode_id"] == "35010365;35010371"
    assert params["sort"] == "datetime_beginning_ept"
    assert params["order"] == "Asc"
    assert "type" not in params
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_pull.py -k build_params -v
```

Expected: TypeError or failures on missing archive_mode arg.

- [ ] **Step 3: Implement**

Modify `_build_params` in `src/surg/acquisition/pull.py`:

```python
def _build_params(
    feed: str,
    chunk_start: date,
    chunk_end: date,
    geo_value: Sequence[int] | str | None,
    *,
    archive_mode: bool = False,
    archive_subtype: str | None = None,
) -> dict[str, Any]:
    spec = _FEED_SPECS[feed]
    date_range = (
        f"{chunk_start.isoformat()} 00:00 to "
        f"{chunk_end.isoformat()} 23:59"
    )

    if archive_mode:
        if not spec.supports_archive:
            raise ValueError(
                f"feed {feed!r} does not support archive-tier queries"
            )
        if not archive_subtype:
            raise ValueError(
                f"archive_subtype is required for archive-mode pulls "
                f"(feed={feed!r})"
            )
        # Historic queries: no pnode_id filter, no sort/order, type filter only.
        params: dict[str, Any] = {
            spec.date_field: date_range,
            "type": archive_subtype,
        }
        if spec.is_lmp:
            params["row_is_current"] = "true"
        return params

    # Standard-tier path (unchanged).
    params = {
        spec.date_field: date_range,
        "sort": spec.date_field,
        "order": "Asc",
    }
    if spec.geo_filter_key is not None and geo_value is not None:
        if isinstance(geo_value, (list, tuple)):
            params[spec.geo_filter_key] = ";".join(str(p) for p in geo_value)
        else:
            params[spec.geo_filter_key] = geo_value
    if spec.is_lmp:
        params["row_is_current"] = "true"
    return params
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/acquisition/test_pull.py -k build_params -v
```

Expected: 4 new tests passing (plus existing build_params regression tests).

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 77 passed (73 + 4 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_pull.py
git commit -m "feat(acquisition): _build_params archive-mode branch"
```

---

## Task 4: Wire `archive_mode` through `pull_feed` (+ client-side filter)

**Files:**
- Modify: `src/surg/acquisition/pull.py`
- Modify: `tests/acquisition/test_pull.py`

- [ ] **Step 1: Write failing test (mock transport)**

Add to `tests/acquisition/test_pull.py`:

```python
def test_pull_feed_archive_mode_filters_to_target_pnodes(tmp_path):
    """Archive-mode pull keeps only rows matching the locked target IDs."""
    from datetime import date
    import httpx
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    # Mock returns 4 rows: 2 target EHV pnodes + 2 unrelated EHV pnodes.
    def handler(request: httpx.Request) -> httpx.Response:
        assert "pnode_id" not in request.url.params  # archive: no pnode filter
        assert request.url.params["type"] == "EHV"
        return httpx.Response(200, json={
            "totalRows": 4,
            "items": [
                {"pnode_id": 35010365, "pnode_name": "LOUDOUN",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 10.0, "total_lmp_rt": 50.0},
                {"pnode_id": 35010371, "pnode_name": "PLEASANT VIEW",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 12.0, "total_lmp_rt": 52.0},
                {"pnode_id": 99999999, "pnode_name": "RANDOM",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 1.0, "total_lmp_rt": 41.0},
                {"pnode_id": 88888888, "pnode_name": "OTHER",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 2.0, "total_lmp_rt": 42.0},
            ],
        })

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(handler),
    )
    paths = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2023, 6, 15), end=date(2023, 6, 15),
        archive_mode=True,
        archive_subtype="EHV",
        target_pnode_ids=[35010365, 35010371],  # filter to these
        group_label="dom_targets_archive_ehv",
        client=client,
        data_root=tmp_path,
    )
    assert len(paths) == 1
    import pandas as pd
    df = pd.read_parquet(paths[0])
    assert len(df) == 2
    assert set(df["pnode_id"]) == {35010365, 35010371}


def test_pull_feed_archive_mode_rejects_standard_geo_kwargs(tmp_path):
    """If archive_mode is set, callers should not pass pnode_ids/zone/etc."""
    from datetime import date
    import httpx
    import pytest
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            "totalRows": 0, "items": []
        })),
    )
    with pytest.raises(ValueError, match="pnode_ids|zone|subzone|locale"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2023, 6, 15), end=date(2023, 6, 15),
            archive_mode=True,
            archive_subtype="EHV",
            target_pnode_ids=[35010365],
            pnode_ids=[35010365],  # ← should error: not allowed with archive
            group_label="dom_targets_archive_ehv",
            client=client,
            data_root=tmp_path,
        )
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_pull.py -k archive -v
```

Expected: TypeError on unknown `archive_mode` kwarg.

- [ ] **Step 3: Implement**

Modify `pull_feed` in `src/surg/acquisition/pull.py`:

```python
def pull_feed(
    feed: str,
    start: date,
    end: date,
    *,
    pnode_ids: Sequence[int] | None = None,
    zone: str | None = None,
    subzone: str | None = None,
    locale: str | None = None,
    archive_mode: bool = False,
    archive_subtype: str | None = None,
    target_pnode_ids: Sequence[int] | None = None,
    group_label: str,
    client: PJMClient,
    data_root: Path,
    force: bool = False,
    max_days_per_chunk: int = 366,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Standard mode (archive_mode=False, default): exactly one of
    (pnode_ids, zone, subzone, locale) must be truthy, matching the
    feed's FeedSpec.geo_filter_key.

    Archive mode (archive_mode=True, LMP feeds only): drops the
    pnode_id filter and adds type=<archive_subtype>. After fetch,
    filters rows to `target_pnode_ids` (defensive client-side filter
    to keep only the locked target pnodes, since Historic returns all
    pnodes of that subtype).
    """
    if feed not in _FEED_SPECS:
        raise ValueError(f"unknown feed: {feed!r}")
    spec = _FEED_SPECS[feed]

    if archive_mode:
        # Reject the standard geo kwargs.
        for name, val in [("pnode_ids", pnode_ids), ("zone", zone),
                          ("subzone", subzone), ("locale", locale)]:
            if val:
                raise ValueError(
                    f"archive_mode=True is incompatible with {name}=…; "
                    f"use target_pnode_ids for client-side filtering"
                )
        if not target_pnode_ids:
            raise ValueError(
                "archive_mode=True requires target_pnode_ids "
                "(client-side filter for the locked target set)"
            )
        if not spec.supports_archive:
            raise ValueError(f"feed {feed!r} does not support archive-tier queries")
        target_set = set(target_pnode_ids)

        written: list[Path] = []
        for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
            if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
                continue
            params = _build_params(
                feed, chunk_start, chunk_end, geo_value=None,
                archive_mode=True, archive_subtype=archive_subtype,
            )
            rows = list(client.get_feed(feed, params))
            df = pd.DataFrame(rows)
            if not df.empty and "pnode_id" in df.columns:
                df = df[df["pnode_id"].isin(target_set)].reset_index(drop=True)
            path = write_chunk(
                data_root=data_root, feed=feed, group_label=group_label,
                chunk_start=chunk_start, chunk_end=chunk_end, df=df,
            )
            written.append(path)
        return written

    # Standard-mode path (unchanged from current implementation) follows…
    [existing standard-mode body]
```

Keep the existing standard-mode body intact below the archive branch.

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/acquisition/test_pull.py -v
```

Expected: 2 new tests passing, no regressions.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 79 passed (77 + 2 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_pull.py
git commit -m "feat(acquisition): pull_feed archive-mode with client-side pnode filter"
```

---

## Task 5: CLI flags `--archive-tier` and `--archive-subtype`

**Files:**
- Modify: `src/surg/acquisition/pull.py`
- Modify: `tests/acquisition/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/acquisition/test_cli.py`:

```python
def test_cli_archive_tier_requires_subtype(monkeypatch, capsys):
    from surg.acquisition.pull import main
    monkeypatch.setenv("PJM_API_KEY", "test")
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier",
        # missing --archive-subtype
        "--group-label", "dom_targets_archive_ehv",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "--archive-subtype" in err


def test_cli_archive_tier_rejected_for_non_lmp_feed(monkeypatch, capsys):
    from surg.acquisition.pull import main
    monkeypatch.setenv("PJM_API_KEY", "test")
    rc = main([
        "--feed", "hrl_load_metered",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier", "--archive-subtype", "LOAD",
        "--zone", "DOM",
        "--group-label", "dom",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "archive" in err.lower()


def test_cli_archive_tier_rejected_for_5min_lmp(monkeypatch, capsys):
    """5-min LMP rejects the `type` filter on Historic — not workable."""
    from surg.acquisition.pull import main
    monkeypatch.setenv("PJM_API_KEY", "test")
    rc = main([
        "--feed", "rt_fivemin_hrl_lmps",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier", "--archive-subtype", "EHV",
        "--group-label", "dom_targets_archive_ehv",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "5-min" in err.lower() or "fivemin" in err.lower()
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_cli.py -k archive -v
```

Expected: unknown-argument errors.

- [ ] **Step 3: Implement**

Modify `_build_arg_parser` and `main` in `src/surg/acquisition/pull.py`:

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    # ... existing args ...
    p.add_argument("--archive-tier", action="store_true",
                   help="Use Historic-tier query semantics (drops pnode_id, "
                        "adds type=<archive-subtype>; for LMP feeds with "
                        "data older than the archive cutoff).")
    p.add_argument("--archive-subtype",
                   help="pnode_subtype value for archive queries "
                        "(AGGREGATE / EHV / EXT / GEN / HUB / INTERFACE / "
                        "LOAD / RESIDUAL_METERED_EDC / TIE / ZONE).")
    return p
```

In `main`, before the existing geo-kwarg validation:

```python
    if args.archive_tier:
        if not args.archive_subtype:
            print("--archive-subtype is required when --archive-tier is set",
                  file=sys.stderr)
            return 2
        spec = _FEED_SPECS[args.feed]
        if not spec.supports_archive:
            print(f"feed '{args.feed}' does not support archive-tier queries",
                  file=sys.stderr)
            return 2
        if args.feed == "rt_fivemin_hrl_lmps":
            print("rt_fivemin_hrl_lmps Historic tier rejects the type filter "
                  "(see docs/sources/pjm-api-constraints.md); archive-tier pull is "
                  "not workable for this feed.", file=sys.stderr)
            return 2
        # Standard geo kwargs should be unset.
        for name, val in [("zone", args.zone), ("subzone", args.subzone),
                          ("locale", args.locale)]:
            if val:
                print(f"--{name} is not valid with --archive-tier "
                      f"(archive uses --archive-subtype + client-side "
                      f"filter to locked target set)", file=sys.stderr)
                return 2
        # Resolve target IDs from targets.py.
        from surg.acquisition.targets import pnode_ids_by_subtype
        target_pnode_ids = pnode_ids_by_subtype(args.archive_subtype)
        if not target_pnode_ids:
            print(f"No target pnodes have subtype={args.archive_subtype!r}; "
                  f"check src/surg/acquisition/targets.py", file=sys.stderr)
            return 2
        # ... call pull_feed with archive_mode=True, target_pnode_ids=...
        # (replace the standard-mode pull_feed call below for this branch)
```

Then in the `with PJMClient(...)` block, dispatch to the archive path or the standard path based on `args.archive_tier`.

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/acquisition/test_cli.py -v
```

Expected: 3 new tests passing.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 84 passed (81 + 3 new).

- [ ] **Step 6: Smoke the CLI**

```
.venv/bin/surg-pull --help
```

Expected: `--archive-tier` and `--archive-subtype` show in the help text.

- [ ] **Step 7: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_cli.py
git commit -m "feat(acquisition): --archive-tier and --archive-subtype CLI flags"
```

---

## Task 6: End-to-end integration test (archive-mode CLI → disk)

**Files:**
- Modify: `tests/acquisition/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/acquisition/test_cli.py`:

```python
def test_cli_archive_pull_end_to_end(monkeypatch, tmp_path):
    """Mock-transport end-to-end: archive CLI pull → parquet on disk filtered to targets."""
    import httpx
    import pandas as pd
    from surg.acquisition.pull import main

    # Mock returns 3 rows: 1 target EHV, 2 unrelated.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "totalRows": 3,
            "items": [
                {"pnode_id": 35010365, "pnode_name": "LOUDOUN",
                 "datetime_beginning_ept": "2023-06-15T03:00:00", "type": "EHV",
                 "congestion_price_rt": 10.0, "total_lmp_rt": 50.0},
                {"pnode_id": 999, "pnode_name": "X",
                 "datetime_beginning_ept": "2023-06-15T03:00:00", "type": "EHV",
                 "congestion_price_rt": 1.0, "total_lmp_rt": 41.0},
                {"pnode_id": 888, "pnode_name": "Y",
                 "datetime_beginning_ept": "2023-06-15T03:00:00", "type": "EHV",
                 "congestion_price_rt": 2.0, "total_lmp_rt": 42.0},
            ],
        })

    monkeypatch.setenv("PJM_API_KEY", "test")
    # Patch PJMClient construction to inject mock transport
    from surg.acquisition import pull as pull_mod
    from surg.acquisition.client import PJMClient

    orig_client = pull_mod.PJMClient
    def factory(*a, **kw):
        return PJMClient(*a, **{**kw, "min_interval_s": 0.0,
                                 "transport": httpx.MockTransport(handler)})
    monkeypatch.setattr(pull_mod, "PJMClient", factory)

    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2023-06-15", "--end", "2023-06-15",
        "--archive-tier", "--archive-subtype", "EHV",
        "--group-label", "test_archive_ehv",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0

    # Confirm output exists and is filtered.
    paths = list((tmp_path / "rt_hrl_lmps").rglob("test_archive_ehv__*.parquet"))
    assert len(paths) == 1
    df = pd.read_parquet(paths[0])
    # Filtered: only the LOUDOUN target row should remain.
    assert len(df) == 1
    assert df["pnode_id"].iloc[0] == 35010365
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/acquisition/test_cli.py -k archive_pull_end_to_end -v
```

If Tasks 1-5 are correct, this should pass directly. If it fails, fix the bug surfaced before continuing.

- [ ] **Step 3: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 85 passed (84 + 1 new).

- [ ] **Step 4: Commit**

```bash
git add tests/acquisition/test_cli.py
git commit -m "test(acquisition): end-to-end archive-mode CLI integration test"
```

---

## Task 7: Gap-fill Standard pull (2024-05-12 → 2024-05-25)

The existing `rt_hrl_lmps` Standard data starts 2024-05-26; the archive cutoff
lands at ~2024-05-11. Fill the 13-day gap for all 11 pnodes via the existing
Standard-tier path. Not a code change.

- [ ] **Step 1: Run gap-fill pull**

```bash
.venv/bin/surg-pull --feed rt_hrl_lmps \
  --start 2024-05-12 --end 2024-05-25 \
  --group-label dom_targets_gap_fill
```

Expected: `wrote data/raw/rt_hrl_lmps/2024/dom_targets_gap_fill__2024-05-12_to_2024-05-25.parquet`. ~1 minute API time.

- [ ] **Step 2: Verify row count**

```
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/raw/rt_hrl_lmps/2024/dom_targets_gap_fill__2024-05-12_to_2024-05-25.parquet')
print(f'{len(df):,} rows; pnodes={sorted(df.pnode_id.unique())}')
"
```

Expected: 11 pnodes × 14 days × 24 hours = 3,696 rows.

- [ ] **Step 3: No commit** — output is gitignored.

---

## Task 8: Archive bulk pull — rt_hrl_lmps EHV (2022-10-02 → 2024-05-11)

- [ ] **Step 1: Run archive pull**

```bash
.venv/bin/surg-pull --feed rt_hrl_lmps \
  --start 2022-10-02 --end 2024-05-11 \
  --archive-tier --archive-subtype EHV \
  --group-label dom_targets_archive_ehv
```

Expected: 3 chunks written:
- `data/raw/rt_hrl_lmps/2022/dom_targets_archive_ehv__2022-10-02_to_2022-12-31.parquet`
- `data/raw/rt_hrl_lmps/2023/dom_targets_archive_ehv__2023-01-01_to_2023-12-31.parquet`
- `data/raw/rt_hrl_lmps/2024/dom_targets_archive_ehv__2024-01-01_to_2024-05-11.parquet`

Wall-clock: ~7 min API time (~40 pages × ~10s/page at the 6/min rate limit), then filter-down.

- [ ] **Step 2: Verify**

```
.venv/bin/python -c "
import pandas as pd
from pathlib import Path
chunks = sorted(Path('data/raw/rt_hrl_lmps').rglob('dom_targets_archive_ehv__*.parquet'))
dfs = [pd.read_parquet(p) for p in chunks]
df = pd.concat(dfs, ignore_index=True)
print(f'{len(df):,} rows; pnodes={sorted(df.pnode_id.unique())}')
print(f'span: {df.datetime_beginning_ept.min()} -> {df.datetime_beginning_ept.max()}')
"
```

Expected: 8 EHV pnodes (35010365, 35010369, 35010371, 62871513, 1356178171, 1356178181, 1356178195, 1356178201), ~14,000 hours per pnode × 8 = ~112,000 rows.

- [ ] **Step 3: No commit** — output is gitignored.

---

## Task 9: Archive bulk pull — rt_hrl_lmps ZONE (2022-10-02 → 2024-05-11)

- [ ] **Step 1: Run archive pull**

```bash
.venv/bin/surg-pull --feed rt_hrl_lmps \
  --start 2022-10-02 --end 2024-05-11 \
  --archive-tier --archive-subtype ZONE \
  --group-label dom_targets_archive_zone
```

Wall-clock: ~1 min API time (~6 pages × ~10s/page).

- [ ] **Step 2: Verify**

```
.venv/bin/python -c "
import pandas as pd
from pathlib import Path
chunks = sorted(Path('data/raw/rt_hrl_lmps').rglob('dom_targets_archive_zone__*.parquet'))
df = pd.concat([pd.read_parquet(p) for p in chunks], ignore_index=True)
print(f'{len(df):,} rows; pnodes={sorted(df.pnode_id.unique())}')
"
```

Expected: 1 ZONE pnode (34964545), ~14,000 rows total.

- [ ] **Step 3: No commit** — output is gitignored.

---

## Task 10: Reserve feeds extension (2022-10-02 → 2024-05-25)

Reserve feeds are not in the archive system; the existing Standard pull
path handles them. Just run them for the older window.

- [ ] **Step 1: Pull sync_reserve_events**

```bash
.venv/bin/surg-pull --feed sync_reserve_events \
  --start 2022-10-02 --end 2024-05-25 \
  --subzone "MidAtlantic-Dominion (MAD)" \
  --group-label mad
```

Expected: 3 chunks (one per calendar year). ~10-15 events expected based on
the empirical retention probe (65 events total back to 2012).

- [ ] **Step 2: Pull reserve_market_results**

```bash
.venv/bin/surg-pull --feed reserve_market_results \
  --start 2022-10-02 --end 2024-05-25 \
  --locale MAD \
  --group-label mad
```

Expected: 3 chunks. ~170K rows (5-min granularity × 1.6y × 2 services).
~2 min API time.

- [ ] **Step 3: Verify**

```
.venv/bin/python -c "
import pandas as pd
from pathlib import Path

for feed, date_col in [('sync_reserve_events', 'event_start_ept'),
                       ('reserve_market_results', 'datetime_beginning_ept')]:
    chunks = sorted(Path(f'data/raw/{feed}').rglob('*.parquet'))
    df = pd.concat([pd.read_parquet(p) for p in chunks], ignore_index=True)
    df[date_col] = pd.to_datetime(df[date_col])
    print(f'{feed}: {len(df):,} rows, {df[date_col].min()} -> {df[date_col].max()}')
"
```

Expected: both feeds now span 2022-10-02 → 2026-05-10.

- [ ] **Step 4: Clean up smoke parquets** (pre-flight for Plan 2):

```bash
rm -f data/raw/sync_reserve_events/2026/mad_smoke__*.parquet
rm -f data/raw/reserve_market_results/2026/mad_smoke__*.parquet
```

- [ ] **Step 5: No commit** — output is gitignored.

---

## Task 11: Update data-catalog.md disk windows

After Tasks 7-10, the on-disk windows have shifted. Update
`docs/sources/data-catalog.md` to reflect the new state.

- [ ] **Step 1: Update the "Disk window" column in the snapshot table**

In `docs/sources/data-catalog.md`, update:

| Feed | Old "Disk window" | New "Disk window" |
|---|---|---|
| `rt_hrl_lmps` | 2024-05-26 → 2026-05-10 | 2022-10-02 → 2026-05-10 (9 pnodes); 2024-05-12 → 2026-05-10 (Ashburn TX1/TX2) |
| `sync_reserve_events` | 2024-05-26 → 2026-03-05 | 2022-10-02 → 2026-03-05 |
| `reserve_market_results` | 2024-05-26 → 2026-05-10 | 2022-10-02 → 2026-05-10 |

- [ ] **Step 2: Commit**

```bash
git add docs/sources/data-catalog.md
git commit -m "docs(catalog): update disk windows after Plan 1.5 backfill"
```

---

## Task 12: Final verification + push

- [ ] **Step 1: Run full suite one last time**

```
.venv/bin/pytest tests/ -v
```

Expected: 85 passed.

- [ ] **Step 2: Verify git state**

```
git log --oneline origin/main..HEAD
```

Expected: 7 commits ahead (Tasks 1-6 + Task 11 each commit; Tasks 7-10 and 12 don't).

- [ ] **Step 3: Push (requires user confirmation)**

> "Plan 1.5 (acquisition archive-mode) complete. 7 new commits. Push?"

If yes:

```bash
git push origin main
```

---

## Definition of done

- [ ] All 12 tasks complete.
- [ ] 85 tests passing (66 baseline + 5 + 2 + 4 + 4 + 3 + 1 = 85).
- [ ] `--archive-tier` and `--archive-subtype` CLI flags work and are tested.
- [ ] Bulk pulls done: `rt_hrl_lmps` covers 2022-10-02 → 2026-05-10 for the 9 EHV+ZONE target pnodes; 2024-05-12 → 2026-05-10 for the 2 LOAD pnodes. `sync_reserve_events` and `reserve_market_results` cover 2022-10-02 → 2026-05-10 (MAD).
- [ ] Smoke parquet duplicates removed from `data/raw/{sync_reserve_events,reserve_market_results}/2026/`.
- [ ] `docs/sources/data-catalog.md` reflects the new disk windows.

## Out of scope (deferred)

- DA LMP backfill (`da_hrl_lmps`) — DA-RT spread analysis is deferred per
  the methodology spec; can backfill later via the same archive-mode code.
- Ashburn TX1/TX2 (`type=LOAD`) backfill to 2022-10 — ~8.5 hours of API
  time; defer unless reviewer pushback requires symmetric Ashburn fit window.
- 5-min LMP backfill — Historic tier rejects the `type` filter on
  `rt_fivemin_hrl_lmps`; intractable without downloading the entire feed.
- Auto-detection of archive vs Standard tier based on date range — current
  design requires explicit `--archive-tier` flag.

## Risks

- **Live API behavior may differ from mock tests.** Tasks 7-10 are the
  first live tests of the archive-mode code path. Watch for:
  - Unexpected 400 errors on the type filter (e.g. if a subtype value not in
    the API guide enum is required).
  - Pagination edge cases when totalRows is very large (e.g. EHV ~1.2M/yr
    requires ~24 pages — the existing pagination handles this but is worth
    monitoring on first run).
  - The `/etc/hosts` workaround for `api.pjm.com` must still be in place
    (see `feedback_nu_dns_pjm.md`).
- **First-page totalRows trust.** The client trusts the first response's
  `totalRows` to know when to stop. If PJM returns a stale count, we could
  miss rows. Add a sanity-check assertion in the bulk-pull verification
  steps (Tasks 8, 9, 10): expected row count vs actual.
