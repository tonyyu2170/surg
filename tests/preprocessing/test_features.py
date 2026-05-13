from datetime import datetime

import pandas as pd
import pytest


def test_add_load_gradient_columns_computes_diff_per_hour():
    from surg.preprocessing.features import add_load_gradient_columns

    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T00:00:00",
            "2024-07-15T01:00:00",
            "2024-07-15T02:00:00",
        ]),
        "dom_load_mw": [10_000.0, 10_120.0, 10_080.0],
    })

    out = add_load_gradient_columns(df)

    # First row has no prior -> NaN
    assert pd.isna(out["dom_load_gradient_mw_per_hr"].iloc[0])
    # Second row: 10120 - 10000 = +120 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[1] == 120.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[1] == 2.0  # 120 / 60
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[1] == 2.0
    # Third row: 10080 - 10120 = -40 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[2] == -40.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[2] == pytest.approx(-40 / 60)
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[2] == pytest.approx(40 / 60)


def test_add_load_gradient_columns_preserves_existing_columns():
    from surg.preprocessing.features import add_load_gradient_columns
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-01-01T00:00:00"]),
        "dom_load_mw": [12_000.0],
        "extra": ["x"],
    })
    out = add_load_gradient_columns(df)
    assert "extra" in out.columns
    assert out["extra"].iloc[0] == "x"
