# Stage 9 — Chemical Interpretation, Limitations, and Conclusions

## Predicting the Electronic Band Gap of Inorganic Crystalline Materials from Composition and Structure

This stage draws together the results of Stages 5–8 into a single scientific narrative. No new computation happens here — every number below was reported by the notebooks in earlier stages and is cited as such.

---

## 1. What was built

**Research question:** How well can composition- and structure-derived descriptors, computed from Materials Project data, predict the DFT(PBE-GGA) electronic band gap of inorganic crystalline materials, and which descriptors contribute most strongly?

**Data:** 154,377 records pulled from the Materials Project (`num_elements` 1–9, no chemistry-based restriction), reduced to 153,597 after basic quality control — 4 rows with a missing target, 0 deprecated, and 776 extreme thermodynamic outliers (`energy_above_hull` > 3.41 eV/atom, the 99.5th percentile). No blanket stability filter was applied: a candidate 0.2 eV/atom cutoff would have discarded 20.1% of the data for a reason unrelated to the electronic-structure question being asked, and the cutoff itself is not chemistry-independent (Stage 4).

**Features:** 24 composition-derived descriptors (elemental statistics — mean/std/min/max/range of atomic number, atomic mass, Pauling electronegativity, and atomic radius; plus transition-metal fraction, main-group fraction, and compositional entropy) and 11 structure-derived descriptors (density, atomic density, volume, site count, and one-hot crystal system), for 35 features total (Stage 5). 21 rows (0.014% of the data) have a missing elemental property, all traced to noble-gas-containing compounds; these were left as `NaN` rather than imputed.

**Modeling:** Five models (Dummy, Ridge, Random Forest, Extra Trees, HistGradientBoosting) trained on both a composition-only and a composition+structure feature set — ten configurations total — using a formula-grouped 80/20 split (123,384 train / 30,213 test rows, verified zero formula overlap) and grouped 5-fold cross-validation. Hyperparameters were fixed, standard values and were not tuned (Stage 6).

**Selected model:** ExtraTrees on composition+structure, chosen by lowest cross-validation MAE. Test MAE = 0.549 eV, test R² = 0.660, with 95% bootstrap confidence intervals of [0.533, 0.567] eV and [0.641, 0.676] respectively (Stage 7). The runner-up, Random Forest, was *not* clearly separated from ExtraTrees by cross-validation alone (CV gap 0.011 eV, smaller than the 0.02–0.03 eV fold-to-fold noise), but a paired bootstrap on the test set — which controls for shared test-set noise between the two models — did find a small, statistically clear advantage for ExtraTrees (test MAE difference −0.012 eV, 95% CI [−0.017, −0.007]). Both comparisons are reported because they use different statistical power, not because one is wrong.

---

## 2. Chemical Interpretation

*Everything in this section states predictive association, not causation. A feature the model found useful for prediction is not thereby a cause of the electronic band gap.*

### 2.1 Which descriptors matter, and does that make chemical sense?

Permutation importance and SHAP agree closely (Spearman rank correlation 0.913 — two independent methods converging on the same picture is a real consistency check, not a coincidence). The top features, by mean test-MAE increase when shuffled (Stage 8):

| Rank | Feature | MAE increase (eV) |
|---|---|---|
| 1 | `frac_transition_metal` | 0.201 |
| 2 | `frac_main_group` | 0.150 |
| 3 | `electronegativity_max` | 0.125 |
| 4 | `electronegativity_mean` | 0.114 |
| 5 | `electronegativity_std` | 0.107 |
| 6 | `electronegativity_range` | 0.087 |
| 7 | `atomic_radius_min` | 0.077 |
| 8 | `atomic_radius_mean` | 0.073 |
| 9 | `density` | 0.047 |

This is chemically plausible. Electronegativity contrast is a long-established proxy for bond ionicity, and more ionic bonding is generally associated with larger band gaps — consistent with the Stage 5 correlation table, where `electronegativity_max` correlated at +0.42 with the target. Transition-metal fraction dominates the ranking, consistent with the Stage 5 correlation (−0.38): more transition-metal character associates with smaller gaps, plausibly because many transition-metal compounds in this dataset are metallic or narrow-gap.

**Structural descriptors trail well behind composition.** The best-ranked structural feature, `density`, sits at rank 9 with less than a quarter of the top feature's importance, and `nsites` and `density_atomic` rank even lower. This is consistent with, though does not on its own prove, the interpretation that structure's contribution (confirmed statistically below) is real but diffuse — spread across several weak signals rather than concentrated in one dominant structural descriptor.

### 2.2 Does adding structural information help?

Yes, and this is one of the more statistically solid findings in this project. For **every** model tested, adding structural descriptors reduced test MAE, and every 95% bootstrap confidence interval on that reduction sat entirely below zero — in all 1,000 bootstrap resamples, the composition+structure version had lower error than the composition-only version (`share_resamples_structure_lower_MAE = 1.0` for all four non-dummy models, Stage 7). The size of the effect:

| Model | Test MAE change | 95% CI |
|---|---|---|
| ExtraTrees | −0.024 eV | [−0.028, −0.020] |
| HistGradientBoosting | −0.023 eV | [−0.027, −0.019] |
| Ridge | −0.020 eV | [−0.024, −0.016] |
| RandomForest | −0.015 eV | [−0.020, −0.009] |

The effect is statistically unambiguous but small in absolute terms (roughly 3–4% of the overall MAE). Notably, even the purely linear Ridge model gained a statistically clear improvement from structure, which suggests the structural signal being captured is not exclusively a nonlinear interaction effect that only tree ensembles could exploit — at least part of it is a fairly direct, near-linear relationship (plausibly density or volume correlating with bonding character). This matches the Stage 2 hypothesis reasonably well: composition does most of the work, and structure is a real but secondary contributor.

### 2.3 Does the model behave differently for transition-metal-containing compounds?

Yes, but the direction is the **opposite** of what the Stage 2 hypothesis anticipated, and the explanation is almost certainly compositional rather than a genuine chemistry win. The Stage 2 hypothesis expected transition-metal compounds to show *higher* error, reasoning from known GGA self-interaction/correlation-error issues for d-electron systems. Instead, transition-metal-containing compounds have *lower* MAE (0.486 eV) than main-group-only compounds (0.718 eV) (Stage 8).

This is best read alongside the band-gap-range result in the next section: transition-metal compounds are disproportionately metallic or small-gap in this dataset (Stage 4 already showed the population is roughly 73% transition-metal-containing, and Stage 5's correlation table showed transition-metal fraction correlates negatively with band gap). Since small-gap materials are, as shown below, the region where this model performs best, the lower TM-group MAE is plausibly an artifact of *which materials happen to fall in that group*, not evidence the model has learned to correctly handle d-electron physics. This project cannot distinguish between those two explanations with the current descriptor set — doing so would require conditioning on band gap magnitude within each group, which was not done here and is noted as future work.

### 2.4 Where does the model fail, and what does that reveal about the descriptors' limits?

This is the most chemically informative part of the analysis, and it shows a systematic, not random, failure pattern.

**Bias grows monotonically and severely with true band gap** (Stage 8):

| True gap range | Mean residual (predicted − true) |
|---|---|
| 0 eV (metal) | +0.303 |
| (0, 1] eV | +0.477 |
| (1, 2] eV | −0.204 |
| (2, 3] eV | −0.633 |
| (3, 4] eV | −0.862 |
| (4, 6] eV | −1.303 |
| > 6 eV | **−2.046** |

The model overpredicts near-zero gaps and increasingly underpredicts as the true gap grows, reaching a mean error of over 2 eV for the (small, 200-compound) wide-gap subset. This is the classic signature of regression toward the bulk of the training distribution, sharpened here by the fact that the target is heavily zero-inflated (Stage 4: 72,456 of 154,373 valid records are exactly metallic). The model has comparatively little data to learn from at high gap values, and aggregate composition/structure statistics evidently do not encode enough information to extrapolate reliably into that sparse region.

**The worst individual predictions name two specific, reproducible failure modes** (Stage 8):

1. **Simple covalent/molecular oxides, severely underpredicted.** CO₂ appears in the worst-20 list **three separate times** (three distinct polymorphs), each underpredicted by 4.5–6.1 eV; B₂O₃ and H₄C (methane-like) show the same pattern. These are genuinely wide-gap materials (CO₂'s true DFT gap here is 6.6–7.7 eV) whose molecular, discretely-bonded character is not something composition-weighted elemental statistics can distinguish from an extended ionic solid with similar elemental electronegativities.

2. **Rare-earth/heavy-element fluorides, severely overpredicted.** CeHf₂F₁₁, EuHfF₇, KCeF₄, and CeZr₂F₁₁ all have small true gaps (0.04–0.8 eV, near-metallic) but are predicted at 4.7–6.8 eV. The model has evidently learned "fluoride → large electronegativity contrast → large gap" as a strong general pattern (consistent with the top-ranked electronegativity features), but this specific chemical family — involving Ce, whose partially-filled f-orbitals can produce anomalous, structure-sensitive electronic behavior not well captured by GGA-level DFT in the first place — breaks that pattern.

Both failure modes point to the same underlying limitation: **the descriptor set captures average elemental character well but has no way to represent bonding topology (molecular vs. extended solid) or element-specific electronic anomalies (f-electron behavior)** that a full electronic-structure or graph-based representation would capture.

---

## 3. Limitations

- **DFT-PBE-GGA band gap underestimation.** The target itself is a computational proxy, not an experimental band gap. GGA is well documented to systematically underestimate gaps relative to experiment, particularly for wide-gap and correlated-electron materials — compounding, for those specific chemistries, with the model's own tendency to underpredict at high gap values (Section 2.4). Any downstream claim about a "predicted band gap" must carry this caveat.
- **No blanket stability filter.** The dataset intentionally retains highly metastable structures (up to 3.41 eV/atom above the hull, aside from the 0.5% extreme-outlier exclusion), on the grounds that DFT band gap is well-defined regardless of thermodynamic stability and that a global cutoff would be chemistry-dependent and bias-introducing (Stage 4). This means some fraction of the dataset may not correspond to experimentally realizable materials.
- **Materials Project coverage bias.** The database skews toward computationally tractable, ordered, high-symmetry structures and underrepresents disordered, defective, or amorphous materials — a limitation inherited from the data source, not introduced by this pipeline.
- **Composition/structure aggregate descriptors cannot represent full electronic structure.** As shown directly by the CO₂/B₂O₃ and rare-earth-fluoride failure cases, this descriptor family has no mechanism to encode bonding topology or element-specific orbital physics. A graph-based representation (e.g., CGCNN, MEGNet) would be expected to handle at least some of these cases better, at the cost of being a materially more complex and compute-intensive approach than was undertaken here.
- **Severe, systematic underperformance at high band gap.** Documented quantitatively in Section 2.4. Any application of this model to wide-gap materials (>4 eV) should be treated as unreliable, not merely "less accurate."
- **The transition-metal error result is ambiguous, not resolved.** As discussed in Section 2.3, this project cannot cleanly separate "the model handles TM chemistry differently" from "TM compounds happen to be concentrated in the easier, small-gap region of the data."
- **Grouped-by-formula split does not guarantee generalization to novel chemistry.** It prevents identical-composition leakage (verified: zero formula overlap, versus 41.6% overlap under a naive random split, Stage 6) but does not prevent chemically *similar* compounds (e.g., same chemical system) from appearing on both sides of the split. The reported test performance may still be optimistic relative to performance on truly novel chemical systems.
- **Hyperparameters are fixed and untuned**, by deliberate choice (Section 4 of the Stage 6/7 discussion) rather than oversight — the CV-vs-test agreement suggests this was a reasonable baseline choice, but a tuned model could plausibly perform somewhat better.
- **SHAP values were computed on a fixed 2,000-row sample of the test set**, not the full 30,213 rows, for computational feasibility. The strong agreement with permutation importance (computed on the full test set) suggests this sample is representative, but it is not a full-coverage result.
- **Single train/test split.** All test-set uncertainty estimates (Section 1) come from bootstrapping *within* one fixed split, which captures test-sampling variability but not variability from a different random split or different random seeds in the tree ensembles.
- **Missing elemental properties (21 rows, noble-gas-containing compounds)** were left as `NaN` rather than imputed; Ridge and the forest models were trained on the complete-case subset only, while HistGradientBoosting used all rows natively. This affects a negligible fraction of the data but is noted for completeness.

---

## 4. Conclusions

Composition- and structure-derived descriptors, computed entirely from Materials Project summary data, predict the DFT-PBE-GGA electronic band gap of inorganic crystalline materials with a test MAE of 0.549 eV and R² of 0.660 (ExtraTrees, composition+structure, 95% CI on both reported above). Structural descriptors provide a modest but statistically unambiguous improvement over composition alone, across every model tested — composition does most of the predictive work, and structure is a real, secondary contributor rather than a dominant one. The model's most important learned features (transition-metal fraction, electronegativity statistics) are chemically sensible and consistent with established bonding-ionicity intuition.

The model's most significant limitation is a strong, systematic bias that shifts from overprediction near zero gap to severe underprediction (over 2 eV, on average) for wide-gap materials — a direct consequence of the heavily zero-inflated, right-skewed target distribution and the model's limited ability to extrapolate into the sparse high-gap region of the data. Two specific, reproducible chemical failure modes were identified: severe underprediction of simple molecular/covalent oxides (CO₂, B₂O₃), and severe overprediction of small-gap rare-earth/heavy-element fluorides — both pointing to the same root cause, that aggregate elemental statistics cannot represent bonding topology or element-specific electronic anomalies.

This is a data-driven computational materials research project, not a novel scientific discovery, and its results should be read accordingly: as a demonstration of a complete, honestly-evaluated machine-learning pipeline for a real materials-informatics problem, with clearly documented and chemically grounded limitations, rather than as a claim of a new predictive capability.

---

## 5. Future Work

- **Hyperparameter tuning** of ExtraTrees/RandomForest via grouped cross-validation only (never against the test set), to establish whether the untuned baseline reported here is close to or well below the ceiling for this descriptor set.
- **Stricter chemical-system-level grouping** in the train/test split, to test whether performance holds up against genuinely novel chemistry rather than merely non-identical compositions.
- **Graph-based models** (e.g., CGCNN, MEGNet) as a direct comparison, specifically to test whether the CO₂/B₂O₃ and rare-earth-fluoride failure modes identified here are resolved by a representation that can encode bonding topology.
- **Separate modeling of the metal/non-metal classification and the non-metal gap magnitude**, rather than one regression across the full zero-inflated target, which could directly address the dominant bias pattern found in Section 2.4.
- **A targeted follow-up on the transition-metal question** (Section 2.3): re-run the metal-vs-main-group error comparison after conditioning on band-gap magnitude, to determine whether the lower TM-group error is a genuine chemistry effect or a population artifact.
- **Full-coverage SHAP** (rather than a 2,000-row sample), if a more efficient explainer or additional compute becomes available.
