"""
Entity resolution: match company names across FDA datasets.

Strategy:
1. Normalize names (lowercase, strip suffixes, remove punctuation)
2. Use TF-IDF cosine similarity for fuzzy matching
3. Use location (city, state, country) as confirmation for borderline matches
4. Segment by product type / issuing office for higher precision
"""

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SUFFIXES = [
    r"\bllc\b", r"\binc\b", r"\bcorp\b", r"\bcorporation\b",
    r"\bltd\b", r"\blimited\b", r"\bco\b", r"\bcompany\b",
    r"\bplc\b", r"\bgmbh\b", r"\bag\b", r"\bsa\b",
    r"\bd/?b/?a\b.*$",
    r"\bwww\.[a-z0-9.-]+\.(com|org|net|us)\b",
]


def normalize_name(name: str) -> str:
    """Normalize a company name for matching."""
    if not name or not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[.,;:!?'\"()\[\]{}/\\]", " ", name)
    for suffix in SUFFIXES:
        name = re.sub(suffix, "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_location(city: str = "", state: str = "", country: str = "") -> str:
    """Normalize location fields for comparison."""
    parts = []
    for p in [city, state, country]:
        if p and isinstance(p, str) and p.strip() not in ("", "N/A", "-"):
            parts.append(p.lower().strip())
    return "|".join(parts)


def match_names_tfidf(
    source_names: list[str],
    target_names: list[str],
    threshold: float = 0.6,
    source_locations: list[str] | None = None,
    target_locations: list[str] | None = None,
    location_bonus: float = 0.15,
) -> dict[int, tuple[int, float]]:
    """
    Match source names to target names using TF-IDF cosine similarity.
    If locations are provided, matches between 0.6-0.8 get confirmed/rejected
    based on location overlap.

    Returns: dict mapping source_index -> (target_index, similarity_score)
    """
    source_normalized = [normalize_name(n) for n in source_names]
    target_normalized = [normalize_name(n) for n in target_names]

    all_names = target_normalized + source_normalized
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    tfidf_matrix = vectorizer.fit_transform(all_names)

    target_matrix = tfidf_matrix[: len(target_normalized)]
    source_matrix = tfidf_matrix[len(target_normalized) :]

    use_location = (source_locations is not None and target_locations is not None)

    matches = {}
    batch_size = 500
    for i in range(0, source_matrix.shape[0], batch_size):
        batch = source_matrix[i : i + batch_size]
        sim = cosine_similarity(batch, target_matrix)
        for j in range(sim.shape[0]):
            src_idx = i + j
            best_idx = sim[j].argmax()
            best_score = sim[j, best_idx]

            # High confidence: accept directly
            if best_score >= 0.8:
                matches[src_idx] = (best_idx, float(best_score))
            # Borderline: use location to confirm
            elif best_score >= threshold and use_location:
                src_loc = source_locations[src_idx]
                tgt_loc = target_locations[best_idx]
                if _locations_overlap(src_loc, tgt_loc):
                    matches[src_idx] = (best_idx, float(best_score + location_bonus))
            elif best_score >= threshold and not use_location:
                matches[src_idx] = (best_idx, float(best_score))

    return matches


def _locations_overlap(loc_a: str, loc_b: str) -> bool:
    """Check if two normalized location strings share any component."""
    if not loc_a or not loc_b:
        return False
    parts_a = set(loc_a.split("|"))
    parts_b = set(loc_b.split("|"))
    return len(parts_a & parts_b) > 0


def match_warning_letters_to_facilities(
    warning_letters: pd.DataFrame,
    facilities: pd.DataFrame,
    threshold: float = 0.6,
) -> pd.DataFrame:
    """
    Match warning letter company names to facility FEI numbers.
    Uses issuing office to segment matching for better precision.
    """
    wl_names = warning_letters["company_name"].tolist()
    fac_names = facilities["Legal Name"].tolist()

    # Build location strings for facilities
    fac_locations = [
        normalize_location(
            str(row.get("City", "")),
            str(row.get("State", "")),
            str(row.get("Country/Area", ""))
        )
        for _, row in facilities.iterrows()
    ]

    # Warning letters don't have structured location, pass None
    print(f"Matching {len(wl_names)} warning letter names to {len(fac_names)} facilities...")
    matches = match_names_tfidf(
        wl_names, fac_names,
        threshold=threshold,
        target_locations=fac_locations,
    )
    print(f"Found {len(matches)} matches above threshold {threshold}")

    fei_numbers = facilities["FEI Number"].tolist()
    warning_letters = warning_letters.copy()
    warning_letters["matched_fei"] = None
    warning_letters["match_score"] = 0.0

    for src_idx, (tgt_idx, score) in matches.items():
        warning_letters.iloc[src_idx, warning_letters.columns.get_loc("matched_fei")] = fei_numbers[tgt_idx]
        warning_letters.iloc[src_idx, warning_letters.columns.get_loc("match_score")] = score

    return warning_letters


def match_enforcement_to_facilities(
    enforcement: pd.DataFrame,
    facilities: pd.DataFrame,
    threshold: float = 0.6,
) -> pd.DataFrame:
    """
    Match enforcement recalling_firm names to facility FEI numbers.
    Uses city/state/country for location confirmation on borderline matches.
    """
    # Deduplicate enforcement firms with their location
    firm_info = enforcement.drop_duplicates("recalling_firm")[
        ["recalling_firm", "city", "state", "country"]
    ].reset_index(drop=True)

    unique_firms = firm_info["recalling_firm"].tolist()
    firm_locations = [
        normalize_location(
            str(row["city"]), str(row["state"]), str(row["country"])
        )
        for _, row in firm_info.iterrows()
    ]

    fac_names = facilities["Legal Name"].tolist()
    fac_locations = [
        normalize_location(
            str(row.get("City", "")),
            str(row.get("State", "")),
            str(row.get("Country/Area", ""))
        )
        for _, row in facilities.iterrows()
    ]

    print(f"Matching {len(unique_firms)} unique enforcement firms to {len(fac_names)} facilities...")
    matches = match_names_tfidf(
        unique_firms, fac_names,
        threshold=threshold,
        source_locations=firm_locations,
        target_locations=fac_locations,
        location_bonus=0.15,
    )
    print(f"Found {len(matches)} matches above threshold {threshold}")

    fei_numbers = facilities["FEI Number"].tolist()
    firm_to_fei = {}
    firm_to_score = {}
    for src_idx, (tgt_idx, score) in matches.items():
        firm_to_fei[unique_firms[src_idx]] = fei_numbers[tgt_idx]
        firm_to_score[unique_firms[src_idx]] = score

    enforcement = enforcement.copy()
    enforcement["matched_fei"] = enforcement["recalling_firm"].map(firm_to_fei)
    enforcement["match_score"] = enforcement["recalling_firm"].map(firm_to_score).fillna(0.0)

    return enforcement


if __name__ == "__main__":
    # Quick test
    test_source = ["Pfizer Inc.", "Johnson & Johnson LLC", "Novartis AG"]
    test_target = ["Pfizer, Inc", "Johnson and Johnson", "Novartis Pharmaceuticals"]
    matches = match_names_tfidf(test_source, test_target, threshold=0.4)
    for src_idx, (tgt_idx, score) in matches.items():
        print(f"  '{test_source[src_idx]}' -> '{test_target[tgt_idx]}' (score: {score:.3f})")
