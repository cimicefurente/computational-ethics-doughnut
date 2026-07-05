"""
Benchmark each lever's assumed effect size against the empirical spread of
the corresponding indicator across the 151 countries in the O'Neill et al.
(2018) dataset.

Rationale: the lever effects in levers.lp are illustrative (no causal,
per-country policy-effect dataset exists), but they must be
*representative*: no assumed effect should be larger than the variation
already observed between real countries on that dimension. This script
makes that check explicit and reproducible, and writes a markdown table
used directly in the report's methodology section.
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).parent
DATA = SRC.parent / "data" / "processed"
REPORT = SRC.parent / "report"

BIO_DIMS = ["co2", "phosphorus", "nitrogen", "blue_water", "ehanpp",
            "eco_footprint", "material_footprint"]
SOC_DIMS = ["life_satisfaction", "healthy_life_exp", "nutrition", "sanitation",
            "income", "energy_access", "education", "social_support",
            "democratic_quality", "equality", "employment"]


def percentile_stats(values):
    vals = sorted(values)
    n = len(vals)
    return {
        "n": n,
        "min": vals[0],
        "max": vals[-1],
        "iqr": vals[int(n * 0.75)] - vals[int(n * 0.25)],
        "p10_90": vals[int(n * 0.9)] - vals[int(n * 0.1)],
    }


def load_lever_effects():
    """Parse affects_bio/affects_soc facts directly out of levers.lp."""
    text = (SRC / "levers.lp").read_text()
    effects = []  # (lever, kind, dim, delta)
    pattern = re.compile(r"affects_(bio|soc)\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(-?\d+)\s*\)\.")
    for m in pattern.finditer(text):
        kind, lever, dim, delta = m.groups()
        effects.append((lever, kind, dim, int(delta)))
    return effects


def main():
    data = json.loads((DATA / "all_values.json").read_text())

    dim_stats = {}
    for d in BIO_DIMS:
        dim_stats[d] = percentile_stats([c["bio"][d] for c in data.values() if d in c["bio"]])
    for d in SOC_DIMS:
        dim_stats[d] = percentile_stats([c["soc"][d] for c in data.values() if d in c["soc"]])

    effects = load_lever_effects()

    rows = []
    for lever, kind, dim, delta in effects:
        stats = dim_stats[dim]
        pct_iqr = round(100 * abs(delta) / stats["iqr"]) if stats["iqr"] else None
        pct_p1090 = round(100 * abs(delta) / stats["p10_90"]) if stats["p10_90"] else None
        flag = "AMBITIOUS" if pct_iqr and pct_iqr >= 45 else "conservative"
        rows.append((lever, dim, delta, stats["iqr"], pct_iqr, stats["p10_90"], pct_p1090, flag))

    rows.sort(key=lambda r: -(r[4] or 0))

    lines = [
        "| Lever | Dimension | Assumed delta | Real IQR | % of IQR | Real P10-P90 | % of P10-P90 | Flag |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r[0]} | {r[1]} | {r[2]:+d} | {r[3]} | {r[4]}% | {r[5]} | {r[6]}% | {r[7]} |"
        )
    table_md = "\n".join(lines)

    REPORT.mkdir(exist_ok=True)
    (REPORT / "representativeness_table.md").write_text(table_md + "\n")
    print(table_md)

    over_p1090 = [r for r in rows if r[6] and r[6] >= 100]
    print(f"\nLevers whose assumed effect EXCEEDS the real P10-P90 spread: {len(over_p1090)}")
    for r in over_p1090:
        print(" ", r)


if __name__ == "__main__":
    main()
