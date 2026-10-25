# Sealed-reference benchmark protocol

## State and roles

One round fixes a curator, unique curator tag, 1–6 binary questions, a salted reference digest, 2–8 participant addresses and bounded phase windows. The curator's literal address cannot enter its roster. Other addresses are not asserted to be different real people.

Rounds persist as canonical JSON in a typed TreeMap. Only roster signers may commit/reveal their own probabilities; only the curator may open the reference. Anyone may advance completed/expired phases or resolve a ready round. No caller can replace outcomes, forecasts or questions.

## Commitment domains

```text
document:
  protocol, chain_id, contract, curator, tag, questions, document, salt
forecast:
  protocol, chain_id, contract, round_id, participant, probabilities, salt
```

SHA-256 hashes canonical JSON: sorted keys, compact separators, ensure_ascii=True. Hash strings and salts are exactly 64 lowercase hexadecimal characters. The JavaScript canonical helper reproduces this encoding. Salts must be cryptographically random in actual use; length checks cannot prove entropy.

Compute preimages locally. Calling the public commitment preview views with secret data exposes it to the RPC provider even though the call does not persist it on-chain. The smoke script hashes locally and uses fresh random 32-byte salts.

The curator tag is unique per curator and known before creation. It allows document binding without racing to guess the globally assigned round ID. Forecasts bind the actual round ID after creation.

## Phase closure

COMMIT accepts one immutable commitment per roster slot until its deadline. Anyone can close early only when all slots committed; otherwise wait for the deadline. Closing permanently freezes the committed cohort.

REVEAL accepts matching complete probability vectors only from that cohort. It closes early only when all committed slots revealed, or at its deadline. Nonrevealers become ineligible.

ANSWER accepts the curator's reference and salt only after forecast closure. A mismatching preimage cannot change state. Timeout records VOID/REFERENCE_WITHHELD.

READY permits one consensus resolution before the deadline. Timeout records VOID/CONSENSUS_TIMEOUT. All-UNKNOWN resolution records VOID/ALL_UNKNOWN. Other VOID reasons include NO_COMMITS and NO_REVEALS. Terminal rounds cannot be revived.

Each window is 60 seconds to one day and starts at the relevant phase transition. Provide enough time for network finality and participant availability; the live demo uses one-hour windows with safe early closure.

## Exact scoring

Probabilities are integers p in [0,10000]. For each globally scorable question, y is 10000 for YES or 0 for NO. UNKNOWN excludes that question for every participant.

```text
L = sum((p_i-y_i)^2) over scorable questions
M = number_of_scorable_questions * 10000^2
display_score_bps = floor((M-L)*10000/M)
rank = 1 + number_of_participants_with_strictly_lower_L
```

The display score is a presentation value. Ranking uses exact L, including distinctions hidden by display rounding. Equal exact losses share rank; address order only stabilizes their display order. Everyone is scored on the same question count, so ranking summed loss equals ranking mean loss.

The binary quadratic loss follows the probability-forecast scoring tradition introduced by [Brier, 1950](https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.xml). This contract implements its explicitly defined binary scaling, rather than claiming that one curated round proves calibrated probabilities.

## Integration

Prepare questions, reference and random salt locally; hash the document domain; create the round. Participants hash forecasts locally, commit, then reveal only in REVEAL. The curator opens the reference in ANSWER. Keepers call resolve in READY and consume finalized get_round/result_commitment results.

Maximum work per resolution is six question outcomes and eight fixed forecasts. There is no pairwise ranking model, payout pool, evidence challenge registry or external identity decision.
