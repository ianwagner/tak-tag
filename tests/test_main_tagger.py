import importlib
import sys
import types
import builtins
import io

# Stub external dependencies not installed during tests
googleapiclient_errors = types.ModuleType('googleapiclient.errors')
googleapiclient_errors.HttpError = type('HttpError', (Exception,), {})

googleapiclient_discovery = types.ModuleType('googleapiclient.discovery')
googleapiclient_discovery.build = lambda *a, **k: object()

googleapiclient_http = types.ModuleType('googleapiclient.http')
googleapiclient_http.MediaIoBaseDownload = object

# google.oauth2.service_account has nested modules
google_module = types.ModuleType('google')
oauth2_module = types.ModuleType('google.oauth2')
service_account_module = types.ModuleType('google.oauth2.service_account')
class FakeCreds:
    @classmethod
    def from_service_account_info(cls, info, scopes=None):
        return object()
service_account_module.Credentials = FakeCreds
oauth2_module.service_account = service_account_module
google_module.oauth2 = oauth2_module

# google.cloud.vision stub
cloud_module = types.ModuleType('google.cloud')
vision_module = types.ModuleType('google.cloud.vision')
class FakeVisionClient:
    def __init__(self, credentials=None):
        pass
vision_module.ImageAnnotatorClient = FakeVisionClient
cloud_module.vision = vision_module

toml_module = types.ModuleType('toml')
toml_module.load = lambda f: {"google": {"service_account": "{}"}, "app_password": "pw"}

stub_modules = {
    'googleapiclient': types.ModuleType('googleapiclient'),
    'googleapiclient.discovery': googleapiclient_discovery,
    'googleapiclient.http': googleapiclient_http,
    'googleapiclient.errors': googleapiclient_errors,
    'google': google_module,
    'google.oauth2': oauth2_module,
    'google.oauth2.service_account': service_account_module,
    'google.cloud': cloud_module,
    'google.cloud.vision': vision_module,
    'toml': toml_module,
}

for name, mod in stub_modules.items():
    sys.modules.setdefault(name, mod)

# Provide empty file for secrets.toml
_open = builtins.open
def fake_open(path, *args, **kwargs):
    if path == 'secrets.toml':
        return io.StringIO('')
    return _open(path, *args, **kwargs)
builtins.open = fake_open

# Import module under test
main_tagger = importlib.import_module('main_tagger')

# Restore open
builtins.open = _open


def test_run_tagger_outputs_basic_columns(monkeypatch):
    sheet_id = 'SHEET123'
    folder_id = 'FOLDER456'
    captured = {}

    def fake_write(sheet_id, rows):
        captured['sheet_id'] = sheet_id
        captured['rows'] = rows

    def fake_list_images(fid):
        captured['folder_id'] = fid
        return [{'id': '1', 'name': 'img', 'webViewLink': 'link'}]

    monkeypatch.setattr(main_tagger, 'write_to_sheet', fake_write)
    monkeypatch.setattr(main_tagger, 'list_images', fake_list_images)
    monkeypatch.setattr(main_tagger, 'analyze_image', lambda fid: (['label'], ['web']))
    monkeypatch.setattr(
        main_tagger,
        'chat_classify',
        lambda *a, **k: {
            'descriptors': ['desc'],
            'match_content': 'match',
            'audience': 'aud',
            'product': 'prod',
            'angle': 'ang',
        },
    )

    main_tagger.run_tagger(sheet_id, folder_id, ['x'])

    assert captured['sheet_id'] == 'SHEET123'
    assert captured['folder_id'] == 'FOLDER456'
    assert captured['rows'][0] == [
        'Image Name',
        'Image Link',
        'Google Labels',
        'Google Web Entities',
        'Descriptors',
        'Matched Content',
        'Audience',
        'Product',
        'Angle',
    ]
    assert captured['rows'][1] == [
        'img',
        'link',
        'label',
        'web',
        'desc',
        'match',
        'aud',
        'prod',
        'ang',
    ]


def test_run_tagger_empty_folder_id_errors_before_api(monkeypatch):
    called = {}

    class FakeFiles:
        def list(self, **kwargs):
            called['called'] = True
            return types.SimpleNamespace(execute=lambda: {})

    class FakeDrive:
        def files(self):
            return FakeFiles()

    monkeypatch.setattr(main_tagger, 'drive_service', FakeDrive())

    try:
        main_tagger.run_tagger('sid', '', [])
    except ValueError as e:
        assert 'folder' in str(e).lower()
    else:
        raise AssertionError('ValueError not raised')

    assert 'called' not in called
