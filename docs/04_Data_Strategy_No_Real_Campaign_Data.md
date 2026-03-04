# Data Strategy (No Real Campaign Data)

## Decision
Use **synthetic scenario data** for MVP.

## Why
- fastest path in 2 days
- fully labeled golden dataset for evals
- no licensing/privacy uncertainty

## Schema
Each scenario includes:
- campaign metrics (`cpa_3d_trend`, `ctr_current`, `audience_saturation`, etc.)
- `expected_action`
- short notes

## Deterministic labels
1. `pause_campaign`: extreme CPA rise
2. `creative_refresh`: strong CTR drop + stale creative
3. `audience_expansion`: high saturation + stable CPA
4. `bid_adjustment`: CPA rise with stable CTR/non-stale creative
5. `maintain`: otherwise

## Dataset target
- 50 balanced scenarios + 10 edge cases

## Output files
- `data/scenarios_v1.jsonl`
- `evals/results_baseline.json`
