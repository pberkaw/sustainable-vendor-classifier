import streamlit as st
import pandas as pd
import time
import os
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

# --- STREAMLIT SETUP ---
st.set_page_config(page_title="Sustainability Vendor Classifier", layout="wide")
st.title("🔍 Sustainability Vendor Classifier")

# --- LOAD ENV VARIABLES ---
load_dotenv(dotenv_path=Path(".env"))
openai_api_key = os.getenv("OPENAI_API_KEY")
serp_api_key = os.getenv("SERPAPI_KEY")
client = OpenAI(api_key=openai_api_key)

# --- DEBUG DISPLAY ---
st.markdown("### 🔧 DEBUG: API Keys")
st.markdown(f"🧪 OpenAI Key loaded: {'✅ Yes' if openai_api_key else '❌ No'}")
st.markdown(f"🔍 SerpAPI Key loaded: {'✅ Yes' if serp_api_key else '❌ No'}")

# --- CATEGORY SELECTION ---
category_prompt = st.selectbox(
    "What sustainability-aligned service are you looking for?",
    options=[
        "solar",
        "green infrastructure",
        "HVAC",
        "lighting",
        "other"
    ]
)

model_choice = st.selectbox("Choose OpenAI model", options=["gpt-4", "gpt-3.5-turbo"], index=0)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📄 Upload your vendor CSV file", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
        df.columns = df.columns.str.strip()

        if not {"Name", "Description"}.issubset(df.columns):
            st.error("CSV must contain 'Name' and 'Description' columns.")
        else:
            # --- SEARCH TERM INPUT (OR logic) ---
            search_terms = st.text_input("🔎 Filter vendors by keyword(s)", placeholder="e.g. solar, dc, lighting")

            def filter_by_keywords(df, search_terms):
                if not search_terms:
                    return df
                terms = [term.strip().lower() for term in search_terms.split(",")]
                return df[df.apply(lambda row: any(
                    term in str(row["Description"]).lower() or term in str(row["Name"]).lower()
                    for term in terms), axis=1)]

            filtered_df = filter_by_keywords(df, search_terms)

            st.markdown("### 🗂️ Filtered Vendor Preview")
            st.dataframe(filtered_df.head())

            # --- CACHED CLASSIFICATION FUNCTION ---
            @st.cache_data(show_spinner=False)
            def get_cached_classification(name, description, category, model_choice):
                prompt = f"""
Given the following business snippet, classify whether the company appears aligned with {category} services.

Company: {name}
Snippet: {description}

Respond with one of:
- ✅ Likely Aligned
- ❓ Possibly Related
- ❌ Not Aligned
"""
                try:
                    response = client.chat.completions.create(
                        model=model_choice,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    return f"❌ Error: {e}"

            # --- APPLY CLASSIFICATION ---
            if not filtered_df.empty:
                st.markdown("### 🏗️ Classifying vendors…")
                with st.spinner("Classifying… This may take a few minutes depending on the file size."):
                    classifications = []
                    for _, row in filtered_df.iterrows():
                        name = str(row["Name"])
                        description = str(row["Description"])
                        result = get_cached_classification(name, description, category_prompt, model_choice)
                        classifications.append(result)
                        time.sleep(1.5)  # Prevent rate limits

                    filtered_df["Classification"] = classifications

                # --- DISPLAY RESULTS ---
                st.markdown("### ✅ Classification Results")
                st.dataframe(filtered_df)

                # --- DOWNLOAD ---
                csv = filtered_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Results CSV", data=csv, file_name="classified_vendors.csv", mime="text/csv")
            else:
                st.warning("⚠️ No vendors matched your search terms.")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

