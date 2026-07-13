# Phase 2: EDA & Entity Resolution

## Plan

| Step | Status |
|------|--------|
| Exploratory analysis of inspections | Done |
| Exploratory analysis of citations | Done |
| Exploratory analysis of warning letters | Done |
| Exploratory analysis of enforcement/recalls | Done |
| Entity resolution: warning letters → inspections | Done |
| Entity resolution: enforcement → inspections | Done |
| Document findings | Done |

## Scope decisions

- **Excluded pure food** Project Areas (Foodborne Biological Hazards, Food Composition, Pesticides, Food Additives, Molecular Biology/Natural Toxins)
- **Kept cosmetics** (Colors and Cosmetics Technology, Technical Assistance: Food and Cosmetics)
- **Excluded tobacco** from warning letters (not relevant for Qualifyze's pharma/device supply chain focus)
- **Enforcement**: drug + device only, skipped food

## Key EDA findings

### Inspections (after excluding food): 165,010

| Classification | Count | Rate |
|---|---|---|
| NAI | 104,536 | 63.3% |
| VAI | 52,746 | 32.0% |
| OAI | 7,728 | 4.7% |

### OAI rate by sector

| Product Type | OAI Rate |
|---|---|
| Tobacco | 12.2% |
| Drugs | 7.6% |
| Devices | 5.9% |
| Veterinary | 4.6% |
| Biologics | 0.9% |
| Food/Cosmetics | 0.6% |

### Repeat offenders
- 5,149 unique facilities with at least 1 OAI
- 497 facilities with 3+ OAIs
- Top offender: 14 OAIs (Meridian Medical Technologies)

### Citations as predictive signal
- 69% of OAI inspections have at least 1 citation
- Only 6.6% of NAI inspections have citations
- Strong predictor

### Warning letters (excl. tobacco): 2,410
- Top subjects: CGMP pharmaceuticals (335), FSVP (302), Unapproved drugs (151)

### Enforcement (drug + device): 57,203
- Class I (severe): 5,308
- Class II (moderate): 49,169
- Class III (minor): 2,725

## Entity resolution

### Method
1. Normalize company names (lowercase, strip suffixes like LLC/Inc/Ltd, remove punctuation, remove "d/b/a" clauses)
2. TF-IDF vectorization with character n-grams (2-4)
3. Cosine similarity matching
4. Threshold: 0.8 (conservative — avoids false matches)

### Results

| Source | Unique names | Matched to FEI | Match rate |
|---|---|---|---|
| Warning letters | 2,356 | 805 | 34.2% |
| Enforcement | 4,585 | 3,220 | 70.2% |

### Why warning letters have lower match rate
Many warning letter recipients are online pharmacies, small retailers, or foreign companies that have never been inspected by the FDA (and thus don't appear in the inspections database). This is expected, not a data quality issue.

### Output
- `data/processed/entity_matches.json` — maps company names to FEI numbers with confidence scores
