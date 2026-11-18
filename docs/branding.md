# PlastIQ naming and compatibility

The public product name is **PlastIQ**. The canonical local workspace remains
`/Users/ruiwang/Projects/APPs/PlastPrior`; the Python package, imports, module
commands, `plastprior` kernel ID and `PLASTPRIOR_*` environment variables remain
unchanged. Notebook presentation uses `PlastIQ.ipynb` and
`PlastIQ (Python 3.12)`. No ownership, licensing terms or third-party names are
changed. This repository still has no project LICENSE or CITATION.cff; a brand
change does not establish either one.

## Current files and legacy inputs

| Role | Current output | Accepted legacy input |
| --- | --- | --- |
| Publication | `PlastIQ_results.csv` | `PlastPrior_results.csv` |
| Analysis | `PlastIQ_results.sqlite` | `PlastPrior_results.sqlite` |
| Dashboard | `PlastIQ_dashboard.sqlite` | `PlastPrior_dashboard.sqlite` |

`plastprior/result_names.py` owns the names and input resolution. New exports
write PlastIQ names, including `PlastIQ_data_dictionary.csv` in the staged
publication package. Existing legacy sets are read using their original names.
An input directory containing both naming generations is rejected, even when
individual files appear usable; missing files never silently produce a new
empty SQLite database. Existing CSV/database pairing checks remain mandatory.

Keep `plastprior-publication-v1`, `plastprior-dashboard-v1`,
`plastprior-scenario-v1`, `plastprior-source-v1`, `plastprior-sankey-v1`,
`plastprior-level1-composition-v1`, `plastprior-ready-biodegradability-v1`,
`compact-v2`, stable figure IDs, table/field names and scoring-policy identifiers.
Saved scenarios continue to be associated with the exact CSV content hash.
The immutable baseline under `result/figure_data/_dependencies/baseline/`
retains its legacy names and original hashes.

## Byte-preserving delivery migration

`plastprior.name_migration.migrate` stages the complete result tree and renames
the three current files without writing database or CSV contents. It does not
run scoring, evidence enrichment, figure preparation, rendering or PPT creation.
Readers must stop before the coordinated directory replacement. The existing
update lock excludes cooperating writers; it is not a universal reader lock.

Validation checks every original file hash, including numerical tables, R
payloads, original dependencies, manuscript images, manual PPT edits and the
user attachment `Solène.xlsx`. Only the external relocation receipt and the
current scenario manifest's output filename keys are updated. A separate
replaceable `figure_data/_metadata/brand_rename.json` records the migration.
Source filename/hash dictionaries, run IDs, original build manifests and
database-embedded provenance retain their actual historical meaning.

Python and R path resolution follows explicit old-to-new mappings. Source code
and metadata hash transitions are recorded separately, without asserting a new
scientific calculation, image rendering or review approval. SI validation uses
these recorded hash transitions for the output-name-only manifest change.

The installation coordinates the result directory and current figure source
lock. Validation failure restores both; success removes the superseded tree.
An interrupted process may leave `.result-update.lock` and `.result-previous`;
inspect those recovery objects before any retry, and restore the matching source
lock from the prior recorded paths if manual crash recovery is necessary.

## Existing figure review limitation

Before this rename, `FigureCode/verify_figures.py` stopped at internal `Fig1`
because the imported asset referenced the prior CSV hash. Three imported assets
(current Extended Data Figures 1, 5 and 6) retain that reference and their review
status. Their image bytes match their recorded image hashes. Naming maintenance
does not resolve, overwrite or approve those historical source associations.
The full figure check must not be reported as passing until that separate review
is completed. Naming checks require no new failures or changes to scientific
data or figure bytes.

Deeper read-only checks also find that the existing numerical figure manifests
omit `source.policy.sha256`, while `managed.source_profile()` adds that key for
comparison. This mismatch is present against the saved pre-rename source lock
as well. It is retained as an existing full-manifest verification limitation;
the eight current prepared sets still pass their file/hash/source checks after
path resolution. Do not fill historical hashes merely to make review pass.

## GitHub and Dashboard handoff

The original repository is still `ALECUnimelb/PlastPrior` until a separately
approved repository rename is performed with an administrator login. Keep the
same owner, repository ID, history and access settings. After that rename, update
`origin`, the actual clone URL in the Windows guide, the README repository link,
repository description and any external archive or manuscript links. Do not
change a working clone URL to a nonexistent destination in advance.

The Dashboard already uses PlastIQ in its interface. Its runtime identifies
data by format, CSV SHA-256 and row count, not the uploaded basename. No protocol
or frontend deployment change is required solely for these filenames.

The separate Dashboard repository still needs its README and auxiliary scripts
updated to accept new and old input sets: `attach-plastprior-fig4.py`,
`attach-plastprior-sankey.py`, `verify-exposure-rules.mjs`,
`verify-plastprior-venn-selection.mjs`, `verify-plastprior-fig45.mjs` and their
fixtures. Keep script names and internal identifiers if callers depend on them.
Verify renamed uploads, paired detail evidence, Fig4, Sankey, Ready
Biodegradability and saved scenarios against the existing runtime.

Previously prepared upload ZIPs are not current result files. Do not publish
them as newly named deliveries without separately updating both the outer ZIP
name and its member name, then checking extracted database hashes. Published
historical archive versions must retain their original provenance.
