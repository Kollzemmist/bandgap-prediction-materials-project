"""
Data acquisition script for:
Predicting the Electronic Band Gap of Inorganic Crystalline Materials
from Composition and Structure.

Reproduces the Stage 3 raw-data pull from the Materials Project using the
modern mp-api / MPRester client. Requires your own, free Materials Project
API key (https://next-gen.materialsproject.org/api).

No API key is hard-coded anywhere in this file. Provide it via the
MP_API_KEY environment variable, or you'll be prompted securely at runtime.

Usage:
    export MP_API_KEY="your_key_here"
    python fetch_materials_project_data.py

Output:
    mp_bandgap_raw.csv                       (full raw dataset)
    mp_bandgap_raw_sample.csv                (first 200 rows, safe to commit)
    mp_bandgap_acquisition_metadata.json     (retrieval date, versions, query params)
    mp_bandgap_stage3_quality_report.json    (basic QA counts and descriptive stats)
"""

import json
import os
import sys
import platform
import importlib.metadata as importlib_metadata
from datetime import datetime, timezone
from getpass import getpass

import pandas as pd
from mp_api.client import MPRester

# mp_api itself does not expose a __version__ attribute -- installed-package
# metadata is the reliable way to get both this and pymatgen's version.
MP_API_VERSION = importlib_metadata.version("mp-api")
PYMATGEN_VERSION = importlib_metadata.version("pymatgen")

PLANNED_FIELDS = [
    "material_id", "formula_pretty", "formula_anonymous", "chemsys",
    "elements", "nelements", "composition", "composition_reduced",
    "band_gap",
    "nsites", "volume", "density", "density_atomic", "symmetry",
    "formation_energy_per_atom", "energy_above_hull", "is_stable",
    "deprecated",
]

# Broad, explicit filter. Deliberately NOT empty: an unfiltered .search() call
# routes through a different backend that also returns deprecated and
# separately-licensed GNoME-derived records outside the normal database view
# (documented on the Materials Project community forum). num_elements=(1, 9) is
# scientifically neutral -- it excludes no chemically realistic inorganic
# compound -- while keeping the query on the normal, filtered path.
QUERY_PARAMS = dict(num_elements=(1, 9))

D_BLOCK = set([
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
])


def get_api_key() -> str:
    key = os.environ.get("MP_API_KEY")
    if key:
        return key
    key = getpass("Enter your Materials Project API key (input hidden): ")
    if not key:
        sys.exit("No API key provided. Get one free at https://next-gen.materialsproject.org/api")
    return key


def doc_to_row(doc) -> dict:
    sym = doc.symmetry
    return {
        "material_id": str(doc.material_id),
        "formula_pretty": doc.formula_pretty,
        "formula_anonymous": doc.formula_anonymous,
        "chemsys": doc.chemsys,
        "nelements": doc.nelements,
        "elements": [str(e) for e in doc.elements] if doc.elements else None,
        "band_gap": doc.band_gap,
        "nsites": doc.nsites,
        "volume": doc.volume,
        "density": doc.density,
        "density_atomic": doc.density_atomic,
        "crystal_system": str(sym.crystal_system) if sym and sym.crystal_system else None,
        "space_group_symbol": sym.symbol if sym else None,
        "space_group_number": sym.number if sym else None,
        "formation_energy_per_atom": doc.formation_energy_per_atom,
        "energy_above_hull": doc.energy_above_hull,
        "is_stable": doc.is_stable,
        "deprecated": doc.deprecated,
    }


def main():
    api_key = get_api_key()

    with MPRester(api_key) as mpr:
        available = mpr.materials.summary.available_fields
        missing = [f for f in PLANNED_FIELDS if f not in available]
        if missing:
            sys.exit(
                f"Planned fields not found in current mp-api schema: {missing}\n"
                "Investigate the schema change before proceeding -- do not silently substitute field names."
            )

        id_only_docs = mpr.materials.summary.search(
            **QUERY_PARAMS, fields=["material_id", "deprecated", "band_gap"]
        )
        total_returned = len(id_only_docs)
        n_deprecated = sum(1 for d in id_only_docs if d.deprecated)
        n_missing_bandgap = sum(1 for d in id_only_docs if d.band_gap is None)

        print(f"Total records returned by query:  {total_returned}")
        print(f"Deprecated records:                {n_deprecated}")
        print(f"Records with missing band_gap:     {n_missing_bandgap}")

        all_docs = mpr.materials.summary.search(**QUERY_PARAMS, fields=PLANNED_FIELDS)

    raw_df = pd.DataFrame([doc_to_row(d) for d in all_docs])
    raw_df.to_csv("mp_bandgap_raw.csv", index=False)
    raw_df.head(200).to_csv("mp_bandgap_raw_sample.csv", index=False)

    metadata = {
        "retrieval_datetime_utc": datetime.now(timezone.utc).isoformat(),
        "mp_api_version": MP_API_VERSION,
        "pymatgen_version": PYMATGEN_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "query_parameters": QUERY_PARAMS,
        "fields_requested": PLANNED_FIELDS,
        "filtering_applied": {
            "deprecated_excluded_from_bulk_pull": False,
            "missing_band_gap_excluded": False,
            "energy_above_hull_cutoff": None,
        },
        "n_records_retrieved_before_qa": total_returned,
        "n_deprecated": n_deprecated,
        "n_missing_band_gap": n_missing_bandgap,
        "n_records_in_raw_csv": int(raw_df.shape[0]),
    }
    with open("mp_bandgap_acquisition_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    report = {
        "n_records_retrieved": int(raw_df.shape[0]),
        "n_deprecated": int(raw_df["deprecated"].sum()),
        "n_missing_band_gap": int(raw_df["band_gap"].isna().sum()),
        "n_with_band_gap": int(raw_df["band_gap"].notna().sum()),
        "n_metallic_bandgap_zero": int((raw_df["band_gap"] == 0).sum()),
        "n_positive_band_gap": int((raw_df["band_gap"] > 0).sum()),
        "missing_values_by_column": {
            k: int(v) for k, v in raw_df.isna().sum().items() if v > 0
        },
        "band_gap_descriptive_stats": raw_df["band_gap"].describe().to_dict(),
        "energy_above_hull_descriptive_stats": raw_df["energy_above_hull"].describe().to_dict(),
        "n_transition_metal_containing": int(
            raw_df["elements"].apply(
                lambda els: bool(set(els) & D_BLOCK) if isinstance(els, list) else False
            ).sum()
        ),
        "n_unique_chemsys": int(raw_df["chemsys"].nunique()),
    }
    all_elements = set()
    raw_df["elements"].dropna().apply(
        lambda els: all_elements.update(els) if isinstance(els, list) else None
    )
    report["n_unique_elements"] = len(all_elements)

    with open("mp_bandgap_stage3_quality_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(json.dumps(report, indent=2, default=str))
    print("\nDone. Raw data, sample, metadata, and quality report written to the current directory.")


if __name__ == "__main__":
    main()
