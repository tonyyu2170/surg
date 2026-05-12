# Acquisition reserve feeds extension — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sync_reserve_events` and `reserve_market_results` to the supported feeds in `src/surg/acquisition/`, with TDD throughout. End state: `surg-pull` can pull both feeds for the 2024-05-26 → 2026-05-10 analysis window into `data/raw/`.

**Architecture:** A `FeedSpec` registry encodes per-feed metadata (date field, geographic filter key, LMP-or-not). The orchestrator's `_build_params` becomes data-driven via this registry. `pull_feed` gains two new kwargs (`subzone`, `locale`) joining the existing `pnode_ids` and `zone`; exactly one is required per call, validated against the feed's `FeedSpec.geo_filter_key`. The CLI gains corresponding `--subzone` and `--locale` arguments.

**Tech Stack:** Python 3.11+, pytest, httpx (existing), pandas/pyarrow (existing). No new dependencies.

**Prerequisite reading:** `docs/plans/2026-05-11-phase-transition-methodology.md` (the design spec); `docs/decisions.md` § "2026-05-11 — Phase 3 method: TAR + quantile regression"; `docs/pjm-api-constraints.md` (API constraints, including the `operational_reserves` 15-day retention note).

**Test discipline:** TDD throughout — failing test, verify failure, minimal implementation, verify pass, commit. Existing 53 tests must remain passing after every task.

---

## Task 1: Add `FeedSpec` dataclass and `_FEED_SPECS` registry

**Files:**
- Modify: `src/surg/acquisition/pull.py` (top of file: add `FeedSpec` dataclass and `_FEED_SPECS` dict)
- Modify: `tests/acquisition/test_pull.py` (append new test)

- [ ] **Step 1: Write the failing test**

Append to `tests/acquisition/test_pull.py`:

```python
def test_feed_specs_registry_has_all_supported_feeds():
    from surg.acquisition.pull import _FEED_SPECS, FeedSpec

    expected_feeds = {
        "rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps",
        "hrl_load_metered",
        "sync_reserve_events", "reserve_market_results",
    }
    assert set(_FEED_SPECS.keys()) == expected_feeds

    # LMP feeds get row_is_current=true added
    for f in ["rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps"]:
        assert _FEED_SPECS[f].is_lmp is True
        assert _FEED_SPECS[f].date_field == "datetime_beginning_ept"
        assert _FEED_SPECS[f].geo_filter_key == "pnode_id"

    # Load feed uses zone filter
    assert _FEED_SPECS["hrl_load_metered"].geo_filter_key == "zone"
    assert _FEED_SPECS["hrl_load_metered"].is_lmp is False

    # New: sync_reserve_events uses event_start_ept and synchronized_sub_zone
    sre = _FEED_SPECS["sync_reserve_events"]
    assert sre.date_field == "event_start_ept"
    assert sre.geo_filter_key == "synchronized_sub_zone"
    assert sre.is_lmp is False

    # New: reserve_market_results uses datetime_beginning_ept and locale
    rmr = _FEED_SPECS["reserve_market_results"]
    assert rmr.date_field == "datetime_beginning_ept"
    assert rmr.geo_filter_key == "locale"
    assert rmr.is_lmp is False
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/pytest tests/acquisition/test_pull.py::test_feed_specs_registry_has_all_supported_feeds -v
```

Expected: `ImportError: cannot import name '_FEED_SPECS'` (or `FeedSpec`).

- [ ] **Step 3: Implement `FeedSpec` and `_FEED_SPECS` in `pull.py`**

Open `src/surg/acquisition/pull.py`. Add `from dataclasses import dataclass` to the top-level imports (it's not currently imported). After the existing imports, before `_LMP_FEEDS`, insert:

```python
@dataclass(frozen=True, slots=True)
class FeedSpec:
    """Per-feed metadata for API parameter construction.

    - date_field: column name used for range filter and sort
    - geo_filter_key: name of the geographic filter param (None means
      the feed has no geographic dimension; we don't currently support
      such feeds, but the field is here for future-proofing)
    - is_lmp: True for LMP feeds (adds row_is_current=true to params)
    """
    date_field: str
    geo_filter_key: str | None
    is_lmp: bool


_FEED_SPECS: dict[str, FeedSpec] = {
    "rt_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True),
    "da_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True),
    "rt_fivemin_hrl_lmps":    FeedSpec("datetime_beginning_ept", "pnode_id", True),
    "hrl_load_metered":       FeedSpec("datetime_beginning_ept", "zone", False),
    "sync_reserve_events":    FeedSpec("event_start_ept", "synchronized_sub_zone", False),
    "reserve_market_results": FeedSpec("datetime_beginning_ept", "locale", False),
}
```

Leave the existing `_LMP_FEEDS = frozenset(...)` in place; the CLI's `choices` argument still uses it. It will be replaced in Task 4.

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/pytest tests/acquisition/test_pull.py::test_feed_specs_registry_has_all_supported_feeds -v
```

Expected: 1 passed.

- [ ] **Step 5: Run full suite to confirm no regressions**

```
.venv/bin/pytest tests/ -v
```

Expected: 54 passed (53 previously + 1 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_pull.py
git commit -m "feat(acquisition): add FeedSpec registry covering 6 feeds"
```

---

## Task 2: Refactor `_build_params` to use `_FEED_SPECS`

The current `_build_params` hard-codes `datetime_beginning_ept` as the date field for all feeds. After this refactor it reads the field from `_FEED_SPECS[feed]`, enabling `sync_reserve_events` to use `event_start_ept`. The signature also changes to take a single `geo_value` rather than separate `pnode_ids` and `zone` (internal-only change; `pull_feed`'s public signature is preserved in Task 3).

**Files:**
- Modify: `src/surg/acquisition/pull.py` (replace `_build_params`; update its call sites)
- Modify: `tests/acquisition/test_pull.py` (append new tests for the two new feeds)

- [ ] **Step 1: Write failing test for `sync_reserve_events` params**

Append to `tests/acquisition/test_pull.py`:

```python
def test_sync_reserve_events_uses_event_start_ept_date_field(tmp_path: Path):
    """sync_reserve_events filters and sorts on event_start_ept, not datetime_beginning_ept."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="sync_reserve_events",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,
        zone=None,
        subzone="MidAtlantic-Dominion (MAD)",
        group_label="mad",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    # Date filter on event_start_ept, NOT datetime_beginning_ept
    assert "event_start_ept" in params
    assert "datetime_beginning_ept" not in params
    assert "2026-04-15 00:00 to 2026-04-15 23:59" in params["event_start_ept"]
    # Sort field matches
    assert params["sort"] == "event_start_ept"
    assert params["order"] == "Asc"
    # Geographic filter uses synchronized_sub_zone
    assert params["synchronized_sub_zone"] == "MidAtlantic-Dominion (MAD)"
    # Not an LMP feed
    assert "row_is_current" not in params


def test_reserve_market_results_uses_locale_filter(tmp_path: Path):
    """reserve_market_results uses the `locale` filter (e.g., 'MAD')."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="reserve_market_results",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,
        zone=None,
        locale="MAD",
        group_label="mad",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    assert "datetime_beginning_ept" in params
    assert params["locale"] == "MAD"
    assert "pnode_id" not in params
    assert "zone" not in params
    assert "synchronized_sub_zone" not in params
    assert "row_is_current" not in params
    assert params["sort"] == "datetime_beginning_ept"
```

These tests will fail because `pull_feed` doesn't yet accept `subzone` or `locale`.

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/pytest tests/acquisition/test_pull.py::test_sync_reserve_events_uses_event_start_ept_date_field tests/acquisition/test_pull.py::test_reserve_market_results_uses_locale_filter -v
```

Expected: 2 failed with `TypeError: pull_feed() got an unexpected keyword argument 'subzone'`.

- [ ] **Step 3: Refactor `_build_params` and add the new kwargs to `pull_feed`**

Replace `_build_params` in `src/surg/acquisition/pull.py` with this version:

```python
def _build_params(
    feed: str,
    chunk_start: date,
    chunk_end: date,
    geo_value: Sequence[int] | str | None,
) -> dict[str, Any]:
    spec = _FEED_SPECS[feed]
    date_range = (
        f"{chunk_start.isoformat()} 00:00 to "
        f"{chunk_end.isoformat()} 23:59"
    )
    params: dict[str, Any] = {
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

Replace the `pull_feed` signature (the keyword-only arguments block) and validation/dispatch:

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
    group_label: str,
    client: PJMClient,
    data_root: Path,
    force: bool = False,
    max_days_per_chunk: int = 366,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Exactly one of (pnode_ids, zone, subzone, locale) must be truthy,
    matching the feed's FeedSpec.geo_filter_key.
    """
    if feed not in _FEED_SPECS:
        raise ValueError(f"unknown feed: {feed}")
    spec = _FEED_SPECS[feed]

    # Map kwarg names → values; resolve which one this feed expects.
    kwarg_by_filter_key = {
        "pnode_id": pnode_ids,
        "zone": zone,
        "synchronized_sub_zone": subzone,
        "locale": locale,
    }
    if spec.geo_filter_key is None:
        # No feeds currently have geo_filter_key=None; reserved for future.
        geo_value = None
    else:
        geo_value = kwarg_by_filter_key.get(spec.geo_filter_key)
        if not geo_value:
            raise ValueError(
                f"feed {feed!r} requires a value for "
                f"{_friendly_kwarg_name(spec.geo_filter_key)}"
            )
        # Ensure no *other* geographic kwarg is set.
        for other_key, other_val in kwarg_by_filter_key.items():
            if other_key != spec.geo_filter_key and other_val:
                raise ValueError(
                    f"feed {feed!r} uses {_friendly_kwarg_name(spec.geo_filter_key)} "
                    f"only; got {_friendly_kwarg_name(other_key)}={other_val!r}"
                )

    written: list[Path] = []
    for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
        if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
            continue
        params = _build_params(feed, chunk_start, chunk_end, geo_value)
        rows = list(client.get_feed(feed, params))
        df = pd.DataFrame(rows)
        path = write_chunk(
            data_root=data_root,
            feed=feed,
            group_label=group_label,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            df=df,
        )
        written.append(path)
    return written


def _friendly_kwarg_name(filter_key: str) -> str:
    """Map API filter param → Python kwarg name for error messages."""
    return {
        "pnode_id": "pnode_ids",
        "zone": "zone",
        "synchronized_sub_zone": "subzone",
        "locale": "locale",
    }.get(filter_key, filter_key)
```

- [ ] **Step 4: Run new tests to verify they pass**

```
.venv/bin/pytest tests/acquisition/test_pull.py::test_sync_reserve_events_uses_event_start_ept_date_field tests/acquisition/test_pull.py::test_reserve_market_results_uses_locale_filter -v
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite to confirm no regressions**

```
.venv/bin/pytest tests/ -v
```

Expected: 56 passed (54 previously + 2 new). If any existing tests fail, the most likely cause is the validation logic in `pull_feed` now rejecting calls that used `pnode_ids=[]` or `zone=""` — those previously raised via the `bool(pnode_ids) == bool(zone)` check. The new validation should still reject them (empty list/string is falsy).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_pull.py
git commit -m "refactor(acquisition): make _build_params FeedSpec-driven; add subzone/locale kwargs"
```

---

## Task 3: Update `pull_feed` validation — reject ambiguous or missing geo kwargs

Task 2 added the kwargs and basic validation. This task adds explicit tests for the failure modes so we lock in the contract.

**Files:**
- Modify: `tests/acquisition/test_pull.py` (append failure-mode tests)

- [ ] **Step 1: Write failing tests for validation edge cases**

Append to `tests/acquisition/test_pull.py`:

```python
def test_sync_reserve_events_requires_subzone(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="requires a value for subzone"):
        pull_feed(
            feed="sync_reserve_events",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone=None,
            subzone=None,
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_sync_reserve_events_rejects_pnode_ids(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="uses subzone only; got pnode_ids"):
        pull_feed(
            feed="sync_reserve_events",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[35010365],
            subzone="MidAtlantic-Dominion (MAD)",
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_reserve_market_results_requires_locale(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="requires a value for locale"):
        pull_feed(
            feed="reserve_market_results",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone=None,
            locale=None,
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_reserve_market_results_rejects_zone(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="uses locale only; got zone"):
        pull_feed(
            feed="reserve_market_results",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            zone="DOM",
            locale="MAD",
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_unknown_feed_raises(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="unknown feed: 'not_a_real_feed'"):
        pull_feed(
            feed="not_a_real_feed",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[35010365],
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )
```

- [ ] **Step 2: Run tests to verify they pass**

The validation was already implemented in Task 2 — these tests should pass on first run.

```
.venv/bin/pytest tests/acquisition/test_pull.py -k "requires_subzone or rejects_pnode_ids or requires_locale or rejects_zone or unknown_feed" -v
```

Expected: 5 passed.

If any test fails because the error message doesn't match the regex, adjust the error message string in `pull_feed` to match the test (or vice versa — the test's message is what we want).

- [ ] **Step 3: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 61 passed (56 + 5 new).

- [ ] **Step 4: Commit**

```bash
git add tests/acquisition/test_pull.py
git commit -m "test(acquisition): lock validation contract for subzone/locale kwargs"
```

---

## Task 4: Update CLI — add `--subzone` and `--locale` args, expand `--feed` choices

The CLI's `_build_arg_parser` currently uses `_LMP_FEEDS | {"hrl_load_metered"}` for `--feed` choices and only knows about `--zone`. This task makes it FeedSpec-aware.

**Files:**
- Modify: `src/surg/acquisition/pull.py` (`_build_arg_parser` and `main`)
- Modify: `tests/acquisition/test_cli.py` (append CLI tests)

- [ ] **Step 1: Write failing tests for new CLI args**

Append to `tests/acquisition/test_cli.py`:

```python
def test_sync_reserve_events_dispatches_with_subzone(monkeypatch, tmp_path):
    """--feed sync_reserve_events --subzone MAD dispatches with subzone kwarg."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    rc = main([
        "--feed", "sync_reserve_events",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--subzone", "MidAtlantic-Dominion (MAD)",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["subzone"] == "MidAtlantic-Dominion (MAD)"
    assert captured.get("pnode_ids") is None
    assert captured.get("zone") is None
    assert captured.get("locale") is None


def test_reserve_market_results_dispatches_with_locale(monkeypatch, tmp_path):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    rc = main([
        "--feed", "reserve_market_results",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--locale", "MAD",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["locale"] == "MAD"
    assert captured.get("pnode_ids") is None


def test_sync_reserve_events_without_subzone_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "sync_reserve_events",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "--subzone is required" in capsys.readouterr().err


def test_reserve_market_results_without_locale_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "reserve_market_results",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "--locale is required" in capsys.readouterr().err


def test_subzone_with_lmp_feed_exits_2(monkeypatch, capsys):
    """--subzone is not valid for LMP feeds (which use pnode_id)."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--subzone", "MAD",
    ])
    assert rc == 2
    assert "--subzone is not valid" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify failure**

```
.venv/bin/pytest tests/acquisition/test_cli.py -v
```

Expected: 5 new tests fail (argparse rejects `--subzone` and `--locale` as unrecognized args).

- [ ] **Step 3: Update `_build_arg_parser` and `main` in `pull.py`**

Replace `_build_arg_parser` with:

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-pull",
        description="Pull a PJM Data Miner 2 feed for a date range to data/raw/.",
    )
    p.add_argument("--feed", required=True,
                   choices=sorted(_FEED_SPECS.keys()),
                   help="API feed name.")
    p.add_argument("--start", required=True, type=_parse_iso_date,
                   help="Inclusive start date (YYYY-MM-DD).")
    p.add_argument("--end",   required=True, type=_parse_iso_date,
                   help="Inclusive end date (YYYY-MM-DD).")
    p.add_argument("--group-label", default="dom_targets",
                   help="Slug used in output filenames.")
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory under which feed/year subdirs are created.")
    p.add_argument("--zone", default=None,
                   help="For zonal feeds (e.g. hrl_load_metered).")
    p.add_argument("--subzone", default=None,
                   help="For sub-zone feeds (e.g. sync_reserve_events). "
                        "Allowed values include 'MidAtlantic-Dominion (MAD)'.")
    p.add_argument("--locale", default=None,
                   help="For locale-filtered feeds (e.g. reserve_market_results). "
                        "Allowed values include 'MAD', 'PJM_RTO'.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing chunk files.")
    return p
```

Replace `main` with:

```python
def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    spec = _FEED_SPECS[args.feed]
    expected_kwarg = _friendly_kwarg_name(spec.geo_filter_key)

    # Per-feed CLI-arg validation. Each feed expects exactly one geographic arg.
    provided = {
        "zone": args.zone,
        "subzone": args.subzone,
        "locale": args.locale,
    }
    for arg_name, value in provided.items():
        if arg_name == expected_kwarg:
            if value is None:
                print(f"--{arg_name} is required for feed '{args.feed}'", file=sys.stderr)
                return 2
        elif value is not None:
            print(f"--{arg_name} is not valid for feed '{args.feed}' "
                  f"(it uses --{expected_kwarg} or implicit pnode set)",
                  file=sys.stderr)
            return 2
    # For LMP feeds (geo_filter_key='pnode_id'), expected_kwarg='pnode_ids' which
    # is not a CLI arg — we use all_pnode_ids() automatically. Validation above
    # would have ensured zone/subzone/locale are all None.

    load_dotenv()
    api_key = os.environ.get("PJM_API_KEY")
    if not api_key:
        print("PJM_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    # Resolve geographic kwargs to pass to pull_feed
    pnode_ids = all_pnode_ids() if spec.geo_filter_key == "pnode_id" else None

    with PJMClient(api_key=api_key) as client:
        paths = pull_feed(
            feed=args.feed,
            start=args.start,
            end=args.end,
            pnode_ids=pnode_ids,
            zone=args.zone,
            subzone=args.subzone,
            locale=args.locale,
            group_label=args.group_label,
            client=client,
            data_root=Path(args.data_root),
            force=args.force,
        )

    if not paths:
        print("No chunks pulled (all already exist; use --force to overwrite).")
    else:
        for p in paths:
            print(f"wrote {p}")
    return 0
```

Note: the existing `--zone is not valid for LMP feed '...'` error message changes shape slightly (now mentions both `--zone` and the expected arg). Update the existing test `test_zone_with_lmp_feed_exits_2` if its assertion `"not valid for LMP"` no longer matches. Test for the new substring `"not valid for feed"`.

- [ ] **Step 4: Update the existing CLI test whose message changed**

Edit `tests/acquisition/test_cli.py`. Find `test_zone_with_lmp_feed_exits_2`. Change:

```python
    assert "not valid for LMP" in capsys.readouterr().err
```

to:

```python
    assert "not valid for feed" in capsys.readouterr().err
```

- [ ] **Step 5: Run tests**

```
.venv/bin/pytest tests/ -v
```

Expected: 66 passed (61 + 5 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/acquisition/pull.py tests/acquisition/test_cli.py
git commit -m "feat(acquisition): add --subzone and --locale CLI args for new feeds"
```

---

## Task 5: Remove the now-stale `_LMP_FEEDS` constant

After Task 4 the CLI uses `_FEED_SPECS.keys()` for choices. The `_LMP_FEEDS` frozenset is no longer used by `_build_params` (which now reads `spec.is_lmp`). Clean it up.

**Files:**
- Modify: `src/surg/acquisition/pull.py`

- [ ] **Step 1: Verify `_LMP_FEEDS` is unused**

```
.venv/bin/grep -nR "_LMP_FEEDS" src/ tests/ || /usr/bin/grep -nR "_LMP_FEEDS" src/ tests/
```

Expected: only the definition in `src/surg/acquisition/pull.py`. If any tests or other files reference it, replace those references with `{f for f, s in _FEED_SPECS.items() if s.is_lmp}` or similar before deleting.

- [ ] **Step 2: Delete the constant**

Edit `src/surg/acquisition/pull.py`. Remove the lines:

```python
# Feeds that follow LMP versioning semantics.
_LMP_FEEDS = frozenset(
    {"rt_hrl_lmps", "rt_fivemin_hrl_lmps", "da_hrl_lmps"}
)
```

- [ ] **Step 3: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 66 passed (no regression).

- [ ] **Step 4: Commit**

```bash
git add src/surg/acquisition/pull.py
git commit -m "refactor(acquisition): drop _LMP_FEEDS — superseded by FeedSpec.is_lmp"
```

---

## Task 6: Smoke pull `sync_reserve_events` for one day against real API

End-to-end verification that the new feed path works against the real PJM API. Picks a known recent date with sync reserve activity (any weekday in the analysis window). Hits the API, verifies parquet output.

**Files:**
- No source changes; uses the CLI

**Prerequisite:** `.env` has `PJM_API_KEY` set. `/etc/hosts` has the `api.pjm.com → 156.154.121.141` workaround if NU DNS still fails (per `memory/feedback_nu_dns_pjm.md`).

- [ ] **Step 1: Run the smoke pull**

```bash
.venv/bin/surg-pull \
  --feed sync_reserve_events \
  --start 2026-04-01 --end 2026-04-30 \
  --subzone "MidAtlantic-Dominion (MAD)" \
  --group-label mad_smoke
```

Expected: one of —
- One `wrote data/raw/sync_reserve_events/2026/mad_smoke__2026-04-01_to_2026-04-30.parquet` line (one chunk, doesn't cross a year boundary), OR
- "No chunks pulled (all already exist...)" if you've run it before.

Wall time ~15-20s (one chunk × 11s throttle + paginated fetch).

- [ ] **Step 2: Verify the parquet has the expected schema**

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/raw/sync_reserve_events/2026/mad_smoke__2026-04-01_to_2026-04-30.parquet')
print(f'rows={len(df)}')
print(f'columns={list(df.columns)}')
print(df.head(3))
"
```

Expected: row count between 0 and ~20 (events are rare even in active months). Columns must include `event_start_ept`, `event_end_ept`, `duration`, `synchronized_reserve_zone`, `synchronized_sub_zone`. All `synchronized_sub_zone` values should be "MidAtlantic-Dominion (MAD)".

If row count is zero, that's a real finding (no MAD-subzone sync reserve events in April 2026) — not a bug. Sanity check by removing the subzone filter and re-running with `--group-label all_smoke`; if total rows > 0 and they're all non-MAD, the filter is working correctly and MAD just had no events that month.

- [ ] **Step 3: No commit** (data files are gitignored)

---

## Task 7: Bulk pull `sync_reserve_events` for the analysis window

**Files:** none modified; data added to `data/raw/sync_reserve_events/`.

- [ ] **Step 1: Run the bulk pull**

```bash
.venv/bin/surg-pull \
  --feed sync_reserve_events \
  --start 2024-05-26 --end 2026-05-10 \
  --subzone "MidAtlantic-Dominion (MAD)" \
  --group-label mad
```

Expected output: 3 chunks (year-boundary splits at 2024-12-31 / 2025-12-31):

```
wrote data/raw/sync_reserve_events/2024/mad__2024-05-26_to_2024-12-31.parquet
wrote data/raw/sync_reserve_events/2025/mad__2025-01-01_to_2025-12-31.parquet
wrote data/raw/sync_reserve_events/2026/mad__2026-01-01_to_2026-05-10.parquet
```

Wall time ~35s (3 chunks × 11s throttle).

- [ ] **Step 2: Verify the data**

```bash
.venv/bin/python -c "
import pandas as pd
from pathlib import Path
files = sorted(Path('data/raw/sync_reserve_events').rglob('mad__*.parquet'))
dfs = [pd.read_parquet(f) for f in files]
df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
print(f'total events in window: {len(df)}')
print(f'all MAD?: {(df.get(\"synchronized_sub_zone\") == \"MidAtlantic-Dominion (MAD)\").all() if len(df) else \"empty\"}')
if len(df):
    print(f'date range: {df.event_start_ept.min()} → {df.event_start_ept.max()}')
    print(f'duration column dtype: {df.duration.dtype}')
"
```

Expected: 5-50 total events over ~715 days (events are rare). All `synchronized_sub_zone == "MidAtlantic-Dominion (MAD)"`.

If total events is < 5, that's a possible finding to flag in `decisions.md` — may need to fall back on the broader `reserve_market_results` clearing-price signal.

- [ ] **Step 3: No commit** (gitignored data)

---

## Task 8: Smoke pull `reserve_market_results` for one day against real API

`reserve_market_results` has 5-min granularity post-2022-10-01, so volume is higher. Smoke this against one day before bulking.

**Files:** none modified.

- [ ] **Step 1: Run the smoke pull**

```bash
.venv/bin/surg-pull \
  --feed reserve_market_results \
  --start 2026-04-15 --end 2026-04-15 \
  --locale MAD \
  --group-label mad_smoke
```

Expected: one `wrote data/raw/reserve_market_results/2026/mad_smoke__2026-04-15_to_2026-04-15.parquet`. Wall time ~12s (one chunk, ~288 5-min intervals × 3 services = ~864 rows, well under the 50K page cap, single paginated call).

- [ ] **Step 2: Verify the schema**

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/raw/reserve_market_results/2026/mad_smoke__2026-04-15_to_2026-04-15.parquet')
print(f'rows={len(df)}')
print(f'columns={list(df.columns)}')
print(f'services={df[\"service\"].unique() if \"service\" in df else \"NO SERVICE COL\"}')
print(f'locales={df[\"locale\"].unique() if \"locale\" in df else \"NO LOCALE COL\"}')
print(df.head(3))
"
```

Expected: ~864 rows (288 5-min intervals × 3 services: SR, PR, REG). All `locale == "MAD"`. Columns include `datetime_beginning_ept`, `service`, `mcp`, `mcp_capped`, `as_mw`, `as_req_mw`, plus other fields per the metadata.

- [ ] **Step 3: No commit**

---

## Task 9: Bulk pull `reserve_market_results` for the analysis window

**Files:** none modified.

- [ ] **Step 1: Run the bulk pull**

```bash
.venv/bin/surg-pull \
  --feed reserve_market_results \
  --start 2024-05-26 --end 2026-05-10 \
  --locale MAD \
  --group-label mad
```

Expected: 3 chunks. Each chunk has ~63K rows per year (288 × 365 × 3 services) which fits within ~2 paginated calls. Wall time ~80-100s total.

- [ ] **Step 2: Verify the data**

```bash
.venv/bin/python -c "
import pandas as pd
from pathlib import Path
files = sorted(Path('data/raw/reserve_market_results').rglob('mad__*.parquet'))
dfs = [pd.read_parquet(f) for f in files]
df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
print(f'total rows: {len(df):,}')
print(f'services: {sorted(df.service.unique())}')
print(f'locales: {sorted(df.locale.unique())}')
print(f'date range: {df.datetime_beginning_ept.min()} → {df.datetime_beginning_ept.max()}')
# Sanity: how many 5-min intervals had a nonzero mcp (= ORDC fired)?
sr = df[df.service == 'SR']
nonzero_pct = (sr.mcp.fillna(0) > 0).mean() * 100
print(f'SR clearing price > 0 in {nonzero_pct:.2f}% of intervals')
"
```

Expected: ~190K total rows. Services should be exactly `['PR', 'REG', 'SR']`. Locale should be exactly `['MAD']`. The nonzero-SR-clearing-price percentage tells us how often ORDC fired — useful for the mechanism analysis and for assessing the high-volatility regime occupancy concern from spec §4.

- [ ] **Step 3: No commit**

---

## Task 10: Final verification and push

- [ ] **Step 1: Run the full test suite one last time**

```
.venv/bin/pytest tests/ -v
```

Expected: 66 passed.

- [ ] **Step 2: Verify git state**

```
git log --oneline origin/main..HEAD
git status
```

Expected: 5 commits ahead of `origin/main` (Tasks 1, 2, 3, 4, 5 each commit). Working tree clean.

- [ ] **Step 3: Push to origin (requires user confirmation)**

This step requires explicit user permission per the project's git workflow. Ask first:

> "Acquisition reserve-feed extension complete. 5 commits ahead of origin. Push?"

If yes:

```bash
git push origin main
```

If no: leave the commits local and proceed to the next plan.

---

## Definition of done

- [ ] All 10 tasks above complete and committed.
- [ ] 66 tests passing.
- [ ] `data/raw/sync_reserve_events/{2024,2025,2026}/mad__*.parquet` exists (3 chunks).
- [ ] `data/raw/reserve_market_results/{2024,2025,2026}/mad__*.parquet` exists (3 chunks).
- [ ] No regressions in existing acquisition behavior (existing tests still pass; existing `surg-pull --feed rt_hrl_lmps ...` and `--feed hrl_load_metered ...` invocations still work unchanged).

## Out of scope (deferred)

- The preprocessing module that consumes these feeds (Plan 2).
- Aggregation of 5-min `reserve_market_results` to hourly (happens in preprocessing).
- The actual `operational_reserves` feed (dropped per the 15-day retention finding documented in `pjm-api-constraints.md`).
