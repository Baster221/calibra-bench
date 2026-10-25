# Live sealed-reference probability benchmark

Validation date: 25 October 2026. Network: **GenLayer StudioNet**, chain ID 61999. The supplied deployment is hosted GenVM execution, not Bradbury or the separate Studio development preview.

Contract: [0x3a9E4B52f1dcD956E95155541Fc21E43bb5a1139](https://explorer-studio.genlayer.com/address/0x3a9E4B52f1dcD956E95155541Fc21E43bb5a1139)

Deployment transaction: `0x4cd3b619ace771c1014ad876289e887f3a18c122363acf91d8ab47aa5afee1aa`

Exact runner, source hashes and byte-for-byte deployment equality are recorded in [deployment.json](../deployment.json).

## Four distinct roles

A curator commits a workshop notice before either forecaster submits. Two different participant addresses seal probability vectors using separate random salts. A fourth address permissionlessly closes completed phases and resolves the final round.

One-hour phase windows leave room for finality. Because every eligible member completes its phase, both closure operations legitimately execute early; no fixed-time shortcut exposes the reference to a participant still able to alter a forecast.

## Outcomes

| Question | Reference content | Agreed answer |
|---|---|---|
| Support on Saturdays? | Monday–Friday only; no Saturday/Sunday support | NO |
| Registration required before entry? | Attendees must register before entering | YES |
| Admission free? | No admission price is established | UNKNOWN |

Forecast A is [1000,9000,5000], forecast B is [9000,1000,0]. The common scorable mask is [0,1].

| Participant | Summed squared error | Display score | Rank |
|---|---:|---:|---:|
| A | 2,000,000 | 9,900 bps | 1 |
| B | 162,000,000 | 1,900 bps | 2 |

The UNKNOWN price column changes neither participant's loss or ranking. State snapshots show empty reference/probability fields during COMMIT, locked forecasts with an unopened reference in ANSWER, and the complete final scored state.

There are **10 finalized successful transactions** in [network.json](../evidence/network.json). Actual model outputs and votes are retained, including idle/disagree votes if present. The run uses normal consensus, not leader-only execution. [state.json](../evidence/state.json) contains sealed, locked and final snapshots plus the result commitment.

Ephemeral signer keys were never saved. Reference and forecast salts are intentionally public after their reveal. The supplied forecast values are illustrative authored inputs, not measured outputs from independent forecasting systems.

## Re-fetch and recompute

```bash
npm ci --ignore-scripts
npm run verify
python scripts/check_manifest.py
```

The online verifier needs no wallet. It compares live source bytes and receipt targets/finality/execution, fetches current round/result, then recomputes the document commitment, every revealed forecast commitment, shared UNKNOWN mask, exact BigInt losses, display scores and ranks. The Python check is offline consistency only.

This focused run does not establish broad model accuracy, unbiased sampling, participant independence or statistical calibration. Those limitations are explicit in the threat model.
