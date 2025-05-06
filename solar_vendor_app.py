import streamlit as st
import pandas as pd
import requests
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

# --- MODEL CHOICE (optional) ---
model_choice = st.selectbox("Choose OpenAI model", options=["gpt-4", "gpt-3.5-turbo"], index=0)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📄 Upload your vendor CSV file", type=["csv"])

if uploaded_file:
    try:
        # --- READ FILE ---
        df = pd.read_csv(uploaded_file, encoding="utf-8")
        df.columns = df.columns.str.strip()  # Clean column names

        # --- DISPLAY PREVIEW ---
        st.markdown("### 🗂️ Preview of Uploaded Data")
        st.dataframe(df.head())

        # --- REQUIRED COLUMNS ---
        if not {"Name", "Description"}.issubset(df.columns):
            st.error("CSV must contain 'Name' and 'Description' columns.")
        else:
            # --- CLASSIFICATION FUNCTION ---
            def classify_snippet(snippet, company):
                prompt = f"""
Given the following business snippet, classify whether the company appears aligned with {category_prompt} services.

Company: {company}
Snippet: {snippet}

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
            st.markdown("### 🏗️ Classifying vendors…")
            with st.spinner("Classifying… This may take a few minutes depending on the file size."):

                classifications = []
                for i, row in df.iterrows():
                    name = str(row["Name"])
                    description = str(row["Description"])
                    result = classify_snippet(description, name)
                    classifications.append(result)
                    time.sleep(1.5)  # prevent rate limit

                df["Classification"] = classifications

            # --- DISPLAY RESULTS ---
            st.markdown("### ✅ Results")
            st.dataframe(df)

            # --- DOWNLOAD LINK ---
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results CSV", data=csv, file_name="classified_vendors.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error processing file: {e}")


