"""
Feature engineering for band-gap prediction from Materials Project data.

Builds composition-derived descriptors (elemental statistics via pymatgen)
and structure-derived descriptors (from Materials Project summary fields).
Mirrors the logic in notebooks/03_feature_engineering.ipynb -- see that
notebook for the full worked example, chemical-meaning documentation, and
the leakage review this module's output was checked against.
"""

import numpy as np
import pandas as pd
from pymatgen.core import Composition, Element

# Same transition-metal / main-group classification used throughout this project.
D_BLOCK = set([
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
])
F_BLOCK = set([
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
])

ELEMENTAL_PROPERTIES = ["Z", "atomic_mass", "electronegativity", "atomic_radius"]


def build_element_property_table(elements):
    """Look up Z, atomic mass, Pauling electronegativity, and atomic radius for a
    list of element symbols. Missing values (e.g. atomic_radius for noble gases)
    are left as NaN -- not imputed -- and should be checked with
    element_props[col].isna() before relying on completeness."""
    rows = []
    for el_symbol in sorted(set(elements)):
        el = Element(el_symbol)
        rows.append({
            "symbol": el_symbol,
            "Z": el.Z,
            "atomic_mass": float(el.atomic_mass),
            "electronegativity": float(el.X) if el.X is not None else np.nan,
            "atomic_radius": float(el.atomic_radius) if el.atomic_radius is not None else np.nan,
        })
    return pd.DataFrame(rows).set_index("symbol")


def composition_features(formula: str, element_props: pd.DataFrame) -> dict:
    """Composition-derived descriptors for one formula string.

    Returns fraction-weighted mean/std plus unweighted min/max/range for each
    property in ELEMENTAL_PROPERTIES, plus n_elements, frac_transition_metal,
    frac_main_group, and composition_entropy (Shannon entropy of elemental
    fractions). Raises if the formula cannot be parsed by pymatgen -- callers
    should catch this and log the failure rather than silently dropping rows
    (see notebooks/03_feature_engineering.ipynb, Step 5.3).
    """
    comp = Composition(formula)
    frac = comp.fractional_composition.get_el_amt_dict()  # {symbol: fraction}, sums to 1

    feats = {"n_elements": len(frac)}
    feats["frac_transition_metal"] = sum(f for el, f in frac.items() if el in D_BLOCK)
    feats["frac_main_group"] = sum(f for el, f in frac.items() if el not in D_BLOCK and el not in F_BLOCK)

    fracs = np.array(list(frac.values()))
    feats["composition_entropy"] = float(-(fracs * np.log(fracs)).sum())

    for prop in ELEMENTAL_PROPERTIES:
        values = np.array([element_props.loc[el, prop] for el in frac.keys()], dtype=float)
        weights = np.array([frac[el] for el in frac.keys()], dtype=float)

        if np.isnan(values).all():
            for stat in ["mean", "std", "min", "max", "range"]:
                feats[f"{prop}_{stat}"] = np.nan
            continue

        valid = ~np.isnan(values)
        v, w = values[valid], weights[valid]
        w = w / w.sum()

        w_mean = float((v * w).sum())
        feats[f"{prop}_mean"] = w_mean
        feats[f"{prop}_std"] = float(np.sqrt((w * (v - w_mean) ** 2).sum()))
        feats[f"{prop}_min"] = float(v.min())
        feats[f"{prop}_max"] = float(v.max())
        feats[f"{prop}_range"] = float(v.max() - v.min())

    return feats


def build_composition_features(formulas, element_props: pd.DataFrame = None):
    """Compute composition_features for each unique formula in `formulas`
    (an iterable of formula strings, one per row -- duplicates are computed
    once and reused). Returns (feature_dataframe, failed_formulas), where
    feature_dataframe has the same index/order as `formulas` and failed
    rows are NaN, not dropped.

    If `element_props` is omitted, it is built automatically by first parsing
    every unique formula to collect the elements present. Pass a pre-built
    table only if you already have one (e.g. reusing it across multiple
    feature-building calls) -- otherwise let this function build a complete
    one for you, so a formula containing an element missing from a
    hand-built table doesn't silently fail (as it would with a partial table)."""
    unique_formulas = pd.unique(pd.Series(formulas))

    if element_props is None:
        all_elements = set()
        for formula in unique_formulas:
            try:
                all_elements.update(Composition(formula).fractional_composition.get_el_amt_dict().keys())
            except Exception:
                pass  # unparseable formulas are caught again, and recorded, in the loop below
        element_props = build_element_property_table(all_elements)

    cache, failed = {}, []
    for formula in unique_formulas:
        try:
            cache[formula] = composition_features(formula, element_props)
        except Exception as e:
            failed.append((formula, str(e)))

    table = pd.DataFrame.from_dict(cache, orient="index")
    out = table.reindex(pd.Series(formulas).to_numpy())
    out.index = range(len(out))
    return out, failed


def encode_structure_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode crystal_system and select the numeric structural fields.
    space_group_number is deliberately excluded -- it's a cataloguing index
    (International Tables for Crystallography), not a meaningful numeric scale."""
    dummies = pd.get_dummies(df["crystal_system"], prefix="crystal_system")
    return pd.concat([df[["density", "density_atomic", "volume", "nsites"]], dummies], axis=1)
