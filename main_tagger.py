
import io
import json
import toml
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
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
    """List image files in a Google Drive folder.

    Parameters
    ----------
    folder_id : str
        ID of the Google Drive folder.

    Returns
    -------
    list[dict]
        File metadata dictionaries with ``id``, ``name`` and ``webViewLink``.
    """

    if not folder_id:
        raise ValueError("folder_id is required")

    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    response = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    return response.get('files', [])

def analyze_image(file_id):
    """Analyze an image with the Vision API.

    Parameters
    ----------
    file_id : str
        ID of the file to analyze.

    Returns
    -------
    tuple[list[str], list[str]]
        Detected labels and web entity labels.
    """

    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    try:
        while not done:
            _, done = downloader.next_chunk()
    except HttpError as e:
        raise RuntimeError(f"Failed to download file {file_id}: {e}")

    image = vision.Image(content=fh.getvalue())

    response = vision_client.annotate_image({
        'image': image,
        'features': [
            {'type': vision.Feature.Type.LABEL_DETECTION},
            {'type': vision.Feature.Type.WEB_DETECTION}
        ]
    })

    labels = [label.description for label in getattr(response, 'label_annotations', [])]
    web_detection = getattr(response, 'web_detection', None)
    entities = getattr(web_detection, 'web_entities', []) if web_detection else []
    web_labels = [entity.description for entity in entities]

    return labels, web_labels

def write_to_sheet(sheet_id, rows):
    """Append rows to a Google Sheet.

    Parameters
    ----------
    sheet_id : str
        Destination Google Sheet ID.
    rows : list[list[str]]
        Data rows to append.

    Returns
    -------
    None
    """

    sheets_service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def run_tagger(sheet_id, folder_id, expected_content=None):
    """Tag images in a Drive folder and write results to a Google Sheet.

    Parameters
    ----------
    sheet_id : str
        Destination Google Sheet ID.
    folder_id : str
        Source Drive folder containing images.
    expected_content : list[str] | None, optional
        Additional content tags to classify. Defaults to ``[]`` if not provided.
    """

    if not sheet_id or not folder_id:
        raise ValueError("sheet_id and folder_id are required")

    expected_content = expected_content or []

    rows = [[
        'Image Name',
        'Image Link',
        'Google Labels',
        'Google Web Entities',
        'Descriptors',
        'Matched Content',
        'Audience',
        'Product',
        'Angle',
    ]]
    files = list_images(folder_id)
    for file in files:
        labels, web_labels = analyze_image(file['id'])

        chat_result = chat_classify(
            labels,
            web_labels,
            expected_content,
        )

        descriptors = ', '.join(chat_result.get("descriptors", []))
        matched_content = chat_result.get("match_content", "unknown")
        audience = chat_result.get("audience", "unknown")
        product = chat_result.get("product", "unknown")
        angle = chat_result.get("angle", "unknown")

        rows.append([
            file['name'],
            file['webViewLink'],
            ', '.join(labels),
            ', '.join(web_labels),
            descriptors,
            matched_content,
            audience,
            product,
            angle,
        ])
    write_to_sheet(sheet_id, rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Tag images in a Drive folder and write results to a Google Sheet"
    )
    parser.add_argument("sheet_id", help="Destination Google Sheet ID")
    parser.add_argument("folder_id", help="Source Google Drive folder ID")
    parser.add_argument(
        "-e",
        "--expected-content",
        nargs="*",
        default=[],
        help="Additional expected content tags",
    )

    args = parser.parse_args()
    run_tagger(args.sheet_id, args.folder_id, args.expected_content)
