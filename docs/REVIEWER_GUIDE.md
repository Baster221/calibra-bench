# Audit a sealed scoring round

1. Inspect commitment domains and immutability: document binds curator/tag/questions, forecasts bind round/participant.
2. Follow advance: an early phase change requires all eligible slots complete. Reference reveal is impossible while a forecast can still enter.
3. Inspect resolve.validator: every outcome, including UNKNOWN, must match an independent full-reference interpretation.
4. Inspect _scores: rank uses exact squared_error, not the rounded display score; ties are shared.
5. Run the rational reference and the public verifier, then compare sealed, locked and final snapshots.

Important tests include display_rounding_cannot_create_a_ranking_tie, reference_cannot_be_revealed_before_predictions_locked, wrong_forecast_salt_vector_and_replay_fail, and reference_withholding_has_permissionless_void_exit.

This is not Blindfold's pairwise retro-funding mechanism: no model compares participants, no positional duel is scored, no Copeland points or payout pool exists. It is a commitment protocol around absolute probability forecasts and exact reference-dependent losses.

Direct mode uses the real SDK in memory and explicitly invokes validators. The live script independently exercises full network consensus with separate curator, two forecasters and keeper accounts. No signing keys are persisted.
