import streamlit as st
import pandas as pd
import time
import requests
from openai import OpenAI

# --- STREAMLIT SETUP ---
st.set_page_config(page_title="Sustainability Vendor Classifier", layout="wide")
st.title("🔍 Sustainability Vendor Classifier")

# --- LOAD SECRETS ---
openai_api_key = st.secrets["OPENAI_API_KEY"].strip()
serp_api_key = st.secrets["SERPAPI_KEY"].strip()
client = OpenAI(api_key=openai_api_key)

# --- DEBUG DISPLAY ---
st.markdown("### 🔧 DEBUG: API Keys")
st.markdown(f"🧪 OpenAI Key loaded: {'✅ Yes' if openai_api_key else '❌ No'}")
st.markdown(f"🔍 SerpAPI Key loaded: {'✅ Yes' if serp_api_key else '❌ No'}")

# --- CATEGORY SELECTION ---
category_prompt = st.selectbox(
    "What type of service are you classifying for?",
    options=[
        "solar",
        "green infrastructure",
        "HVAC",
        "lighting",
        "other"
    ]
)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📄 Upload your vendor CSV file", type=["csv"])

if uploaded_file:
    try:
        # --- LOAD CSV ---
        df = pd.read_csv(uploaded_file, encoding="utf-8")
        df.columns = df.columns.str.strip()

        if not {"Company", "Location"}.issubset(df.columns):
            st.error("CSV must contain 'Company' and 'Location' columns.")
        else:
            # --- SEARCH TERMS INPUT ---
            search_terms = st.text_input(
                "🔎 Enter keywords to filter vendors (OR logic)",
                placeholder="e.g. solar, DC, Maryland"
            )

            def filter_by_keywords(df, search_terms):
                if not search_terms:
                    return df
                terms = [term.strip().lower() for term in search_terms.split(",")]
                return df[df.apply(lambda row: any(
                    term in str(row["Location"]).lower() or term in str(row["Company"]).lower()
                    for term in terms), axis=1)]

            filtered_df = filter_by_keywords(df, search_terms)

            # --- DISPLAY FULL + FILTERED PREVIEWS ---
            st.markdown("### 🗂️ Full Vendor Dataset Preview")
            st.dataframe(df.head())

            if search_terms:
                st.markdown(f"### 🔍 Filtered Vendors Matching: `{search_terms}`")
                if not filtered_df.empty:
                    st.dataframe(filtered_df.head())
                else:
                    st.warning("⚠️ No vendors matched your search terms.")
            else:
                st.info("👆 Enter keywords above to filter vendors before classification.")

            # --- SERPAPI LOOKUP FUNCTION ---
            def get_serp_snippet(company, location, search_terms, serp_api_key):
                query = f"{company} {location} {search_terms}"
                params = {
                    "engine": "google",
                    "q": query,
                    "api_key": serp_api_key,
                    "num": 1
                }
                try:
                    response = requests.get("https://serpapi.com/search", params=params)
                    data = response.json()
                    snippet = data.get("organic_results", [{}])[0].get("snippet", "No snippet found")
                    return snippet
                except Exception as e:
                    return f"Error retrieving snippet: {e}"

            # --- CACHED CLASSIFICATION FUNCTION ---
            @st.cache_data(show_spinner=False)
            def get_cached_classification(company, snippet, category, model_choice):
                prompt = f"""
You are helping classify vendors for a project.

Given the following company information, classify whether the company appears aligned with **{category}** services.

Company: {company}
Google Snippet: {snippet}

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

            # --- MODEL CHOICE ---
            model_choice = st.selectbox("Choose OpenAI model", options=["gpt-4", "gpt-3.5-turbo"], index=0)

            # --- CLASSIFICATION ---
            if not filtered_df.empty:
                st.markdown("### 🏗️ Classifying vendors…")
                with st.spinner("Classifying… This may take a few minutes depending on file size."):
                    classifications = []
                    for _, row in filtered_df.iterrows():
                        company = str(row["Company"])
                        location = str(row["Location"])
                        query_terms = search_terms if search_terms else ""
                        snippet = get_serp_snippet(company, location, query_terms, serp_api_key)
                        result = get_cached_classification(company, snippet, category_prompt, model_choice)
                        classifications.append(result)
                        time.sleep(1.5)  # avoid rate limits

                    filtered_df["Classification"] = classifications

                # --- DISPLAY RESULTS ---
                st.markdown("### ✅ Classification Results")
                st.dataframe(filtered_df)

                # --- DOWNLOAD BUTTON ---
                csv = filtered_df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Results CSV", data=csv, file_name="classified_vendors.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
