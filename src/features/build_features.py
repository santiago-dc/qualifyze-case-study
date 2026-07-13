"""
Feature engineering pipeline.

Unit of analysis: one row per inspection.
For each inspection, we build features from the facility's PRIOR history
(everything before that inspection's date).

Target: is this inspection classified as OAI? (binary)

Temporal split:
- Train: inspections before 2025
- Test: inspections 2025-2026
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np

DATA_RAW = Path(__file__).parents[2] / "data" / "raw"
DATA_PROCESSED = Path(__file__).parents[2] / "data" / "processed"

FOOD_ONLY_AREAS = [
    "Foodborne Biological Hazards",
    "Food Composition, Standards, Labeling and Econ",
    "Pesticides and Chemical Contaminants",
    "Food and Color Additives Petition Review",
    "Molecular Biology and Natural Toxins",
]


def load_inspections() -> pd.DataFrame:
    """Load and filter inspections dataset."""
    df = pd.read_excel(DATA_RAW / "inspections.xlsx")
    df = df[~df["Project Area"].isin(FOOD_ONLY_AREAS)].copy()
    df["Inspection End Date"] = pd.to_datetime(df["Inspection End Date"])
    df = df.sort_values(["FEI Number", "Inspection End Date"]).reset_index(drop=True)
    df["is_oai"] = (df["Classification"] == "Official Action Indicated (OAI)").astype(int)
    df["is_vai"] = (df["Classification"] == "Voluntary Action Indicated (VAI)").astype(int)
    df["is_nai"] = (df["Classification"] == "No Action Indicated (NAI)").astype(int)
    return df


def load_citations() -> pd.DataFrame:
    """Load citations dataset."""
    df = pd.read_excel(DATA_RAW / "citations.xlsx")
    return df


def load_entity_matches() -> dict:
    """Load entity resolution results."""
    with open(DATA_PROCESSED / "entity_matches.json") as f:
        return json.load(f)


def load_warning_letters(entity_matches: dict) -> pd.DataFrame:
    """Load warning letters with matched FEI numbers."""
    with open(DATA_RAW / "warning_letters.json") as f:
        wl = pd.DataFrame(json.load(f))
    wl["issue_date"] = pd.to_datetime(wl["issue_date"])
    wl_matches = entity_matches["warning_letters"]
    wl["matched_fei"] = wl["company_name"].map(
        lambda x: wl_matches.get(x, {}).get("fei")
    )
    return wl[wl["matched_fei"].notna()].copy()


def load_enforcement(entity_matches: dict) -> pd.DataFrame:
    """Load enforcement data with matched FEI numbers."""
    records = []
    for product in ["drug", "device"]:
        with open(DATA_RAW / f"{product}-enforcement-0001-of-0001.json") as f:
            data = json.load(f)
        for r in data["results"]:
            records.append({
                "recalling_firm": r.get("recalling_firm", ""),
                "classification": r.get("classification", ""),
                "recall_initiation_date": r.get("recall_initiation_date", ""),
                "voluntary_mandated": r.get("voluntary_mandated", ""),
            })
        del data

    enf = pd.DataFrame(records)
    enf["recall_date"] = pd.to_datetime(enf["recall_initiation_date"], format="%Y%m%d", errors="coerce")
    enf_matches = entity_matches["enforcement"]
    enf["matched_fei"] = enf["recalling_firm"].map(
        lambda x: enf_matches.get(x, {}).get("fei")
    )
    return enf[enf["matched_fei"].notna()].copy()


def load_483s() -> pd.DataFrame:
    """Load published 483s dataset."""
    df = pd.read_excel(DATA_RAW / "published_483s.xlsx")
    df["Record Date"] = pd.to_datetime(df["Record Date"], errors="coerce")
    df["FEI Number"] = pd.to_numeric(df["FEI Number"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["Record Date", "FEI Number"])
    return df


def build_history_features(inspections: pd.DataFrame, citations: pd.DataFrame,
                           warning_letters: pd.DataFrame, enforcement: pd.DataFrame,
                           published_483s: pd.DataFrame) -> pd.DataFrame:
    """
    For each inspection, build features from the facility's prior history.
    Only uses information available BEFORE the inspection date (no leakage).
    """
    # Pre-compute citation counts per inspection
    citation_counts = citations.groupby("Inspection ID").agg(
        n_citations=("Act/CFR Number", "count"),
        n_unique_cfr=("Act/CFR Number", "nunique"),
    ).reset_index()

    # Merge citation counts into inspections
    inspections = inspections.merge(citation_counts, on="Inspection ID", how="left")
    inspections["n_citations"] = inspections["n_citations"].fillna(0).astype(int)
    inspections["n_unique_cfr"] = inspections["n_unique_cfr"].fillna(0).astype(int)

    # Sort for rolling computation
    inspections = inspections.sort_values(["FEI Number", "Inspection End Date"]).reset_index(drop=True)

    features_list = []

    for fei, group in inspections.groupby("FEI Number"):
        group = group.sort_values("Inspection End Date").reset_index(drop=True)

        for i in range(len(group)):
            row = group.iloc[i]
            inspection_date = row["Inspection End Date"]

            # Prior inspections (strictly before this one)
            prior = group.iloc[:i]

            # Facility static features
            feat = {
                "inspection_id": row["Inspection ID"],
                "fei_number": fei,
                "inspection_date": inspection_date,
                "product_type": row["Product Type"],
                "country": row["Country/Area"],
                "project_area": row["Project Area"],
                "target_oai": row["is_oai"],
            }

            # Inspection history features
            feat["n_prior_inspections"] = len(prior)
            feat["n_prior_oai"] = prior["is_oai"].sum() if len(prior) > 0 else 0
            feat["n_prior_vai"] = prior["is_vai"].sum() if len(prior) > 0 else 0
            feat["n_prior_nai"] = prior["is_nai"].sum() if len(prior) > 0 else 0
            feat["pct_oai"] = feat["n_prior_oai"] / max(feat["n_prior_inspections"], 1)
            feat["pct_vai"] = feat["n_prior_vai"] / max(feat["n_prior_inspections"], 1)

            # Recency
            if len(prior) > 0:
                last_date = prior["Inspection End Date"].iloc[-1]
                feat["days_since_last_inspection"] = (inspection_date - last_date).days
                feat["last_classification_oai"] = int(prior["is_oai"].iloc[-1])
                feat["last_classification_vai"] = int(prior["is_vai"].iloc[-1])
            else:
                feat["days_since_last_inspection"] = -1
                feat["last_classification_oai"] = 0
                feat["last_classification_vai"] = 0

            # Trend: compare last 2 inspections classification
            if len(prior) >= 2:
                recent_2 = prior.iloc[-2:]
                feat["trend_worsening"] = int(recent_2["is_oai"].iloc[-1] > recent_2["is_oai"].iloc[-2])
                feat["recent_oai_rate"] = recent_2["is_oai"].mean()
            else:
                feat["trend_worsening"] = 0
                feat["recent_oai_rate"] = 0.0

            # Citation features (from prior inspections)
            if len(prior) > 0:
                feat["total_prior_citations"] = prior["n_citations"].sum()
                feat["avg_citations_per_inspection"] = prior["n_citations"].mean()
                feat["max_citations_single_inspection"] = prior["n_citations"].max()
                feat["total_unique_cfr_violated"] = prior["n_unique_cfr"].sum()
            else:
                feat["total_prior_citations"] = 0
                feat["avg_citations_per_inspection"] = 0.0
                feat["max_citations_single_inspection"] = 0
                feat["total_unique_cfr_violated"] = 0

            # Warning letter features (before this inspection)
            wl_prior = warning_letters[
                (warning_letters["matched_fei"] == fei) &
                (warning_letters["issue_date"] < inspection_date)
            ]
            feat["n_warning_letters"] = len(wl_prior)
            feat["has_warning_letter"] = int(len(wl_prior) > 0)
            if len(wl_prior) > 0:
                feat["days_since_last_wl"] = (inspection_date - wl_prior["issue_date"].max()).days
            else:
                feat["days_since_last_wl"] = -1

            # Enforcement features (before this inspection)
            enf_prior = enforcement[
                (enforcement["matched_fei"] == fei) &
                (enforcement["recall_date"] < inspection_date)
            ]
            feat["n_recalls"] = len(enf_prior)
            feat["has_recall"] = int(len(enf_prior) > 0)
            feat["n_class_I_recalls"] = int((enf_prior["classification"] == "Class I").sum())
            feat["n_class_II_recalls"] = int((enf_prior["classification"] == "Class II").sum())

            # 483 features
            f483_prior = published_483s[
                (published_483s["FEI Number"] == fei) &
                (published_483s["Record Date"] < inspection_date)
            ]
            feat["n_published_483s"] = len(f483_prior)
            feat["has_published_483"] = int(len(f483_prior) > 0)

            features_list.append(feat)

    return pd.DataFrame(features_list)


def main():
    print("Loading data...")
    inspections = load_inspections()
    citations = load_citations()
    entity_matches = load_entity_matches()
    warning_letters = load_warning_letters(entity_matches)
    enforcement = load_enforcement(entity_matches)
    published_483s = load_483s()

    print(f"  Inspections (in scope): {len(inspections):,}")
    print(f"  Citations: {len(citations):,}")
    print(f"  Warning letters (matched): {len(warning_letters):,}")
    print(f"  Enforcement (matched): {len(enforcement):,}")
    print(f"  Published 483s: {len(published_483s):,}")

    print("\nBuilding features (this may take a while)...")
    features = build_history_features(
        inspections, citations, warning_letters, enforcement, published_483s
    )

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = DATA_PROCESSED / "features.parquet"
    features.to_parquet(output_path, index=False)
    print(f"\nSaved {len(features):,} rows to {output_path}")
    print(f"  Target distribution: {features['target_oai'].value_counts().to_dict()}")
    print(f"  OAI rate: {features['target_oai'].mean():.4f}")

    # Train/test split info
    features["year"] = features["inspection_date"].dt.year
    train = features[features["year"] < 2025]
    test = features[features["year"] >= 2025]
    print(f"\n  Train (< 2025): {len(train):,} rows, OAI rate: {train['target_oai'].mean():.4f}")
    print(f"  Test (>= 2025): {len(test):,} rows, OAI rate: {test['target_oai'].mean():.4f}")


if __name__ == "__main__":
    main()
