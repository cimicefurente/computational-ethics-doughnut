# A Doughnut-Economics Constraint Model of Floor and Ceiling Trade-offs: An Answer Set Programming Approach

**Course:** Computational Ethics 2026 — Prof. Lagioia, Prof. Giuseppe Pisano  
**Author:** Thomas Gualandi  
**Track:** System/code

---

## 1. Introduction and problem statement

Kate Raworth's *Doughnut Economics* (2017) reframes the goal of an economy as
staying within a "safe and just space": above a **social floor** that
guarantees everyone the essentials of a decent life, and below an
**ecological ceiling** defined by the planet's biophysical limits. The
framework is intuitively appealing and has been adopted by cities such as
Amsterdam as a policy compass, but it is rarely turned into a *formal
reasoning problem*: given a country's current situation, does a
combination of feasible policies exist that closes every social gap and
respects every ecological boundary at once, and if not, why not?

This project treats that question as a **constraint satisfaction problem**,
encoded in **Answer Set Programming (ASP)** and solved with `clingo`.
Given a country's baseline on 7 ecological and 11 social indicators, and a
menu of 14 candidate policy levers each with an estimated effect on one or
more of them, the model searches for the most parsimonious lever subset
that brings every indicator inside the doughnut. When no such subset
exists, it does not just report failure: it computes the minimal
remaining violation and identifies which dimensions stay structurally out
of reach, which serves as a computational explanation of the
impossibility.

ASP suits a computational-ethics context better than a generic linear or
integer program would, because it represents the problem declaratively,
as facts and constraints close to the natural-language statement of the
two ethical principles at stake ("no dimension may be below the floor,"
"no dimension may exceed the ceiling"), rather than as a bespoke
optimization routine. That same declarative form also makes the model
easy to extend, since a new lever or country is just a new fact, and easy
to interrogate, since it is always possible to ask which constraints fail
and under which assumptions.

## 2. Ethical framework

The model formalizes two distinct normative theories, one governing each
side of the doughnut:

- **Sufficientarianism** (Frankfurt, 1987; the capability approach of Sen,
  1999, and Nussbaum, 2011) governs the social floor. Its central claim is
  that what matters morally is that everyone reaches a sufficient level of
  capability/well-being; falling short on *any* dimension is a violation
  that cannot be offset by surplus on another dimension. This is why the
  model treats each of the 11 social indicators as an independent hard
  constraint rather than averaging them into a single welfare score: an
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
of building a single aggregate objective function. This is worth stating
explicitly because it is the modeling decision most exposed to challenge in
discussion. A single aggregate, such as a weighted sum of all 18
indicators, would have been computationally simpler, but ethically wrong
under either theory.

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

This is real, published, peer-reviewed data rather than a synthetic
scenario, so the trade-offs the model surfaces are trade-offs a real
country actually faces, not artifacts of an invented example.

## 4. Formalization

Turning the doughnut into something a solver can actually check means
building a short pipeline, each stage handling one part of the problem:

1. **`data_prep.py`** turns the raw O'Neill et al. spreadsheet into ASP
   facts describing where a country currently stands (Section 4.1).
2. **`levers.lp`** declares the menu of 14 candidate policies and their
   estimated effects (Section 4.2).
3. **`doughnut.lp`** is the core ASP program: it chooses a subset of
   levers and checks whether it satisfies every floor and ceiling
   constraint at once (Section 4.3).
4. **`best_effort.lp`** takes over when no subset works, diagnosing how
   far off the best achievable outcome still is (Section 4.4).
5. **`run_scenario.py`** drives `clingo` end to end and writes the
   results discussed in Section 7.
6. **`representativeness_check.py`** independently checks that the lever
   effects assumed in step 2 are realistic (Section 5).

The rest of this section walks through the two ASP programs, `doughnut.lp`
and `best_effort.lp`, block by block. Section 6 covers how to actually run
this pipeline.

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

A lever is a binary intervention: at solve time it is either selected or
not (Section 4.3), and if selected it contributes a fixed, pre-declared
delta to every dimension it affects. The solver never decides how much of
a lever to apply, only whether to apply it at all. A lever can touch
several dimensions at once, and two levers can be declared mutually
exclusive via `conflicts/2` (used once, for `l1`/`l11` below). All 14
levers, declared in `src/levers.lp`, are:

| #   | Lever                                   | What it represents                                                                                        | Effect on ecological dimensions           | Effect on social dimensions                                                                       | Indicative source (direction/order of magnitude only)                                  |
| --- | --------------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| L1  | `l1_renewable_energy`                   | Renewable-energy transition (wind/solar/hydro investment displacing fossil generation)                    | co2 −35                                   | energy_access +15                                                                                 | IPCC AR6 WGIII mitigation pathways; IEA net-zero scenario                               |
| L2  | `l2_circular_economy`                   | Circular-economy / material policy (reuse, recycling, product-life extension)                             | material_footprint −30; eco_footprint −15 | —                                                                                                  | Ellen MacArthur Foundation circular-economy reports                                    |
| L3  | `l3_sustainable_agriculture`            | Sustainable/regenerative agriculture (lower nutrient runoff and land pressure)                            | nitrogen −25; phosphorus −25; ehanpp −30  | nutrition −10 (modeled trade-off: lower-intensity farming reduces short-term nutritional surplus) | FAO / EAT-Lancet on regenerative agriculture & nutrient runoff                          |
| L4  | `l4_water_efficiency`                   | Water-efficiency infrastructure and demand management                                                     | blue_water −20                            | —                                                                                                  | UN water-efficiency reports                                                             |
| L5  | `l5_working_time_reduction`             | Working-time reduction (e.g. four-day week)                                                               | eco_footprint −20; material_footprint −15 | life_satisfaction +22; employment +10                                                             | Kallis et al. (degrowth); four-day-week trials (Iceland, Autonomy UK)                   |
| L6  | `l6_universal_basic_income`             | Universal basic income                                                                                    | —                                         | income +20; sanitation +15; nutrition +10                                                         | ILO Social Protection Floor Recommendation 202                                          |
| L7  | `l7_universal_healthcare`               | Universal healthcare coverage                                                                             | —                                         | healthy_life_exp +20; social_support +10                                                          | WHO Universal Health Coverage reports                                                   |
| L8  | `l8_participatory_governance`           | Participatory governance (participatory budgeting, deliberative bodies)                                   | —                                         | democratic_quality +30; social_support +10                                                        | OECD participatory-budgeting / open-government studies                                  |
| L9  | `l9_wealth_tax`                         | Progressive wealth taxation                                                                               | —                                         | equality +25; income +10                                                                          | Piketty, *Capital in the Twenty-First Century*                                          |
| L10 | `l10_education_investment`              | Public education investment                                                                               | —                                         | education +20; employment +10                                                                     | UNESCO education-investment reports                                                     |
| L11 | `l11_fossil_energy_expansion`           | Fossil-fuel-based energy access expansion, cheaper and faster than L1, but dirtier; `conflicts(l1, l11)`  | co2 +15                                   | energy_access +20                                                                                 | Deliberately modeled as the cheap/dirty alternative to L1 (Section 4.3)                 |
| L12 | `l12_decentralization_reform`           | Decentralization / subsidiarity reform                                                                    | —                                         | democratic_quality +20; social_support +5                                                         | Subsidiarity/decentralization literature (Ostrom)                                       |
| L13 | `l13_sanitation_infrastructure`         | Sanitation infrastructure investment                                                                      | —                                         | sanitation +25                                                                                    | WHO/UNICEF WASH programme reports                                                       |
| L14 | `l14_carbon_fee_dividend_reforestation` | Carbon fee-and-dividend combined with large-scale reforestation                                           | co2 −50; ehanpp −35                       | equality +15 (fee revenue returned as an equal per-capita dividend)                               | Hansen et al. 2013 (fee-and-dividend); IPCC AR6 WGIII (reforestation as a carbon sink)  |

As Section 5 discusses, every delta in this table is an illustrative
assumption about direction and rough order of magnitude, not a fitted
causal estimate: the "indicative source" column names the literature that
motivates the sign and ballpark of each effect, not a regression this
project reproduces.

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

A rule of the form `head :- body.` means "if body is true, derive head."
A rule with no head, `:- body.`, is instead an integrity constraint: it
forbids the body from ever being true, discarding the whole candidate
answer set rather than penalizing it. `{ select(L) } :- lever(L).` is the
opposite kind of rule, a choice rule marked by the curly braces: the
solver is free to make each `select(L)` true or false independently,
generating up to 2^14 candidate lever subsets as the starting search
space, and everything below only filters or scores that space.
`conflicts/2` puts the integrity-constraint pattern to its one real use
here, ruling out `l1_renewable_energy` and `l11_fossil_energy_expansion`
together, since the two levers reach the same energy-access target
through opposite ecological means: forcing a choice between them gives
the model a genuine normative fork, where which one a solution uses is
settled by which side effects are considered acceptable rather than by
the formalism itself, precisely the kind of decision computational
ethics is meant to expose rather than paper over.

The two `#sum` rules add up the deltas of every selected lever on each
dimension, including the lever identifier `L` inside the aggregate's
tuple so that two different levers with the same delta on the same
dimension are not silently collapsed into one (this additive,
no-interaction simplification is revisited as a limitation in Section 8).
`new_bio_value` and `new_soc_value` add that net effect to the baseline
of whichever country is the current `target(C)`, a fact injected by
`run_scenario.py` at solve time so the same program serves every country
unchanged. `ceiling_ok` and `floor_met` just name whether a dimension
passes, and the two constraints right after them enforce it one
dimension at a time: because nothing is folded into a single combined
score, a solution that fixes every dimension but one is still thrown out
entirely, which is exactly the non-substitutability that
sufficientarianism and strong sustainability demand (Section 2).

Among the answer sets that survive, `#minimize { 1,L : select(L) }`
prefers those using the fewest levers, a parsimony criterion that is
itself a small normative assumption made explicit here rather than left
implicit. `run_scenario.py` calls `clingo` with `--opt-mode=optN`, which
keeps every answer set tied at this optimal cost instead of stopping at
the first one found, and that is what surfaces cases like Costa Rica's
four equally parsimonious solutions in Section 7.2.

### 4.4 The diagnostic model for unsatisfiable cases

When no subset of levers satisfies every constraint, `doughnut.lp`
correctly returns UNSAT, a real result since the problem is genuinely
infeasible under the model's assumptions, but simply reporting that
would leave Section 7 with nothing more to say about Costa Rica or the
United States than "no," which is not useful for either a policy
discussion or an ethical argument. `src/best_effort.lp` turns that "no"
into a measurement, reusing the same facts, lever menu and
effect-aggregation machinery as `doughnut.lp` but dropping the two hard
constraints, and instead minimizing how much of the floor and ceiling is
still violated once the best available combination of levers has been
applied.

```prolog
overshoot(Dim, V - 100) :- new_bio_value(_, Dim, V), V > 100.
deficit(Dim, 100 - V)   :- new_soc_value(_, Dim, V), V < 100.

#minimize { P,Dim : overshoot(Dim, P) }.
#minimize { P,Dim : deficit(Dim, P) }.
```

The two `#minimize` statements carry no explicit priority, so `clingo`
treats them as one joint objective, and the optimal model reports a
single "total residual violation" figure rather than overshoot and
deficit scored separately. This is exactly the number Section 7 uses to
compare Costa Rica's pre-fix outcome (77) against the United States
(2815), and the gap between them, roughly two orders of magnitude, is
the more robust part of the argument in Section 8: even if the exact
lever effect sizes were debated, that ordering is unlikely to flip.
Selecting no levers at all is always a valid, if poor, answer set, so
this diagnostic model is always satisfiable: it plays the role a minimal
unsatisfiable core would play in a purely logical setting, but expressed
in units an ethical argument can actually use rather than a list of
conflicting rule instances (a deliberate substitution revisited as a
limitation in Section 8), and `run_scenario.py` only calls on it once
`doughnut.lp` itself has already come back UNSAT.

## 5. Representativeness of the assumed lever effects

The 14 levers in Section 4.2 are illustrative rather than fitted: there is
no dataset of causal, per-country policy effects for these indicators, so
every effect size is a simplified estimate of plausible direction and
rough size, not a parameter estimated from data. Stating this as a
limitation is not enough on its own, so `src/representativeness_check.py`
makes the assumption checkable, comparing every assumed effect against
how much the same indicator actually varies across the 151 real
countries in the O'Neill et al. dataset.

Concretely, for each indicator the script looks at the full distribution
of values across all 151 countries and asks two questions. First, how
spread out are the middle half of countries, from the 25th to the 75th
percentile? This is the interquartile range, or IQR, and it captures the
kind of variation that is common and unremarkable: most countries differ
from each other by roughly this much. Second, how far apart are a fairly
typical low country and a fairly typical high country, from the 10th to
the 90th percentile? This wider P10–P90 range captures variation that is
still real and observed, but closer to the extremes. An assumed lever
effect is judged representative if it stays within the kind of gap that
already exists between real countries, so that it does not ask a country
to jump further than countries already differ from one another.

The result, tabulated in full in `report/representativeness_table.md`, is
that no lever's assumed effect exceeds the real P10–P90 spread on its
dimension. Most levers are conservative by this standard, using well
under half of even the narrower IQR: the renewable-energy lever's assumed
−35 point effect on CO2, for instance, is only 7% of the real IQR. A
smaller group of levers is more ambitious, using between 45% and 89% of
the IQR: universal basic income on income, the wealth tax on equality,
participatory governance and decentralization reform on democratic
quality, universal healthcare on healthy life expectancy, working-time
reduction on life satisfaction, and the carbon-fee-and-dividend lever's
effects on equality and eHANPP. These are flagged explicitly, since they
are the assumptions most likely to be challenged in discussion, though
even they stay smaller than a difference that already exists between two
comparable real countries.

## 6. Running the pipeline

All code is Python 3.11 and `clingo` 5.8.0, isolated in a project-local
virtual environment with a two-line `requirements.txt` (`clingo`,
`openpyxl`). After `pip install -r requirements.txt`, the whole pipeline
described in Section 4 runs with three commands:

```bash
python3 src/data_prep.py                    # spreadsheet -> ASP facts
python3 src/representativeness_check.py     # checks lever effects (Section 5)
python3 src/run_scenario.py <country_slug>   # e.g. vietnam, costa_rica, united_states
```

`data_prep.py` and `representativeness_check.py` only need to be run
once; `run_scenario.py` is run once per country and writes its result to
`results/<slug>.json`, which is exactly what Section 7's tables are built
from.

Two implementation details are worth knowing if a number looks
surprising when reproducing these results. `data_prep.py` skips a
spreadsheet cell rather than zero-filling it when it is blank, which is
why Vietnam ends up with only 17 of the usual 18 tracked dimensions
(Section 7.1): a gap inherited from the source data, not a bug in this
pipeline. `run_scenario.py` asks `clingo` for every answer set tied at
the optimal cost, not just the first one found, which is why Costa Rica
comes back with four equally parsimonious solutions instead of one
(Section 7.2); a small de-duplication step then filters out the
occasional duplicate `clingo` produces when two models differ only on
atoms that are not shown.

## 7. Case studies and results

Three countries were selected after ranking all 151 by worst ecological
overshoot and worst social deficit, to cover a spectrum of difficulty:
Vietnam (mild overshoot on a single ecological dimension, moderate social
gaps), Costa Rica (overshoot on six of seven ecological dimensions, but
only two small social deficits), and the United States (overshoot on
*all seven* ecological dimensions, some by an order of magnitude, but
nearly all social dimensions already met).

### 7.1 Vietnam: feasible, with equivalent alternatives

Vietnam is missing the `education` indicator in the source spreadsheet
(Section 6), so only 17 of the usual 18 dimensions are tracked for this
country. In the baseline, CO2 is the only ecological violation, at 135,
and four social dimensions fall short: democratic quality at 52,
sanitation at 76, equality at 77, and life satisfaction at 79.

*(Values are x100 ratios-to-threshold; ceiling dimensions pass at ≤100,
floor dimensions pass at ≥100. Bold = changed by the selected levers.)*

| Dimension | Type | Baseline | Model 1 (via L1) | Model 2 (via L14) |
|---|---|---|---|---|
| co2 | ceiling | 135 | **100** | **85** |
| phosphorus | ceiling | 84 | 84 | 84 |
| nitrogen | ceiling | 88 | 88 | 88 |
| blue_water | ceiling | 38 | 38 | 38 |
| ehanpp | ceiling | 73 | 73 | **38** |
| eco_footprint | ceiling | 79 | **59** | **59** |
| material_footprint | ceiling | 92 | **77** | **77** |
| life_satisfaction | floor | 79 | **101** | **101** |
| healthy_life_exp | floor | 102 | 102 | 102 |
| nutrition | floor | 100 | 100 | 100 |
| sanitation | floor | 76 | **101** | **101** |
| income | floor | 101 | **111** | **111** |
| energy_access | floor | 105 | **120** | 105 |
| social_support | floor | 100 | **115** | **115** |
| democratic_quality | floor | 52 | **102** | **102** |
| equality | floor | 77 | **102** | **117** |
| employment | floor | 116 | **126** | **126** |

The problem turns out to be satisfiable, with two equally parsimonious
optimal models of six levers each, differing only in how CO2 is closed:

- **Model 1:** `l1_renewable_energy, l5_working_time_reduction,
  l8_participatory_governance, l9_wealth_tax, l12_decentralization_reform,
  l13_sanitation_infrastructure`
- **Model 2:** the same, with `l1_renewable_energy` swapped for
  `l14_carbon_fee_dividend_reforestation`

Both are formally equivalent ways to satisfy the CO2 ceiling. L14
additionally closes `ehanpp` further and lifts `equality` higher, through
its per-capita dividend, but leaves `energy_access` at its baseline since,
unlike L1, it does not target that dimension. All 17 tracked dimensions
land inside the doughnut in both models.

### 7.2 Costa Rica: infeasible until a more ambitious lever is added

In the baseline, six of the seven ecological dimensions are in overshoot:
CO2 at 172, phosphorus at 120, nitrogen at 114, eHANPP at 157, ecological
footprint at 129, material footprint at 141. Only equality (62) and
employment (93) fall short socially.

With the initial 13-lever menu the problem is unsatisfiable: the best
achievable outcome still leaves CO2 37 points over, eHANPP 27 points over,
and equality 13 points under, for a residual violation of 77 points.
After adding a 14th lever, carbon fee-and-dividend combined with
large-scale reforestation (Section 4.2), the problem becomes satisfiable,
with four equally parsimonious optimal models of eight levers each:

| Dimension | Type | Baseline | Model 1 | Model 2 | Model 3 | Model 4 |
|---|---|---|---|---|---|---|
| co2 | ceiling | 172 | **87** | **87** | **87** | **87** |
| phosphorus | ceiling | 120 | **95** | **95** | **95** | **95** |
| nitrogen | ceiling | 114 | **89** | **89** | **89** | **89** |
| blue_water | ceiling | 44 | 44 | 44 | 44 | 44 |
| ehanpp | ceiling | 157 | **92** | **92** | **92** | **92** |
| eco_footprint | ceiling | 129 | **94** | **94** | **94** | **94** |
| material_footprint | ceiling | 141 | **96** | **96** | **96** | **96** |
| life_satisfaction | floor | 120 | **142** | **142** | **142** | **142** |
| healthy_life_exp | floor | 117 | 117 | 117 | 117 | 117 |
| nutrition | floor | 120 | 120 | 120 | **110** | **110** |
| sanitation | floor | 98 | **113** | **113** | **123** | **123** |
| income | floor | 104 | **134** | **134** | **114** | **114** |
| energy_access | floor | 105 | **120** | **120** | **120** | **120** |
| education | floor | 112 | 112 | 112 | 112 | 112 |
| social_support | floor | 99 | **104** | **109** | **109** | **104** |
| democratic_quality | floor | 99 | **119** | **129** | **129** | **119** |
| equality | floor | 62 | **102** | **102** | **102** | **102** |
| employment | floor | 93 | **103** | **103** | **103** | **103** |

All four models share the same six core levers, `l1_renewable_energy,
l2_circular_economy, l3_sustainable_agriculture, l5_working_time_reduction,
l9_wealth_tax, l14_carbon_fee_dividend_reforestation`, and differ only in
which two of `l6_universal_basic_income`, `l8_participatory_governance`,
`l12_decentralization_reform`, `l13_sanitation_infrastructure` close the
remaining social gaps: Model 1 combines the core with L6 and L12, Model 2
with L6 and L8, Model 3 with L8 and L13, Model 4 with L12 and L13. None of
these four levers touches an ecological dimension, so all seven
ecological values are identical across models; `nutrition`, `sanitation`
and `income` shift between L6 and L13, while `social_support` and
`democratic_quality` shift between L8 and L12.

This is the clearest illustration in the project of the model surfacing a
genuine value choice. Several institutional designs are formally
equivalent with respect to the doughnut's constraints, but they are not
equivalent in what kind of society they build: participatory governance
and top-down decentralization reflect different readings of democratic
legitimacy, and the ASP encoding correctly leaves that choice to human
judgement rather than resolving it computationally.

### 7.3 United States: structurally infeasible

In the baseline, all seven ecological dimensions are in overshoot, several
of them massively so: CO2 at 1314, more than 13 times the sustainable
share; phosphorus at 782; nitrogen at 663; material footprint at 378;
ecological footprint at 393. Only equality (81) and employment (88) fall
short socially, and only slightly.

| Dimension | Type | Baseline | Best-effort result | Status |
|---|---|---|---|---|
| co2 | ceiling | 1314 | 1229 | still **1129** over |
| phosphorus | ceiling | 782 | 757 | still **657** over |
| nitrogen | ceiling | 663 | 638 | still **538** over |
| eco_footprint | ceiling | 393 | 358 | still **258** over |
| material_footprint | ceiling | 378 | 333 | still **233** over |
| blue_water | ceiling | 106 | 86 | met |
| ehanpp | ceiling | 142 | 77 | met |
| life_satisfaction | floor | 117 | 139 | met |
| healthy_life_exp | floor | 117 | 117 | met |
| nutrition | floor | 194 | 184 | met |
| sanitation | floor | 105 | 105 | met |
| income | floor | 107 | 117 | met |
| energy_access | floor | 106 | 121 | met |
| education | floor | 100 | 120 | met |
| social_support | floor | 104 | 104 | met |
| democratic_quality | floor | 102 | 102 | met |
| equality | floor | 81 | 121 | met |
| employment | floor | 88 | 108 | met |

Even with all 14 levers available, the problem remains unsatisfiable. The
best-effort diagnostic selects eight levers, `l1_renewable_energy,
l2_circular_economy, l3_sustainable_agriculture, l4_water_efficiency,
l5_working_time_reduction, l9_wealth_tax, l10_education_investment,
l14_carbon_fee_dividend_reforestation`, the largest and most varied lever
set of the three case studies. This fully closes the social floor, with
all 11 dimensions met, but leaves five of the seven ecological ceilings
breached, for a total residual violation of 2815 points (the five
overshoot figures sum exactly: 1129 + 657 + 538 + 258 + 233), roughly 36
times Costa Rica's pre-fix residual. `blue_water` and `ehanpp` are brought
under their ceilings; the impossibility concentrates specifically in CO2,
phosphorus and nitrogen, where US overshoot is most extreme to begin
with.

This is, in formal terms, exactly the empirical finding of O'Neill et al.
(2018) themselves, that no country in their dataset meets the social
floor without transgressing the ecological ceiling, reproduced here as a
logical consequence of the model rather than a restatement of the paper's
regression results. Given real baseline data and levers bounded to
plausible real-world magnitudes (Section 5), no subset of marginal
reforms is enough at the scale of US overshoot. This operationalizes,
computationally, the central argument of *Doughnut Economics* against
incremental reform of high-consumption economies.

## 8. Discussion and limitations

- **Effect sizes.** These are assumptions, not estimates. The
  representativeness check in Section 5 bounds them against real
  cross-country variation, but it cannot make them causal. A different,
  equally defensible set of magnitudes could shift Costa Rica back to
  unsatisfiable, or shift the United States implausibly to satisfiable.
  What survives this uncertainty is the ordering: the United States'
  residual violation, 2815, is roughly two orders of magnitude larger
  than Costa Rica's pre-fix residual of 77, and that ordering is far more
  robust to the specific numbers chosen than any single feasibility
  verdict is.

- **Static model.** The model compares one baseline year against one
  post-reform state, and says nothing about transition dynamics, the time
  each lever takes to produce its effect, or path-dependency between
  levers, for instance whether renewable investment becomes cheaper once
  a circular-economy policy has already reduced material demand. A
  dynamic extension would need a temporal ASP formulation or a hybrid
  with system-dynamics simulation.

- **Additive lever effects.** The encoding sums each selected lever's
  effect on a dimension with no interaction terms, while in reality
  combined policies plausibly have synergies or redundancies, since two
  levers both targeting material throughput may not simply add. This
  simplification is what keeps the best-effort diagnostic well defined
  and fast to compute, at the cost of realism.

- **Best-effort as a stand-in for a minimal core.** The diagnostic model
  is a substitute for a true unsatisfiable core, chosen deliberately
  (Section 4.4) because it reports the explanation in units an ethical
  argument can use, namely remaining floor or ceiling violation, rather
  than a set of conflicting logic-program rules that would be harder to
  interpret substantively. A genuine minimal-core extraction, via
  `clingo`'s assumption-based core computation, was considered and set
  aside for this project given the added complexity of handling the
  `conflicts/2` mutual-exclusion constraint correctly inside an
  assumption set; it is noted here as a natural next step rather than a
  hidden gap.

- **Country-level aggregation.** Both the floor and ceiling indicators
  are national averages, so a country meeting the income floor on
  average can still have a large share of its population below it. The
  model inherits this limitation directly from the underlying O'Neill et
  al. dataset.

- **Binary levers.** Each lever is on or off at one pre-set size, rather
  than a graduated intensity (a carbon fee can be €20/t or €150/t; this
  model only encodes one), which trades away realism for a search space
  small enough to enumerate exhaustively.

- **Limited policy family.** The 14 levers represent one particular
  package of policies, not the full space of options; alternatives such
  as nuclear power, carbon capture, or trade and efficiency-led growth
  are absent, so an unsatisfiable result means infeasible with this
  menu, not infeasible in principle.

## 9. Conclusion

Framing Doughnut Economics as an ASP constraint-satisfaction problem over
real country data does two things that a purely descriptive or purely
optimization-based treatment would not. First, it forces every implicit
ethical commitment into the open: treating both floor and ceiling as hard
constraints, rather than as terms in a weighted objective, is a direct,
auditable encoding of sufficientarianism and strong sustainability, not an
incidental modeling convenience. Second, when the problem is infeasible
the model does not simply fail silently or report an infeasibility flag:
it produces a structured, quantified account of which constraints remain
unreachable and by how much, which is what turns a solver result into
something a policy discussion can actually use.

Applied to real data, the model reproduces the central empirical claim of
Doughnut Economics as a logical consequence of its own stated assumptions
rather than as an assertion: at the scale of overshoot displayed by a
country like the United States, no combination of the kind of marginal
policy levers considered here is sufficient. At the same time, the model
shows this is not a universal verdict. Vietnam's situation is comfortably
solvable, and Costa Rica sits in between, solvable only with a more
ambitious lever and, even then, through several institutionally distinct
and formally equivalent paths whose final choice the model correctly
leaves to human political judgement rather than resolving computationally.

## References

- Autonomy / Alda — Haraldsson, G. D., & Kellam, J. (2021). *Going Public:
  Iceland's Journey to a Shorter Working Week.* Autonomy / Alda.
- Ellen MacArthur Foundation (2013). *Towards the Circular Economy:
  Economic and Business Rationale for an Accelerated Transition.*
- Frankfurt, H. (1987). Equality as a Moral Ideal. *Ethics*, 98(1), 21–43.
- Hansen, J. et al. (2013). Assessing "Dangerous Climate Change": Required
  Reduction of Carbon Emissions to Protect Young People, Future
  Generations and Nature. *PLOS ONE*.
- IEA (2021). *Net Zero by 2050: A Roadmap for the Global Energy Sector.*
  International Energy Agency.
- ILO (2012). *Social Protection Floors Recommendation, 2012 (No. 202).*
  International Labour Organization.
- IPCC (2022). *Climate Change 2022: Mitigation of Climate Change.*
  Working Group III Contribution to AR6.
- Kallis, G., Kostakis, V., Lange, S., Muraca, B., Paulson, S., &
  Schmelzer, M. (2018). Research on Degrowth. *Annual Review of
  Environment and Resources*, 43, 291–316.
- Nussbaum, M. (2011). *Creating Capabilities: The Human Development
  Approach.* Harvard University Press.
- OECD (2020). *Innovative Citizen Participation and New Democratic
  Institutions: Catching the Deliberative Wave.* OECD Publishing.
- O'Neill, D. W., Fanning, A. L., Lamb, W. F., & Steinberger, J. K. (2018).
  A good life for all within planetary boundaries. *Nature
  Sustainability*, 1, 88–95.
- Ostrom, E. (1990). *Governing the Commons: The Evolution of Institutions
  for Collective Action.* Cambridge University Press.
- Piketty, T. (2014). *Capital in the Twenty-First Century* (A.
  Goldhammer, Trans.). Harvard University Press.
- Raworth, K. (2017). *Doughnut Economics: Seven Ways to Think Like a
  21st-Century Economist.* Chelsea Green Publishing.
- Rockström, J. et al. (2009). A safe operating space for humanity.
  *Nature*, 461, 472–475.
- Sen, A. (1999). *Development as Freedom.* Oxford University Press.
- UNESCO (2015). *Incheon Declaration and Framework for Action for the
  Implementation of Sustainable Development Goal 4.*
- UN-Water (2021). *The United Nations World Water Development Report
  2021: Valuing Water.* UNESCO, on behalf of UN-Water.
- WHO & World Bank (2017). *Tracking Universal Health Coverage: 2017
  Global Monitoring Report.*
- WHO/UNICEF Joint Monitoring Programme (2021). *Progress on Household
  Drinking Water, Sanitation and Hygiene 2000–2020: Five Years into the
  SDGs.*
- Willett, W. et al. (2019). Food in the Anthropocene: the EAT–Lancet
  Commission on healthy diets from sustainable food systems. *The
  Lancet*, 393(10170), 447–492.
