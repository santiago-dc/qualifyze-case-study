# Phase 1: Data Collection

## Plan

| Step | Status |
|------|--------|
| Create repository structure | Done |
| Set up environment with `uv` | Done |
| Download Warning Letters (FDA.gov datatables API) | Done |
| Download Enforcement/Recalls (openFDA bulk API) | Done |
| Download Inspections Dataset (FDA Data Dashboard) | Done (manual) |
| Download Citations Dataset (FDA Data Dashboard) | Done (manual) |
| Download Published 483s Dataset (FDA Data Dashboard) | Done (manual) |

## Data sources (links from the case study brief)

| # | Link from PDF | What we downloaded | Output file |
|---|---|---|---|
| 1 | [qualifyze.com](https://www.qualifyze.com) | Nothing — business context only | — |
| 2 | [Warning Letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters) | Warning letters via datatables API | `warning_letters.json` |
| 3 | [Inspection Classifications](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-classification-database) | Redirects to FDA Dashboard → manual download | `inspections.xlsx`, `citations.xlsx`, `published_483s.xlsx` |
| 4 | [Broader FDA data-sets](https://open.fda.gov) | Bulk download enforcement/recalls | `drug-enforcement-0001-of-0001.json` |
| 5 | [FDA Dashboards](https://datadashboard.fda.gov) | Same as #3 (visual interface) | (same files) |

## Download method

- **Warning Letters**: paginated scraping of the FDA.gov datatables API (`src/data/fetch_warning_letters.py`). Uses `start`/`length`/`draw` params for pagination.
- **Enforcement/Recalls**: direct bulk download from openFDA (`https://download.open.fda.gov/drug/enforcement/drug-enforcement-0001-of-0001.json.zip`).
- **Inspections, Citations, and 483s**: manual download from the FDA Data Dashboard (uses Qlik Sense internally — cannot be automated without a headless browser). URL: `https://datadashboard.fda.gov/oii/cd/inspections.htm`.

---

## Context: What is all this?

### The FDA and pharmaceutical regulation

The **FDA** (Food and Drug Administration) is the U.S. government agency that regulates food, drugs, medical devices, and cosmetics. Any company that manufactures, packages, or distributes these products can be inspected by the FDA to verify compliance with quality and safety standards (known as **GMP** — Good Manufacturing Practices, or **CGMP** — Current Good Manufacturing Practices).

This applies globally: if you manufacture drugs in India and export them to the U.S., the FDA can inspect your facility.

### The regulatory enforcement flow (least to most severe)

```
Routine Inspection
    │
    ├── NAI (No Action Indicated) → Everything OK ✓
    │
    ├── VAI (Voluntary Action Indicated) → Minor issues found,
    │   the company must voluntarily correct them
    │
    └── OAI (Official Action Indicated) → Serious issues,
        the FDA takes official action:
            │
            ├── Form 483 → Document listing specific observations,
            │   handed to the company at the end of the inspection
            │
            ├── Warning Letter → Formal letter demanding corrections.
            │   If you don't respond, things get worse:
            │
            └── Enforcement Action → Recalls, import alerts,
                court injunctions, plant shutdowns
```

### What this means for Qualifyze

Qualifyze evaluates suppliers for their clients (pharmaceutical companies, etc.). If a supplier has a history of OAIs, warning letters, or recalls, it's a high-risk supplier. Our model needs to predict this BEFORE it happens, using early signals.

---

## Downloaded files

### `data/raw/inspections.xlsx`
- **What it is**: All FDA inspections with their final classification outcome.
- **Size**: 337,519 rows × 15 columns
- **Key columns**:
  - `FEI Number` — Unique facility identifier (Facility Establishment Identifier). This is the **primary key** for joining datasets.
  - `Legal Name` — Company legal name.
  - `Classification` — **NAI / VAI / OAI**. This is the most important variable. OAI = serious problems.
  - `Inspection End Date` — When the inspection was completed.
  - `Project Area` — Regulatory area (e.g., "Drug Quality", "Foodborne Biological Hazards").
  - `Product Type` — Product type (Drugs, Food/Cosmetics, Medical Devices, etc.).
  - `Fiscal Year` — Fiscal year of the inspection.
- **How we use it**: This is our primary dataset. Each row is an inspection of a facility with its outcome. We can build the complete history of each company and predict their next classification.

### `data/raw/citations.xlsx`
- **What it is**: Specific regulatory violations cited in each inspection.
- **Size**: 277,463 rows × 8 columns
- **Key columns**:
  - `Inspection ID` — Links to the inspections dataset.
  - `FEI Number` — Facility identifier.
  - `Act/CFR Number` — The specific regulation violated (e.g., "21 CFR 211.68" = lack of automatic controls in production).
  - `Short Description` / `Long Description` — Text describing the violation.
  - `Program Area` — Area (Drugs, Foods, Devices, etc.).
- **How we use it**: Detail-level features. A company with 2 minor violations is not the same as one with 15 sterility violations. This lets us categorize severity and type of non-compliance.

### `data/raw/published_483s.xlsx`
- **What it is**: Published Form 483 documents. This is the formal document an inspector delivers at the end of an inspection when problems are found.
- **Size**: 1,973 rows × 7 columns
- **Key columns**:
  - `FEI Number` — Facility identifier.
  - `Record Date` — Inspection date.
  - `Download` — URL to the Form 483 PDF (with detailed observations).
  - `Publish Date` — When it was made public.
- **How we use it**: Primarily as a binary signal (does it have a published 483?). Optionally we could do NLP on the PDFs to extract observation categories, but that's scope creep for a 7-day timeline.

### `data/raw/warning_letters.json`
- **What it is**: All warning letters issued by the FDA (2021–2026).
- **Size**: 3,608 records
- **Key fields**:
  - `company_name` — Company name.
  - `issue_date` — Date issued.
  - `issuing_office` — FDA center that issued it (CDER = drugs, CDRH = devices, CFSAN = food).
  - `subject` — Type of violation (e.g., "CGMP/Finished Pharmaceuticals/Adulterated").
  - `letter_url` — URL to the full letter.
- **How we use it**: High-severity feature. A warning letter is a strong risk signal. It could also be part of the target if we want to predict "will this company receive a warning letter in the next 12 months?".
- **Limitation**: Does not have FEI Number, so entity matching by name is required to join with inspections.

### `data/raw/drug-enforcement-0001-of-0001.json`
- **What it is**: All enforcement actions (primarily product recalls).
- **Size**: 17,773 records
- **Key fields**:
  - `recalling_firm` — Company recalling the product.
  - `classification` — Recall severity: **Class I** (health hazard/death), **Class II** (reversible or low probability), **Class III** (no adverse health effects).
  - `product_type` — Drugs, Devices, Food, etc.
  - `reason_for_recall` — Free text explaining the reason.
  - `recall_initiation_date` — When the recall started.
  - `city`, `state`, `country` — Company location.
  - `voluntary_mandated` — Whether voluntary or FDA-mandated.
- **How we use it**: Additional risk feature. A prior Class I recall is an extremely strong signal. It's also a possible alternative target.
- **Limitation**: Does not have FEI Number. Entity matching by `recalling_firm` required.

---

## Dataset relationships

```
                    FEI Number
inspections.xlsx ◄──────────────► citations.xlsx
       │                                │
       │ FEI Number                     │ Inspection ID
       │                                │
       ▼                                ▼
published_483s.xlsx              (detail per inspection)


       Entity matching by name
inspections.xlsx ◄·····················► warning_letters.json
       │
       │ Entity matching by name
       ▼
drug-enforcement-0001-of-0001.json
```

**Key**: `FEI Number` directly joins inspections + citations + 483s. For warning letters and enforcement, we need fuzzy name matching (entity resolution).

---

## Known limitations

### Inspections dataset is not comprehensive

The FDA Data Dashboard states:

> "This database does not represent a comprehensive listing of all conducted inspections and should not be used as a source to compile official data."

**What this means**: The inspections dataset is a subset. It excludes certain categories (e.g., pre-approval inspections, state contract inspections, mammography, nonclinical lab inspections).

**Impact on our model**: Some facilities may have regulatory history not captured in this dataset, biasing the model toward false negatives for those companies.

**Mitigation strategy**:
- Acknowledge this as an explicit limitation in the report.
- In production, Qualifyze would supplement this with their private audit data (which is exactly what task 1b asks: "Link Public and Private Data").
- The model should be presented as a "public-data baseline" that improves when enriched with proprietary sources.

### Warning letters and enforcement lack FEI Number

These datasets identify companies by name only, with no unique identifier. Entity resolution (fuzzy matching) will introduce some noise. We accept this trade-off and document the matching precision.

---

## Class distribution (Inspections)

| Classification | Records | % | Meaning |
|--------------|-----------|---|---------|
| NAI | 218,417 | 64.7% | No issues |
| VAI | 106,058 | 31.4% | Minor issues |
| OAI | 13,044 | 3.9% | Serious issues → OUR TARGET |

The dataset is **heavily imbalanced** (only 3.9% OAI). This will need to be addressed during modeling (class weighting, SMOTE, or threshold tuning).
