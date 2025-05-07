
import streamlit as st
import pandas as pd
import time
import requests
import io
from openai import OpenAI

# --- STREAMLIT SETUP ---
st.set_page_config(page_title="Sustainability Vendor Classifier", layout="wide")
st.title("🔍 Sustainability Vendor Classifier")

# --- LOAD SECRETS ---
openai_api_key = st.secrets["OPENAI_API_KEY"].strip()
serp_api_key = st.secrets["SERPAPI_KEY"].strip()
client = OpenAI(api_key=openai_api_key)

# --- SESSION STATE INITIALIZATION ---
if "classified" not in st.session_state:
    st.session_state["classified"] = False
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- CATEGORY SELECTION ---
category_prompt = st.selectbox(
    "What type of service are you classifying for?",
    options=["solar", "green infrastructure", "HVAC", "lighting", "other"]
)

# --- SEARCH TERMS INPUT ---
search_terms = st.text_input(
    "🔎 Enter keywords to filter vendors (OR logic)",
    placeholder="e.g. solar, DC, Maryland (leave blank to skip filtering)"
)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📄 Upload your vendor CSV file", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
        df.columns = df.columns.str.strip().str.title()  # Normalize to Title Case

        if not {"Company", "Location"}.issubset(df.columns):
            st.error("CSV must contain 'Company' and 'Location' columns.")
        else:
            def filter_by_keywords(df, search_terms):
                if not search_terms.strip():
                    return df
                terms = [term.strip().lower() for term in search_terms.split(",")]
                return df[df.apply(lambda row: any(
                    term in str(row["Location"]).lower() or term in str(row["Company"]).lower()
                    for term in terms), axis=1)]

            filtered_df = filter_by_keywords(df, search_terms)

            st.markdown("### 🗂️ Full Vendor Dataset Preview")
            st.dataframe(df.head())

            if search_terms:
                st.markdown(f"### 🔍 Filtered Vendors Matching: `{search_terms}`")
                if not filtered_df.empty:
                    st.dataframe(filtered_df.head())
                else:
                    st.warning("⚠️ No vendors matched your search terms.")
            else:
                st.info("👆 No keywords entered. All vendors will be classified.")

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

            def classify_vendor(company, snippet, category, model_choice):
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

            model_choice = st.selectbox("Choose OpenAI model", options=["gpt-4", "gpt-3.5-turbo"], index=0)

            button_disabled = uploaded_file is None or filtered_df.empty
            if st.button("🚦 Begin Classifying Vendors", disabled=button_disabled):
                classifications = []
                debug_logs = []
                with st.spinner("Classifying… This may take a few minutes depending on file size."):
                    for _, row in filtered_df.iterrows():
                        company = str(row["Company"])
                        location = str(row["Location"])
                        query_terms = search_terms if search_terms else ""
                        snippet = get_serp_snippet(company, location, query_terms, serp_api_key)
                        result = classify_vendor(company, snippet, category_prompt, model_choice)
                        classifications.append(result)
                        debug_logs.append({
                            "Company": company,
                            "Location": location,
                            "Snippet": snippet,
                            "Classification": result
                        })
                        time.sleep(1.5)

                    filtered_df["Classification"] = classifications
                    st.session_state["classified"] = True
                    st.session_state["last_result"] = filtered_df.copy()
                    st.session_state["history"].append(filtered_df.copy())

            if st.session_state["classified"]:
                st.markdown("### ✅ Classification Results")
                st.dataframe(st.session_state["last_result"])

                with st.expander("🪵 Show Debug Info Per Vendor"):
                    debug_df = pd.DataFrame(debug_logs)
                    st.dataframe(debug_df)

                excel_buffer = io.BytesIO()
                
try:
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        st.session_state["last_result"].to_excel(writer, index=False, sheet_name="Vendors")

    st.download_button(
        label="📥 Download Results Excel",
        data=excel_buffer.getvalue(),
        file_name="classified_vendors.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
except ImportError:
    st.error("❌ Please install openpyxl to enable Excel export.")


    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

# --- HISTORY TAB ---
if st.session_state["history"]:
    st.markdown("## 📚 Classification History (This Session)")
    for i, past_df in enumerate(reversed(st.session_state["history"][-3:])):
        with st.expander(f"🔁 Past Run #{len(st.session_state['history']) - i}"):
            st.dataframe(past_df)


    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
