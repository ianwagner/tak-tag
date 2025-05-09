import openai
import os
import json
import random
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# Scopes for Sheets and Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]
# Layout and copy sheet
LAYOUT_COPY_SHEET_ID = "1M_-6UqmSE8yAlaSQl3EoGRZfdkzklb0Qpy2wwJmYq8E"
def get_google_service(service_account_info):
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    sheets = build('sheets', 'v4', credentials=credentials)
    drive = build('drive', 'v3', credentials=credentials)
    return sheets, drive
def read_sheet(service, spreadsheet_id, sheet_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name
    ).execute()
    rows = result.get('values', [])
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    data = rows[1:]
    return pd.DataFrame(data, columns=headers)
def get_asset_link(drive_service, file_name, folder_id):
    query = f"name = '{file_name}' and '{folder_id}' in parents and mimeType contains 'image/'"
    try:
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        if not files:
            return "NOT FOUND"
        return f"https://drive.google.com/uc?id={files[0]['id']}"
    except HttpError:
        return "ERROR LINKING FILE"
def choose_assets(tagged_assets, count=1):
    candidates = [a for a in tagged_assets if a.get('Matched Audience', '').lower() != 'unknown']
    if len(candidates) < count:
        return [], True
    return random.sample(candidates, count), False
def choose_recipe_components(layouts_df, copy_df):
    layout = layouts_df.sample(1).iloc[0].to_dict()
    copy_format = copy_df.sample(1).iloc[0].to_dict()
    return layout, copy_format
def get_brand_profile(brand_df, brand_code):
    profile = brand_df[brand_df['Brand Code'] == brand_code]
    return profile.iloc[0].to_dict() if not profile.empty else {}
def generate_recipe_copy(asset, layout, copy_format, brand):
    style = copy_format.get("Prompt Style", "").strip()
    if not style:
        style = "⚠️ Prompt Style missing — please check the copy_formats sheet."
    product = asset.get("Matched Product")
    audience = asset.get("Matched Audience")
    angle = asset.get("Matched Angle")
    descriptors = asset.get("Descriptors", "")
    tone = brand.get("Copy Tone", "neutral")
    keywords = brand.get("Keywords", "")
    prompt = f"""
You're an expert Meta ad copywriter. Generate copy that matches the following structure and purpose:
📌 Layout: {layout.get('Name')} — {layout.get('Use Case')}
🖋 Copy Format: {copy_format.get('Name')} — {copy_format.get('Use Case')}
✍️ You MUST format the ad using this structure — do not deviate:
{style}
🏷 Audience: {audience}
📦 Product: {product}
💡 Angle: {angle}
🎯 Descriptors: {descriptors}
🗣 Tone: {tone}
Return only the finished ad copy.
"""
    print("=== PROMPT SENT TO GPT ===\n" + prompt)
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a brilliant ad copywriter."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip().strip('"').strip("\'")
    except Exception as e:
        return f"ERROR: {e}"
def generate_recipes(sheet_id, service_account_info, folder_id, brand_code, brand_sheet_id, num_recipes=10):
    sheets_service, drive_service = get_google_service(service_account_info)
    # Load all relevant sheets
    layouts_df = read_sheet(sheets_service, LAYOUT_COPY_SHEET_ID, 'layouts')
    copy_df = read_sheet(sheets_service, LAYOUT_COPY_SHEET_ID, 'copy_formats')
    asset_df = read_sheet(sheets_service, sheet_id, 'Sheet1')
    brand_df = read_sheet(sheets_service, brand_sheet_id, 'brands')
    brand = get_brand_profile(brand_df, brand_code)
    tagged_assets = asset_df.to_dict(orient='records')
    output = [["Ad id", "Layout", "Copy Format", "Audience", "Product", "Angle", "Asset 1 Link", "Asset 2 Link", "Copy", "Notes"]]
    for i in range(num_recipes):
        layout, copy_format = choose_recipe_components(layouts_df, copy_df)
        ad_id = f"{brand_code}-P{i+1:03d}"
        asset_count = int(layout.get("Asset Count", "1"))
        selected_assets, needs_generation = choose_assets(tagged_assets, asset_count)
        if needs_generation:
            output.append([
                ad_id,
                layout.get("Name"),
                copy_format.get("Name"),
                "", "", "",
                "", "",
                "ASSET NOT FOUND — RECOMMEND GENERATION",
                f"No available tagged assets for layout requiring {asset_count} image(s)."
            ])
            continue
        # Extract key info
        links = [get_asset_link(drive_service, a.get("Image Name"), folder_id) for a in selected_assets]
        first_asset = selected_assets[0]
        ad_copy = generate_recipe_copy(first_asset, layout, copy_format, brand)
        output.append([
            ad_id,
            layout.get("Name"),
            copy_format.get("Name"),
            first_asset.get("Matched Audience", ""),
            first_asset.get("Matched Product", ""),
            first_asset.get("Matched Angle", ""),
            links[0] if len(links) > 0 else "",
            links[1] if len(links) > 1 else "",
            ad_copy,
            ""
        ])

    # Write output to Google Sheet
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="recipes!A1",
        valueInputOption="RAW",
        body={"values": output}
    ).execute()
    return output
    recipes.append(recipe)