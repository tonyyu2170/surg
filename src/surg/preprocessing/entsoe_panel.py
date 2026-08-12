"""Build native-resolution and hourly panels from raw ENTSO-E rows.

Two panels come from one source (design section 3.3):

  * native  -- each zone at its own resolution (NL PT15M, IE PT30M, IT PT60M
               or PT15M depending on the year)
  * hourly  -- mean within the hour, for cross-zone comparison

A caution that must survive into the write-up: an hourly panel DERIVED BY
AVERAGING sub-hourly data is low-pass filtered, so it is smoother than a
natively-metered hourly series. vol_norm LEVELS are therefore not strictly
comparable between these zones and the 11 existing panels. Within-zone TRENDS
are, and the trend is what this design tests.

Resolution is read PER DOCUMENT, never assumed per zone -- IT-North switches
from PT60M to PT15M somewhere between 2021 and 2026 (design section 1.2).

to_hourly reports n_obs -- the number of native slots that went into each
hourly mean. An hour built from fewer slots than its resolution implies (a
gap between documents, or the edge of a pull window) still produces a
plausible-looking number, so completeness is recorded as data rather than
assumed. Callers that care must filter on it; nothing here drops rows.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.entsoe_expand import expand_curve, resolution_minutes
from surg.preprocessing.entsoe_zones import BY_KEY

_DOC_KEYS = ["doc_start", "doc_end", "resolution", "curve_type"]


def build_zone_series(
    raw: pd.DataFrame, *, zone_key: str, value_name: str
) -> pd.DataFrame:
    """Expand every document in `raw` and localize to naive local prevailing.

    Returns columns: timestamp_utc, timestamp_local, <value_name>.
    """
    zone = BY_KEY[zone_key]

    # 12.1.D returns whole days in the AREA's timezone, so a day straddling a
    # calendar-year boundary comes back from both adjacent year requests and
    # `load_raw` concatenates two identical copies of it. Measured on Italian
    # price: 622 of 118,263 rows, in 311 groups, ALL agreeing on value.
    # Deduplicate on the value as well as the position, so an exact repeat is
    # dropped while a genuine conflicting duplicate still reaches
    # expand_curve's duplicate-position guard and raises.
    raw = raw.drop_duplicates(subset=[*_DOC_KEYS, "position", "value"])

    frames = []
    for (start, end, resolution, curve_type), group in raw.groupby(
        _DOC_KEYS, sort=True
    ):
        points = list(zip(group["position"], group["value"], strict=True))
        dense, _ = expand_curve(
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            resolution=resolution,
            curve_type=curve_type,
            points=points,
        )
        index = pd.date_range(
            start=pd.Timestamp(start),
            periods=len(dense),
            freq=f"{resolution_minutes(resolution)}min",
            tz="UTC",
        )
        frames.append(pd.DataFrame({"timestamp_utc": index, value_name: dense}))

    if not frames:
        return pd.DataFrame(columns=["timestamp_utc", "timestamp_local", value_name])

    out = pd.concat(frames, ignore_index=True)
    # Documents can overlap (12.1.D returns whole days regardless of the
    # window asked for), so de-duplicate on the UTC instant.
    out = out.drop_duplicates(subset="timestamp_utc").sort_values("timestamp_utc")
    out["timestamp_local"] = (
        out["timestamp_utc"].dt.tz_convert(zone.timezone).dt.tz_localize(None)
    )
    out.attrs["timezone"] = zone.timezone
    out.attrs["zone_key"] = zone_key
    return out.reset_index(drop=True)[["timestamp_utc", "timestamp_local", value_name]]


def to_hourly(native: pd.DataFrame, *, value_name: str, timezone: str | None = None) -> pd.DataFrame:
    """Mean within the hour, plus the dst_transition_hour flag stage1 needs.

    The timezone comes from `native.attrs` (set by build_zone_series) unless
    passed explicitly. It cannot be recovered by offset arithmetic, because the
    offset changes across DST -- which is the whole point of the flag.
    """
    columns = [
        "timestamp_utc", "timestamp_local", value_name,
        "n_obs", "dst_transition_hour",
    ]
    if native.empty:
        return pd.DataFrame(columns=columns)

    tz = timezone or native.attrs.get("timezone")
    if tz is None:
        raise ValueError(
            "timezone unknown: pass timezone= explicitly, or build the frame "
            "with build_zone_series so attrs['timezone'] is set"
        )

    work = native.copy()
    work["hour_utc"] = work["timestamp_utc"].dt.floor("h")
    grouped = (
        work.groupby("hour_utc", as_index=False)
        .agg(**{value_name: (value_name, "mean"), "n_obs": (value_name, "size")})
        .rename(columns={"hour_utc": "timestamp_utc"})
    )
    grouped["timestamp_local"] = (
        grouped["timestamp_utc"].dt.tz_convert(tz).dt.tz_localize(None)
    )
    grouped["dst_transition_hour"] = grouped["timestamp_local"].duplicated(keep=False)
    grouped.attrs["timezone"] = tz
    return grouped[columns].reset_index(drop=True)


def load_raw(item: str, zone_key: str, root: str = "data/raw/entsoe") -> pd.DataFrame:
    """Concatenate every year file on disk for one zone and item."""
    files = sorted(Path(root, item, zone_key).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no raw files for {item}/{zone_key} under {root}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def zone_panel(
    item: str, zone_key: str, *, value_name: str, root: str = "data/raw/entsoe"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience: disk -> (native, hourly)."""
    raw = load_raw(item, zone_key, root)
    native = build_zone_series(raw, zone_key=zone_key, value_name=value_name)
    return native, to_hourly(native, value_name=value_name)
