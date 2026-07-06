% ============================================================================
% Doughnut Economics as a constraint satisfaction problem (ASP encoding)
%
% Ethical grounding:
%   - Social floor  -> sufficientarianism (Frankfurt; capability approach,
%     Sen/Nussbaum): below the threshold on ANY dimension is a hard violation,
%     not tradeable against gains elsewhere.
%   - Ecological ceiling -> strong sustainability (planetary boundaries,
%     Rockström et al. 2009): boundaries are hard constraints, not negotiable
%     against economic benefit.
%
% Data: O'Neill, Fanning, Lamb & Steinberger (2018), values scaled x100.
%   bio_value(Country, Dim, V):  V <= 100 means the boundary is respected.
%   soc_value(Country, Dim, V):  V >= 100 means the threshold is met.
%
% Decision problem: given a target country and a menu of policy levers, find
% subset(s) of levers such that, once their effects are summed onto the
% baseline values, ALL social dimensions meet the floor AND ALL biophysical
% dimensions stay under the ceiling. If no subset works, the program is
% UNSAT and the unsat core (see run_scenario.py) identifies which
% floor/ceiling constraints remain structurally unreachable.
% ============================================================================

#include "levers.lp".

% target country is supplied externally, at solve time, as a fact target(C)
% (see run_scenario.py: ctl.add("base", [], f"target({country_slug}).") ).
% Keeping it external instead of hardcoded means the same program is reused
% for every country without touching the .lp file.

% { select(L) } is a CHOICE rule, not a plain implication: the curly braces
% tell clingo that select(L) is optional for each lever, so the solver
% branches over every one of the 2^14 subsets of levers as a candidate
% answer set. Everything below this line is a filter over that search space.
{ select(L) } :- lever(L).

% An integrity constraint (a rule with no head) discards WHOLE answer sets:
% any candidate where two conflicting levers are both selected is thrown
% away entirely, it never reaches the optimization step below.
:- select(L1), select(L2), conflicts(L1, L2).

% #sum aggregates the Delta of every lever that (a) was selected and
% (b) affects this Dim, so unselected levers contribute nothing. The ",L"
% inside the aggregate's tuple matters: without it, two different levers
% that happen to share the same Delta on the same Dim would collapse into
% one term (ASP aggregates dedupe identical tuples), silently under-counting
% the effect.
bio_effect(Dim, Sum) :-
    bio_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_bio(L, Dim, Delta) }.

soc_effect(Dim, Sum) :-
    soc_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_soc(L, Dim, Delta) }.

% Baseline value V plus the net lever effect E on that dimension. Ordinary
% integer arithmetic works here because everything is on the x100 integer
% scale from data_prep.py - clingo has no floats.
new_bio_value(C, Dim, V + E) :- target(C), bio_value(C, Dim, V), bio_effect(Dim, E).
new_soc_value(C, Dim, V + E) :- target(C), soc_value(C, Dim, V), soc_effect(Dim, E).

% These two predicates just name the pass/fail condition per dimension;
% the actual enforcement is the pair of integrity constraints right below.
ceiling_ok(C, Dim)  :- new_bio_value(C, Dim, V), V <= 100.
floor_met(C, Dim)   :- new_soc_value(C, Dim, V), V >= 100.

% Sufficientarianism and strong sustainability both reject trade-offs
% between dimensions, so this is written as two integrity constraints
% (one per dimension, dropped as soon as it fails) rather than one
% aggregate score - an answer set that fixes 17 dimensions but leaves one
% floor unmet is still discarded, exactly as the two theories require.
:- target(C), bio_value(C, Dim, _), not ceiling_ok(C, Dim).
:- target(C), soc_value(C, Dim, _), not floor_met(C, Dim).

% Among the answer sets that survive both constraints above, prefer the
% ones using fewer levers. run_scenario.py calls clingo with
% --opt-mode=optN, so ties at the optimal lever count are not resolved
% arbitrarily - every equally parsimonious answer set is reported, which is
% what surfaces cases like Costa Rica's four equivalent solutions.
#minimize { 1,L : select(L) }.

% Restricting #show to just these three predicates is also what
% --project (set in run_scenario.py) uses to decide which atoms count when
% checking whether two answer sets are "the same" model.
#show select/1.
#show new_bio_value/3.
#show new_soc_value/3.
