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

**[REVISED 2026-05-14 after advisor pass — flipping primary and conservative-simplification roles.]**

**DC-attributed scaling (primary if `dc_share_of_load` is available).** Treats current Z as `Z_dc + Z_other`. Assumes `Z_dc` scales with DC growth, `Z_other` stays constant.
```
Z_dc_current = Z_current × dc_share_of_load
Z_other = Z_current × (1 − dc_share_of_load)
Z_projected = growth_factor × Z_dc_current + Z_other
```

Requires `dc_share_of_load` (e.g., 0.30 if DC is currently 30% of DOM load). Source: JLARC Rpt598-2 + PJM load decomposition. This is the more defensible model — it explicitly says "DC growth scales the DC-attributed fraction of Z, not all of Z."

**Proportional scaling (conservative simplification — used as primary fallback if `dc_share_of_load` is unavailable).** Treats Z as fully attributable to DC growth:
```
Z_projected = growth_factor × Z_current
```

This is the *strong* claim — it assumes non-DC sources contribute zero to current Z, which is empirically false (residential / commercial load gradients exist even at 2-5 AM, just smaller). Use as primary only when `dc_share_of_load` is unobtainable, with an explicit caveat in `method_notes` of the output JSON: "primary model overstates DC contribution to load-gradient growth; treat as upper-bound trajectory."

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

**[REVISED 2026-05-14 after advisor pass — primary/secondary metric priority swapped.]**

**Primary metric: `exceedance_hours_per_year` above an externally-anchored LMP benchmark.** This number is interpretable to a policymaker without further context: "by year Y, the grid spends N hours/year above $850 (the ORDC first-step penalty level)." External policy anchoring beats internal distribution-shape diagnostics for paper headline.

**[DEFAULT — user may override]** `benchmark_lmp`: defaults to **$850/MWh** (ORDC first-step penalty level — externally documented in PJM's 2023 *Formation of LMP under Reserve Shortage Events* paper, cited in proposal). Alternative anchors the user might pick: $300 (PR second-step), $3700 (post-2022-10 cap level). A pure quantile-based anchor (e.g., historical 99th-pct of total_lmp) is also valid but less policy-meaningful.

**Secondary metric: `quantile_shift_year`** (the "95th-pct becomes new 50th-pct" framing). Useful as a distribution-shape diagnostic — answers "how compressed has the projected Z distribution become at the historical extremes?" — but not a policy-interpretable headline. Reported alongside the exceedance number, not as the headline.

**[DEFAULT — user may override]** Source/target quantiles for `quantile_shift_year`: 0.95 → 0.50, matching the 2026-05-13 entry's framing. User may prefer 0.90 → 0.50 or 0.95 → 0.10.

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

1. **Primary headline framing.** Confirm: primary metric is `exceedance_hours_per_year` above $850/MWh (ORDC first-step penalty level), secondary is the 0.95→0.50 quantile-shift year. (Default updated 2026-05-14 after advisor pass — was previously quantile-shift primary.)
2. **Benchmark LMP value.** Default $850 (ORDC first-step). User may prefer $300 (PR penalty), $3700 (post-2022-10 cap), or a quantile-based anchor (e.g., historical 99th-pct).
3. **Whether DC-attributed scaling is primary or fallback.** Depends on availability of `dc_share_of_load`. The user's extraction work from JLARC Rpt598-2 + PJM data determines this.
4. **Growth-curve shape between 2025 and 2040 anchors.** Linear vs exponential (CAGR). JLARC reports anchor points; the path between is not specified. Linear is simpler and conservative for early years; exponential matches a constant-growth-rate hypothesis.
5. **Reference year for the historical baseline.** Default 2025 (uses full panel as baseline). Alternative: 2026 (panel end), or "panel median date."
6. **Output location.** Per existing convention, `outputs/projection/trajectories.json`. Single file is simpler to interpret than per-scenario splits.
7. **Source/target quantiles for the secondary `quantile_shift_year`.** Default 0.95→0.50. User may prefer 0.90→0.50 or 0.95→0.10 depending on what "permanently past" reads as.
8. **Extrapolation factor threshold for the warning flag.** Default 2.0. Trajectories with `Z_max(year) / Z_max(historical) > 2.0` get marked `extrapolation_warning: true`. Threshold could be tighter (1.5) or looser (3.0).

## Load-bearing assumptions

Surfaced after advisor pass as the design's *central* analytical claims (not "caveats to footnote"). The paper must justify or qualify each one.

1. **QR-full response curves are linear in Z out to projected extrapolation distances.** The slopes `z_slope_τ` from the existing fit characterize the marginal response within the *historical* Z range. Projecting Z to 2× or 3× its historical max requires extrapolating those slopes into never-observed territory. The actual response curve may bend (saturate, accelerate, or change sign) outside the fitted range. Mitigation in code: every projected trajectory entry in the output JSON carries an `extrapolation_factor` field (= projected `Z_max(year)` / historical `Z_max`); if this exceeds **2.0**, the entry's `extrapolation_warning` flag is set `true` and a `caveats` array gets the entry "extrapolation factor > 2 — projected LMP_τ is outside the fitted slope's validity range; treat as suggestive, not predictive."

2. **DC growth is the dominant driver of load-gradient growth.** Both scaling models (proportional and DC-attributed) rest on this assumption — proportional in the strong form ("DC is the *only* driver"), DC-attributed in the weak form ("DC drives growth in the DC-attributable fraction"). If non-DC sources of load volatility also grow (e.g., electrification of heating, residential EV charging at scale), both models understate future Z growth. Out of scope to model; document as a known limitation.

3. **The QR-full fit's z_slope CIs at τ=0.99 cross zero on the production data.** This was the central Strategy C finding 2026-05-14: bootstrap CI `[-0.075, 1.194]` at τ=0.99 on the Loudoun-cluster congestion response. The projection layer at τ=0.99 inherits this uncertainty. Mitigation in code: at τ=0.99, the JSON output flags `slope_significant_at_95pct: false` for any pnode whose CI crosses 0, and the corresponding projection trajectory is marked `low_confidence: true`.

## How this design depends on the 2026-05-14 conditional-Z battery outcomes

The projection layer relies on the **QR-full response curves** (`outputs/qr_full/*.json`), NOT on the GPD conditional-Z mechanism test. Therefore:

- If the conditional-Z battery confirms the median-split rejection: the projection layer still works using QR-full slopes. The interpretive narrative changes (paper would say "even though the tail-heaviness mechanism is rejected, the moderate-quantile response is positive and projected growth still pushes the grid toward chronic high-LMP regime"), but the code is unaffected.
- If the conditional-Z battery's Spec A triggers Spec B (continuous ξ(Z) regression): the projection layer's *level* projection (LMP_τ trajectories) is still independent. **Spec B becomes load-bearing for projection IF AND ONLY IF Spec B's continuous slope β₁ is significantly different from zero** — in that case, a follow-up enhancement could project tail-heaviness forward (ξ as a function of projected Z), not just quantile levels. That enhancement is explicitly out of scope here; it would be its own design + plan once Spec B numbers are in. If Spec B never triggers or returns a null slope, no follow-up is needed.

Either way, the projection layer can be built and run before the conditional-Z application-of-pre-reg entry is written.

## Implementation effort estimate

~1 session of focused work to write the implementation plan (mechanical translation of this design into verbatim test + impl tasks). ~1-2 sessions to execute via subagent-driven-development on a sibling worktree (matching the Strategy C / conditional-Z pattern). Total: 2-3 sessions. Data acquisition (manual JLARC/PJM extraction) is independent and can happen in parallel.

## Risks

- **Growth-rate input uncertainty dwarfs modeling uncertainty.** A single low/base/high scenario sweep captures the dominant uncertainty source, but a single 2040 anchor point from JLARC is itself a forecast with its own ranges. Acceptable for v1; document the limitation.
- **`exceedance_hours_per_year` interpretation requires a consistent comparison baseline.** Reporting "Y hours/year above $850 in 2040" is only meaningful relative to a current baseline. The output JSON should report the *historical* exceedance hours at the same benchmark alongside the projected values; otherwise the magnitude is uninterpretable.

(The "extrapolation distance" and "proportional vs DC-attributed" concerns previously here have been promoted to first-class **Load-bearing assumptions** above per advisor pass — they are claims the paper must justify, not caveats to footnote.)

## Implementation plan

The implementation plan will be written in `docs/plans/2026-05-14-jlarc-projection-implementation.md` AFTER user review of this design.
