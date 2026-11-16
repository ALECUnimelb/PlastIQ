# PBMT and exposure scoring: current implementation

Current status (2026-11-16): exposure is scored **directly by revised rules**.
The prior exposure mapping implementation was superseded after the user clarified
that the original 0.5 rule outputs themselves must become 1. The experimental
`exposure_score_mapping.py` and its mapping tests have been removed. PBMT mapping
and preservation of original PlastChem evidence remain as previously agreed.

## Current exposure rules and deliverables

- `plastprior/exposure_policy.json` now assigns 1 at the former 0.5 count thresholds.
- `production_score()` in `plastprior/exposure.py` directly returns at least 1
  for positive quantities and eligible positive qualitative market evidence.
- `score_selected_exposure_inputs()` recalculates inventory, patent, literature
  and production scores from selected raw counts, quantities, availability and
  market presence. It does not read an old component score to derive its result.
- Food-contact and human-detection binary scores, missingness, evidence selection,
  weights, rounding and ranking rules are unchanged. No new exposure
  `*_score_original` mapping columns are created. Original counts, quantities,
  evidence and historical calculations remain in the immutable baseline archive.
- Current rule policy: `exposure-three-level-rules-v1`.
- Current priority policy: `priority-pbmt-exposure-rules-rounded-v1`.
- The scoring configuration uses `exposure_score_policy`, **not**
  `exposure_score_mapping`. `--three-level-exposure` selects these direct rules
  together with the existing PBMT mapping. Legacy scenario policies can still
  reproduce their recorded scores from the immutable baseline.

The user authorized regeneration and direct replacement without old-figure
backups. CSV, both SQLite files, all seven numerical publication figures, their
prepared tables, the retained identity list/tree and the SI workbook/PDF have
been regenerated and installed as one validated set at `result/`. Imported
manuscript rasters and the manually edited PPT remain unchanged and explicitly
require updating/review. The existing historical sensitivity figure is retained.
Dashboard source now contains the corresponding frontend changes, confirmed by
read-only inspection on 2026-11-16. Deployment status was not verified during
this cleanup; no deployment was performed from this session.

Current levels: **115 / 1,324 / 3,647 / 4,738 / 5,301**. Level 1 membership remains
115 compounds; 14 primary uses remain pending review. Relative to the previous
PBMT-only dataset, 8,365 raw exposure totals, 6,113 rounded exposure/priority totals,
426 levels and 14,710 numeric ranks change. Top-100 membership including ties is
unchanged. All 15,125 current exposure indicator scores are 0, 1, 2 or missing.
Fig. 2d and the SI score palette no longer contain a 0.5 score category.

Validation: 34 targeted Python tests and R profile regression checks pass;
all current numerical manifests, data tables, count conservation, CSV/SQLite
score agreement and SQLite integrity checks pass. The SI workbook has 115 rows,
34 columns and two sheets; its four-page PDF includes every compound. New Fig. 2
and Fig. 3 were visually inspected. Fig. 3 baseline labels now read the data
(17.13%) rather than a hard-coded historical percentage; percentage axes retain
all segments despite floating-point summation at 100%. All figures remain pending
review rather than automatically approved. Temporary and superseded result sets
are removed after successful coordinated replacement.

## Dashboard implementation and cleanup (2026-11-16)

The actual ChemicalPrioDashboard working source now supports
`priority-pbmt-exposure-rules-rounded-v1` with
`exposure_score_policy: exposure-three-level-rules-v1`. It reads the supplied
`Exposure_*_score` component columns directly. It does not duplicate the backend's
raw-evidence scoring rules or add an exposure mapping. Changing weights only
recalculates domain totals, levels and ranks. Fractional exposure component
scores are rejected under the new policy; missing values stay missing.
PBMT mapping, original source evidence and legacy dataset support are preserved.

The handoff changes were confirmed in the actual Dashboard working tree using
`git apply --reverse --check` (read-only; no reverse application was performed).
No runtime or build references to the handoff patch were found. The completed
handoff patch has therefore been deleted with the user's authorization. Future
changes should edit the normal Dashboard source directly. The temporary build
workspace was already removed; no backup or replacement patch was created.

Retained implementation files include:
- `app/src/core/exposurePolicy.js`: policy identifiers, explanation text and
  raw-value positions for evidence bars; it does not calculate component scores.
- `app/src/core/scoringScenario.js`: policy validation, supplied-score weighting,
  levels and ranks, with policy-preserving reset and scenario reload.
- Existing evidence/UI modules: current score display, missingness, descriptions
  and exposure bars. Existing charts hide empty fractional-score categories.
- `app/src/core/exposurePolicy.test.js` and
  `scripts/verify-exposure-rules.mjs`: regression and full-population parity checks.

Validation previously completed in the isolated implementation copy:
- 191 core tests passed, including five new regression tests.
- Production Vite build passed.
- All 15,125 records matched Python for seven score/rank/tie fields under both
  official and fractional weights; restoring defaults matched the official data.
- Paired CSV/SQLite checks and profile count/missingness checks passed.
- Overview SVG markup rendered; no interactive browser/screenshot acceptance
  was claimed by this session.
- Modified files introduced no additional lint diagnostics. The two existing
  large UI components retained 18 pre-existing errors and three warnings.

The full-population check remains available from the Dashboard project root:

```sh
node scripts/verify-exposure-rules.mjs /Users/ruiwang/Projects/APPs/PlastPrior/result
```

This cleanup only removes the completed handoff file and updates this document.
It does not change Dashboard source, tests, scoring rules, data, figures or the
existing uncommitted work in either project. Browser acceptance and production
deployment status must be established from the Dashboard project separately;
this cleanup makes no claim that deployment is complete.

## Historical migration record (superseded where noted above)

# PBMT three-level scoring: staged migration

Follow-up status (2026-11-16): Phase 2 exposure mapping code and validation are
complete, pending user inspection. The new combined policy has **not** been
installed into the formal data or figures; `result/` still uses the PBMT-only
policy described below. See the exposure Phase 2 section at the end.

Status: Phase 6 local result replacement is complete. The current `result/`
contains PBMT three-level data and matching regenerated numerical figures and
SI workbook, pending user review. Dashboard compatibility is fixed locally;
deployment remains blocked by Cloudflare login. The manually edited PPT and
three imported manuscript rasters are preserved and still require updating or
review against the new scores. The legacy default policy remains available;
reproducing this dataset requires the explicit three-level policy.

## Rule and scope

| Selected source score | Current PBMT score |
|---|---|
| 0 | 0 |
| 0.25 | 1 |
| 0.5 | 1 |
| 1 | 1 |
| 2 | 2 |
| Missing | Missing |

The mapping is `pbmt-three-level-v1`; the corresponding priority policy is
`priority-pbmt-three-level-rounded-v1`. `three_level_policy()` explicitly selects
it. The exporter accepts `--three-level-hazard` or an explicit configuration.
The existing default policy remains unchanged during the staged migration.

Mapping runs after existing source selection and eligibility checks, but before
weighting, totals, classification and ranking. It applies to the four PBMT
components and, when present, Aquatic_M_score and LRTP_M_score. Exposure scores,
weights, domain cutpoints, domain rounding and ranking tie rules are unchanged.
Unknown source scores fail validation rather than being coerced.

## Original evidence remains intact

- Each mapped component has an added `<field>_original` column, for example
  `Persistence_score_original`. This is the selected pre-mapping component; it
  is not necessarily a PlastChem score.
- Source-native PlastChem scores, independent candidates, physical predictions,
  ADI values and source-selection explanations remain in the original evidence
  JSON and baseline archive. Those values are never overwritten by the mapping.
- The current CSV, SQLite `scenario_results` and `current_compounds`, and
  Dashboard SQLite `compound_audit` expose the same mapped component fields.
- Re-scoring mapped records retains their first original scores and checks for
  contradictions. Legacy-policy reproduction must use the preserved baseline.

The mapping is monotonic, so mapping an already selected maximum produces the
same current score as taking the maximum of mapped candidates. Existing source
provenance and tie choices are retained; additional ties introduced by merging
categories do not retroactively change which source was selected.

## Equivalent prediction boundaries

The original prediction functions remain available for baseline reproduction.
Applying the mapping to their output gives these current PBMT categories:

| Predictor | 0 | 1 | 2 |
|---|---|---|---|
| IRFMN persistence assessment | nP | nP/P or P/vP | vP |
| logBCF | <2 | >=2 and <3.7 | >=3.7 |
| logKoc | >=4 | >=2 and <4 | <2 |
| LRTP ratio | <0.25 | >=0.25 and <1 | >=1 |
| Fish acute LC50 (mg/L) | >100 | >1 and <=100 | <=1 |

These concern eligible predictions only. ADI and identity gates remain in force.
The LRTP ratio cutoff of 0.25 and ADI threshold of 0.5 are physical/eligibility
thresholds, not source scores, and must not be mapped.

## Review and subsequent phases

Phase 2 tests cover mapping and physical boundaries, missing evidence, retained
independent zero, exposure and rounding preservation, repeat scoring, ranking
ties, and agreement between synthetic CSV/SQLite exports and original evidence.

Before publishing actual results:

1. Generate and verify a temporary result set (Phase 3).
2. Update Dashboard calculations and score bars (Phase 4; implemented in the
   Dashboard project, with the additional Phase 5 finding below).
3. Map both independent and PlastChem scores for concordance, preserving both
   raw sides; update figure checks that currently compare selected raw evidence
   directly with final scores. Refresh all dependent figure data (Phase 5).
4. Validate and replace the complete result set together (Phase 6).

Exposure merging and removal of rounding remain separate decisions. The new
policy must not be used to publish a partially migrated result set.

## Phase 5 implementation and review (2026-11-16)

Publication Fig. 1 is implemented under `FigureCode/Fig2`; publication Fig. 2,
3 and 4 use internal IDs Fig3, Fig4 and Fig5 respectively.

- Concordance selects the scale from the dataset's explicit scoring policy.
  Both comparison sides use 0/1/2; paired raw independent, PlastChem and selected
  final scores remain in `*_score_raw` columns. The matrix becomes 3 by 3 and
  agreement bands become exact, one-level difference and two-level difference.
  Legacy datasets retain their original scale. Coverage and missingness stay
  unchanged; stored final scores are checked against mapped selected evidence.
- Hazard profiles omit the merged categories under the new policy. Exposure
  profiles and all exposure arithmetic/rounding remain unchanged.
- Landscape and sensitivity checks compare computed levels with every stored
  source level, rather than requiring the historical population counts.
- Level 1 identities are prepared with composition data in the same staging
  operation. Existing use annotations are retained verbatim by InChIKey; new
  members are explicitly `Pending use review`. Composition, retained identity
  list and tree use the current cohort size. The tree retains its overlap check.
- No source evidence, original research annotation, default scoring policy,
  formal source lock, approval status, imported manuscript image or PPT was
  changed. Frozen historical sensitivity assets remain frozen.

Temporary full-data validation:

| Check | Result |
|---|---|
| Python tests (scoring, export, storage and affected figure checks) | 91 passed |
| Dashboard core tests | 183 passed |
| R concordance regression | Legacy/new scale, raw preservation, missingness, count conservation and rejection of invalid scores passed |
| Dashboard/Python parity | 15,125 records × 28 fields, zero differences |
| Raw comparison evidence | All 60,500 rows retained, coverage unchanged |
| Current level counts | 115 / 1,253 / 3,531 / 4,757 / 5,469 |
| Level 1 annotations | Original 101 unchanged; 14 pending use review |
| Structure verification | All 115 SMILES regenerated the exact supplied InChIKey |
| Rendering | Main Fig. 1–4, Extended Data Fig. 2–4, retained list/tree and four SI evidence pages generated |
| Geometry checks | Source-overlap alignment passed; 115 tree labels, 124 edges, no label overlap or clipping |

| Comparison | Shared n | Exact n | Exact % | Mean absolute difference |
|---|---:|---:|---:|---:|
| Toxicity | 2,963 | 1,328 | 44.82 | 0.67634 |
| Bioaccumulation | 270 | 122 | 45.19 | 0.66667 |
| Mobility | 135 | 55 | 40.74 | 0.75556 |
| Persistence | 234 | 139 | 59.40 | 0.50427 |

An increase in exact agreement is partly inherent to merging categories; it
must not be described as improved predictive performance without that context.

### Remaining gate before Phase 6

`ChemicalPrioDashboard/app/src/core/level1Composition.js` still requires exactly
16 primary-use categories. The temporary candidate correctly has 17 categories,
including 14 pending annotations, and the current loader rejects it. This was
reproduced using the actual newly packaged SQLite payload. This session has no
write access to that project, so its file was not modified.

The minimal Dashboard follow-up is to derive category counts from the supplied
members while still rejecting duplicate categories, missing categories,
incorrect counts and mismatched CSV provenance; add a 115-member/17-category
regression. Alternatively, reviewed classifications for all 14 newcomers may
eliminate the pending category, but the loader should not assume a historical
category count. Do not silently merge pending uses into a known use category.

For publication, the 14 new use annotations need human review. At Phase 6,
regenerate the complete candidate, pair `managed_sources.json` and
`Supplementary/SILevel1Evidence/source.json` with it, and validate all dependent
tables together. Preserve the relocation receipt and fixed dependencies.
Replace the result set only through coordinated installation, update figure
review statuses without auto-approval, and explicitly review imported raster
assets against the new scores. PPT regeneration requires a separate explicit
instruction because the existing deck may contain manual edits.

Temporary validation files are removed after review checks; no parallel result
set is retained. Formal CSV/SQLite/PPT hashes and the complete formal-result
file inventory are checked before and after this phase.

## User inspection copy (2026-11-16)

At the user's request to inspect the new figures and data, one temporary set was
regenerated at `/tmp/PlastPrior_review/result/`. It contains the candidate CSV,
both SQLite databases, prepared figure data and rendered PNG/PDF files using
publication figure names. Its CSV matches the Phase 5 validation hash. Formal
results remain unchanged; all build copies and rendering intermediates were
removed. Keep this one inspection set until the user has reviewed it; do not
delete it before inspection or treat it as an approved/published result.

## Phase 6 authorization and preflight (2026-11-16)

The user authorized replacing the current `result/` with the new data and
figures, requesting that remaining issues be reported. This authorization
persists; it is not an approval of individual manuscript figures or a request
to overwrite manual PPT edits.

Preflight confirmed the candidate CSV/SQLite checksums and reproduced the
Dashboard composition-loader rejection with the actual 115-member/17-category
payload. `ChemicalPrioDashboard/app/src/core/level1Composition.js` still has
fixed category counts; this session cannot write to that project. Formal
replacement was held until that compatibility fix was verified (now resolved below).

The missing candidate `Supplementary_Table_Level1.xlsx` was generated with the
existing exporter: 115 rows, 34 columns, two sheets; every exported cell matches
the prepared SI payload, identifiers remain text, and filter/freeze/format checks
passed. Export intermediates were removed. The 14 pending use annotations remain
explicitly marked; they must not be fabricated to satisfy the old loader.

When the Dashboard fix is available, continue the already authorized coordinated
replacement. Preserve real dependency files (the temporary candidate currently
links to them), the retained historical sensitivity figure, imported manuscript
rasters and the manually named PPT. Mark stale imported images and PPT as needing
review/update, rather than implying that they use the new scoring dataset.

## Phase 6 local replacement completed (2026-11-16)

The Dashboard fix was independently rechecked: its composition loader accepts
the actual 115-member, 17-category payload, and all 15,125 records agree across
28 scoring/ranking fields. The 10 targeted Dashboard regression tests pass.

The complete staged directory was validated and installed at
`/Users/ruiwang/Projects/APPs/PlastPrior/result/` with rollback protection.
Source locks, figure manifests, preparation records and review catalog entries
were synchronized. Post-install verification confirmed CSV/SQLite equality,
both SQLite integrity checks, current figure/table hashes and the SI workbook.
The selected policy and counts are unchanged from the reviewed candidate:
115 / 1,253 / 3,531 / 4,757 / 5,469; 14 primary-use annotations remain pending.

Raw research dependencies, the manually named PPT, three imported manuscript
rasters and frozen historical sensitivity images were retained byte-for-byte.
Regenerated figures are marked for review, not approved. The PPT and imported
rasters are explicitly stale relative to the new scores; historical manuscript
and conference metadata have not been revalidated. Full manuscript readiness
must not be inferred from the successful numerical-set verification.

The installed CSV SHA-256 is
`90ca85bbb27cf2e2014b1510760236626aa439fb6d359f3302e5ae0b8e1155bb`.
The replaceable current receipt is
`result/figure_data/_metadata/publication_consistency.json`.
The old current-result copy and `/tmp/PlastPrior_review/` were removed after
successful installation. Original baseline research evidence remains preserved
under `_dependencies/`. No commit or online deployment was performed here.

## Follow-up Phase 1: Figure 3 / Extended Data Figure 4 exchange (2026-11-16)

Publication Fig. 3 now uses internal `ExtendedDataFig3` (GIC concordance);
Extended Data Fig. 4 uses internal `Fig4` (Level 1 composition). The registry,
indexes, documentation, existing numbering regression tests and the two caption
sections were synchronized. Their existing PNG/PDF bytes were exchanged at the
public paths; neither rendering nor numerical preparation was run. Caption
counts use the existing 115-member / 17-group composition and 16.65% GIC baseline.

The complete result tree was staged and replaced with rollback protection.
All scoring files, prepared numerical inputs, other figures, original evidence,
review states and the manually edited PPT remain byte-identical. The existing
manifest records the numbering hash transition, without claiming a new render.
Current numbering status is in `publication_consistency.json`; older numbering
receipts remain historical. Temporary staging is removed after validation.

The Dashboard local label registry already uses this order; it was not changed.
The external Word manuscript and PPT were not updated in this phase. Other
caption statistics need a final data-wide review after the exposure migration.
Exposure scores, thresholds, rounding and policy version are still unchanged.
Pause for user inspection before starting the exposure phase.

## Follow-up Phase 2: exposure mapping code and validation (2026-11-16)

The user authorized implementation of exposure 0.5 -> 1 after reviewing the
assessment. This phase changes scoring/export code and tests only, then pauses
for inspection. Formal CSV/SQLite, prepared figure data, images, PPT, Dashboard
code and deployment have not been updated by this phase.

### Implemented rule

- New mapping: `exposure-three-level-v1`, in
  `plastprior/exposure_score_mapping.py`.
- New combined policy: `priority-pbmt-exposure-three-level-rounded-v1`, selected
  by `three_level_exposure_policy()` or the exporter flag
  `--three-level-exposure`. This includes the existing PBMT mapping.
- Selected exposure component scores map 0 -> 0, 0.5 -> 1, 1 -> 1, 2 -> 2;
  missing stays missing. Mapping occurs before weights, totals, labels and ranks.
- Each of the six exposure indicators retains its first selected pre-mapping
  value in `Exposure_*_score_original`. Raw counts, quantities, source selection,
  evidence JSON and source-native scores remain unchanged. Food-contact and
  human-biomonitoring maxima remain 1; their current binary scores are unchanged.
- Repeated scoring is idempotent. Contradictory mapped/original scores, invalid
  discrete scores, unknown mappings and unsupported policies fail validation.
- Both the legacy and PBMT-only policies remain available. A mapped exposure
  record cannot be silently interpreted under a policy without exposure mapping;
  replay from the preserved baseline instead.
- Historical `exposure.py` and `exposure_policy.json` remain unchanged. Their
  threshold and production-fallback scores are mapped at the scoring boundary,
  preserving reproducibility without missing the production 0.5 special case.
- Exported current CSV, `scenario_results`, `current_compounds` and Dashboard
  `compound_audit` receive matching current/original fields. Metadata, data
  dictionary and implementation hashes describe the selected exposure policy.
- Weights, domain cutpoints, half-up rounding and tie handling are unchanged.
  Custom weights can still produce fractional weighted contributions.

### Verification completed

38 targeted tests passed across exposure mapping, original exposure rules,
PBMT mapping, scenario scoring and scenario export. Synthetic exports verify
paired CSV/SQLite fields, preserved original tables and original scores,
metadata, missing values and temporary-file cleanup. The CLI exposes the new
flag mutually exclusively with the existing policy options.

All 15,125 actual records were scored in memory with the new code. Current
exposure component scores contain no 0.5 values; original values are retained.
Re-scoring is identical. Scoring from the immutable baseline and upgrading the
current PBMT-only records agree in all 49 derived fields. Hazard scores and
non-derived evidence fields are unchanged.

| Change relative to current PBMT-only results | Compounds |
|---|---:|
| Raw exposure sum | 8,365 |
| Rounded exposure / priority total | 6,113 |
| Priority level | 426 |
| Numeric rank | 14,710 |
| Level 1 membership | 0 |
| Top-100 membership, including ties | 0 |

The calculated level counts are 115 / 1,324 / 3,647 / 4,738 / 5,301. These are
validation results, not a newly published dataset. The formal result tree still
has 288 files with exactly the same paths and SHA-256 hashes as before this phase.
No parallel result set, temporary script or test export was retained.

### Remaining work and risk

Phase 3 must update Dashboard policy support and explanations, prepare candidate
data with this explicit policy, update the exposure-profile classes/legend and
refresh affected numerical figures and tables consistently. The current
Dashboard has not been verified against this new policy; do not install new
data into it yet. Current Fig. 2d still shows 0.5 because its data and rendering
have intentionally not been replaced in this phase.

Phase 4 follows user review and validates the complete candidate set before
coordinated formal replacement and cleanup. Preserve manuscript/PPT edits;
update their contents only within the separately agreed scope. Implementation
risk is low-to-moderate; the scientific effect and cross-system synchronization
remain material, since 426 compounds change priority level. No commit or online
deployment was performed in this phase.
