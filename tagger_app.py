
import streamlit as st
from main_tagger import run_tagger
import toml

st.set_page_config(page_title="Tak Tag", layout="centered")
st.title("🧠 Tak Tag")

# Load secrets for app password
with open("secrets.toml", "r") as f:
    secrets = toml.load(f)

app_password = secrets["app_password"]

# Password gate
password = st.text_input("🔒 Enter password", type="password")
if password != app_password:
    st.stop()

# Inputs
sheet_id = st.text_input("Google Sheet ID")
folder_id = st.text_input("Google Drive Folder ID")

st.subheader("🎯 Your Expected Tags (Optional Matching)")

audiences = st.text_input("Expected Audiences (comma-separated)", value="mom, teen, athlete, grandma")
products = st.text_input("Expected Products (comma-separated)", value="deodorant, concealer, sneaker, moisturizer")
angles = st.text_input("Expected Angles (comma-separated)", value="confidence, natural beauty, performance, wellness")

# Clean and convert to lists
expected_audiences = [a.strip().lower() for a in audiences.split(",") if a.strip()]
expected_products = [p.strip().lower() for p in products.split(",") if p.strip()]
expected_angles = [a.strip().lower() for a in angles.split(",") if a.strip()]

if st.button("Run Tagger"):
    try:
        st.info("Running tagger...")
        run_tagger(sheet_id, folder_id, expected_audiences, expected_products, expected_angles)
        st.success("✅ Done! Tags written to Google Sheet.")
    except Exception as e:
        st.error(f"❌ Error: {e}")

