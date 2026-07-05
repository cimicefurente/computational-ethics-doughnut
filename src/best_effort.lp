% ============================================================================
% Diagnostic variant: no hard floor/ceiling constraints. Instead, directly
% minimize the total remaining violation (sum of overshoot beyond the
% ceiling + sum of deficit below the floor) over the choice of levers.
%
% Used only when the feasibility program (doughnut.lp) is UNSAT for a
% country: it identifies the best achievable outcome and, per dimension,
% exactly how much of the floor/ceiling violation cannot be closed by any
% combination of the available levers - i.e. it plays the role an
% unsatisfiable core would play, but expressed as "remaining ethical
% violation per dimension" rather than as a set of conflicting rule
% instances (see report for the methodological note on why this substitute
% was used).
% ============================================================================

#include "levers.lp".

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

overshoot(Dim, V - 100) :- new_bio_value(_, Dim, V), V > 100.
deficit(Dim, 100 - V)   :- new_soc_value(_, Dim, V), V < 100.

#minimize { P,Dim : overshoot(Dim, P) }.
#minimize { P,Dim : deficit(Dim, P) }.

#show select/1.
#show overshoot/2.
#show deficit/2.
