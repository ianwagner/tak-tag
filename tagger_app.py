
import streamlit as st
import toml
import json
from main_tagger import run_tagger
from recipe_generator import generate_recipes
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load app secrets
with open("secrets.toml", "r") as f:
    secrets = toml.load(f)

app_password = secrets["app_password"]
SERVICE_ACCOUNT_INFO = json.loads(secrets["google"]["service_account"])

def get_google_service(service_account_info):
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
    )
    return build('sheets', 'v4', credentials=credentials), build('drive', 'v3', credentials=credentials)

BRAND_SHEET_ID = "1j74m77q9LIUBv1DJdSGA4cAx4pADXznSD-_RBVosG7g"  # Replace with actual sheet ID

st.set_page_config(page_title="StudioTAK Tagger + Recipe Builder", layout="centered")

# Password gate
password = st.text_input("🔒 Enter password", type="password")
if password != app_password:
    st.stop()

tab1, tab2, tab3 = st.tabs(["🧠 Tag Assets", "📋 Generate Recipes", "🏷️ Manage Brands"])

with tab1:
    st.title("🧠 Tag Image Assets")
    sheet_id = st.text_input("Google Sheet ID (for tagged assets)", key="tag_sheet")
    folder_id = st.text_input("Google Drive Folder ID (image folder)")

    st.subheader("Expected Tags (used for classification)")
    audiences = st.text_input("Expected Audiences", value="mom, teen, athlete, grandma")
    products = st.text_input("Expected Products", value="deodorant, concealer, sneakers")
    angles = st.text_input("Expected Angles", value="confidence, natural beauty, performance")

    expected_audiences = [a.strip().lower() for a in audiences.split(",") if a.strip()]
    expected_products = [p.strip().lower() for p in products.split(",") if p.strip()]
    expected_angles = [a.strip().lower() for a in angles.split(",") if a.strip()]

    if st.button("Run Tagging"):
        try:
            st.info("Tagging images...")
            run_tagger(sheet_id, folder_id, expected_audiences, expected_products, expected_angles)
            st.success("✅ Tagging complete. Check your Google Sheet.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

with tab2:
    st.title("📋 Generate Creative Recipes")
    recipe_sheet_id = st.text_input("Tagged Asset Sheet ID", key="recipe_sheet")
    image_folder_id = st.text_input("Google Drive Folder ID (for image links)", key="asset_folder")
    brand_code = st.text_input("Brand Code (matches brand tab)", key="brand_code")

    num_recipes = st.number_input("How many recipes to generate?", min_value=1, max_value=100, value=10)

    if st.button("Generate Recipes"):
        try:
            st.info("Generating recipes...")
            recipes = generate_recipes(
                recipe_sheet_id,
                SERVICE_ACCOUNT_INFO,
                image_folder_id,
                brand_code,
                BRAND_SHEET_ID,
                num_recipes
            )
            st.success("✅ Recipes generated. Check your Google Sheet.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

with tab3:
    st.title("🏷️ Manage Brand Guidelines")

    try:
        sheets_service = get_google_service(SERVICE_ACCOUNT_INFO)[0]
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=BRAND_SHEET_ID,
            range="brands"
        ).execute()
        brands_data = result.get("values", [])[1:]
        brand_options = [f"{row[0]} - {row[1]}" for row in brands_data]
        selected_brand = st.selectbox("Select Existing Brand (or scroll down to add new)", options=[""] + brand_options)

        brand_code = brand_name = guideline_source = guideline_link = copy_tone = keywords = formatting_notes = ""
        if selected_brand:
            selected_row = brands_data[brand_options.index(selected_brand)]
            brand_code, brand_name, guideline_source, guideline_link, copy_tone, keywords, formatting_notes = selected_row
    except Exception as e:
        st.warning(f"⚠️ Could not load existing brands: {e}")
        selected_brand = ""
        brand_code = brand_name = guideline_source = guideline_link = copy_tone = keywords = formatting_notes = ""

    st.text_input("Brand Code", value=brand_code, key="bc")
    st.text_input("Brand Name", value=brand_name, key="bn")
    guideline_source = st.selectbox("Guideline Source", options=["link", "upload"], index=0 if guideline_source == "link" else 1)
    st.text_input("Guideline Link", value=guideline_link, key="gl")
    st.text_input("Copy Tone", value=copy_tone, key="ct")
    st.text_area("Keywords", value=keywords, key="kw")
    st.text_area("Formatting Notes", value=formatting_notes, key="fn")

    if st.button("➕ Add Brand to Sheet"):
        try:
            new_row = [[
                brand_code,
                brand_name,
                guideline_source,
                guideline_link,
                copy_tone,
                keywords,
                formatting_notes
            ]]
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=BRAND_SHEET_ID,
                range="brands"
            ).execute()
            existing = result.get("values", [])
            if not existing or existing[0][0] != "Brand Code":
                headers = ["Brand Code", "Brand Name", "Guideline Source", "Guideline Link", "Copy Tone", "Keywords", "Formatting Notes"]
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=BRAND_SHEET_ID,
                    range="brands!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()
                existing = [headers]
            insert_range = f"brands!A{len(existing)+1}"
            sheets_service.spreadsheets().values().update(
                spreadsheetId=BRAND_SHEET_ID,
                range=insert_range,
                valueInputOption="RAW",
                body={"values": new_row}
            ).execute()
            st.success("✅ Brand profile added.")
        except Exception as e:
            st.error(f"❌ Failed to add brand: {e}")