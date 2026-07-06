% ============================================================================
% Policy levers: illustrative, order-of-magnitude effect sizes.
%
% These are NOT fitted/causal estimates - no per-country causal dataset of
% policy effects exists. Each effect is a deliberately simplified, literature
% -informed guess at plausible direction and rough magnitude, scaled to the
% same x100 units as the O'Neill et al. indicators. This simplification is a
% declared limitation of the model (see report), not a hidden one: the ASP
% program is a tool for exploring the LOGIC of trade-offs between floor and
% ceiling under stated assumptions, not a predictive economic model.
%
% Loose sourcing per lever (direction/order of magnitude, not point estimates):
%   L1  - IPCC AR6 WGIII mitigation pathways / IEA net-zero scenario
%   L2  - Ellen MacArthur Foundation circular economy reports
%   L3  - FAO / EAT-Lancet on regenerative agriculture & nutrient runoff
%   L4  - UN Water efficiency reports
%   L5  - Kallis et al. (degrowth); 4-day week trials (Iceland, Autonomy UK)
%   L6  - ILO Social Protection Floor Recommendation 202
%   L7  - WHO Universal Health Coverage reports
%   L8  - OECD participatory budgeting / open government studies
%   L9  - Piketty, "Capital in the 21st Century" (wealth taxation)
%   L10 - UNESCO education investment reports
%   L11 - competing/cheaper alternative to L1 (fossil-based energy access)
%   L12 - subsidiarity/decentralization literature (Ostrom)
%   L13 - WHO/UNICEF WASH programme reports
%   L14 - carbon fee-and-dividend + large-scale reforestation (Hansen et al.
%         2015 on carbon fee and dividend; IPCC AR6 WGIII on reforestation
%         as a carbon sink; the equality co-benefit follows from returning
%         carbon-fee revenue as an equal per-capita dividend)
% ============================================================================

lever(l1_renewable_energy).
lever(l2_circular_economy).
lever(l3_sustainable_agriculture).
lever(l4_water_efficiency).
lever(l5_working_time_reduction).
lever(l6_universal_basic_income).
lever(l7_universal_healthcare).
lever(l8_participatory_governance).
lever(l9_wealth_tax).
lever(l10_education_investment).
lever(l11_fossil_energy_expansion).
lever(l12_decentralization_reform).
lever(l13_sanitation_infrastructure).
lever(l14_carbon_fee_dividend_reforestation).

% --- effects on biophysical dimensions (negative = reduces overshoot) -----
affects_bio(l1_renewable_energy,     co2, -35).
affects_bio(l2_circular_economy,     material_footprint, -30).
affects_bio(l2_circular_economy,     eco_footprint, -15).
affects_bio(l3_sustainable_agriculture, nitrogen, -25).
affects_bio(l3_sustainable_agriculture, phosphorus, -25).
affects_bio(l3_sustainable_agriculture, ehanpp, -30).
affects_bio(l4_water_efficiency,     blue_water, -20).
affects_bio(l5_working_time_reduction, eco_footprint, -20).
affects_bio(l5_working_time_reduction, material_footprint, -15).
affects_bio(l11_fossil_energy_expansion, co2, 15).
affects_bio(l14_carbon_fee_dividend_reforestation, co2, -50).
affects_bio(l14_carbon_fee_dividend_reforestation, ehanpp, -35).

% --- effects on social dimensions (positive = closes deficit) -------------
affects_soc(l1_renewable_energy,     energy_access, 15).
affects_soc(l3_sustainable_agriculture, nutrition, -10).
affects_soc(l5_working_time_reduction, life_satisfaction, 22).
affects_soc(l5_working_time_reduction, employment, 10).
affects_soc(l6_universal_basic_income, income, 20).
affects_soc(l6_universal_basic_income, sanitation, 15).
affects_soc(l6_universal_basic_income, nutrition, 10).
affects_soc(l7_universal_healthcare,  healthy_life_exp, 20).
affects_soc(l7_universal_healthcare,  social_support, 10).
affects_soc(l8_participatory_governance, democratic_quality, 30).
affects_soc(l8_participatory_governance, social_support, 10).
affects_soc(l9_wealth_tax,           equality, 25).
affects_soc(l9_wealth_tax,           income, 10).
affects_soc(l10_education_investment, education, 20).
affects_soc(l10_education_investment, employment, 10).
affects_soc(l11_fossil_energy_expansion, energy_access, 20).
affects_soc(l12_decentralization_reform, democratic_quality, 20).
affects_soc(l12_decentralization_reform, social_support, 5).
affects_soc(l13_sanitation_infrastructure, sanitation, 25).
affects_soc(l14_carbon_fee_dividend_reforestation, equality, 15).

% --- competing policy approaches: cannot both be chosen --------------------
% Only the (l1, l11) pair is stated; the second rule below derives the
% symmetric fact conflicts(l11, l1) automatically, so doughnut.lp's
% conflicts(L1, L2) check catches the pair regardless of which order the
% solver happens to try the two levers in.
conflicts(l1_renewable_energy, l11_fossil_energy_expansion).
conflicts(X, Y) :- conflicts(Y, X).
