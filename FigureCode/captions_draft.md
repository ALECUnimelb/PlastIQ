# Figure caption drafts

Current manuscript numbering: four main figures and six extended figures. Approval is recorded separately in `catalog.json`. Imported raster assets remain pending review.

Numerical captions use the current PBMT three-level and direct exposure-rule dataset; all drafts remain pending scientific/editorial review. Imported manuscript assets and the manually edited PPT have not been updated.

## Fig. 1

Fig. 1 | PBMT score coverage and concordance with PlastChem. (a) Availability of accepted computational and mapped PlastChem scores among 15,125 compounds. (b–e) Paired score comparisons for toxicity, bioaccumulation, mobility and persistence. Cell labels are selectively shown for readability. Shading represents within-domain fractions, scaled separately for each domain.

## Fig. 2

Fig. 2 | Priority landscape and component evidence profiles among 15,125 compounds. (a) Distribution of total priority scores S = H + E among 15,125 compounds, coloured by five-level priority class; labels show counts. The inset summarises priority classes and their recorded regulatory context. (b) Joint distribution of separately rounded hazard (H) and exposure-relevance (E) scores across all 289 integer combinations from 0 to 16. Cell labels show compound counts, including zeros; colour denotes priority level. Domain bands are low (0–3), moderate (4–7), high (8–11) and very high (12–16). The five-level matrix assigns 115 compounds to Level 1, 1,324 to Level 2, 3,647 to Level 3, 4,738 to Level 4 and 5,301 to Level 5. Level 1 requires H ≥12 and E ≥12; the complete classification matrix is defined in Methods. (c) Distributions of unweighted PBMT component scores distinguish missing evidence from evidence-supported zeros and display current scores of 0, 1 and 2; source-native curated scores remain preserved in the evidence archive. (d) Distributions of scores calculated directly under the revised exposure rules (0, 1 and 2) across five unweighted exposure dimensions; food-contact and human-biomonitoring evidence form one joint dimension. Partial evidence indicates that only one of these two indicators is available, whose contribution is retained. Missing inputs contribute zero only when scores are summed. A numerical zero does not establish absence of hazard or exposure.

## Fig. 3

Fig. 3 | GIC regulatory concordance and sensitivity to component weights. a, Distribution of recorded GIC categories within the five priority levels. Parentheses indicate group sizes; each compound is assigned its highest-precedence recorded category. b, Capture of compounds annotated as prohibited/phase-out or restricted/authorisation under four ranking approaches, screening the top 5% of the 15,125-compound inventory. Capture is the percentage of all 1,451 compounds with these annotations selected, rather than their percentage within the screened subset. The dashed line marks the integrated-score baseline of 17.13%. c, Capture after separately decreasing or increasing each component weight by 20%. Parentheses show changes from baseline in percentage points; blue and warm shading indicate decreased and increased capture, respectively. Percentages and changes are rounded independently. In b and c, boundary score ties receive equal fractional selection weights, giving 756.25 expected selections. Perturbed domain scores are rescaled to a theoretical maximum of 16 before half-up rounding; inventory omission rescales the remaining exposure inputs. Evidence and missing-data treatment are fixed, and official weights, scores and ranks are unchanged. Because GIC inventory evidence also contributes to scoring, these comparisons describe concordance rather than independent validation or optimal weights. An unmatched GIC record does not establish absence of regulation.

## Fig. 4

Fig. 4 | Sensitivity of five-level priorities to weights and classification thresholds. (a) Jaccard similarity between baseline and perturbed Level 1 or Level 1 + 2 lists. Each component weight is reduced or increased by 20% separately; each point shows the lower similarity of the two directions for that cohort. Rows are ordered by the lower of the two cohort values. The x axis begins at 40%. (b) Agreement with baseline under separately applied alternative assumptions: equal PBMT weights, equal exposure weights, halved inventory weight, or a hazard/exposure vH cutoff of 11 or 13 instead of 12. Overall level agreement is the percentage of compounds retaining the same five-level class; list Jaccard is intersection divided by union, including both departures and entrants. All displayed values are percentages. The baseline contains 15,125 compounds, with 115 in Level 1 and 1,439 in Levels 1 + 2. In weight scenarios, the affected domain is rescaled to a theoretical maximum of 16 before half-up rounding. Cutoff alternatives apply to rounded domain scores; the other boundaries remain 4 and 8. Evidence and missing-data treatment are fixed. These deterministic sensitivity scenarios do not establish optimal weights or provide confidence intervals.

## Extended Data Fig. 1

Extended Data Fig. 1 | Database assembly and use. Source records are resolved to compound identities, linked to hazard and exposure evidence, and delivered through a database and dashboard. Compounds unsuitable for QSAR remain in the inventory. Regulatory action and analytical-platform annotations provide context and do not contribute to the priority score

## Extended Data Fig. 2

Extended Data Fig. 2 | Assembly and source overlap of the chemical inventory. Source records (n = 87,209) are followed through structure resolution and final quality control to 15,125 full-InChIKey compounds. Counts before deduplication refer to records; later counts refer to compounds. The source-intersection panel shows exact combinations with at least 100 compounds (23 combinations; 13,221 compounds; 87.4% of the inventory). Source membership is nonexclusive.

## Extended Data Fig. 3

Extended Data Fig. 3 | PBMT availability and positive exposure-evidence patterns. (a) Exact combinations of nonmissing final PBMT scores, including evidence-supported zeros. Of 15,125 compounds, 8,550 have all four domains and 2,087 have none. (b) Exact combinations of positive scores across five exposure dimensions; 14,073 compounds have at least one positive dimension and 1,052 have none. Food-contact and human-biomonitoring evidence form one dimension. Complete source tables retain all 16 hazard and 32 exposure patterns, including zero-count combinations. The panels use distinct membership definitions and do not both measure missingness.

## Extended Data Fig. 4

Extended Data Fig. 4 | Primary uses, structural classes and regulatory profiles of Level 1 chemicals. The 115 Level 1 compounds satisfy hazard scores H ≥ 12 and exposure scores E ≥ 12. (a) Distribution across 17 primary-use groups, comprising 16 retained categories and Pending use review for 14 compounds, with one assignment per compound. (b) Distribution across nine mutually exclusive structural classes based on halogen content, aromaticity and heteroatom composition. X denotes F, Cl, Br or I; nitrogen/sulfur-containing aromatics may also contain oxygen. (c) Regulatory annotations from the Global Inventory Compiler (GIC). Multiple annotations are collapsed into one category using the precedence: prohibited/phase-out, restricted/authorisation, candidate/high concern, monitoring/reporting/hazard classification, then inventory/registration/use. Bars and labels show compound counts, summing to 115 in each panel. Regulatory annotations reflect recorded inventory associations rather than verified current legal status.

## Extended Data Fig. 5

Extended Data Fig. 5 | Compound-level evidence review illustrated with decabromodiphenyl oxide. The overview links chemical identity to hazard components, exposure proxies and total score. Aqueous mobility and long-range transport remain separate. The final B score reflects the structural halogen rule rather than the displayed QSAR logBCF prediction. Inventory points are capped at 2; FCChumon points use reported human detection. Regulatory status and analytical-platform predictions contribute no points. The sidebar item count includes collapsed chemical-family groups and is not the compound total.

## Extended Data Fig. 6

Extended Data Fig. 6 | A timeline presenting databases of PACs published within the last 5 years, the overall number of entries in each of databases and relationships between them.
