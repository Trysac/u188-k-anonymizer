# Project Record

## Objective
Check k-anonymity of tabular data over quasi-identifiers and find minimal full-domain generalisation levels with bounded suppression using a native Python implementation.

## Scope
- In scope: The public API documented in the README (`check_k`, `anonymize`, `numeric_range`, `prefix_mask`, and `KAnonError`), which is fully typed and tested.
- Out of scope: L-diversity, differential privacy, local recoding (like Mondrian), and date hierarchies.

## Effort Metrics
| Metric | Value |
|---|---|
| Tokens (input / output) | 1677683 / 22652 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.3591 |

## Factory run u188 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4289 | 14028 | 0 | 0 | 0.0279 |
| fix-1 | gemini-3.8-flash | no | 83734 | 3097 | 0 | 599202 | 0.1194 |
| fix-2 | gemini-3.8-flash | no | 57309 | 2288 | 0 | 229321 | 0.0688 |
| fix-3 | gemini-3.8-flash | no | 71021 | 1779 | 0 | 422979 | 0.0917 |
| audit | gemini-3.1-flash-lite | no | 29520 | 141 | 0 | 14220 | 0.0079 |
| docs | gemini-3.1-flash-lite | no | 166088 | 1319 | 0 | 0 | 0.0435 |

Total: $0.3591. Prices: Anthropic list prices.
