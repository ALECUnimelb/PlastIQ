# Figure code

The current manuscript contains **Fig. 1–4 and Extended Data Fig. 1–6**.
`publication_order.json` is the single source of publication numbering and order.
Use [INDEX.md](INDEX.md) and [SI_INDEX.md](SI_INDEX.md) for current files and review status.

Publication filenames are separate from stable implementation/data IDs:

| Publication | Internal module and data ID | Content |
|---|---|---|
| Fig. 1 | Fig2 | PBMT coverage and concordance |
| Fig. 2 | Fig3 | Priority landscape and evidence profiles |
| Fig. 3 | ExtendedDataFig3 | GIC regulatory concordance |
| Fig. 4 | Fig5 | Weight and threshold sensitivity |
| Extended Data Fig. 1 | Fig1 | Imported workflow diagram |
| Extended Data Fig. 2 | ExtendedDataFig1 | Inventory assembly and source overlap |
| Extended Data Fig. 3 | ExtendedDataFig2 | PBMT and exposure evidence patterns |
| Extended Data Fig. 4 | Fig4 | Level 1 uses, structures and regulation |
| Extended Data Fig. 5 | ExtendedDataFig4 | Imported dashboard screenshot |
| Extended Data Fig. 6 | DatabaseTimeline | Imported database timeline |

Historical module names, `result/figure_data/<internal ID>/`, metadata directories
and database evidence keys remain stable. In particular, the database `Fig4` key
still means Level 1 composition, now published as Extended Data Fig. 4. Never globally substitute
these identifiers when manuscript numbers change.

## Render by current publication name

```sh
.venv/bin/python FigureCode/run_plot.py --figure Fig3
.venv/bin/python FigureCode/run_plot.py --figure ExtendedDataFig6
.venv/bin/python FigureCode/verify_figures.py
```

The numerical renderers consume existing CSV tables and `plot_data.rds`; they do
not rescore compounds. Direct historical module entrypoints also publish to the
mapped current filenames. Layout and numbering work must not run preparation.
Scientific data updates still use `FigureCode/prepare_data.py` explicitly, with
stable internal IDs for `--figures`. Its default excludes imported raster assets.
Changed prepared inputs make dependent rendered figures stale until rebuilt.

The workflow, dashboard and timeline are imported from the supplied manuscript.
Their original raster bytes live in `result/figure_data/_dependencies/manuscript_assets/`.
`_metadata/<internal ID>/publication_asset.json` records the source document hash,
embedded image, image hashes and any retained historical evidence. Their publication
entrypoints restore those pinned rasters; they do not invoke the old workflow
renderer or silently recapture a different dashboard. These assets have PNG exports,
not newly created vector PDFs, and remain pending review until explicitly accepted.
Retained historical metadata does not claim that the imported image was built by
that historical code.

## Storage and verification

Images are flat in `result/figures/`; each current figure has one set. Unchanged
numerical inputs remain in `result/figure_data/<internal ID>/`. `_dependencies/`
contains required baselines and annotations; `_metadata/` contains provenance and
validation. Original build manifests keep internal filenames; `artifact_path()`
resolves the corresponding public filename exactly once. Retirement records account
for removed standalone Fig3b exports. Numbering transitions do not approve images.

Updates are staged, validated and installed as a complete result tree with rollback.
The source CSV, both SQLite databases, scores, ranks and Top-N membership are unchanged
by publication renumbering. Keep the SI workbook/PDF, retained identity list, structural
tree and old sensitivity figure. Do not recreate retired exploratory exports.

## Presentation

`node FigureCode/update_ppt.mjs` explicitly regenerates the sole PPTX in `result/`,
preserving its manual filename and using the ten registry entries in order. It has
no historical-deck dependency. Do not run it over manual PPT edits unless regeneration
is requested. For the manuscript reorder, the existing deck was edited locally:
its masters, layouts and first six existing figure frames were preserved, titles
and notes were synchronized, outdated GIC/dashboard images were replaced, and workflow
and timeline slides were added. SI pages and retained ancillary figures are excluded.

`manage.py approve <publication name>` explicitly accepts a reviewed public figure;
`manage.py index` refreshes the index. Acceptance is never implied by file replacement.
See [storage rules](../docs/results_layout.md).

The latest Fig. 3 / Extended Data Fig. 4 exchange updates the registry and PNG/PDF
filenames only. The manually edited PPT and external manuscript were not changed
in this phase; their numbering and numerical text still require synchronization.
