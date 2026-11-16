> Current publication: **Fig. 3**. `ExtendedDataFig3` is the stable internal code/data ID. Use the root publication registry and render entrypoint. Historical descriptions below retain internal IDs.

# Extended Data Fig. 3: GIC regulatory concordance

The current-data module replaces the former three-tier positive-input figure.
It is integrated into the manuscript build workflow and has been approved by
the user. Approval is recorded in the figure catalog. The GIC exploration module and draft
exports are retired; there is one current set of figure files.

```sh
# Explicit numerical preparation; scenario calculations never modify official results.
.venv/bin/python FigureCode/prepare_data.py --figures ExtendedDataFig3
# Read-only reproduction check in temporary staging.
.venv/bin/python FigureCode/prepare_data.py --figures ExtendedDataFig3 --check
# Layout rendering only; no score or scenario recomputation.
.venv/bin/python FigureCode/ExtendedDataFig3/run_plot.py
```

`prepare.py` prepares numerical tables, using exact integer-ratio half-up
rounding and independent Decimal checks. `prepare.R` invokes it and saves the
typed R payload through `setup.R`. `build.R` reads only that payload and draws
the three panels in R. Full methods are in `FigureCode/captions_draft.md`.

- Panel a: GIC composition within each of the five figure-level priority groups.
- Panel b: alternative rankings at a fixed 5% screening budget; the denominator
  for capture is all 1,451 prohibition/phase-out or restriction/authorisation
  compounds. Hazard-only and exposure-only are ranking references.
- Panel c: adjusted capture with change from the 16.99% baseline, under separate
  -20% and +20% component-weight scenarios. Parentheses contain percentage points.
- All 15,125 compounds are retained. Missing input scores contribute zero only
  to sums; their original missingness is retained in the compound audit table.
- Boundary score ties receive equal fractional selection weights. A 5% budget
  means 756.25 expected selections; captured counts are expectations, not a
  uniquely selected chemical list.
- Perturbed domains retain a theoretical maximum of 16, followed by half-up
  rounding. Removing inventory rescales the remaining exposure inputs. Official
  weights, scores, ranks and Top-N membership are never replaced.
- Supporting tables retain 1%, 5%, and 10% budgets and a secondary endpoint that
  additionally includes candidate/high-concern annotations. The figure uses only
  the prespecified 5% budget and the narrower prohibition/restriction endpoint.
- GIC annotations are frozen database context and overlap scoring sources. These
  comparisons are descriptive, not independent validation or weight optimization.

Images: `result/figures/Fig3.png` and `.pdf`.
CSV/JSON and RDS: `result/figure_data/ExtendedDataFig3/`.
Source/configuration hashes, preparation and build manifests, migration receipt
and QA: `result/figure_data/_metadata/ExtendedDataFig3/`.
No PowerPoint regeneration is part of this module.
