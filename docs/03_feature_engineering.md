# Phase 3: Feature Engineering

## Plan

| Step | Status |
|------|--------|
| Define unit of analysis | Done |
| Build history-based features | Done |
| Integrate warning letters & enforcement via entity matches | Done |
| Handle temporal leakage prevention | Done |
| Save processed dataset | Done |

## Design decisions

### Unit of analysis
**One row per inspection**. For each inspection, features are built from the facility's PRIOR history only (everything before that inspection's date). This prevents data leakage.

### Target variable
`target_oai` — binary: 1 if this inspection resulted in OAI, 0 otherwise.

### Temporal split
- **Train**: inspections before 2025 (154,386 rows, OAI rate 4.66%)
- **Test**: inspections 2025+ (10,624 rows, OAI rate 4.97%)

Rates are similar → no significant distribution shift.

## Features built (per inspection)

### Inspection history (from prior inspections of the same facility)
| Feature | Description |
|---|---|
| `n_prior_inspections` | Total inspections before this one |
| `n_prior_oai` | Count of prior OAI classifications |
| `n_prior_vai` | Count of prior VAI classifications |
| `n_prior_nai` | Count of prior NAI classifications |
| `pct_oai` | OAI rate in history (redundant for trees, useful for linear) |
| `pct_vai` | VAI rate in history (same) |
| `days_since_last_inspection` | Recency (-1 if first inspection) |
| `last_classification_oai` | Was the most recent prior inspection OAI? |
| `last_classification_vai` | Was the most recent prior inspection VAI? |
| `trend_worsening` | Did classification get worse in the last 2 inspections? |
| `recent_oai_rate` | OAI rate in last 2 inspections |

### Citation features (from prior inspections)
| Feature | Description |
|---|---|
| `total_prior_citations` | Sum of all citations in prior inspections |
| `avg_citations_per_inspection` | Mean citations per prior inspection |
| `max_citations_single_inspection` | Peak violations in one inspection |
| `total_unique_cfr_violated` | Number of distinct CFR codes violated |

### Warning letter features (before this inspection's date)
| Feature | Description |
|---|---|
| `n_warning_letters` | Count of warning letters received |
| `has_warning_letter` | Binary (redundant for trees) |
| `days_since_last_wl` | Recency of last warning letter (-1 if none) |

### Enforcement features (before this inspection's date)
| Feature | Description |
|---|---|
| `n_recalls` | Total recalls |
| `has_recall` | Binary (redundant for trees) |
| `n_class_I_recalls` | Count of severe (Class I) recalls |
| `n_class_II_recalls` | Count of moderate (Class II) recalls |

### Published 483s features
| Feature | Description |
|---|---|
| `n_published_483s` | Count of published Form 483s |
| `has_published_483` | Binary (redundant for trees) |

### Categorical features
| Feature | Description |
|---|---|
| `product_type` | Drugs, Devices, Biologics, Veterinary, etc. |
| `country` | Country of the facility |
| `project_area` | Regulatory area (Drug Quality, Compliance Devices, etc.) |

## Redundant features note

Features marked "redundant for trees" (`has_*`, `pct_*`) are kept in the dataset but:
- **Used** by Logistic Regression (helps capture non-linear threshold effects)
- **Excluded** from XGBoost (tree can learn `n > 0` splits natively)

## Output
- `data/processed/features.parquet` — 165,010 rows × 30 columns
