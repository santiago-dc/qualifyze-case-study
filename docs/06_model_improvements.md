# Phase 6: Model Improvements

## Motivation

Initial model achieved ROC-AUC 0.87, PR-AUC 0.37. While decent, we identified three areas where we weren't extracting all available signal from the data:

1. Entity matching was losing 66% of warning letters
2. Citations were only counted, not categorized by severity
3. Warning letter type/subject was not used as a feature

## Changes made

### 1. Improved entity resolution

**Before**: TF-IDF matching at threshold 0.8 (name only)
**After**: TF-IDF at threshold 0.6 + location confirmation for borderline matches (0.6-0.8)

Logic:
- Score ≥ 0.8 → accept directly (high confidence on name alone)
- Score 0.6-0.8 → accept only if city/state/country overlaps between source and target
- Score < 0.6 → reject

Also added: URL stripping from company names (many WL recipients are `www.something.com`)

| Dataset | Before | After | Improvement |
|---|---|---|---|
| Warning letters | 805 / 2,356 (34%) | 1,291 / 2,356 (55%) | +60% |
| Enforcement | 3,220 / 4,585 (70%) | 3,760 / 4,585 (82%) | +17% |

### 2. Citation severity categorization

Instead of just counting total citations, we now categorize each CFR code violation:

| Category | Example CFR codes | What it means |
|---|---|---|
| `sterility` | 211.113, 211.42, 211.46 | Contamination / sterility failures (most severe) |
| `process_validation` | 211.100, 211.110, 820.75 | Process not validated |
| `quality_system` | 211.22, 211.192, 820.22 | QA system failures |
| `records_documentation` | 211.180, 211.186, 820.184 | Documentation gaps |
| `testing_lab` | 211.160, 211.165 | Lab testing failures |
| `other` | Everything else | Catch-all |

New features: `prior_citations_sterility`, `prior_citations_process_validation`, etc.

**Why this matters**: A facility with 5 sterility violations is much higher risk than one with 5 labeling violations. Categorizing lets the model learn this distinction.

### 3. Warning letter subject features

Instead of just `n_warning_letters` (count), we now extract the TYPE of violation from the `subject` field:

| Feature | What it captures |
|---|---|
| `wl_cgmp` | GMP manufacturing violations |
| `wl_unapproved_drug` | Selling unapproved drugs |
| `wl_adulterated` | Product adulteration |
| `wl_misbranded` | Labeling/branding issues |
| `wl_medical_device` | Device-specific violations |
| `wl_compounding` | Pharmacy compounding issues |
| `wl_fsvp` | Foreign supplier verification failures |

**Why this matters**: A CGMP warning letter is a much stronger signal of manufacturing quality issues than an FSVP letter (which is about paperwork for imports).

## Important: no inspections are discarded

If a facility has no matched warning letters or enforcement records, those features are simply 0. The 165,010 inspections ALL remain in the final dataset. The entity matching adds signal for facilities that DO have external records — it doesn't filter out those that don't.

## New feature count

- Before: 22 numeric features + 3 categorical
- After: ~35 numeric features + 3 categorical (+13 new features from citation categories and WL types)

## Expected impact

- More warning letter signal flowing into the model (55% vs 34% coverage)
- Model can now distinguish between HIGH severity violations (sterility) and LOW severity (documentation)
- Warning letter type lets the model weight CGMP letters differently from FSVP letters
