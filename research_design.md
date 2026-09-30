# Research Design

## Research Question

**Main question:** How well can composition- and structure-derived descriptors, computed from Materials Project data, predict the DFT(PBE-GGA) electronic band gap of inorganic crystalline materials, and which descriptor classes contribute most strongly to that prediction?

**Secondary questions:**
1. How much predictive improvement, if any, does adding structure-derived descriptors (density, unit-cell size, crystal symmetry) provide over composition-only descriptors alone?
2. Which elemental descriptors (electronegativity, atomic radius, atomic number/mass statistics) are most predictive, and are the relationships chemically plausible given known band-structure theory?
3. Does model behavior differ systematically between transition-metal-containing and main-group compounds — and is that consistent with known limitations of GGA-level DFT for correlated d-electron systems?
4. Where does the model fail most systematically, and what does that reveal about the limits of aggregate composition/structure descriptors for electronic-structure prediction?

**Objectives:** build a reproducible, leakage-checked pipeline that (a) quantifies predictive performance honestly across train/CV/test, (b) isolates the marginal value of structural vs. compositional information, and (c) produces a chemically grounded account of what the model has and hasn't learned.

**Hypothesis:** Composition-based descriptors capture most of the band-gap variance (bonding character/electronegativity contrast); structural descriptors add a modest additional improvement, since aggregate statistics don't encode local orbital-overlap information. Transition-metal-containing compounds were expected to show higher error, consistent with GGA self-interaction/correlation-error issues for d-electron systems — see `interpretation_limitations_conclusions.md` for how this held up against the actual results.

## Chemical Scope

Three population options were compared (see the project's Stage 2 discussion, condensed here):

| Option | Chosen? | Reasoning |
|---|---|---|
| Full periodic-table inorganic crystals, metals and non-metals both included | **Yes** | Standard practice in the field; avoids selection bias; lets transition-metal behavior be tested, not assumed |
| Non-metals only (`band_gap > 0`) | No | Filters on the target itself before modeling — a form of selection bias |
| A specific chemical class (e.g. transition-metal oxides only) | No | Reduces statistical power/generalizability, and choosing it specifically because of the author's coordination-chemistry background would be convenience-driven, not scientifically motivated |

Transition-metal fraction is instead an **engineered feature and a subgroup-analysis axis**, so whether TM chemistry matters is discovered by the analysis rather than assumed by the sampling.

## Target Variable

`band_gap` from the Materials Project summary endpoint — DFT band gap at the PBE-GGA level. GGA is well documented to systematically underestimate band gaps relative to experiment. Predictions from this model should always be read as predictions of the *computational* quantity, not experimental band gap.

## Leakage Review

Excluded from all feature sets: `cbm`, `vbm` (algebraically define `band_gap`), `is_metal` (deterministic function of `band_gap == 0`), `efermi` and `is_gap_direct` (derived from the same electronic-structure calculation as the target). `formation_energy_per_atom`, `energy_above_hull`, and `is_stable` are independent thermodynamic quantities, not leakage, but were tested cautiously rather than assumed predictive.

## Train/Test Methodology

Primary split: grouped by formula (`GroupShuffleSplit`/`GroupKFold`), so polymorphs of the same composition never appear on both sides. Compared against a naive random split to quantify how much that naive approach overstates generalization (41.6% of random-test rows had a formula also present in random-train, in this project's data).

## Full Details

The complete Stage 2 planning document — including the full field-by-field data dictionary, the detailed feature-engineering plan, and the model/evaluation protocol — informed every subsequent notebook in `notebooks/`. This file summarizes the decisions that shaped the final pipeline; see `interpretation_limitations_conclusions.md` for how those decisions played out against the actual results.
