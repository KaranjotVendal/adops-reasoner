# Data Strategy (No Real Campaign Data Available)

You currently have no real campaign dataset. For a 2-day showcase, the fastest and strongest path is:

## Recommended: Synthetic Scenario Dataset (Primary)
Build a realistic synthetic dataset with explicit expected actions.

---

## 1) Why synthetic is the right choice now
- You control class balance and edge cases
- You can create a labeled golden dataset quickly
- You avoid licensing/privacy issues
- It directly supports interview discussion on eval design

---

## 2) Scenario schema (use this exact shape)

```json
{
  "scenario_id": "scn_001",
  "campaign": {
    "campaign_id": "camp_001",
    "cpa_3d_trend": 28.0,
    "cpa_7d_trend": 31.0,
    "ctr_current": 0.9,
    "ctr_7d_avg": 1.8,
    "audience_saturation": 86.0,
    "days_since_creative_refresh": 21,
    "competitor_activity_score": 7.0,
    "current_spend_3d": 6500.0
  },
  "expected_action": "creative_refresh",
  "difficulty": "medium",
  "notes": "Classic creative fatigue pattern"
}
```

---

## 3) Labeling policy (deterministic baseline)
Use deterministic rules to generate expected labels:

1. **pause_campaign**
   - if `cpa_3d_trend > 50` and `cpa_7d_trend > 50`
2. **creative_refresh**
   - if `ctr_current < ctr_7d_avg * 0.7` and `days_since_creative_refresh > 14`
3. **audience_expansion**
   - if `audience_saturation > 85` and `cpa_3d_trend <= 20`
4. **bid_adjustment**
   - if `cpa_3d_trend > 20` and creative is not stale and CTR stable
5. **maintain**
   - otherwise

This gives a transparent expected label for eval.

---

## 4) Dataset size for 2-day MVP
- **50 scenarios total** is enough:
  - 10 per action class (balanced)
- Add **10 adversarial edge cases**:
  - conflicting signals
  - missing optional context
  - borderline thresholds

Total ~60 scenarios.

---

## 5) How to generate quickly

## Option A (fastest): Scripted random generator + deterministic labels
- Use NumPy random ranges for features
- Apply rule-based label function
- Write JSONL

## Option B (hybrid): Rule-generated + manually curated 10 scenarios
- Better interview quality because you can explain tricky edge cases

---

## 6) Optional public dataset (only if time remains)
If you still want external grounding, use one small public ad/campaign dataset from Kaggle and map available columns to your schema.

But for 2 days: **do not block on this**.
Synthetic + clear labeling is stronger than a rushed, messy real dataset.

---

## 7) What to say in interview about data
"Since I didn’t have production campaign data, I created a synthetic golden dataset with deterministic labeling rules and adversarial edge cases. This let me validate agent behavior reproducibly and build an evaluation harness. In production, I’d swap this input layer with BigQuery campaign snapshots and compare against human approval outcomes."

---

## 8) Minimal files to create
- `data/scenarios_v1.jsonl`
- `scripts/generate_scenarios.py`
- `evals/run_evals.py`
- `evals/results_baseline.json`

This is enough to demonstrate data generation + evaluation maturity.
