"""
Convert the O'Neill et al. (2018) supplementary dataset into ASP facts.

Source: O'Neill, Fanning, Lamb & Steinberger, "A good life for all within
planetary boundaries", Nature Sustainability 1, 88-95 (2018).
Supplementary data file: 41893_2018_21_MOESM2_ESM.xlsx

Values in the original data are ratios to a threshold:
- Biophysical indicators: ratio to the per-capita share of a planetary
  boundary. <= 1.0 means the boundary is respected, > 1.0 means overshoot.
- Social indicators: ratio to a threshold for a "good life". >= 1.0 means
  the threshold is met, < 1.0 means a deficit.

All ratios are scaled by 100 and rounded to the nearest integer so the ASP
encoding can use integer arithmetic (clingo has no native float support).
"""
import json
import re
import unicodedata
from pathlib import Path

import openpyxl

RAW_XLSX = Path(__file__).parent.parent / "data" / "raw" / "oneill2018_supp.xlsx"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ASP-safe identifiers for the dimension names used in the spreadsheet.
BIO_DIMS = {
    "CO2 Emissions": "co2",
    "Phosphorus": "phosphorus",
    "Nitrogen": "nitrogen",
    "Blue Water": "blue_water",
    "eHANPP": "ehanpp",
    "Ecological Footprint": "eco_footprint",
    "Material Footprint": "material_footprint",
}
SOC_DIMS = {
    "Life Satisfaction": "life_satisfaction",
    "Healthy Life Expect.": "healthy_life_exp",
    "Nutrition": "nutrition",
    "Sanitation": "sanitation",
    "Income": "income",
    "Access to Energy": "energy_access",
    "Education": "education",
    "Social Support": "social_support",
    "Democratic Quality": "democratic_quality",
    "Equality": "equality",
    "Employment": "employment",
}


def slug_country(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    return slug


def sheet_to_dict(ws, dim_map):
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0][1:]
    dims = [dim_map[h] for h in header]
    data = {}
    for r in rows[1:]:
        country = r[0]
        if not country:
            continue
        values = {}
        for dim, v in zip(dims, r[1:]):
            if isinstance(v, (int, float)):
                values[dim] = round(v * 100)
        data[country] = values
    return data


def main():
    wb = openpyxl.load_workbook(RAW_XLSX, data_only=True)
    bio = sheet_to_dict(wb["Biophysical"], BIO_DIMS)
    soc = sheet_to_dict(wb["Social"], SOC_DIMS)

    countries = sorted(set(bio) & set(soc))

    facts = []
    facts.append("% Auto-generated from O'Neill et al. (2018) supplementary data.")
    facts.append("% Scale: value = ratio-to-threshold * 100 (integer).")
    for dim in BIO_DIMS.values():
        facts.append(f"bio_dim({dim}).")
    for dim in SOC_DIMS.values():
        facts.append(f"soc_dim({dim}).")

    for country in countries:
        c = slug_country(country)
        facts.append(f"country({c}).")
        for dim, val in bio[country].items():
            facts.append(f"bio_value({c},{dim},{val}).")
        for dim, val in soc[country].items():
            facts.append(f"soc_value({c},{dim},{val}).")

    (OUT_DIR / "countries_facts.lp").write_text("\n".join(facts) + "\n")

    # Save a lookup table country name <-> slug, and the raw values, for the report.
    lookup = {slug_country(c): c for c in countries}
    (OUT_DIR / "country_names.json").write_text(json.dumps(lookup, indent=2, ensure_ascii=False))

    export = {c: {"bio": bio[c], "soc": soc[c]} for c in countries}
    (OUT_DIR / "all_values.json").write_text(json.dumps(export, indent=2, ensure_ascii=False))

    print(f"Exported {len(countries)} countries to {OUT_DIR/'countries_facts.lp'}")

    for name in ["Vietnam", "Costa Rica", "United States", "Cuba"]:
        if name in bio:
            print(f"\n{name}:")
            print("  bio:", bio[name])
            print("  soc:", soc[name])
        else:
            print(f"\n{name}: NOT FOUND in dataset")


if __name__ == "__main__":
    main()
