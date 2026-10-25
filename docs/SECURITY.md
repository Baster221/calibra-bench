# Trust and information boundaries

## Curated benchmark, not objective global truth

The curator chooses the document, questions and roster and knows the document before the round. Commitment prevents later substitution; it cannot prevent prior knowledge, leaks, biased sampling, collusion or use of another address. Excluding the curator's own address is not a Sybil defense.

Scores concern this round's reference and resolved mask only. They are not globally comparable reputation, proof of human identity, or a statistical calibration certificate. No funds are awarded.

A curator can withhold a reference selectively. The round then remains visibly registered and eventually records VOID/REFERENCE_WITHHELD; it cannot be deleted or quietly cancelled. External benchmark consumers must account for voids and curator behavior. No economic penalty or bond is claimed.

## Commitment privacy

Use independent random 32-byte salts generated locally. A predictable or reused salt can permit dictionary attacks on small forecast spaces or predictable references. Contract length/hex checks do not measure entropy. Preview views expose their arguments to the RPC provider; they are for already-public data or local testing. The demo performs pre-reveal hashing locally.

This is temporary commitment hiding, not confidential computation. All revealed forecasts, salts, reference and outcomes become public. A participant or curator may voluntarily leak information; the contract cannot prevent off-chain disclosure.

## Model and outcome risks

Validators independently interpret the entire reference. Correlated mistakes or a malicious majority can still mislabel a question. Exact agreement can also reduce liveness on ambiguous text. The live example is not a broad adversarial-model benchmark.

Every UNKNOWN column is excluded for everyone. A missing reveal receives no score rather than an invented forecast. If every question is unresolved, the round is VOID. Fixed forecasts cannot change after the answer appears. Display rounding cannot change ranks.

## State, bounds and availability

One commitment and reveal per participant; immutable reference digest/questions/roster; per-curator tag uniqueness; deployment/round/participant domain separation; explicit phase deadlines and permissionless advancement. Early closure requires every still-eligible member to have completed the phase, preventing an early answer from being shown to an uncommitted participant.

The protocol assumes keepers eventually call advancement/expiry. No automatic scheduler or guaranteed model availability exists. Resolution is bounded to six questions and eight forecasts; reference text is at most 6,000 characters.

No payable methods, assets, external messages or callbacks exist. External consumers wait for finalized scored state. The supplied network is StudioNet, distinct from Bradbury and the separate Studio development preview.
