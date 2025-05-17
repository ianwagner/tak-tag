
import io
import json
import toml
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
    while not downloader.next_chunk()[1]:
        pass

    image = vision.Image(content=fh.getvalue())

    response = vision_client.annotate_image({
        'image': image,
        'features': [
            {'type': vision.Feature.Type.LABEL_DETECTION},
            {'type': vision.Feature.Type.WEB_DETECTION}
        ]
    })

    labels = [label.description for label in response.label_annotations]
    web_labels = [entity.description for entity in response.web_detection.web_entities]

    return labels, web_labels

def write_to_sheet(sheet_id, rows):
    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def run_tagger(sheet_id, folder_id, expected_audiences, expected_products, expected_angles, expected_content=None):
    """Tag images in a Drive folder and write results to a Google Sheet.

    Parameters
    ----------
    sheet_id : str
        Destination Google Sheet ID.
    folder_id : str
        Source Drive folder containing images.
    expected_audiences : list[str]
        Possible audience tags.
    expected_products : list[str]
        Possible product tags.
    expected_angles : list[str]
        Possible angle tags.
    expected_content : list[str] | None, optional
        Additional content tags to classify. Defaults to ``[]`` if not
        provided.
    """

    expected_content = expected_content or []

    rows = [['Image Name', 'Image Link', 'Google Labels', 'Google Web Entities',
             'GPT Audience', 'GPT Product', 'GPT Angle', 'Descriptors',
             'Matched Audience', 'Matched Product', 'Matched Angle',
             'Matched Content']]
    files = list_images(folder_id)
    for file in files:
        labels, web_labels = analyze_image(file['id'])

        chat_result = chat_classify(
            labels,
            web_labels,
            expected_audiences,
            expected_products,
            expected_angles,
            expected_content,
        )

        gpt_audience = chat_result.get("audience", "unknown")
        gpt_product = chat_result.get("product", "unknown")
        gpt_angle = chat_result.get("angle", "unknown")
        descriptors = ', '.join(chat_result.get("descriptors", []))
        matched_audience = chat_result.get("match_audience", "unknown")
        matched_product = chat_result.get("match_product", "unknown")
        matched_angle = chat_result.get("match_angle", "unknown")
        matched_content = chat_result.get("match_content", "unknown")

        rows.append([
            file['name'],
            file['webViewLink'],
            ', '.join(labels),
            ', '.join(web_labels),
            gpt_audience,
            gpt_product,
            gpt_angle,
            descriptors,
            matched_audience,
            matched_product,
            matched_angle,
            matched_content,
        ])
    write_to_sheet(sheet_id, rows)
