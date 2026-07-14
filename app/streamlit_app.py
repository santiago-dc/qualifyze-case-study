"""
Supplier Risk Assessment — Streamlit App

Interactive interface to query risk scores for FDA-regulated facilities.
"""

import joblib
import pandas as pd
import numpy as np
import shap
import streamlit as st
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data" / "processed"


@st.cache_resource
def load_model():
    """Load the champion model and metadata."""
    model = joblib.load(MODELS_DIR / "champion.joblib")
    meta = joblib.load(MODELS_DIR / "champion_meta.joblib")
    return model, meta


@st.cache_data
def load_features():
    """Load the feature dataset."""
    df = pd.read_parquet(DATA_DIR / "features.parquet")
    return df


@st.cache_resource
def get_explainer(_model):
    """Create SHAP explainer."""
    return shap.TreeExplainer(_model)


def get_facility_info(df: pd.DataFrame, fei: int) -> pd.DataFrame:
    """Get all inspections for a facility."""
    return df[df["fei_number"] == fei].sort_values("inspection_date", ascending=False)


def predict_risk(model, meta, facility_row: pd.Series) -> tuple[float, np.ndarray]:
    """Generate risk prediction and SHAP values for a facility."""
    features = meta["features"]
    X = facility_row[features].values.reshape(1, -1)
    risk_score = model.predict_proba(X)[0, 1]

    explainer = get_explainer(model)
    shap_values = explainer.shap_values(X)[0]

    return risk_score, shap_values


def risk_tier(score: float) -> tuple[str, str]:
    """Map risk score to tier and color."""
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
    st.markdown("Predict the likelihood of FDA non-compliance (OAI) for a facility based on its historical data.")

    model, meta = load_model()
    df = load_features()

    # Encode categoricals (same as training)
    label_encoders = meta["label_encoders"]
    for col, le in label_encoders.items():
        df[col + "_encoded"] = le.transform(df[col].astype(str))

    # Sidebar
    st.sidebar.header("Query")
    all_feis = sorted(df["fei_number"].unique())

    fei_input = st.sidebar.text_input("Enter FEI Number:", placeholder="e.g. 3007058211")
    if not fei_input:
        st.info("Enter a FEI Number in the sidebar to get a risk assessment. "
                "Try one of the examples below.")
        st.markdown("**Example FEI Numbers** (high risk):")
        examples = df[df["target_oai"] == 1]["fei_number"].value_counts().head(10).index.tolist()
        for fei in examples[:5]:
            name = df[df["fei_number"] == fei].iloc[0].get("product_type", "")
            st.code(f"{fei}")
        return

    try:
        fei = int(fei_input)
    except ValueError:
        st.error("Please enter a valid numeric FEI Number.")
        return

    facility_data = get_facility_info(df, fei)
    if facility_data.empty:
        st.error(f"FEI {fei} not found in our database.")
        return

    # Use most recent inspection as the facility's current state
    latest = facility_data.iloc[0]

    # Predict
    risk_score, shap_values = predict_risk(model, meta, latest)
    tier, emoji = risk_tier(risk_score)

    # Display results
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risk Score", f"{risk_score:.1%}")
    with col2:
        st.metric("Risk Tier", f"{emoji} {tier}")
    with col3:
        st.metric("Last Inspection", latest["inspection_date"].strftime("%Y-%m-%d"))

    st.divider()

    # Facility info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Facility Profile")
        st.markdown(f"""
        - **FEI Number:** {fei}
        - **Product Type:** {latest['product_type']}
        - **Country:** {latest['country']}
        - **Project Area:** {latest['project_area']}
        - **Total Inspections:** {len(facility_data)}
        """)

    with col2:
        st.subheader("Historical Summary")
        n_oai = int(latest.get("n_prior_oai", 0))
        n_vai = int(latest.get("n_prior_vai", 0))
        n_nai = int(latest.get("n_prior_nai", 0))
        st.markdown(f"""
        - **Prior OAI inspections:** {n_oai}
        - **Prior VAI inspections:** {n_vai}
        - **Prior NAI inspections:** {n_nai}
        - **Warning Letters:** {int(latest.get('n_warning_letters', 0))}
        - **Recalls:** {int(latest.get('n_recalls', 0))}
        - **Published 483s:** {int(latest.get('n_published_483s', 0))}
        """)

    st.divider()

    # Risk drivers (SHAP)
    st.subheader("Risk Drivers")
    st.markdown("Features that contribute most to this facility's risk score:")

    features = meta["features"]
    shap_df = pd.DataFrame({
        "Feature": features,
        "SHAP Value": shap_values,
        "Feature Value": [latest[f] for f in features],
    }).sort_values("SHAP Value", key=abs, ascending=False)

    # Top drivers
    top_drivers = shap_df.head(8)
    for _, row in top_drivers.iterrows():
        direction = "↑" if row["SHAP Value"] > 0 else "↓"
        color = "red" if row["SHAP Value"] > 0 else "green"
        st.markdown(
            f"- {direction} **{row['Feature']}** = {row['Feature Value']:.0f} "
            f"(impact: {row['SHAP Value']:+.3f})"
        )

    st.divider()

    # Inspection history table
    st.subheader("Inspection History")
    history_cols = ["inspection_date", "target_oai", "product_type", "project_area"]
    display_df = facility_data[
        [c for c in history_cols if c in facility_data.columns]
    ].copy()
    display_df["Classification"] = display_df["target_oai"].map({1: "OAI ⚠️", 0: "NAI/VAI"})
    display_df = display_df.drop(columns=["target_oai"])
    st.dataframe(display_df, use_container_width=True)


if __name__ == "__main__":
    main()
