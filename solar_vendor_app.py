import streamlit as st
import pandas as pd
import openai
import requests
import time
import os
from dotenv import load_dotenv
from pathlib import Path

# --- SETUP ---
st.set_page_config(page_title="Sustainability Vendor Classifier", layout="wide")
st.title("🔍 Sustainability Vendor Classifier")

# --- LOAD ENV VARIABLES ---
load_dotenv(dotenv_path=Path(".env"))
openai_api_key = os.getenv("OPENAI_API_KEY")
serp_api_key = os.getenv("SERPAPI_KEY")

# Debug display
st.markdown("### 🔧 DEBUG: ENV Keys")
st.markdown(f"🧪 OpenAI Key loaded: {'✅ Yes' if openai_api_key else '❌ No'}")
st.markdown(f"🔍 SerpAPI Key loaded: {'✅ Yes' if serp_api_key else '❌ No'}")

# --- API Key Fallback UI ---
if not openai_api_key:
    openai_api_key = st.text_input("Enter your OpenAI API Key", type="password")
if not serp_api_key:
    serp_api_key = st.text_input("Enter your SerpAPI Key", type="password")

# --- Upload Company CSV ---
uploaded_file = st.file_uploader("Upload a CSV file of companies", type=["csv"])

# --- Use Case and Search Terms Input ---
category_prompt = st.text_input("What type of service are you trying to classify? (e.g., solar, stormwater, energy retrofit)", "solar")
default_terms = "solar, photovoltaic, battery, inverter, electrification, clean energy"
search_terms_input = st.text_input("Search terms to filter companies (comma-separated):", default_terms)
search_terms = [term.strip() for term in search_terms_input.split(",") if term.strip()]

# --- Model Selection ---
model_choice = st.selectbox("Choose GPT model", ["gpt-4", "gpt-3.5-turbo"])

# --- Main Functions ---
def search_snippet(company, location, search_terms):
    query = f"{company} {location} (" + " OR ".join(search_terms) + ")"
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": serp_api_key,
        "engine": "google",
        "num": 1
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "organic_results" in data and len(data["organic_results"]) > 0:
        return data["organic_results"][0].get("snippet", "No snippet found.")
    return "No results."

def classify_snippet(snippet, company):
    prompt = f"""
Given the following business snippet, classify whether the company appears aligned with {category_prompt} services.

Company: {company}
Snippet: {snippet}

Respond with:
- ✅ Likely Aligned
- ❓ Possibly Related
- ❌ Not Aligned
"""
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message["content"].strip()

# --- Run App ---
if uploaded_file and openai_api_key and serp_api_key:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="cp1252")

    if "Company" not in df.columns or "Location" not in df.columns:
        st.error("CSV must have 'Company' and 'Location' columns")
    else:
        results = []
        progress = st.progress(0)
        total = len(df)
        with st.spinner("Running classification..."):
            for index, row in df.iterrows():
                company = row["Company"]
                location = row["Location"]
                snippet = search_snippet(company, location, search_terms)
                time.sleep(1)
                classification = classify_snippet(snippet, company)
                results.append({
                    "Company": company,
                    "Location": location,
                    "Snippet": snippet,
                    "Classification": classification
                })
                progress.progress((index + 1) / total)

        result_df = pd.DataFrame(results)
        st.success("✅ Classification complete!")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Results as CSV",
            data=csv,
            file_name="classified_vendors.csv",
            mime="text/csv"
        )


