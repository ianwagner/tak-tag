
import io
import json
import toml
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
from chat_classifier import chat_classify

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/cloud-platform'
]

# Load secrets from secrets.toml
with open("secrets.toml", "r") as f:
    secrets = toml.load(f)

SERVICE_ACCOUNT_INFO = json.loads(secrets["google"]["service_account"])
app_password = secrets["app_password"]

credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)

drive_service = build('drive', 'v3', credentials=credentials)
sheets_service = build('sheets', 'v4', credentials=credentials)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

def list_images(folder_id):
    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    response = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    return response.get('files', [])

def analyze_image(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    image = vision.Image(content=fh.getvalue())
    response = vision_client.web_detection(image=image)
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")
    return [entity.description for entity in response.web_detection.web_entities]

def soft_match(expected_list, gpt_value):
    gpt_value = gpt_value.lower()
    return next((x for x in expected_list if x in gpt_value), "unknown")

def write_to_sheet(sheet_id, rows):
    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def run_tagger(sheet_id, folder_id, expected_audiences, expected_products, expected_angles):
    rows = [['Image Name', 'Image Link', 'Raw Labels', 'GPT Audience', 'GPT Product', 'GPT Angle', 'Descriptors', 'Matched Audience', 'Matched Product', 'Matched Angle']]
    files = list_images(folder_id)
    for file in files:
        labels = analyze_image(file['id'])

        # Run GPT classification
        chat_result = chat_classify(labels)
        gpt_audience = chat_result.get("audience", "unknown")
        gpt_product = chat_result.get("product", "unknown")
        gpt_angle = chat_result.get("angle", "unknown")
        descriptors = ', '.join(chat_result.get("descriptors", []))

        # Compare to expected categories
        matched_audience = soft_match(expected_audiences, gpt_audience)
        matched_product = soft_match(expected_products, gpt_product)
        matched_angle = soft_match(expected_angles, gpt_angle)

        rows.append([
            file['name'],
            file['webViewLink'],
            ', '.join(labels),
            gpt_audience,
            gpt_product,
            gpt_angle,
            descriptors,
            matched_audience,
            matched_product,
            matched_angle
        ])
    write_to_sheet(sheet_id, rows)

