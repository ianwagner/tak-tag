
import streamlit as st
import toml
import json
from streamlit_tags import st_tags
from main_tagger import run_tagger
from recipe_generator import generate_recipes, read_sheet, LAYOUT_COPY_SHEET_ID
from google.oauth2 import service_account
from googleapiclient.discovery import build
from utils import parse_google_id, load_history, save_history

# Load app secrets
with open("secrets.toml", "r") as f:
    secrets = toml.load(f)

app_password = secrets["app_password"]
SERVICE_ACCOUNT_INFO = json.loads(secrets["google"]["service_account"])
HISTORY = load_history()


def history_input(label, options, key_prefix):
    """Return an ID from saved options or new entry using a single widget.

    Parameters
    ----------
    label : str
        Label for the input field.
    options : dict[str, str]
        Mapping of display names to IDs.
    key_prefix : str
        Unique key prefix for Streamlit widgets.

    Returns
    -------
    str
        The selected or entered ID string.
    """

    mode_key = f"{key_prefix}_mode"
    mode = st.session_state.get(mode_key, "select")

    if mode == "select":
        choice_label = "Add new..."
        select = st.selectbox(
            label,
            options=list(options.keys()) + [choice_label],
            key=f"{key_prefix}_select",
        )
        if select == choice_label:
            st.session_state[mode_key] = "input"
            return ""
        return options.get(select, "")

    value = st.text_input(label, key=f"{key_prefix}_input")
    if st.button("Cancel", key=f"{key_prefix}_cancel"):
        st.session_state[mode_key] = "select"
        return ""
    return parse_google_id(value)

def get_google_service(service_account_info):
    """Create authorized Google Sheets and Drive clients.

    Parameters
    ----------
    service_account_info : dict
        Service account JSON credentials.

    Returns
    -------
    tuple
        Authorized Sheets and Drive service objects.
    """

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
    )
    return build('sheets', 'v4', credentials=credentials), build('drive', 'v3', credentials=credentials)

def get_file_name(drive_service, file_id):
    """Return Drive file name for given ID."""
    try:
        meta = drive_service.files().get(fileId=file_id, fields='name').execute()
        return meta.get('name', file_id)
    except Exception:
        return file_id

@st.cache_data(show_spinner=False)
def load_layout_copy_options(service_account_info):
    """Fetch layout and copy format options and cache the result."""
    sheets_service = get_google_service(service_account_info)[0]
    layouts_df = read_sheet(sheets_service, LAYOUT_COPY_SHEET_ID, 'layouts')
    copy_df = read_sheet(sheets_service, LAYOUT_COPY_SHEET_ID, 'copy_formats')
    return layouts_df['Name'].tolist(), copy_df['Name'].tolist()

BRAND_SHEET_ID = "1j74m77q9LIUBv1DJdSGA4cAx4pADXznSD-_RBVosG7g"  # Set to your Google Sheet ID; remove this note if the ID is final

st.set_page_config(page_title="StudioTAK Tagger + Recipe Builder", layout="centered")

# Password gate
password = st.text_input("🔒 Enter password", type="password")
if password != app_password:
    st.stop()

tab1, tab2, tab_brand = st.tabs(["🧠 Tag Assets", "📋 Generate Recipes", "🏷 Manage Brands"])
with tab1:
    st.title("🧠 Tag Image Assets")
    sheet_options = {e['name']: e['id'] for e in HISTORY.get('sheets', [])}
    folder_options = {e['name']: e['id'] for e in HISTORY.get('folders', [])}

    sheet_id = history_input(
        "Google Sheet URL or ID (for tagged assets)",
        sheet_options,
        "sheet",
    )
    folder_id = history_input(
        "Google Drive Folder URL or ID (image folder)",
        folder_options,
        "folder",
    )

    st.subheader("Expected Content")
    expected_content = st_tags(label="Add tags", key="expected_content")

    if st.button("Run Tagging"):
        try:
            st.info("Tagging images...")
            final_sheet = sheet_id
            final_folder = folder_id
            run_tagger(final_sheet, final_folder, expected_content)

            sheets_service, drive_service = get_google_service(SERVICE_ACCOUNT_INFO)
            if not any(e['id'] == final_sheet for e in HISTORY.get('sheets', [])):
                HISTORY.setdefault('sheets', []).append({
                    'id': final_sheet,
                    'name': get_file_name(drive_service, final_sheet)
                })
            if not any(e['id'] == final_folder for e in HISTORY.get('folders', [])):
                HISTORY.setdefault('folders', []).append({
                    'id': final_folder,
                    'name': get_file_name(drive_service, final_folder)
                })
            save_history(HISTORY)
            st.success("✅ Tagging complete. Check your Google Sheet.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

with tab2:
    st.title("📋 Generate Creative Recipes")
    col_main, = st.columns([1])
    with col_main:
        sheet_id = history_input(
            "Google Sheet URL or ID (for tagged assets)",
            sheet_options,
            "sheet",
        )
        folder_id = history_input(
            "Google Drive Folder URL or ID (for image links)",
            folder_options,
            "folder",
        )
        brand_code = st.text_input("Brand Code (matches brand list)", key="brand_code")

        try:
            layout_options, copy_options = load_layout_copy_options(SERVICE_ACCOUNT_INFO)
        except Exception as e:
            st.warning(f"⚠ Could not load layout/copy options: {e}")
            layout_options = []
            copy_options = []

        selected_layouts = st.multiselect("Select Layouts", options=layout_options, default=layout_options)
        selected_copy_formats = st.multiselect("Select Copy Formats", options=copy_options, default=copy_options)

        angles_input = st.text_area("Angles (comma-separated)")
        audiences_input = st.text_area("Audiences (comma-separated)")
        offers_input = st.text_area("Offers (comma-separated)")

        num_recipes = st.number_input("How many recipes to generate?", min_value=1, max_value=100, value=10)

        if st.button("Generate Recipes"):
            try:
                st.info("Generating recipes...")
                final_sheet = sheet_id
                final_folder = folder_id
                recipes = generate_recipes(
                    final_sheet,
                    SERVICE_ACCOUNT_INFO,
                    final_folder,
                    brand_code,
                    BRAND_SHEET_ID,
                    num_recipes,
                    angles=[a.strip() for a in angles_input.split(',') if a.strip()],
                    audiences=[a.strip() for a in audiences_input.split(',') if a.strip()],
                    offers=[o.strip() for o in offers_input.split(',') if o.strip()],
                    selected_layouts=selected_layouts,
                    selected_copy_formats=selected_copy_formats,
                )
                sheets_service, drive_service = get_google_service(SERVICE_ACCOUNT_INFO)
                if not any(e['id'] == final_sheet for e in HISTORY.get('sheets', [])):
                    HISTORY.setdefault('sheets', []).append({
                        'id': final_sheet,
                        'name': get_file_name(drive_service, final_sheet)
                    })
                if not any(e['id'] == final_folder for e in HISTORY.get('folders', [])):
                    HISTORY.setdefault('folders', []).append({
                        'id': final_folder,
                        'name': get_file_name(drive_service, final_folder)
                    })
                save_history(HISTORY)
                st.success("✅ Recipes generated. Check your Google Sheet.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

with tab_brand:
    st.title("🏷 Manage Brand Guidelines")
    try:
        sheets_service = get_google_service(SERVICE_ACCOUNT_INFO)[0]
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=BRAND_SHEET_ID,
            range="brands"
        ).execute()
        brands_data = result.get("values", [])[1:]
        brand_options = [f"{row[0]} - {row[1]}" for row in brands_data]
        selected_brand = st.selectbox(
            "Select Existing Brand (or scroll down to add new)",
            options=[""] + brand_options,
        )

        brand_code = brand_name = guideline_source = guideline_link = copy_tone = keywords = formatting_notes = ""
        if selected_brand:
            selected_row = brands_data[brand_options.index(selected_brand)]
            selected_row = (selected_row + [""] * 7)[:7]
            (
                brand_code,
                brand_name,
                guideline_source,
                guideline_link,
                copy_tone,
                keywords,
                formatting_notes,
            ) = selected_row
    except Exception as e:
        st.warning(f"⚠ Could not load existing brands: {e}")
        selected_brand = ""
        brand_code = brand_name = guideline_source = guideline_link = copy_tone = keywords = formatting_notes = ""

    st.text_input("Brand Code", value=brand_code, key="bc")
    st.text_input("Brand Name", value=brand_name, key="bn")
    guideline_source = st.selectbox(
        "Guideline Source",
        options=["link", "upload"],
        index=0 if guideline_source == "link" else 1,
    )
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
                formatting_notes,
            ]]
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=BRAND_SHEET_ID,
                range="brands",
            ).execute()
            existing = result.get("values", [])
            if not existing or existing[0][0] != "Brand Code":
                headers = [
                    "Brand Code",
                    "Brand Name",
                    "Guideline Source",
                    "Guideline Link",
                    "Copy Tone",
                    "Keywords",
                    "Formatting Notes",
                ]
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=BRAND_SHEET_ID,
                    range="brands!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]},
                ).execute()
                existing = [headers]
            insert_range = f"brands!A{len(existing)+1}"
            sheets_service.spreadsheets().values().update(
                spreadsheetId=BRAND_SHEET_ID,
                range=insert_range,
                valueInputOption="RAW",
                body={"values": new_row},
            ).execute()
            st.success("✅ Brand profile added.")
        except Exception as e:
            st.error(f"❌ Failed to add brand: {e}")

