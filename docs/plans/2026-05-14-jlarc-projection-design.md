# JLARC Projection Layer — Design Spec (sub-question 2)

> **Status:** Drafted overnight 2026-05-14 with no user in-the-loop. Default decisions are marked **[DEFAULT — user may override on review]**. User is requested to review before plan-writing begins.

## Goal

Answer the proposal's second sub-question: *"At what point in the future will [the volatility threshold] become the chronic operating state of the NOVA grid?"*

In the post-smooth-curve-diagnosis framing (2026-05-13 entry, follow-up from 2026-05-14 Strategy C findings): there is no single MW/min threshold. The question becomes *"Given projected DC growth, how does the load-volatility distribution Z shift over time, and when do high-LMP hours that are currently rare become routine?"*

The projection layer applies JLARC/PJM growth forecasts to the current load-volatility distribution and the historical QR-full response curves to produce multi-scenario, multi-metric trajectories of grid stress through 2040.

## Non-goals (explicit out-of-scope)

- **Automated PDF parsing of JLARC/PJM reports.** Growth rates are extracted manually by the user and committed to a config file. The projection layer reads the config; it does not download or parse external reports.
- **Probabilistic uncertainty modeling on the projection.** Point estimates per scenario only (low / base / high). No posterior over the projection horizon.
- **Cost translation (dollar impacts).** Outside the proposal's scope for this paper.
- **DC-load decomposition from first principles.** We use proportional scaling (whole-load proxy) as primary. DC-attributed scaling is a robustness check; if the data to support it isn't readily available, that check is skipped without affecting the primary trajectory.
- **Re-running the historical analysis at different windows.** The projection layer consumes the existing QR-full response curves (`outputs/qr_full/*.json`) and the existing analysis panel; it does not re-fit.
- **Spec B from the conditional-Z battery (continuous ξ(Z) regression).** Independent work track. If Spec B triggers based on the battery's verdict, that work happens in its own plan; the projection design here does not depend on whether B runs.

## Architecture

A new module `src/surg/projection/` with four files, each with one responsibility:

```
src/surg/projection/
  __init__.py
  growth_forecasts.py   — load growth-rate scenarios from YAML config; expose annual factors
  z_distribution.py     — current Z distribution + per-year projection via scaling assumption
  exceedance.py         — exceedance-frequency calculations and quantile-shift summaries
  run.py                — orchestrator + CLI entry point `surg-project`
```

A new config file `data/config/growth_scenarios.yaml` (gitignored by the existing `data/` rule, except for a `.gitkeep` anchor and an `example.yaml` template):

```yaml
# Example structure — actual values come from JLARC Rpt598-2 + PJM Load Forecast Report.
# User edits this file with extracted numbers, then runs `surg-project`.

scenarios:
  low:
    description: "JLARC low-growth scenario"
    dc_load_2025_mw: 6000
    dc_load_2040_mw: 9000
    growth_curve: "linear"  # or "exponential"
  base:
    description: "JLARC base-case scenario (Rpt598-2 reference)"
    dc_load_2025_mw: 6000
    dc_load_2040_mw: 12000
    growth_curve: "linear"
  high:
    description: "JLARC high-growth scenario"
    dc_load_2025_mw: 6000
    dc_load_2040_mw: 18000
    growth_curve: "linear"

projection:
  years: [2025, 2030, 2035, 2040]   # report years
  reference_year: 2025                # the year whose Z distribution is our baseline
  z_lmp_response_method: "qr_full_linear"   # or "qr_full_year_fe"
  metrics:
    - quantile_shift          # year when 95th-pct of baseline Z becomes 50th-pct of projected Z
    - exceedance_hours        # projected hours/year above LMP_τ benchmark
    - mean_z_growth_factor    # scalar projected E[Z(y)] / E[Z(2025)]
```

**[DEFAULT — user may override]** The config YAML structure: I picked YAML over JSON for the human-edited file. JSON is fine if the user prefers it.

## Module responsibilities

### `growth_forecasts.py`

```python
@dataclass(frozen=True, slots=True)
class GrowthScenario:
    name: str                       # "low" | "base" | "high"
    description: str
    dc_load_2025_mw: float
    dc_load_2040_mw: float
    growth_curve: Literal["linear", "exponential"]

def load_growth_scenarios(config_path: Path) -> dict[str, GrowthScenario]: ...

def annual_growth_factor(scenario: GrowthScenario, year: int) -> float:
    """Return DC load(year) / DC load(2025) under this scenario's curve."""
```

`annual_growth_factor` returns a multiplicative factor (e.g., 1.0 in 2025, 2.0 in 2040 for a doubling scenario). Linear interpolation between 2025 and 2040 anchors. Exponential uses CAGR derived from the two anchors.

### `z_distribution.py`

The core projection mechanism — proportional scaling.

```python
@dataclass(frozen=True, slots=True)
class ZDistribution:
    """Empirical CDF of Z over a finite set of historical observations."""
    sorted_values: np.ndarray         # ascending Z values from the analysis panel
    reference_year: int

def current_z_distribution(panel: pd.DataFrame, threshold_col: str, reference_year: int) -> ZDistribution: ...

def project_z_distribution(
    z_current: ZDistribution,
    growth_factor: float,
    *,
    scaling_method: Literal["proportional", "dc_attributed"] = "proportional",
    dc_share_of_load: float | None = None,  # required for dc_attributed
) -> ZDistribution:
    """Return a projected Z distribution under the named scaling assumption."""
```

**Proportional scaling.** If DC load doubles, then Z (load gradient) doubles:
```
Z_projected = growth_factor × Z_current
```

This is the simplest defensible model. It treats Z as fully attributable to DC growth — overstates volatility growth if non-DC load contributes to Z.

**DC-attributed scaling (robustness only).** Treats current Z as `Z_dc + Z_other`. Assumes `Z_dc` scales with DC growth, `Z_other` stays constant.
```
Z_dc_current = Z_current × dc_share_of_load
Z_other = Z_current × (1 − dc_share_of_load)
Z_projected = growth_factor × Z_dc_current + Z_other
```

Requires `dc_share_of_load` (e.g., 0.30 if DC is currently 30% of DOM load). Source: JLARC + PJM load decomposition. **[DEFAULT — user may override]** If this number isn't readily available, the dc_attributed robustness path is skipped; only proportional runs.

### `exceedance.py`

Convert projected Z distributions into headline metrics via QR-full response curves.

```python
@dataclass(frozen=True, slots=True)
class QRFullResponseCurve:
    """A τ-indexed linear response: LMP_τ(Z) = intercept_τ + slope_τ * Z."""
    quantile: float                # τ ∈ {0.90, 0.95, 0.99}
    intercept: float               # baseline LMP_τ at E[Z(reference_year)]
    slope: float                   # z_slope from qr_full primary spec
    pnode_label: str

def load_qr_full_response_curves(outputs_dir: Path, pnode_label: str = "total_lmp") -> list[QRFullResponseCurve]: ...

def projected_lmp_quantile(
    response: QRFullResponseCurve,
    z_projected: ZDistribution,
    z_reference: ZDistribution,
) -> float:
    """Apply the linear response curve to project LMP_τ from current to future Z."""

def exceedance_hours_per_year(
    lmp_quantile_projected: float,
    z_projected: ZDistribution,
    benchmark_lmp: float,
    hours_per_year: int = 8760,
) -> float:
    """Estimate hours/year where projected LMP exceeds benchmark."""

def quantile_shift_year(
    z_current: ZDistribution,
    growth_factors_by_year: dict[int, float],
    source_quantile: float = 0.95,   # baseline quantile of interest
    target_quantile: float = 0.50,   # what it becomes in the projected distribution
) -> int | None:
    """First year where baseline 95th-pct Z becomes the 50th-pct of the projected Z.

    Returns None if no projected year achieves the shift within the config's horizon.
    """
```

**[DEFAULT — user may override]** Source/target quantiles for `quantile_shift_year`: 0.95 → 0.50 is the metric the 2026-05-13 entry mentioned by name ("When does the historical 95th percentile of Z become the new 50th percentile?"). Defensible. User may prefer 0.90 → 0.50 or 0.95 → 0.10.

**[DEFAULT — user may override]** `benchmark_lmp` for exceedance: defaults to a parameter; we'll need the user to pick a number. Reasonable starting point: the 99th-pct of historical LMP (matches the QR-full τ=0.99 quantile we already fit).

### `run.py`

```python
def run_projection(
    panel_path: Path,
    qr_full_dir: Path,
    config_path: Path,
    out_root: Path,
) -> None:
    """Orchestrate the projection layer:
      1. Load current Z distribution from analysis panel.
      2. Load QR-full response curves from outputs/qr_full/.
      3. Load growth scenarios from config YAML.
      4. For each scenario × report-year × τ ∈ {0.90, 0.95, 0.99}:
         - Project Z distribution forward
         - Apply response curve → projected LMP_τ
         - Compute exceedance hours/year above benchmark
      5. Compute quantile_shift_year per scenario.
      6. Write JSON output: outputs/projection/trajectories.json

    CLI: `surg-project [--config data/config/growth_scenarios.yaml]
                       [--panel data/interim/analysis_panel.parquet]
                       [--out-root outputs/]`
    """
```

Output schema (`outputs/projection/trajectories.json`):

```json
{
  "config_path": "...",
  "reference_year": 2025,
  "scenarios": {
    "base": {
      "description": "...",
      "growth_factors": {"2025": 1.0, "2030": 1.33, "2035": 1.66, "2040": 2.0},
      "trajectories": [
        {
          "year": 2030,
          "z_mean_factor": 1.33,
          "projected_lmp_quantiles": {"0.90": 156.3, "0.95": 198.7, "0.99": 425.1},
          "exceedance_hours_per_year_above_benchmark": 312.4
        },
        ...
      ],
      "quantile_shift_year_95_to_50": 2034,
      "quantile_shift_year_95_to_25": null
    },
    "low": { ... },
    "high": { ... }
  },
  "method_notes": {
    "scaling_method": "proportional",
    "response_method": "qr_full_linear",
    "benchmark_lmp_used": 268.3,
    "caveats": [
      "Linear extrapolation of QR-full slopes assumes the response is locally linear in Z; the actual response curve may bend at larger Z.",
      "Proportional scaling treats Z growth as fully proportional to DC load growth, overstating volatility if non-DC sources contribute to Z."
    ]
  }
}
```

## Test design

Each module gets its own test file under `tests/projection/`. Synthetic data; no real-panel dependence.

- **`test_growth_forecasts.py`** — config-loading roundtrip; linear vs exponential growth curve; out-of-range year clipping.
- **`test_z_distribution.py`** — proportional scaling preserves CDF shape; DC-attributed at dc_share=1.0 reproduces proportional; DC-attributed at dc_share=0.0 returns the unchanged distribution.
- **`test_exceedance.py`** — quantile_shift_year correctness on planted distributions; exceedance_hours boundary cases (benchmark above max, below min).
- **`test_run.py`** — end-to-end with synthetic panel + synthetic qr_full JSON + synthetic config → produces a valid trajectories.json with the expected schema.

## Open questions for user review

1. **Source/target quantiles for the headline metric.** I defaulted to 0.95→0.50 per the 2026-05-13 entry's framing. The proposal language ("permanently exceed the grid's stability threshold") could read instead as 0.99→0.95 (the current rare event becomes the new "5% of hours" level) or some other choice. Worth picking deliberately before plan-writing.
2. **Benchmark LMP for exceedance.** A specific dollar value (e.g., $268 = historical 99th-pct of total_lmp_cluster_mean) or a quantile-based reference (e.g., "current 99th-pct" rolled forward). I'd default to a dollar value the user picks based on what's policy-meaningful — perhaps $850 (the ORDC first-step penalty level) which has external policy meaning. **[DEFAULT — flagged for user]**
3. **Whether to include DC-attributed scaling.** Depends on whether the user can readily extract `dc_share_of_load` from JLARC/PJM data. If yes, robustness check; if no, drop with a one-line caveat in `method_notes`.
4. **Growth-curve shape.** Linear interpolation between 2025 and 2040 anchors vs. exponential (CAGR). JLARC reports a 2040 doubling figure; the curve between is not specified. Either is defensible. Linear is simpler and conservative for early years.
5. **Reference year.** I defaulted to 2025 because the analysis panel ends 2026-05; a 2025-anchored reference uses the full panel as historical baseline. Could instead use 2026 (panel end) or "panel median date".
6. **Output location.** Per existing convention, `outputs/projection/trajectories.json`. Could split into per-scenario files instead. Single file is simpler to interpret.

## How this design depends on the 2026-05-14 conditional-Z battery outcomes

The projection layer relies on the **QR-full response curves** (`outputs/qr_full/*.json`), NOT on the GPD conditional-Z mechanism test. Therefore:

- If the conditional-Z battery confirms the median-split rejection: the projection layer still works using QR-full slopes. The interpretive narrative changes (paper would say "even though the tail-heaviness mechanism is rejected, the moderate-quantile response is positive and projected growth still pushes the grid toward chronic high-LMP regime"), but the code is unaffected.
- If the conditional-Z battery's Spec A triggers Spec B (continuous ξ(Z) regression): the projection layer is still independent. Spec B's outputs would inform a future enhancement (e.g., projecting the *shape* of the LMP tail forward, not just the quantile level), but that's deferred.

Either way, the projection layer can be built and run before the conditional-Z application-of-pre-reg entry is written.

## Implementation effort estimate

~1 session of focused work to write the implementation plan (mechanical translation of this design into verbatim test + impl tasks). ~1-2 sessions to execute via subagent-driven-development on a sibling worktree (matching the Strategy C / conditional-Z pattern). Total: 2-3 sessions. Data acquisition (manual JLARC/PJM extraction) is independent and can happen in parallel.

## Risks

- **Linear extrapolation of QR-full slopes is fragile at large extrapolation distances.** The current Z distribution is the only data we have; projecting Z 2-3× beyond its historical max means trusting the response curve in regions never observed. The method_notes section in the output JSON flags this explicitly. Mitigation: report projected LMP_τ values alongside the "effective extrapolation factor" so reviewers can judge.
- **Growth-rate input uncertainty dwarfs modeling uncertainty.** A single low/base/high scenario sweep captures the dominant uncertainty source, but a single 2040 anchor point from JLARC is itself a forecast with its own ranges. Acceptable for v1; document the limitation.
- **Proportional scaling may overstate near-term volatility.** Non-DC load contributes to Z today, but the proportional model attributes all of Z's growth to DC. DC-attributed scaling (if user provides `dc_share_of_load`) addresses this directly.

## Implementation plan

The implementation plan will be written in `docs/plans/2026-05-14-jlarc-projection-implementation.md` AFTER user review of this design.
