# Predicting the Electronic Band Gap of Inorganic Crystalline Materials from Composition and Structure

An independent, data-driven computational materials research project: composition- and structure-derived descriptors from Materials Project data are used to predict DFT-computed electronic band gaps, with a focus on honest evaluation and chemical interpretation over leaderboard performance.

## Table of Contents

- [Research Question](#research-question)
- [Scientific Background](#scientific-background)
- [Dataset](#dataset)
- [Methodology](#methodology)
- [Models](#models)
- [Results](#results)
- [Key Findings](#key-findings)
- [Chemical Interpretation](#chemical-interpretation)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [Reproducibility](#reproducibility)
- [Repository Structure](#repository-structure)
- [Citation](#citation)
- [Author](#author)

## Research Question

**Main question:** How well can composition- and structure-derived descriptors, computed from Materials Project data, predict the DFT(PBE-GGA) electronic band gap of inorganic crystalline materials, and which descriptors contribute most strongly to that prediction?

**Secondary questions:**
1. How much predictive improvement, if any, does adding structure-derived descriptors provide over composition-only descriptors?
2. Which elemental descriptors are most predictive, and are the relationships chemically plausible?
3. Does model behavior differ systematically between transition-metal-containing and main-group compounds?
4. Where does the model fail most systematically, and what does that reveal about the limits of aggregate composition/structure descriptors?

Full reasoning, hypotheses, and the chemical-scope decision are in [`docs/research_design.md`](docs/research_design.md).

## Scientific Background

Band gap is a central electronic property governing a material's conductivity, optical behavior, and suitability for semiconductor, photovoltaic, and catalytic applications. DFT calculations at the PBE-GGA level (as used throughout the Materials Project) are known to systematically **underestimate** band gaps relative to experiment, a consequence of self-interaction/derivative-discontinuity error in semi-local exchange-correlation functionals. This project predicts that computational quantity directly — not an experimental band gap — and this distinction is carried through the analysis and limitations.

## Dataset

- **Source:** [Materials Project](https://materialsproject.org), accessed via the modern `mp-api` / `MPRester` client.
- **Citation:** Jain, A. et al. (2013). *Commentary: The Materials Project: A materials genome approach to accelerating materials innovation.* APL Materials, 1(1), 011002. https://doi.org/10.1063/1.4812323
- **Population:** 154,377 records (`num_elements` between 1 and 9 — a broad, explicit filter chosen to avoid an undocumented backend routing quirk in `mp-api`, not a chemistry restriction). No restriction to any chemical class (transition metals, oxides, semiconductors); metallic materials (`band_gap == 0`) are deliberately retained.
- **Cleaning:** 4 records with a missing target were dropped; 0 were deprecated; 776 extreme thermodynamic outliers (`energy_above_hull` > 3.41 eV/atom, the 99.5th percentile) were removed as a data-quality decision, **not** a blanket stability/synthesizability filter — a candidate 0.2 eV/atom cutoff would have discarded 20.1% of the data for a reason unrelated to the research question. Final dataset: **153,597 records**.
- **Data is not committed to this repository** (raw pull is tens of MB and the source is a live, versioned database). See [`data/README.md`](data/README.md) for exact reproduction instructions, including the retrieval date and query parameters used.

## Methodology

1. **Acquisition** — `mp-api` query, verified against the live client schema before use (`notebooks/01_data_acquisition.ipynb`, `src/data_acquisition.py`).
2. **Inspection & cleaning** — dimension/type/duplicate/missing-value checks, stability-filter decision made from the observed distribution rather than assumed (`notebooks/02_data_inspection_eda.ipynb`).
3. **Feature engineering** — 24 composition-derived descriptors (elemental statistics via `pymatgen`) and 11 structure-derived descriptors, with an explicit leakage review (`notebooks/03_feature_engineering.ipynb`, `src/features.py`).
4. **Train/test split** — formula-grouped 80/20 split (123,384 / 30,213 rows), verified zero formula overlap, compared against a naive random split (41.6% formula overlap) to quantify leakage risk (`notebooks/04_modeling.ipynb`).
5. **Modeling** — 5 models × 2 feature sets, grouped 5-fold cross-validation, a single held-out test evaluation, fixed/untuned hyperparameters (`src/modeling.py`).
6. **Evaluation & selection** — model comparison by cross-validation MAE, bootstrap confidence intervals on test metrics, overfitting analysis (`notebooks/05_model_comparison.ipynb`).
7. **Explainability & error analysis** — permutation importance, SHAP, partial dependence, and error breakdowns by metallicity, transition-metal content, band-gap range, and crystal system (`notebooks/06_explainability_error_analysis.ipynb`).
8. **Interpretation** — chemical discussion, limitations, and conclusions (`docs/interpretation_limitations_conclusions.md`).

## Models

| Model | Role |
|---|---|
| Dummy (mean) | Reference floor |
| Ridge | Linear baseline |
| Random Forest | Robust nonlinear ensemble |
| Extra Trees | Randomized ensemble, different bias-variance trade-off |
| HistGradientBoosting | Efficient boosted trees, native missing-value handling |

## Results

Selected model: **Extra Trees, composition + structure features** (chosen by lowest grouped cross-validation MAE).

| Metric | Value | 95% CI |
|---|---|---|
| CV MAE | 0.566 eV | fold std ± 0.025 |
| Test MAE | 0.549 eV | [0.533, 0.567] |
| Test R² | 0.660 | [0.641, 0.676] |

| Feature set | Model | CV MAE | Test MAE | Test R² |
|---|---|---:|---:|---:|
| composition + structure | **Extra Trees** | **0.566** | **0.549** | **0.660** |
| composition + structure | Random Forest | 0.577 | 0.561 | 0.650 |
| composition + structure | HistGradientBoosting | 0.615 | 0.610 | 0.630 |
| composition + structure | Ridge | 0.948 | 0.948 | 0.328 |
| composition only | Random Forest | 0.586 | 0.575 | 0.632 |
| composition only | Extra Trees | 0.590 | 0.573 | 0.631 |
| composition only | HistGradientBoosting | 0.633 | 0.633 | 0.607 |
| composition only | Ridge | 0.971 | 0.968 | 0.311 |
| both feature sets | Dummy (mean) | 1.221 | 1.221 | ~0.000 |

Structural descriptors improved test MAE for **every** model (95% CI entirely below zero in all cases; 1,000/1,000 bootstrap resamples favored structure for every model). Full tables and the bootstrap methodology are in `notebooks/05_model_comparison.ipynb`.

## Key Findings

- Composition descriptors (especially transition-metal fraction and electronegativity statistics) drive most of the predictive signal; structure adds a small, statistically robust improvement (≈0.015–0.024 eV MAE reduction across models).
- Permutation importance and SHAP agree closely (Spearman rank correlation 0.913).
- The model shows a strong, systematic bias: it **overpredicts near-zero gaps** and **increasingly underpredicts as the true gap grows**, reaching a mean error of −2.05 eV for gaps above 6 eV.
- Two specific, reproducible chemical failure modes were identified: severe underprediction of simple molecular/covalent oxides (CO₂, B₂O₃), and severe overprediction of small-gap rare-earth/heavy-element fluorides.

## Chemical Interpretation

Full discussion, including the four secondary research questions answered in detail, is in [`docs/interpretation_limitations_conclusions.md`](docs/interpretation_limitations_conclusions.md).

## Limitations

DFT-PBE-GGA band gap underestimation vs. experiment; no blanket thermodynamic stability filter (dataset includes metastable structures); Materials Project's inherent coverage bias; aggregate elemental/structural descriptors cannot represent bonding topology or element-specific electronic anomalies; severe underperformance above ~4 eV; grouped split prevents identical-formula leakage but not chemically-similar-compound leakage; hyperparameters fixed and untuned by design; SHAP computed on a 2,000-row test sample. Full discussion in `docs/interpretation_limitations_conclusions.md`.

## Future Work

Hyperparameter tuning (CV-only); stricter chemical-system-level split; graph-based models (CGCNN, MEGNet) as a comparison, specifically for the identified molecular-oxide and rare-earth-fluoride failure cases; separate modeling of the metal/non-metal classification and non-metal gap magnitude; a targeted re-analysis of the transition-metal error result conditioned on band-gap magnitude; full-coverage SHAP.

## Reproducibility

```bash
git clone <this-repo-url>
cd <repo-name>
pip install -r requirements.txt
```

Get a free Materials Project API key at https://next-gen.materialsproject.org/api, then either run the notebooks in `notebooks/` in order (01 → 06), or use the standalone scripts in `src/` directly. See [`data/README.md`](data/README.md) for exact data-acquisition parameters and the original retrieval date. Random seed (42) is fixed throughout; package versions used are logged in each notebook's environment-setup cell.

## Repository Structure

```
.
├── README.md
├── notebooks/
│   ├── 01_data_acquisition.ipynb
│   ├── 02_data_inspection_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_modeling.ipynb
│   ├── 05_model_comparison.ipynb
│   └── 06_explainability_error_analysis.ipynb
├── data/
│   └── README.md
├── figures/
├── src/
│   ├── data_acquisition.py
│   ├── features.py
│   └── modeling.py
├── docs/
│   ├── research_design.md
│   └── interpretation_limitations_conclusions.md
├── requirements.txt
└── LICENSE
```

## Citation

If referencing this work, please cite the Materials Project as above, and this repository:

```
Kolawole Emmanuel Oluwaseyi (2026). Predicting the Electronic Band Gap of Inorganic
Crystalline Materials from Composition and Structure. GitHub repository.
```

## Author

**Kolawole Emmanuel Oluwaseyi** — First-Class B.Sc. Chemistry, University of Ibadan. Background in coordination/inorganic chemistry (synthesis and characterization of Ni(II)/Cu(II) complexes, IR/UV-Vis spectroscopy, magnetic susceptibility), combined with Python, SQL, and data analysis.
