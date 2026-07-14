"""
Supplier Risk Assessment — Streamlit App

Interactive interface to query risk scores for FDA-regulated facilities.
Uses the parquet dataset with a correction for inference:
the last known inspection is included in the history (not predicted).
"""

import joblib
import numpy as np
import pandas as pd
import shap
import streamlit as st
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"


@st.cache_resource
def load_model():
    model = joblib.load(MODELS_DIR / "champion.joblib")
    meta = joblib.load(MODELS_DIR / "champion_meta.joblib")
    return model, meta


@st.cache_data
def load_features():
    return pd.read_parquet(DATA_DIR / "features.parquet")


@st.cache_resource
def get_explainer(_model):
    return shap.TreeExplainer(_model)


def build_inference_row(facility_data: pd.DataFrame) -> dict:
    """
    Build corrected features for inference.
    Takes the last row of a facility and adjusts it to include
    that inspection in the history (predicting the NEXT one).
    """
    last = facility_data.iloc[0]  # most recent (sorted desc)
    feat = last.to_dict()

    # Include the last inspection in the history
    feat["n_prior_inspections"] += 1

    if last["target_oai"] == 1:
        feat["n_prior_oai"] += 1
    else:
        feat["n_prior_nai"] += 1  # assume NAI if not OAI

    # Recalculate percentages
    n = feat["n_prior_inspections"]
    feat["pct_oai"] = feat["n_prior_oai"] / n
    feat["pct_vai"] = feat["n_prior_vai"] / n

    # Update recency: days from the last inspection date to today
    last_date = pd.Timestamp(last["inspection_date"])
    feat["days_since_last_inspection"] = (pd.Timestamp.now() - last_date).days

    # Last classification is now THIS inspection's outcome
    feat["last_classification_oai"] = int(last["target_oai"] == 1)
    feat["last_classification_vai"] = 0  # we assumed NAI if not OAI

    # Trend: compare this inspection vs the previous
    if len(facility_data) >= 2:
        prev = facility_data.iloc[1]
        feat["trend_worsening"] = int(last["target_oai"] > prev["target_oai"])
        feat["recent_oai_rate"] = (last["target_oai"] + prev["target_oai"]) / 2
    else:
        feat["trend_worsening"] = 0
        feat["recent_oai_rate"] = float(last["target_oai"])

    return feat


def risk_tier(score: float) -> tuple[str, str]:
    if score >= 0.6:
        return "CRITICAL", "🔴"
    elif score >= 0.3:
        return "HIGH", "🟠"
    elif score >= 0.1:
        return "MEDIUM", "🟡"
    else:
        return "LOW", "🟢"


def main():
    st.set_page_config(page_title="Supplier Risk Assessment", page_icon="🏭", layout="wide")

    st.title("🏭 Supplier Risk Assessment")
    st.caption("by Santiago Dominguez")
    st.markdown("Predict the likelihood of FDA non-compliance (OAI) on the **next** inspection.")

    model, meta = load_model()
    df = load_features()
    label_encoders = meta["label_encoders"]
    features = meta["features"]

    # Encode categoricals
    for col, le in label_encoders.items():
        df[col + "_encoded"] = le.transform(df[col].astype(str))

    # Sidebar
    st.sidebar.header("Query")
    fei_input = st.sidebar.text_input("Enter FEI Number:", placeholder="e.g. 3007058211")

    if not fei_input:
        st.info("Enter a FEI Number in the sidebar to get a risk assessment.")
        st.markdown("**Example FEI Numbers** (high risk):")
        for fei in [3005350897, 3010892830, 2242352, 1950222, 3007058211]:
            st.code(str(fei))
        return

    try:
        fei = int(fei_input)
    except ValueError:
        st.error("Please enter a valid numeric FEI Number.")
        return

    facility_data = df[df["fei_number"] == fei].sort_values("inspection_date", ascending=False)
    if facility_data.empty:
        st.error(f"FEI {fei} not found in our database.")
        return

    # Build corrected inference features
    feat = build_inference_row(facility_data)

    # Predict
    X = np.array([[feat.get(f, 0) for f in features]])
    risk_score = model.predict_proba(X)[0, 1]
    tier, emoji = risk_tier(risk_score)

    explainer = get_explainer(model)
    shap_values = explainer.shap_values(X)[0]

    # Display results
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risk Score", f"{risk_score:.1%}")
    with col2:
        st.metric("Risk Tier", f"{emoji} {tier}")
    with col3:
        st.metric("Last Inspection", pd.Timestamp(feat["inspection_date"]).strftime("%Y-%m-%d"))

    st.divider()

    # Facility info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Facility Profile")
        st.markdown(f"""
        - **FEI Number:** {fei}
        - **Product Type:** {feat['product_type']}
        - **Country:** {feat['country']}
        - **Project Area:** {feat['project_area']}
        - **Total Inspections:** {feat['n_prior_inspections']}
        """)

    with col2:
        st.subheader("Full History (including latest)")
        st.markdown(f"""
        - **OAI inspections:** {feat['n_prior_oai']}
        - **VAI inspections:** {feat['n_prior_vai']}
        - **NAI inspections:** {feat['n_prior_nai']}
        - **Warning Letters:** {int(feat['n_warning_letters'])}
        - **Recalls:** {int(feat['n_recalls'])}
        - **Published 483s:** {int(feat['n_published_483s'])}
        - **Days since last inspection:** {feat['days_since_last_inspection']}
        """)

    st.divider()

    # Risk drivers (SHAP)
    st.subheader("Risk Drivers")
    st.markdown("Why the model assigned this risk score:")

    shap_df = pd.DataFrame({
        "Feature": features,
        "SHAP Value": shap_values,
        "Feature Value": [feat.get(f, 0) for f in features],
    }).sort_values("SHAP Value", key=abs, ascending=False)

    for _, row in shap_df.head(8).iterrows():
        direction = "↑" if row["SHAP Value"] > 0 else "↓"
        st.markdown(
            f"- {direction} **{row['Feature']}** = {row['Feature Value']:.0f} "
            f"(impact: {row['SHAP Value']:+.3f})"
        )

    st.divider()

    # Inspection history
    st.subheader("Inspection History")
    history = facility_data[["inspection_date", "target_oai", "product_type", "project_area"]].copy()
    history["Classification"] = history["target_oai"].map({1: "OAI ⚠️", 0: "NAI/VAI"})
    history = history.drop(columns=["target_oai"])
    st.dataframe(history, use_container_width=True)


if __name__ == "__main__":
    main()
