# Fig. 5: sensitivity of five-level priorities

`prepare.R` prepares individual ±20% weight experiments and eight alternative-setting scenarios from the locked current evidence. `build.R` renders the prepared tables without recalculation. Only necessary axis labels, legends and panel letters appear in the image; the methods and metric definitions are in the Fig. 5 section of `FigureCode/captions_draft.md`.

```sh
.venv/bin/python FigureCode/prepare_data.py --figures Fig5
.venv/bin/python FigureCode/Fig5/run_plot.py
```

Current PNG/PDF: `result/figures/Fig5.*`. Paired CSV tables and `plot_data.rds`: `result/figure_data/Fig5/`. Source/configuration hashes and validation: `result/figure_data/_metadata/Fig5/`.

Scenario scores are temporary analytical values only. Official scores, ranking and Top-N membership are never overwritten. Missing evidence contributes zero only to sums. Each domain retains a theoretical maximum of 16, with exact rational half-up rounding. Baseline cohorts contain 101 Level 1 and 1,220 Level 1 + 2 compounds. Jaccard includes entrants and departures. Panel a independently selects the lower of the two directions for each cohort, with both directions retained in `weight_scenarios.csv`.
