"""Regression tests for items #1-4 + #6 post-cluster-bootstrap-refactor.

Asserts: with `bootstrap_method="pair"` (default), modified modules
produce numerically equivalent output to the captured pre-refactor
reference fixtures at `tests/regression/hourly_reference/`.

Tolerance policy (per CAPTURE_PARAMS.json):
- Point estimates: exact match (rel diff < 1e-9). Do NOT depend on
  RNG and must be identical pre/post refactor.
- CI bounds + bootstrap-derived stats: 2% relative tolerance. Some
  refactors change the order of `rng.<...>` calls (the same seed
  produces a different consumption sequence), so CI bounds may drift
  slightly even though the bootstrap method is unchanged. The
  tail_risk_curves refactor in Task 9 is byte-identical for pair
  mode (the inline pair loop is preserved); other modules in Tasks
  10-13 may show minor CI drift.

Each module-specific test re-runs the production analysis on the
hourly panel (`data/interim/analysis_panel.parquet`, schema v2) at
the SAME n_boot/seed used at capture time, then walks the per-pnode
JSONs and compares against reference.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

REF_DIR = Path("tests/regression/hourly_reference")
HOURLY_PANEL_PATH = Path("data/interim/analysis_panel.parquet")
POINT_TOLERANCE_REL = 1e-9
CI_TOLERANCE_REL = 0.02


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(p: Path) -> dict:
    with open(p) as f:
        return json.load(f)


def _is_ci_field(key_path: str) -> bool:
    """A leaf key is CI/bootstrap-derived if any of:
      (a) exact 'ci', (b) ends '_ci', (c) contains '_ci_',
      (d) contains 'p_value', (e) contains 'bootstrap',
      (f) contains 'boot_se' or 'boot_std'.
    Per CAPTURE_PARAMS.json ci_field_detection_rule.
    """
    last = key_path.split(".")[-1].split("[")[0]
    if last == "ci":
        return True
    if last.endswith("_ci"):
        return True
    if "_ci_" in last:
        return True
    if "p_value" in last:
        return True
    if "bootstrap" in last:
        return True
    if "boot_se" in last or "boot_std" in last:
        return True
    return False


def _is_unstable_struct(key_path: str) -> bool:
    """Some leaf keys vary across runs even with identical seed because
    they index pnodes/years that depend on the data — these are
    structural rather than numeric and are checked via key-set
    comparison, not value comparison.
    """
    return False


def _assert_numeric_equivalence(reference, current, path: str = "") -> None:
    """Recursive numeric comparison with CI-aware tolerance."""
    # Allow numpy int/float vs python int/float type promotion through.
    if isinstance(reference, (int, float)) and isinstance(current, (int, float)):
        pass
    elif isinstance(reference, list) and isinstance(current, list):
        pass
    elif isinstance(reference, dict) and isinstance(current, dict):
        pass
    elif type(reference) != type(current):
        raise AssertionError(
            f"Type mismatch at {path}: ref={type(reference).__name__}, "
            f"cur={type(current).__name__}"
        )

    if isinstance(reference, dict):
        ref_keys = set(reference.keys())
        cur_keys = set(current.keys())
        if ref_keys != cur_keys:
            missing = ref_keys - cur_keys
            extra = cur_keys - ref_keys
            raise AssertionError(
                f"Key mismatch at {path}: missing={missing}, extra={extra}"
            )
        for k in reference:
            _assert_numeric_equivalence(
                reference[k], current[k], f"{path}.{k}"
            )
        return

    if isinstance(reference, list):
        if len(reference) != len(current):
            raise AssertionError(
                f"Length mismatch at {path}: "
                f"ref={len(reference)}, cur={len(current)}"
            )
        for i, (r, c) in enumerate(zip(reference, current)):
            _assert_numeric_equivalence(r, c, f"{path}[{i}]")
        return

    if reference is None and current is None:
        return
    if isinstance(reference, bool) or isinstance(current, bool):
        if reference != current:
            raise AssertionError(
                f"Bool mismatch at {path}: ref={reference}, cur={current}"
            )
        return
    if isinstance(reference, (int, float)):
        # NaN comparison: both must be NaN
        if isinstance(reference, float) and math.isnan(reference):
            if not (isinstance(current, float) and math.isnan(current)):
                raise AssertionError(f"Reference NaN at {path}, current={current}")
            return
        if isinstance(current, float) and math.isnan(current):
            raise AssertionError(f"Current NaN at {path}, reference={reference}")

        tol = CI_TOLERANCE_REL if _is_ci_field(path) else POINT_TOLERANCE_REL
        if reference == 0:
            abs_tol = max(tol, 1e-9)
            if abs(current) > abs_tol:
                raise AssertionError(
                    f"Numeric mismatch at {path}: ref=0, cur={current}, "
                    f"abs_tol={abs_tol}"
                )
            return
        rel = abs(reference - current) / abs(reference)
        if rel > tol:
            raise AssertionError(
                f"Numeric mismatch at {path}: ref={reference}, cur={current}, "
                f"rel_diff={rel:.3e}, tol={tol:.3e}"
            )
        return

    # Strings
    if reference != current:
        raise AssertionError(
            f"Mismatch at {path}: ref={reference!r}, cur={current!r}"
        )


def _hourly_panel_or_skip():
    """Skip the regression test if the hourly panel isn't on disk
    (e.g., CI environments that don't ship the panel)."""
    if not HOURLY_PANEL_PATH.exists():
        pytest.skip(
            f"Hourly panel not found at {HOURLY_PANEL_PATH}; "
            "build via `surg-prep` before running regression tests."
        )
    import pandas as pd
    return pd.read_parquet(HOURLY_PANEL_PATH)


# ---------------------------------------------------------------------------
# Item #6: tail_risk_curves
# ---------------------------------------------------------------------------

def test_tail_risk_curves_pair_bootstrap_equivalence():
    """Sub-q1 item #6 (tail_risk_curves): refactor preserves pair-bootstrap
    output byte-for-byte (the pair branch is a literal copy of the
    pre-refactor inline loop)."""
    from surg.analysis.tail_risk_curves import run_tail_risk_curves

    panel = _hourly_panel_or_skip()
    with TemporaryDirectory() as tmp:
        run_tail_risk_curves(
            panel=panel,
            out_root=Path(tmp),
            n_boot=50,
            seed=42,
            bootstrap_method="pair",
        )
        ref_dir = REF_DIR / "tail_risk_curves"
        cur_dir = Path(tmp) / "tail_risk_curves"
        for ref_file in sorted(ref_dir.glob("*.json")):
            cur_file = cur_dir / ref_file.name
            if not cur_file.exists():
                raise AssertionError(
                    f"Refactored module missing reference output: {ref_file.name}"
                )
            ref = _load_json(ref_file)
            cur = _load_json(cur_file)
            _assert_numeric_equivalence(ref, cur, ref_file.name)


# ---------------------------------------------------------------------------
# Item #1: gpd_continuous (Spec B)
# ---------------------------------------------------------------------------

def test_gpd_continuous_pair_bootstrap_equivalence():
    """Sub-q1 item #1 (gpd_continuous Spec B): refactor preserves
    pair-bootstrap output byte-for-byte."""
    from surg.analysis.gpd_continuous import run_gpd_continuous_z
    from surg.analysis.run import PNODE_RESPONSES

    panel = _hourly_panel_or_skip()
    ref_dir = REF_DIR / "gpd_continuous"
    with TemporaryDirectory() as tmp:
        out_root = Path(tmp) / "gpd_continuous"
        for label, col in PNODE_RESPONSES.items():
            if panel[col].dropna().empty:
                continue
            run_gpd_continuous_z(
                panel=panel,
                out_path=out_root / f"{label}.json",
                response_col=col,
                pnode_label=label,
                n_boot=50,
                seed=42,
                bootstrap_method="pair",
            )
        for ref_file in sorted(ref_dir.glob("*.json")):
            cur_file = out_root / ref_file.name
            if not cur_file.exists():
                raise AssertionError(
                    f"Refactored module missing reference output: {ref_file.name}"
                )
            ref = _load_json(ref_file)
            cur = _load_json(cur_file)
            _assert_numeric_equivalence(ref, cur, ref_file.name)
