from utils import parse_google_id

def test_parse_google_id():
    sheet_url = 'https://docs.google.com/spreadsheets/d/ABC123/edit'
    folder_url = 'https://drive.google.com/drive/folders/FOLDER456'
    assert parse_google_id(sheet_url) == 'ABC123'
    assert parse_google_id(folder_url) == 'FOLDER456'
    assert parse_google_id('PLAINID') == 'PLAINID'
