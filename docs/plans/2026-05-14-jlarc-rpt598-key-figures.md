# JLARC Report 598 (2024) — Key Figures for Projection Layer

> **Status:** Extracted overnight 2026-05-14 from the JLARC Dec 2024 commission draft (`Rpt598-2.pdf`). User should verify these numbers against the final published version before they land in any paper-bound output. The extraction is meant to populate `data/config/growth_scenarios.yaml` (per the JLARC projection design at `docs/plans/2026-05-14-jlarc-projection-design.md`).

## Source

- **Title:** "Data Centers in Virginia" (2024)
- **Report number:** JLARC Report 598
- **Date:** December 9, 2024 (Commission draft)
- **URL:** https://jlarc.virginia.gov/pdfs/reports/Rpt598-2.pdf
- **Pages cited below:** specific page numbers in the PDF (matches the Commission-draft page numbering shown on each page)

## Numbers that map directly to the projection layer's config inputs

### 1. Current (2024–2025) NOVA data-center capacity

- **4,140 MW** in the "traditional Northern Virginia market" (Fairfax, Loudoun, Prince William counties, plus Manassas).
- Plus an additional ~**560 MW** in Culpeper, Fauquier, and the Richmond metro region (per the footnote to Fig 2-7).
- Source: **Figure 2-7** (p. 22), citing Cushman & Wakefield 2024 Global Data Center Market Comparison.

> **For the config's `dc_load_2025_mw` field:** use **4,140 MW** for a strict NOVA / DOM-zone-focused projection, or **4,700 MW** if including the I-95-corridor extension that JLARC describes as "expected" growth area.

### 2. Statewide Virginia aggregate energy demand — multi-scenario 2023 → 2040 forecasts

From **Figure 3-3** (p. 28), "Data center demand would drive immense increase in energy demand in Virginia." Y-axis is average monthly energy use in GWh; x-axis is calendar year 2023→2040.

Read off the chart's anchor values:

| Scenario | 2023 baseline (GWh/mo) | 2040 endpoint (GWh/mo) | Implied multiplier 2023→2040 |
|---|---|---|---|
| **Unconstrained demand** | ~10,500 | ~30,500 | **~2.90×** |
| **PJM forecast (adjusted)** | ~10,500 | ~27,500 | **~2.62×** |
| **Half of unconstrained demand** | ~10,500 | ~20,500 | **~1.95×** |
| **No new data center demand** | ~10,500 | ~12,500 | **~1.19×** (baseline non-DC growth) |

> **Visual extraction; the user should verify against the source figure's exact numbers if available.** JLARC may publish an Excel companion file with the underlying time series; if so, that's the preferred source.

**Important nuance for `growth_scenarios.yaml`:** Figure 3-3 reports *total Virginia statewide* monthly energy use, not DC-specific. The DC-attributable growth in each scenario is the differential against the "No new data center demand" trajectory:

| Scenario | 2040 DC-attributable energy growth (GWh/mo above no-new-DC) |
|---|---|
| Unconstrained | +18,000 |
| PJM forecast | +15,000 |
| Half-unconstrained | +8,000 |

> **For the config's `dc_load_2040_mw` field — recommended derivation.** Convert the DC-attributable energy growth to capacity (MW) by assuming load factor *f* and a 2040 horizon: `dc_load_2040_mw ≈ dc_load_2025_mw + (DC_attributable_2040_GWh_per_mo × 1000) / (f × 720 h/mo)`. JLARC implies a load factor in the 0.5–0.7 range for data centers; an *f* = 0.7 gives a conservative upper bound on growth.

### 3. PJM 2024 forecast for the Dominion transmission zone (annual rate)

- **5.5% year-over-year growth** in the Dominion transmission zone — PJM 2024 forecast (p. 27 narrative).
- Compounded: `1.055^15 ≈ 2.23×` by 2040 from a 2025 baseline.

> **Use case for the config's `growth_curve: "exponential"` mode.** The 5.5% YoY rate is well-aligned with the half-unconstrained scenario in Figure 3-3 (1.95× compares to 2.23× — same order of magnitude, slightly more aggressive). Either the linear interpolation between 2025/2040 anchors OR the exponential CAGR at 5.5% would be defensible. The user should pick one and document it in the config's `growth_curve` field per scenario.

### 4. Almost all demand growth is in the Dominion transmission zone

Direct quote from p. 27: "Almost all of the demand growth is expected to occur in the Dominion transmission zone."

> **Implication for the projection layer's geographic scope.** This validates using the *statewide* JLARC numbers (Figure 3-3) as a proxy for *DOM zone* growth, since the non-DOM zones (APCO, co-ops) contribute negligible DC growth.

### 5. Generation capacity needs by 2040 — Table 3-1

From **Table 3-1** (p. 29), "Addressing demand from data centers would require substantial investment in new in-state generation resources and transmission by 2040."

| Component | Current capacity | Scenario 1 (Unconstrained, No VCEA) net increase | Data center share |
|---|---|---|---|
| Generation (in-state) | 36,000 MW | +54,100 MW | **+35,600 MW (65.8% of growth)** |
| Generation (in-state, Scenario 2 — Half unconstrained, No VCEA) | 36,000 MW | +31,200 MW | **+12,800 MW (41% of growth)** |
| Transmission (interzonal) | 8,700 MW | +3,500 MW (Scenario 1) | **+3,500 MW (100%)** |
| Imported energy (annual) | 38 TWh | +62 TWh (Scenario 1) | **+79 TWh** |

> **Implication for `dc_share_of_load` (used by DC-attributed scaling in `z_distribution.py`).** Table 3-1's "Data center share" of generation capacity *additions* ranges from 41% (Scenario 2) to 65.8% (Scenario 1) of total growth. The DC share of *current* load (not growth) is a different number; **JLARC does not directly report this in the pages we've extracted**. The user may need to derive it from PJM Load Forecast Report data or estimate from NOVA capacity (4,140 MW) / total DOM peak load.

### 6. PJM reserve margin trajectory — Figure 3-5

From **Figure 3-5** (p. 35), "PJM projects available generating capacity could decline below reserve levels within a few years":

| Year | High entry of new generation (% reserve) | Low entry of new generation (% reserve) |
|---|---|---|
| 2023 | 26% | 23% |
| 2024 | 23% | 19% |
| 2025 | 21% | 17% |
| 2026 | 19% | 15% |
| 2027 | 17% | 11% |
| 2028 | 16% | 8% |
| 2029 | 17% | 8% |
| 2030 | 15% | 5% |

Historical minimum required reserve margin: 15–18%.

> **Implication for paper narrative (NOT for projection layer code).** Independent of the load-volatility → LMP projection, PJM's *capacity* reserve margin is projected to cross below the historical minimum 15% threshold under the low-entry scenario as early as 2027–2028. This is a separate-but-corroborating data point for "DC growth is straining PJM grid stability." Worth a cite in the paper's introduction.

## Numbers that need separate user extraction

The following are not present in the pages extracted (1-15, 19-38) but the user will likely need them:

- **Current (2024–2025) DOM-zone DC share of total DOM load** — needed for `dc_share_of_load` parameter. May be in Chapter 4 (Energy Costs, pages 43-56) or Appendix B (Research methods, pages 95+).
- **Year-by-year DC load projection trajectory** (not just 2023/2040 anchors). Likely in an Excel companion file to the JLARC report or in PJM's annual Load Forecast Report.
- **DOM-zone-specific 2040 forecast** (vs statewide Virginia numbers). PJM Load Forecast Report (annual publication, public, ~Q1 release) has DOM-zone breakouts.

## Suggested `growth_scenarios.yaml` based on what's extracted

This is a draft for the user to refine. **Numbers below are JLARC-derived where possible, but require user verification before they enter any production analysis.**

```yaml
# Generated from JLARC Rpt598-2 extraction 2026-05-14 (commission draft).
# User should verify against the final published JLARC report + cross-check
# against PJM Load Forecast Report (annual) for DOM-zone-specific data.

scenarios:
  low:
    description: "JLARC 'Half of unconstrained demand' (Scenario 2) — 1.95× by 2040"
    dc_load_2025_mw: 4140
    dc_load_2040_mw: 8073   # 4140 × 1.95
    growth_curve: "linear"
  base:
    description: "PJM 2024 forecast for Dominion transmission zone — 5.5% YoY"
    dc_load_2025_mw: 4140
    dc_load_2040_mw: 9236   # 4140 × 1.055^15 ≈ 2.23×
    growth_curve: "exponential"
  high:
    description: "JLARC 'Unconstrained demand' (Scenario 1) — 2.9× by 2040"
    dc_load_2025_mw: 4140
    dc_load_2040_mw: 12006  # 4140 × 2.90
    growth_curve: "linear"

projection:
  years: [2025, 2030, 2035, 2040]
  reference_year: 2025
  z_lmp_response_method: "qr_full_linear"
  metrics:
    - exceedance_hours          # primary: hours/year above $850 LMP benchmark
    - quantile_shift            # secondary: year when historical 95th-pct Z becomes new 50th-pct
    - mean_z_growth_factor
  benchmark_lmp: 850            # ORDC first-step penalty level
  extrapolation_warning_threshold: 2.0

# Optional (for DC-attributed scaling robustness path):
# Population this only if dc_share_of_load can be reliably estimated.
# dc_share_of_load: 0.30  # placeholder — user to verify from PJM/JLARC sources
```

## Caveats for user review

1. **Figure 3-3 is graphed values, not tabular data.** The 10,500 / 20,500 / 27,500 / 30,500 numbers are read off the chart's y-axis at the 2040 endpoint. Exact values may differ by ±500 GWh/mo from the source data. If JLARC publishes an Excel file, use that instead.

2. **The 4,140 MW NOVA figure is from a third-party report (Cushman & Wakefield 2024), not JLARC's own measurement.** The "Northern Virginia" geography in this figure is Fairfax+Loudoun+Prince William+Manassas — which is broader than our analysis's "Loudoun cluster" of 6 EHV pnodes. The mapping from "NOVA capacity in MW" to "load gradient growth at the Loudoun-cluster pnodes" requires an explicit modeling step the user should approve.

3. **The 5.5% YoY PJM figure is the 2024 forecast; PJM revises annually.** A subsequent revision could materially shift the base case. The projection layer should treat the config's growth rates as inputs subject to revision — the layer itself doesn't pin a calendar date.

4. **JLARC's "data center share" of generation growth (Table 3-1) is a generation-side number, not a load-side number.** "65.8% of new generation capacity is for DC" answers "how much generation must we build for DC" — not "what fraction of DOM load is DC." The user should derive `dc_share_of_load` from a different source (e.g., PJM zonal load forecast) rather than reading it from Table 3-1.

5. **The "Unconstrained" scenario JLARC labels as "VERY DIFFICULT TO ACHIEVE."** Using it as a projection input means projecting LMP under a counterfactual that JLARC's own infrastructure modeling shows is structurally implausible. Worth a paragraph in the paper's projection-section caveats.
