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

% --- target country is supplied externally via a fact target(C). ----------

% --- choice: any subset of the available levers may be selected -----------
{ select(L) } :- lever(L).

% --- mutually exclusive levers (competing policy approaches) --------------
:- select(L1), select(L2), conflicts(L1, L2).

% --- net effect of selected levers on a dimension --------------------------
bio_effect(Dim, Sum) :-
    bio_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_bio(L, Dim, Delta) }.

soc_effect(Dim, Sum) :-
    soc_dim(Dim),
    Sum = #sum { Delta,L : select(L), affects_soc(L, Dim, Delta) }.

% --- resulting value after applying the selected levers --------------------
new_bio_value(C, Dim, V + E) :- target(C), bio_value(C, Dim, V), bio_effect(Dim, E).
new_soc_value(C, Dim, V + E) :- target(C), soc_value(C, Dim, V), soc_effect(Dim, E).

% --- hard constraints: sufficientarian floor, strong-sustainability ceiling
ceiling_ok(C, Dim)  :- new_bio_value(C, Dim, V), V <= 100.
floor_met(C, Dim)   :- new_soc_value(C, Dim, V), V >= 100.

:- target(C), bio_value(C, Dim, _), not ceiling_ok(C, Dim).
:- target(C), soc_value(C, Dim, _), not floor_met(C, Dim).

% --- parsimony preference: fewer levers = less invasive policy ------------
#minimize { 1,L : select(L) }.

#show select/1.
#show new_bio_value/3.
#show new_soc_value/3.
