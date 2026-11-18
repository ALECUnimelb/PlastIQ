# Display evidence and complete result delivery

This repair adds source evidence and packaging only. It does not execute VEGA,
recalculate scores, change weights, select candidates, change ADI thresholds,
change PBMT mapping, rerank compounds or alter Top-N membership. The original
`compounds` table, archived stage artifacts and baseline directory remain immutable.

## Reproduce the evidence-only release

From `/Users/ruiwang/Projects/APPs/PlastPrior`:

```sh
python -m plastprior.evidence_release
```

The command copies the current complete set to temporary staging under the
project root, enriches current compound evidence, re-prepares the seven current
numerical figures and SI evidence, and checks their scientific inputs for exact
equivalence. It builds both publication payloads from verified prepared files,
checks full-population invariance and all retained archive tables, and uses the
existing directory replacement/rollback mechanism under the result update lock.
A failure preserves the last complete set. Temporary and superseded files are
removed after completion. Only the fixed `result/` is a persistent delivery.
The manually named PPT and all existing image bytes remain unchanged. Review
status is not changed by a provenance refresh.

`figure_data/_metadata/evidence_release.json` is the replaceable validation report;
`scenario_manifest.json` records the current CSV/database hashes and delivery
status. `FigureCode/managed_sources.json` and the SI source pin are coordinated
with replacement and restored if post-install validation fails. Historical
render hashes remain recorded; an explicit code transition receipt distinguishes
numerically verified evidence refreshes from new rendering.

## Future scenario exports

`plastprior.scenario_export.export_scenario()` still creates a **data-only**
scenario from the immutable baseline. It now includes Ready Biodegradability
through the archived QSAR identity mapping, and reports
`pending_matching_figure_preparation_and_packaging` rather than claiming a
complete delivery. Existing score functions are unchanged.

For a new scored dataset, prepare all affected figures against that candidate
in staging, then call `plastprior.evidence_release.finalize_delivery(stage)`.
This rebuilds Fig4 and Sankey from matching prepared files, validates them and
the raw-to-export compound evidence, updates final file hashes, and marks the
Dashboard delivery complete. Never attach an old payload and merely replace its
hashes. The numerical preparation hook also packages Sankey whenever
ExtendedDataFig1 is prepared. Formal `install_package(..., result)` refuses an
incomplete delivery, including an absent or invalid Sankey.

The evidence-only release deliberately rejects changed figure values. Use the
separate scored-data/figure regeneration workflow for an actual scoring change.
Source-lock overrides (`PLASTPRIOR_SOURCE_LOCK`) direct R and Sankey preparation
to an unpublished candidate, without rewriting the live source lock mid-build.

## Sankey contract

Read `result/PlastIQ_dashboard.sqlite`:

```sql
SELECT format, csv_sha256, payload_sha256, payload_json
FROM publication_figures WHERE figure_id = 'ExtendedDataFig1a';
```

The stable internal ID is `ExtendedDataFig1a`, format `plastprior-sankey-v1`.
Display **Extended Data Figure 2a** in the manuscript-facing UI. The payload
retains `nodes`, `edges`, `connectors`, `summary` and `provenance`; the existing
Dashboard reader needs no format change. Fig4 and other rows are retained.

Validation binds the CSV and analysis hashes, six scientific/layout files,
source/compound/eligibility counts, node uniqueness, edge identity and direction,
flow conservation, layout bounds and finite coordinates. Final delivery compares
the stored payload with a newly reconstructed payload, including its hash.
Expected current data: 31 nodes, 55 edges, 87,209 source records, 57,839 resolved
records, 15,125 unique compounds and 11,236 QSAR-eligible compounds.

## Ready Biodegradability contract

Model: **Ready Biodegradability model (IRFMN), version 1.0.10**;
calculation core **1.3.19**; model ID `readybio_irfmn_2`.
Source report: `report_READYBIO_IRFMN_2.txt`, SHA-256
`9b454d909d5bff89c63e4e10377e57aae7315f17f0d8001d942bc67ab2b63b29`.

The original selected fields are archived at `stage3/qsar_predictions.csv` in
the full analysis database. Read them using `plastprior.export.read_artifact_records`.
The original report/configuration metadata are cross-checked with the archived
model summary and QSAR manifest. Full chemical identities join through
`qsar_inchikey`, frozen screening, input-row manifest and `qsar_identity_audit`.
This is an explicitly validated many-to-one join, never a result-row-position join.

The following fields are present in the CSV, analysis `scenario_results` and
`current_compounds`, and Dashboard `compound_audit`:

| Field | Meaning |
|---|---|
| `Ready_Biodegradability_prediction_raw` | Original `Predicted RB activity` text |
| `Ready_Biodegradability_assessment_raw` | Original `Assessment`, including explicit reliability/experimental wording |
| `Ready_Biodegradability_ADI_raw` | Original ADI text, including `-` when supplied |
| `Ready_Biodegradability_ADI` | Numeric ADI, or missing; actual numeric zero remains zero |
| `Ready_Biodegradability_similarity_index_raw` | Original `Similarity index` |
| `Ready_Biodegradability_accuracy_index_raw` | Original `Accuracy index` |
| `Ready_Biodegradability_concordance_index_raw` | Original `Concordance index` |
| `Ready_Biodegradability_ACF_index_raw` | Original `ACF index` |
| `Ready_Biodegradability_remarks_raw` | Original `Remarks` |
| `Ready_Biodegradability_reliability` | Only explicit LOW/MODERATE/GOOD reliability in Assessment; otherwise missing |
| `Ready_Biodegradability_status` | `predicted`, `not_classifiable`, `model_error`, `missing` or `identity_review_required` |
| `Ready_Biodegradability_identity_verified` | Frozen identity verification flag |
| `Ready_Biodegradability_identity_status` | Original audited identity status |
| `Ready_Biodegradability_qsar_inchikey` | QSAR structure key used for association |
| `Ready_Biodegradability_model_name` | Exact model name |
| `Ready_Biodegradability_model_version` | Exact model version |
| `Persistence_evidence` | Existing persistence evidence plus an independent supplemental object |

Dashboard key: `compound_audit.inchikey_std`; CSV/analysis key: `inchikey`.
The supplemental JSON path after parsing `Persistence_evidence` is:

```text
ready_biodegradability
  .prediction / .assessment / .adi / .reliability
  .assessment_basis / .status / .prediction_status
  .raw["Predicted RB activity"] / .raw["Assessment"] / .raw["ADI"]
  .raw["Similarity index"] / .raw["Accuracy index"]
  .raw["Concordance index"] / .raw["ACF index"] / .raw["Remarks"]
  .identity.inchikey / .identity.qsar_inchikey / .identity.verified
  .identity.status / .identity.reason / .identity.vega_row_no
  .model / .source / .used_in_scoring
```

Its format is `plastprior-ready-biodegradability-v1`; role is
`supplementary_display_only`; `used_in_scoring` is always false.
`.model` includes name, version, calculation-core version, report file and hash.
`.source` identifies archived prediction and identity artifacts and their hashes.
Definitions also appear in Dashboard `data_dictionary` and the metadata key
`ready_biodegradability`.

Missing parsed JSON values are `null`. CSV and TEXT database projections encode
missing as an empty string. Raw `-` stays `-`; do not cast it or an empty string
to zero. `Not classifiable` is a reported outcome, distinct from a missing report
or model calculation error. `(EXPERIMENTAL value)` sets
`assessment_basis="experimental_value"`; it does not imply a reliability label
or replace the separate original prediction. No new ADI cutoff is applied.

Display a separate **Ready Biodegradability — supplementary evidence** section
within Persistence, with conclusion, original Assessment, ADI, explicit reliability,
model version and source. Explain “not used in Persistence scoring.” Do not
replace IRFMN water/soil/sediment endpoints or modify score bars. If
`identity.verified` is false and status is `identity_review_required`, label the
association as requiring review and keep raw results in an expandable audit
section. If status is `missing`, show “No associated prediction.” A missing JSON
object in an older database means evidence is unavailable, not a negative result.

## Current coverage

| Measure | Count |
|---|---:|
| Original raw model rows | 10,655 |
| Raw rows with a prediction value | 10,653 |
| Raw ADI missing (`-`) | 1,055 |
| Full compounds with a mapped model record | 11,236 |
| Identity-verified mapped compounds | 11,221 |
| Identity-review compounds | 15 |
| Compounds without an associated report | 3,889 |
| Identity-verified class predictions | 10,147 |
| Identity-verified `Not classifiable` | 1,072 |
| Identity-verified model errors | 2 |
| All associated compounds with missing ADI | 1,078 |

The 15 review compounds retain 11 class predictions and four unclassifiable
outcomes for audit only. They are excluded from the identity-verified counts.
Raw record and compound counts differ because one QSAR structure can map to
multiple distinct full chemical identities; no full identity is merged.

## Changed implementation files and validation

- Compound evidence and export: `plastprior/ready_biodegradability.py`,
  `plastprior/scenario_export.py`.
- Publication evidence and delivery: `plastprior/sankey_evidence.py`,
  `plastprior/figure_evidence.py`, `plastprior/evidence_release.py`,
  `plastprior/result_storage.py`.
- Staged figure inputs and source verification:
  `FigureCode/ExtendedDataFig1/prepare_data.py`,
  `FigureCode/ExtendedDataFig3/prepare.py`,
  `FigureCode/Supplementary/Level1Identity/prepare.py`,
  `FigureCode/_shared/managed.py`, `FigureCode/_shared/managed.R`,
  `FigureCode/_shared/preparation.py`, `FigureCode/_shared/result_paths.py`.
- Current source pins: `FigureCode/managed_sources.json`,
  `FigureCode/Supplementary/SILevel1Evidence/source.json`.
- Regression coverage: `tests/test_ready_biodegradability.py`,
  `tests/test_sankey_evidence.py`.
- Documentation: `docs/methods.md`, `docs/rounded_scoring.md`, this document.
- Generated delivery: the three current CSV/SQLite files, current numerical
  preparation/provenance files, supplemental SI evidence fields, classification
  provenance and current validation records under `result/figure_data/`.

Full-population verification checks all 81 pre-existing CSV fields exactly,
270 pre-existing current-analysis fields and 276 Dashboard fields (with the
new supplemental JSON member removed before comparing existing persistence
content). All 15,125 identities and their row order, scores, weights, ranks,
levels, missingness and Top-N flags are unchanged. Top-N includes 127 compounds
because boundary ties are retained. The five level counts remain
115 / 1,324 / 3,647 / 4,738 / 5,301.

Every exported Ready Biodegradability field is checked against the archived
keyed source for all 15,125 compounds. The report includes representative raw
checks for predictions, unclassifiable outcomes, model errors, no association,
identity review, numeric-zero ADI and experimental Assessment wording.
Both SQLite integrity/foreign-key checks and source-flow conservation pass.
The original baseline and all retained archive tables are unchanged.

Validation commands used:

```sh
python -m unittest tests.test_ready_biodegradability tests.test_sankey_evidence \
  tests.test_scenario_export tests.test_result_storage tests.test_figure_evidence \
  tests.test_scoring_scenarios tests.test_hazard_score_mapping -q
python -m unittest discover -s FigureCode/tests -q
```

These cover 53 Python tests and 25 figure tests. The actual Dashboard Sankey and
Fig4 validators also accept the packaged payloads. No Dashboard source is edited
or deployed by this change; the supplemental evidence UI is a separate handoff.
No Git commit or push is performed.

The read-only Dashboard full-population parity script also passes for official
and fractional weights (15,125 rows × seven fields each), restoring defaults,
paired SQLite, missingness and component profiles. This validation does not
change the formal dataset or Dashboard source.
