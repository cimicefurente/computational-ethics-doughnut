# A Doughnut-Economics Constraint Model of Floor and Ceiling Trade-offs: An Answer Set Programming Approach

**Course:** Computational Ethics 2026 — Prof. Giuseppe Pisano (discussion: Prof. Lagioia)
**Author:** [Your Name]
**Track:** System/code

---

## 1. Introduction and problem statement

Kate Raworth's *Doughnut Economics* (2017) reframes the goal of an economy as
staying within a "safe and just space": above a **social floor** that
guarantees everyone the essentials of a decent life, and below an
**ecological ceiling** defined by the planet's biophysical limits. The
framework is intuitively appealing and has been adopted by cities such as
Amsterdam as a policy compass, but it is rarely operationalized as a
*formal reasoning problem*: given a country's current situation, does a
combination of feasible policies exist that closes every social gap and
respects every ecological boundary at the same time — and if not, why not?

This project treats that question as a **constraint satisfaction problem**
and encodes it in **Answer Set Programming (ASP)**, using the `clingo`
solver. Concretely: given a country's baseline values on 7 ecological and 11
social indicators, and a menu of 14 candidate policy levers each with an
estimated effect on one or more indicators, the model searches for the most
parsimonious subset of levers that brings every indicator inside the
doughnut. When no such subset exists, the model does not simply report
failure: it computes the *minimal remaining violation* and identifies
exactly which dimensions remain structurally out of reach, which functions
as a computational explanation of the impossibility.

The choice of ASP (rather than, e.g., a generic linear or integer program)
is deliberate for a computational-ethics context: ASP represents the
problem *declaratively*, as a set of logical facts and constraints rather
than a bespoke optimization routine, which keeps the encoding auditable and
close to natural-language statements of the two ethical principles at
stake ("no dimension may be below the floor," "no dimension may exceed the
ceiling"). It also makes the model easy to extend (new levers or countries
are just new facts) and easy to interrogate (which constraints fail, and
under which assumptions).

## 2. Ethical framework

The model formalizes two distinct normative theories, one governing each
side of the doughnut:

- **Sufficientarianism** (Frankfurt, 1987; the capability approach of Sen,
  1999, and Nussbaum, 2011) governs the social floor. Its central claim is
  that what matters morally is that everyone reaches a sufficient level of
  capability/well-being; falling short on *any* dimension is a violation
  that cannot be offset by surplus on another dimension. This is why the
  model treats each of the 11 social indicators as an independent hard
  constraint rather than averaging them into a single welfare score — an
  average could hide a severe deficit in, say, sanitation behind a surplus
  in income, which sufficientarianism explicitly rules out as acceptable.

- **Strong sustainability**, grounded in the planetary boundaries framework
  (Rockström et al., 2009), governs the ecological ceiling. Unlike "weak"
  sustainability, which allows trading natural capital for produced or
  economic capital, strong sustainability treats certain biophysical
  boundaries as non-substitutable: no amount of economic benefit justifies
  crossing them. This is why the 7 ecological indicators are also
  independent hard constraints, not a single weighted ecological index.

The combination of the two is what makes the "doughnut" shape: a space
bounded by two structurally different kinds of constraint, justified by
two different ethical theories, both of which reject the more common move
of building a single aggregate objective function. This is stated
explicitly because it is the modeling decision most exposed to challenge in
discussion: an aggregate (e.g., a weighted sum of all 18 indicators) would
have been computationally simpler, but ethically wrong under either theory.

## 3. Data

All baseline country data come from O'Neill, Fanning, Lamb & Steinberger
(2018), *"A good life for all within planetary boundaries"*, Nature
Sustainability 1, 88–95. The paper computes, for 151 countries, 7
biophysical indicators (CO2 emissions, phosphorus, nitrogen, blue water,
embodied HANPP, ecological footprint, material footprint) and 11 social
indicators (life satisfaction, healthy life expectancy, nutrition,
sanitation, income, access to energy, education, social support,
democratic quality, equality, employment), each expressed as a **ratio to
a threshold**:

- Biophysical indicators: value ≤ 1.0 means the per-capita share of the
  planetary boundary is respected; value > 1.0 means overshoot.
- Social indicators: value ≥ 1.0 means the threshold for a good life is
  met; value < 1.0 means a deficit.

The official supplementary data file (`41893_2018_21_MOESM2_ESM.xlsx`,
hosted by Springer Nature) was downloaded directly and converted into ASP
facts by `src/data_prep.py`, scaling every ratio by 100 and rounding to the
nearest integer so the encoding can use integer arithmetic (`clingo` has no
native floating-point support). For example, Vietnam's CO2 ratio of 1.35 is
stored as the fact `bio_value(vietnam, co2, 135)`.

This is real, published, peer-reviewed data — not a synthetic scenario —
which matters for a computational ethics project: the trade-offs the model
surfaces are trade-offs a real country actually faces, not artifacts of an
invented example.

## 4. Formalization

### 4.1 Facts

For each country `C`, dimension `D`, and baseline value `V`:

```
bio_value(C, D, V).   % D in {co2, phosphorus, nitrogen, blue_water,
                      %       ehanpp, eco_footprint, material_footprint}
soc_value(C, D, V).   % D in {life_satisfaction, healthy_life_exp, ...}
```

### 4.2 Levers and their effects

Each policy lever `L` is declared once, together with the dimensions it
affects and by how much (a signed integer delta, in the same x100 scale):

```
lever(L).
affects_bio(L, Dim, Delta).
affects_soc(L, Dim, Delta).
```

### 4.3 Choice and constraints

The core of the encoding (`src/doughnut.lp`) is a **choice rule** over the
lever menu, followed by hard integrity constraints that encode the two
ethical principles from Section 2:

```prolog
{ select(L) } :- lever(L).

:- select(L1), select(L2), conflicts(L1, L2).

bio_effect(Dim, Sum) :-
    bio_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_bio(L, Dim, Delta) }.

soc_effect(Dim, Sum) :-
    soc_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_soc(L, Dim, Delta) }.

new_bio_value(C, Dim, V + E) :- target(C), bio_value(C, Dim, V), bio_effect(Dim, E).
new_soc_value(C, Dim, V + E) :- target(C), soc_value(C, Dim, V), soc_effect(Dim, E).

ceiling_ok(C, Dim) :- new_bio_value(C, Dim, V), V <= 100.
floor_met(C, Dim)  :- new_soc_value(C, Dim, V), V >= 100.

:- target(C), bio_value(C, Dim, _), not ceiling_ok(C, Dim).
:- target(C), soc_value(C, Dim, _), not floor_met(C, Dim).

#minimize { 1,L : select(L) }.
```

`{ select(L) } :- lever(L).` generates every possible subset of levers as a
candidate answer set. The two `:-` integrity constraints at the end are the
direct translation of "no ceiling may be exceeded" and "no floor may be
missed": any answer set that violates either is discarded by the solver,
regardless of any benefit it produces elsewhere. This is precisely the
non-substitutability that sufficientarianism and strong sustainability
demand, and it is enforced structurally by ASP's semantics rather than by a
penalty term that could in principle be outweighed.

Among the answer sets that survive, `#minimize { 1,L : select(L) }`
prefers those using the fewest levers — a **parsimony** criterion,
justified on the grounds that a less invasive reform is, all else equal,
preferable (this is itself a further, minor normative assumption, made
explicit here rather than left implicit).

A `conflicts/2` predicate lets two levers be declared mutually exclusive
(used for two competing approaches to expanding energy access — see
Section 5).

### 4.4 The diagnostic model for unsatisfiable cases

When no subset of levers satisfies every constraint, the feasibility
program above is, correctly, **UNSAT** — `clingo` returns no answer set at
all. This is a real result (the problem is genuinely infeasible under the
model's assumptions), but on its own it does not explain *why*. To extract
an explanation, `src/best_effort.lp` re-uses exactly the same facts and
lever effects but drops the two hard integrity constraints, replacing them
with a direct minimization of total remaining violation:

```prolog
overshoot(Dim, V - 100) :- new_bio_value(_, Dim, V), V > 100.
deficit(Dim, 100 - V)   :- new_soc_value(_, Dim, V), V < 100.

#minimize { P,Dim : overshoot(Dim, P) }.
#minimize { P,Dim : deficit(Dim, P) }.
```

This program is always satisfiable (the empty lever selection is a valid,
if poor, answer set) and its optimal model identifies the best achievable
outcome and, dimension by dimension, exactly how much of the floor/ceiling
violation cannot be closed by any available lever. Methodologically, this
plays the role that a minimal unsatisfiable core would play in a pure
satisfiability setting, but expressed in the units that matter ethically
(remaining floor/ceiling violation) rather than as a set of conflicting
rule instances. This trade-off is a deliberate engineering choice, not an
oversight, and is revisited as a limitation in Section 8.

## 5. Policy levers and their representativeness

Fourteen levers were modeled, spanning ecological interventions (renewable
energy transition, circular-economy/material policy, sustainable
agriculture, water efficiency, working-time reduction, carbon
fee-and-dividend with reforestation) and social interventions (universal
basic income, universal healthcare, participatory governance,
progressive wealth taxation, public education investment, decentralization
reform, sanitation infrastructure), plus one deliberately "cheap but dirty"
alternative (fossil-fuel-based energy expansion) included specifically to
create a genuine trade-off (Section 5.1). Full effect tables and loose
literature grounding for direction and order of magnitude are in
`src/levers.lp`.

No dataset of *causal*, per-country policy effects exists for these
indicators, so every effect size is an **illustrative assumption**: a
deliberately simplified estimate of plausible direction and rough
magnitude, not a fitted parameter. This is stated as a limitation rather
than hidden, but a bare "this seems plausible" is a weak methodological
defense on its own. To make the assumption falsifiable and check it is not
arbitrary, `src/representativeness_check.py` benchmarks every assumed
effect against the **empirical spread of the same indicator across the
151 real countries** in the dataset: the interquartile range (IQR, the
spread of the middle 50% of countries) and the P10–P90 range (the spread
between the 10th and 90th percentile country). The reasoning: an assumed
policy effect is representative if it does not imply a bigger jump than
countries already display against one another in the real world.

The result (full table in `report/representativeness_table.md`): **no
lever's assumed effect exceeds the real P10–P90 spread on its dimension.**
Most levers are conservative, using well under half of even the tighter
IQR range — for example, the renewable-energy lever's assumed −35 point
effect on CO2 is only 7% of the real IQR (533 points) and 4% of the real
P10–P90 range (808 points). A handful of levers are more ambitious,
sitting between 45% and 89% of the IQR (universal basic income on income,
wealth tax on equality, participatory governance on democratic quality,
universal healthcare on healthy life expectancy, working-time reduction on
life satisfaction, decentralization reform on democratic quality, and the
carbon-fee-and-dividend lever's effects on inequality and eHANPP). These
are flagged explicitly rather than left to blend in with the conservative
majority, since they are the assumptions most likely to be challenged in
discussion, and the honest answer is: ambitious, but still smaller than a
real, observed difference between two comparable countries.

### 5.1 A modeled trade-off: two ways to expand energy access

Two levers target the same social deficit (access to energy) by opposite
ecological means: `l1_renewable_energy` raises energy access by investing
in renewables (and, as a side effect, lowers CO2), while
`l11_fossil_energy_expansion` raises energy access faster and more
cheaply but *increases* CO2. A `conflicts/2` fact makes them mutually
exclusive, so the solver must pick at most one. This is included
specifically to give the model a genuine normative fork rather than only a
technical optimization: whenever both would otherwise satisfy the same
constraint, which one a solution uses is not dictated by the formalism,
only by which side effects are acceptable — precisely the kind of decision
computational ethics is meant to expose rather than paper over.

## 6. Implementation

The pipeline is: `data_prep.py` (parses the O'Neill et al. spreadsheet into
ASP facts) → `levers.lp` (the policy menu) → `doughnut.lp` / `best_effort.lp`
(the two ASP programs) → `run_scenario.py` (drives `clingo` via its Python
API, `--opt-mode=optN --project` to enumerate all *distinct* optimal
answer sets rather than duplicates that differ only on hidden atoms,
handles the UNSAT-then-diagnose flow automatically, and serializes results
to JSON) → `representativeness_check.py` (the benchmarking script in
Section 5). All code is Python 3.11 and `clingo` 5.8.0, isolated in a
project-local virtual environment; the repository includes a
`requirements.txt` for reproducibility.

## 7. Case studies and results

Three countries were selected after ranking all 151 by worst ecological
overshoot and worst social deficit, to cover a spectrum of difficulty:
Vietnam (mild overshoot on a single ecological dimension, moderate social
gaps), Costa Rica (overshoot on six of seven ecological dimensions, but
only two small social deficits), and the United States (overshoot on
*all seven* ecological dimensions, some by an order of magnitude, but
nearly all social dimensions already met).

### 7.1 Vietnam — feasible, with equivalent alternatives

**Baseline:** CO2 overshoot (135, i.e. 35% over the boundary) is the only
ecological violation; four social dimensions fall short (democratic
quality 52, sanitation 76, equality 77, life satisfaction 79).

**Result: SAT.** The optimal solution uses 6 levers (working-time
reduction, wealth tax, participatory governance, decentralization reform,
sanitation infrastructure, plus one of two interchangeable options for
CO2). After projecting out duplicate answer sets, `clingo` reports **two**
equally parsimonious optimal models, differing only in whether CO2 is
closed via `l1_renewable_energy` or via `l14_carbon_fee_dividend_reforestation`
— both are, at the level of this model, formally equivalent ways to
satisfy the same constraint. All 18 dimensions end up inside the doughnut
in both models (e.g. CO2 lands at exactly 100, the boundary; democratic
quality rises to 102).

### 7.2 Costa Rica — infeasible until a more ambitious lever is added

**Baseline:** six of seven ecological dimensions are in overshoot (CO2 172,
phosphorus 120, nitrogen 114, eHANPP 157, ecological footprint 129,
material footprint 141); only equality (62) and employment (93) fall short
socially.

**Result with the initial 13-lever menu: UNSAT.** The best achievable
outcome (via the diagnostic model) still leaves CO2 at 37 points over the
boundary, eHANPP at 27 points over, and equality 13 points below the
floor — a total residual violation of 77 points, small compared to what
follows for the United States, but still a genuine, formally
demonstrated impossibility with the levers available at that point.

**After adding a 14th, more ambitious lever** (carbon fee-and-dividend with
large-scale reforestation, informed by Hansen et al. 2015 on carbon
fee-and-dividend and IPCC AR6 WGIII on reforestation as a carbon sink, with
an equality co-benefit from returning the fee as an equal per-capita
dividend), the problem becomes **SAT**. The optimal solutions use 8 of the
14 levers, and **four distinct optimal models** exist, differing in which
combination of small, largely interchangeable institutional reforms
(participatory governance vs. decentralization reform vs. sanitation
infrastructure vs. universal basic income) is used to close the last,
small remaining social gaps. This is the clearest illustration in the
project of the model surfacing a genuine value choice: several
institutional designs are formally equivalent with respect to the
doughnut's 18 constraints, but they are not equivalent in what kind of
society they build (e.g. participatory governance vs. top-down
decentralization reflect different readings of democratic legitimacy),
and the ASP encoding — correctly — has no way to prefer one over the
other. Choosing between them is left, deliberately, to human judgement.

### 7.3 United States — structurally infeasible

**Baseline:** all seven ecological dimensions are in overshoot, several
massively so (CO2 1314, i.e. more than 13 times the sustainable per-capita
share; phosphorus 782; nitrogen 663; material footprint 378; ecological
footprint 393). Only two social dimensions fall short, and only slightly
(equality 81, employment 88).

**Result: UNSAT, even with all 14 levers available.** The diagnostic model's
best achievable outcome still leaves a total residual violation of 2815
points — roughly 36 times larger than Costa Rica's pre-fix residual — driven
overwhelmingly by CO2 (1129 points over, even after every applicable
lever), phosphorus (657 over), and nitrogen (538 over). No combination of
the modeled policy levers, even used all at once, comes close to closing
these gaps: their assumed effect sizes, chosen precisely to be no larger
than real cross-country variation (Section 5), are simply too small
relative to the scale of US overshoot.

This is, in formal terms, exactly the empirical finding of O'Neill et al.
(2018) themselves — no country in their dataset meets the social floor
without transgressing the ecological ceiling — reproduced here not as a
restatement of the paper's regression results, but as a *logical
consequence* of the model: given the paper's own baseline data and a set
of policy levers whose magnitude is bounded by real observed
cross-country variation, no subset of marginal reforms suffices for an
economy at the US's scale of overshoot. It operationalizes, computationally,
the central argument of *Doughnut Economics* against incremental reform of
high-consumption economies: the required reduction is not of a kind that
marginal levers, however combined, can supply.

## 8. Discussion and limitations

**Effect sizes are assumptions, not estimates.** Section 5's
representativeness check bounds these assumptions against real
cross-country variation, but it cannot make them causal. A different,
equally defensible set of magnitudes could shift Costa Rica back to UNSAT
or the United States (implausibly) to SAT. The qualitative conclusion that
survives this uncertainty is the *ordering*: the United States' residual
violation (2815) is roughly two orders of magnitude larger than Costa
Rica's (77, pre-fix), which is far more robust to the specific numbers
chosen than any single feasibility verdict is.

**The model is static.** It compares one baseline year against one
post-reform state; it says nothing about transition dynamics, the time
each lever takes to produce its effect, or path-dependency between levers
(e.g., whether renewable investment is cheaper after a circular-economy
policy has already reduced material demand). A dynamic extension would
need a temporal ASP formulation or a hybrid with system-dynamics
simulation.

**Lever effects are additive and independent.** The encoding sums each
selected lever's effect on a dimension with no interaction terms; in
reality, combined policies plausibly have synergies or redundancies (two
levers both targeting material throughput may not simply add). This
simplification is what makes the "best achievable" diagnostic
well-defined and fast to compute, at the cost of realism.

**The "best-effort" diagnostic is a substitute for a true unsatisfiable
core**, chosen deliberately (Section 4.4) because it reports the
explanation in ethically meaningful units (remaining floor/ceiling
violation) rather than a set of conflicting logic-program rules, which
would be harder to interpret substantively. A genuine minimal-core
extraction (via `clingo`'s assumption-based core computation) was
considered and rejected for this project given the added complexity of
handling the `conflicts/2` mutual-exclusion constraint correctly inside an
assumption set; it is noted here as a natural next step rather than a
hidden gap.

**Country-level aggregation hides internal distribution.** Both the floor
and the ceiling indicators are national averages; a country meeting the
income floor on average can still have a large internal population below
it. The model inherits this limitation directly from the underlying
O'Neill et al. dataset.

## 9. Conclusion

Framing Doughnut Economics as an ASP constraint-satisfaction problem over
real country data does two things a purely descriptive or purely
optimization-based treatment would not. First, it forces every implicit
ethical commitment into the open: the choice to treat both floor and
ceiling as *hard* constraints rather than terms in a weighted objective is
a direct, auditable encoding of sufficientarianism and strong
sustainability, not an incidental modeling convenience. Second, when the
problem is infeasible, the model does not merely fail silently or report
an infeasibility flag: it produces a structured, quantified account of
which constraints remain unreachable and by how much, which is what turns
a solver result into something a policy discussion can actually use.

Applied to real data, the model reproduces — as a logical consequence of
its own stated assumptions, not as an assertion — the central empirical
claim of Doughnut Economics: at the scale of overshoot displayed by a
country like the United States, no combination of the kind of marginal
policy levers considered here is sufficient. At the same time, the model
shows that this is not a universal verdict: Vietnam's situation is
comfortably solvable, and Costa Rica sits in between, solvable only with a
more ambitious lever and, even then, via several institutionally distinct
and formally equivalent paths whose final choice the model correctly
leaves to human political judgement rather than resolving computationally.

## References

- Frankfurt, H. (1987). Equality as a Moral Ideal. *Ethics*, 98(1), 21–43.
- Hansen, J. et al. (2015). Assessing "Dangerous Climate Change": Required
  Reduction of Carbon Emissions to Protect Young People, Future
  Generations and Nature. *PLOS ONE*.
- IPCC (2022). *Climate Change 2022: Mitigation of Climate Change.*
  Working Group III Contribution to AR6.
- Nussbaum, M. (2011). *Creating Capabilities: The Human Development
  Approach.* Harvard University Press.
- O'Neill, D. W., Fanning, A. L., Lamb, W. F., & Steinberger, J. K. (2018).
  A good life for all within planetary boundaries. *Nature
  Sustainability*, 1, 88–95.
- Raworth, K. (2017). *Doughnut Economics: Seven Ways to Think Like a
  21st-Century Economist.* Chelsea Green Publishing.
- Rockström, J. et al. (2009). A safe operating space for humanity.
  *Nature*, 461, 472–475.
- Sen, A. (1999). *Development as Freedom.* Oxford University Press.
