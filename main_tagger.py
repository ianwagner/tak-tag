import io
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/cloud-platform'
]

import toml

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

def match_tag(labels, tag_map):
    for label in labels:
        for category, synonyms in tag_map.items():
            if label.lower() in [s.lower() for s in synonyms]:
                return category
    return "unknown"

def write_to_sheet(sheet_id, rows):
    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def run_tagger(sheet_id, folder_id, audience_map, product_map, angle_map):
    rows = [['Image Name', 'Image Link', 'Tags', 'Audience', 'Product', 'Angle']]
    files = list_images(folder_id)
    for file in files:
        labels = analyze_image(file['id'])
        audience = match_tag(labels, audience_map)
        product = match_tag(labels, product_map)
        angle = match_tag(labels, angle_map)
        rows.append([
            file['name'],
            file['webViewLink'],
            ', '.join(labels),
            audience,
            product,
            angle
        ])
    write_to_sheet(sheet_id, rows)
