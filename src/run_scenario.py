"""
Run the doughnut-economics ASP model for a target country.

Usage: python3 run_scenario.py <country_slug> [--max-models N]

Behaviour:
  - Solves src/doughnut.lp (hard floor + ceiling constraints) for the
    country. If satisfiable, prints up to N optimal models (lever subsets)
    with the resulting values.
  - If unsatisfiable, falls back to src/best_effort.lp, which drops the
    hard constraints and instead minimizes total remaining floor/ceiling
    violation - this plays the role of an explanation ("what's the best
    achievable, and which dimensions remain structurally unreachable").
"""
import argparse
import json
import sys
from pathlib import Path

import clingo

SRC = Path(__file__).parent
DATA = SRC.parent / "data" / "processed"


def load_country_names():
    return json.loads((DATA / "country_names.json").read_text())


def solve(country_slug, program_files, max_models=8):
    # --opt-mode=optN asks clingo to keep enumerating models AT the optimum
    # once found, instead of stopping at the first one - this is what lets
    # us detect cases like Costa Rica's four equally parsimonious solutions.
    # --project restricts model comparison to #show'n atoms.
    ctl = clingo.Control(["--opt-mode=optN", f"--models={max_models}", "--project"])
    for f in program_files:
        path = SRC / f
        if not path.exists():
            path = DATA / f
        ctl.load(str(path))
    ctl.add("base", [], f"target({country_slug}).")
    ctl.ground([("base", [])])

    models = []
    seen = set()
    best_cost = None
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            cost = model.cost
            if best_cost is None or cost < best_cost:
                # A strictly better model showed up: everything collected
                # so far was only optimal until now, so discard it and
                # restart the collection at the new best cost.
                best_cost = cost
                models = []
                seen = set()
            if cost == best_cost:
                # --project alone can still yield two "models" that are
                # byte-identical once restricted to shown atoms (a known
                # clingo artifact when the underlying grounding differs on
                # atoms that aren't shown). Deduping on the sorted, shown
                # atom tuple is what actually guarantees each entry in
                # `models` is a genuinely distinct answer set.
                atoms = tuple(sorted(str(a) for a in model.symbols(shown=True)))
                if atoms not in seen:
                    seen.add(atoms)
                    models.append(list(atoms))
        result = handle.get()

    return result.satisfiable, models, best_cost


def parse_model(atoms):
    # clingo gives symbols as strings like "select(l1_renewable_energy)" or
    # "new_bio_value(vietnam,co2,100)" - there's no structured API for this
    # in the Python bindings' shown-atoms output, so we peel off the
    # functor name and split the argument list by hand.
    selected = []
    bio_vals = {}
    soc_vals = {}
    overshoot = {}
    deficit = {}
    for a in atoms:
        if a.startswith("select("):
            selected.append(a[len("select("):-1])
        elif a.startswith("new_bio_value("):
            inner = a[len("new_bio_value("):-1]
            _, dim, v = inner.split(",")
            bio_vals[dim] = int(v)
        elif a.startswith("new_soc_value("):
            inner = a[len("new_soc_value("):-1]
            _, dim, v = inner.split(",")
            soc_vals[dim] = int(v)
        elif a.startswith("overshoot("):
            inner = a[len("overshoot("):-1]
            dim, v = inner.split(",")
            overshoot[dim] = int(v)
        elif a.startswith("deficit("):
            inner = a[len("deficit("):-1]
            dim, v = inner.split(",")
            deficit[dim] = int(v)
    return {
        "selected_levers": sorted(selected),
        "bio_values": bio_vals,
        "soc_values": soc_vals,
        "overshoot": overshoot,
        "deficit": deficit,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("country_slug")
    ap.add_argument("--max-models", type=int, default=8)
    args = ap.parse_args()

    names = load_country_names()
    label = names.get(args.country_slug, args.country_slug)

    print(f"=== {label} ({args.country_slug}) ===\n")

    sat, models, cost = solve(
        args.country_slug, ["doughnut.lp", "countries_facts.lp"], args.max_models
    )

    result = {"country": label, "slug": args.country_slug}

    if sat:
        print(f"FEASIBILITY: SAT  (optimal cost = fewest levers = {cost})")
        print(f"Number of optimal models found: {len(models)}\n")
        parsed_models = [parse_model(m) for m in models]
        for i, pm in enumerate(parsed_models, 1):
            print(f"--- Model {i} ---")
            print("  levers:", ", ".join(pm["selected_levers"]) or "(none needed)")
        result["status"] = "SAT"
        result["models"] = parsed_models
    else:
        print("FEASIBILITY: UNSAT")
        print("No combination of the available levers satisfies every floor and "
              "ceiling constraint simultaneously.\n")
        print("Running best-effort diagnostic (src/best_effort.lp)...\n")
        # Only the single best outcome matters here (there's no "second most
        # parsimonious violation" to report), so max_models=1.
        _, be_models, be_cost = solve(
            args.country_slug, ["best_effort.lp", "countries_facts.lp"], max_models=1
        )
        pm = parse_model(be_models[0]) if be_models else {}
        print(f"Minimal total remaining violation (overshoot + deficit points): {be_cost}\n")
        print("Best-effort levers selected:", ", ".join(pm.get("selected_levers", [])))
        print("\nDimensions that STILL breach the ceiling after every applicable lever:")
        for dim, v in sorted(pm.get("overshoot", {}).items(), key=lambda x: -x[1]):
            print(f"  {dim}: still {v} points over the boundary")
        print("\nDimensions that STILL fall short of the floor after every applicable lever:")
        for dim, v in sorted(pm.get("deficit", {}).items(), key=lambda x: -x[1]):
            print(f"  {dim}: still {v} points below the threshold")
        result["status"] = "UNSAT"
        result["best_effort"] = pm
        result["best_effort_cost"] = be_cost

    out_dir = SRC.parent / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{args.country_slug}.json").write_text(json.dumps(result, indent=2))
    print(f"\nSaved results to results/{args.country_slug}.json")


if __name__ == "__main__":
    main()
