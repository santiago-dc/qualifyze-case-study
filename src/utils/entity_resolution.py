"""
Entity resolution: match company names across FDA datasets.

Strategy:
1. Normalize names (lowercase, strip suffixes, remove punctuation)
2. Use TF-IDF cosine similarity for fuzzy matching
3. Optionally use location (city, state, country) as a tiebreaker
"""

import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SUFFIXES = [
    r"\bllc\b", r"\binc\b", r"\bcorp\b", r"\bcorporation\b",
    r"\bltd\b", r"\blimited\b", r"\bco\b", r"\bcompany\b",
    r"\bplc\b", r"\bgmbh\b", r"\bag\b", r"\bsa\b",
    r"\bd/?b/?a\b.*$",  # "doing business as" and everything after
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


def match_names_tfidf(
    source_names: list[str],
    target_names: list[str],
    threshold: float = 0.6,
) -> dict[int, tuple[int, float]]:
    """
    Match source names to target names using TF-IDF cosine similarity.

    Returns: dict mapping source_index -> (target_index, similarity_score)
    Only includes matches above the threshold.
    """
    source_normalized = [normalize_name(n) for n in source_names]
    target_normalized = [normalize_name(n) for n in target_names]

    all_names = target_normalized + source_normalized
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    tfidf_matrix = vectorizer.fit_transform(all_names)

    target_matrix = tfidf_matrix[: len(target_normalized)]
    source_matrix = tfidf_matrix[len(target_normalized) :]

    matches = {}
    batch_size = 500
    for i in range(0, source_matrix.shape[0], batch_size):
        batch = source_matrix[i : i + batch_size]
        sim = cosine_similarity(batch, target_matrix)
        for j in range(sim.shape[0]):
            best_idx = sim[j].argmax()
            best_score = sim[j, best_idx]
            if best_score >= threshold:
                matches[i + j] = (best_idx, float(best_score))

    return matches


def match_warning_letters_to_facilities(
    warning_letters: pd.DataFrame,
    facilities: pd.DataFrame,
    threshold: float = 0.6,
) -> pd.DataFrame:
    """
    Match warning letter company names to facility FEI numbers.

    Args:
        warning_letters: DataFrame with 'company_name' column
        facilities: DataFrame with 'FEI Number' and 'Legal Name' columns
        threshold: minimum similarity score

    Returns:
        warning_letters DataFrame with added 'matched_fei' and 'match_score' columns
    """
    wl_names = warning_letters["company_name"].tolist()
    fac_names = facilities["Legal Name"].tolist()

    print(f"Matching {len(wl_names)} warning letter names to {len(fac_names)} facilities...")
    matches = match_names_tfidf(wl_names, fac_names, threshold=threshold)
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

    Args:
        enforcement: DataFrame with 'recalling_firm' column
        facilities: DataFrame with 'FEI Number' and 'Legal Name' columns
        threshold: minimum similarity score

    Returns:
        enforcement DataFrame with added 'matched_fei' and 'match_score' columns
    """
    # Deduplicate enforcement firms first for efficiency
    unique_firms = enforcement["recalling_firm"].unique().tolist()
    fac_names = facilities["Legal Name"].tolist()

    print(f"Matching {len(unique_firms)} unique enforcement firms to {len(fac_names)} facilities...")
    matches = match_names_tfidf(unique_firms, fac_names, threshold=threshold)
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
