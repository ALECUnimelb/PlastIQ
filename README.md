# PlastIQ

PlastIQ is a framework for prioritising plastic-associated chemicals by
integrating chemical identity, hazard and exposure evidence. It provides
compound-level scores, priority classifications and traceable supporting evidence
for screening and subsequent assessment. The companion PlastIQ Dashboard supports
interactive exploration of the results and review of individual chemicals.

[Source code](https://github.com/ALECUnimelb/PlastIQ) ·
[Methods](docs/methods.md) ·
[Input data](docs/data_preparation.md) ·
[Technical documentation](#documentation)

## Scientific approach

The workflow combines chemical inventories and supporting evidence through
structure-based identity resolution, evidence integration and prioritisation.
Source identifiers, selected evidence and missing-data indicators are retained
alongside the results.

Hazard assessment covers persistence (P), bioaccumulation (B), mobility (M) and
toxicity (T). Exposure indicators cover food contact, human biomonitoring,
inventory occurrence, production and market evidence, patents and scientific
literature. The current scoring policy uses three-level PBMT scores (0, 1 and 2)
and direct exposure rules with outputs of 0, 1 or 2, while preserving original
source evidence and missing values.

Weighted hazard and exposure totals are rounded separately using half-up
rounding. Their sum determines the priority score and competition rank; a
hazard–exposure matrix assigns Levels 1–5. Level 1 represents the highest priority.
Ties at a Top-N boundary are retained. The implemented current policy is
`priority-pbmt-exposure-rules-rounded-v1`; its rules and provenance are documented
in the [scoring specification](docs/pbmt_three_level_scoring.md).

These scores support comparative screening. They do not constitute quantitative
risk estimates or establish that a chemical originates from plastics. Missing
evidence contributes zero to score sums but remains explicitly identified;
a low score therefore does not establish low concern or safety. Interpretation
requires consideration of evidence coverage, model applicability and sample
context.

## Data and result files

This repository contains analysis code, configuration and tests. Research inputs
and generated results are distributed separately and are not downloaded by
cloning the repository. Reproduction requires the exact input snapshots and
scoring configuration associated with the selected analysis. The
[input specification](docs/data_preparation.md) describes the required files;
the [source register](docs/data_access_register.json) records provenance and
source-specific access information.

For access to the matching research data and result package, contact
[ALEC-Chemistry](mailto:ALEC-Chemistry@unimelb.edu.au). A public data-archive DOI
is not yet provided in this README.

| File | Contents and intended use |
| --- | --- |
| `PlastIQ_results.csv` | Compound identities, selected evidence, scores, ranks, priority levels and missing-data indicators |
| `PlastIQ_dashboard.sqlite` | Detailed compound evidence and packaged figure data for the Dashboard; paired with the CSV by SHA-256 |
| `PlastIQ_results.sqlite` | Full analysis archive, including current results and retained source and audit records |
| `figure_data/` | Prepared figure tables, supporting dependencies and provenance metadata |
| `figures/` | Rendered figures and supplementary visual outputs |

Place the matching result package in `result/`. To explore it in the PlastIQ
Dashboard, load the CSV and its paired Dashboard SQLite file from the same
package. The full analysis database is intended for offline inspection.

In the full analysis database, `current_compounds` and `scenario_results`
contain the current scenario results. The original `compounds` table is retained
for baseline provenance and must not be used as a substitute for current scores.
The [result layout](docs/results_layout.md) and
[evidence specification](docs/evidence_delivery.md) describe the files and
embedded evidence in detail.

## Installation

Use 64-bit Python 3.12 and Git. From a terminal:

```sh
git clone https://github.com/ALECUnimelb/PlastIQ.git
cd PlastIQ
python -m venv .venv
```

Activate the environment using the command for your shell:

| Shell | Command |
| --- | --- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows Command Prompt | `.venv\Scripts\activate.bat` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |

Then install the declared dependencies:

```sh
python -m pip install -r requirements.txt
```

The requirements specify RDKit with InChI support and a pinned Global Inventory
Compiler Git revision. The similarly named PyPI package is not a substitute.
Direct dependencies are pinned; the complete transitive environment is not locked.
For native Windows launchers and platform-specific instructions, see the
[Windows installation guide](docs/windows.md).

## Reproducing the analysis

### Current scoring

Reproduction of the current scores starts from the matching immutable evidence
baseline, comprising a CSV and both SQLite databases. The current result CSV
alone does not contain every raw input needed for rescoring.

Run the following from the repository root, replacing the example paths with the
baseline location and a new candidate directory in a temporary workspace outside
the repository:

```sh
python -m plastprior.scenario_export \
  --source /path/to/frozen-baseline \
  --output /path/to/temporary-workspace/candidate \
  --three-level-exposure
```

The `--three-level-exposure` option selects both the current PBMT treatment and
the direct exposure rules. Omitting it selects an earlier scoring policy.
The source baseline is preserved.

This command creates a data-only candidate for comparison. A complete Dashboard
and publication package additionally requires figure evidence prepared against
that same candidate, packaging and validation, as described in the
[delivery procedure](docs/evidence_delivery.md#future-scenario-exports).
Validate candidates before replacing `result/`; retain one coordinated current
result set and remove temporary candidates after verification.

### Evidence reconstruction

To reconstruct the underlying evidence collection, prepare the frozen inputs
listed in the [data specification](docs/data_preparation.md), then follow the
[reproduction guide](docs/reproduction.md). The `main.py` workflow and
`PlastIQ.ipynb` implement this evidence-building pipeline. They retain baseline
scoring behaviour; running them alone does not select the current scenario
policy described above.

For the notebook interface, register the kernel and launch JupyterLab:

```sh
python -m ipykernel install --sys-prefix --name plastprior --display-name "PlastIQ (Python 3.12)"
python -m jupyterlab
```

Open `PlastIQ.ipynb` and select **PlastIQ (Python 3.12)**. The workflow reads frozen
VEGA reports and query outputs; it does not rerun VEGA or retrieve live source
databases. Exact source versions and supporting files are necessary for
reproduction.

## Verification

Run the fixture-based tests from the repository root:

```sh
python -m unittest discover -s tests -v
```

These tests exercise scoring boundaries, evidence handling and export behaviour
without requiring the research input collection. They do not establish complete
reproduction or successful installation on every platform.

For a reproduced dataset, compare records by full InChIKey, including component
scores, domain totals, ranks, ties, priority levels and missingness. Verify the
CSV–Dashboard database pairing, source fingerprints and figure-data provenance.
The [verification guide](docs/reproduction.md#verification) distinguishes
scientific-value comparisons from byte-level file checks. Independently generated
SQLite files may have different hashes because of run metadata, even when their
scientific contents agree.

## Documentation

| Topic | Reference |
| --- | --- |
| Evidence integration and analysis stages | [Methods](docs/methods.md) |
| Current PBMT and exposure rules | [Scoring specification](docs/pbmt_three_level_scoring.md) |
| Input snapshots and required file layout | [Data preparation](docs/data_preparation.md) |
| Environment, execution and comparison procedures | [Reproduction and verification](docs/reproduction.md) |
| Result storage and database contents | [Result layout](docs/results_layout.md) |
| Compound evidence and Dashboard packaging | [Evidence delivery](docs/evidence_delivery.md) |
| Publication figure implementations | [Main and extended figures](FigureCode/INDEX.md), [supplementary material](FigureCode/SI_INDEX.md) |
| Existing integrations and older data formats | [Compatibility](docs/branding.md) |

Technical documents include explicitly identified historical baselines and
validation records. Their counts and policies apply to the named versions;
they should not be substituted for the selected current analysis.

## Citation and licensing

When reporting analyses performed with PlastIQ, identify the code commit, data
version and scoring configuration used, and cite the original evidence sources.
Formal manuscript and archived-software citation details have not yet been added
to this repository.

PlastIQ source code is released under the [MIT License](LICENSE),
Copyright (c) 2026 The University of Melbourne. The PlastIQ Dashboard is a
publicly accessible web interface and is not part of this source release.
Third-party software and source datasets retain their respective terms and
attribution requirements; see the [source documentation](docs/data_distribution_checklist.md).

## Contact

PlastIQ is maintained under the
[ALECUnimelb](https://github.com/ALECUnimelb) account.
For research and data enquiries, contact
[ALEC-Chemistry@unimelb.edu.au](mailto:ALEC-Chemistry@unimelb.edu.au).
Report software issues through the
[repository issue tracker](https://github.com/ALECUnimelb/PlastIQ/issues).
