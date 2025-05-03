import streamlit as st
from main_tagger import run_tagger

st.set_page_config(page_title="StudioTAK Tagger", layout="centered")
st.title("🧠 StudioTAK Tagger")

# Password protection
password = st.text_input("🔒 Enter password", type="password")
if password != st.secrets["app_password"]:
    st.stop()

# Inputs
sheet_id = st.text_input("Google Sheet ID")
folder_id = st.text_input("Google Drive Folder ID")

st.subheader("🎯 Audience Tags")
audience_tags = {}
num_audience = st.number_input("How many audience tags?", min_value=1, max_value=10, value=2)
for i in range(num_audience):
    key = st.text_input(f"Audience Tag #{i+1}", key=f"aud_key_{i}")
    synonyms = st.text_input(f"Synonyms (comma-separated)", key=f"aud_syn_{i}")
    if key:
        audience_tags[key] = [s.strip() for s in synonyms.split(',') if s.strip()]

st.subheader("📦 Product Tags")
product_tags = {}
num_products = st.number_input("How many product tags?", min_value=1, max_value=10, value=2)
for i in range(num_products):
    key = st.text_input(f"Product Tag #{i+1}", key=f"prod_key_{i}")
    synonyms = st.text_input(f"Synonyms (comma-separated)", key=f"prod_syn_{i}")
    if key:
        product_tags[key] = [s.strip() for s in synonyms.split(',') if s.strip()]

st.subheader("🧠 Angle Tags")
angle_tags = {}
num_angles = st.number_input("How many angle tags?", min_value=1, max_value=10, value=2)
for i in range(num_angles):
    key = st.text_input(f"Angle Tag #{i+1}", key=f"angle_key_{i}")
    synonyms = st.text_input(f"Synonyms (comma-separated)", key=f"angle_syn_{i}")
    if key:
        angle_tags[key] = [s.strip() for s in synonyms.split(',') if s.strip()]

if st.button("Run Tagger"):
    try:
        st.info("Running tagger...")
        run_tagger(sheet_id, folder_id, audience_tags, product_tags, angle_tags)
        st.success("✅ Done! Tags written to Google Sheet.")
    except Exception as e:
        st.error(f"❌ Error: {e}")