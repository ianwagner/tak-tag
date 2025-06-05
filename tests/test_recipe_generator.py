import importlib
import sys
import types

# Stub external dependencies not installed during tests
googleapiclient_errors = types.ModuleType('googleapiclient.errors')
googleapiclient_errors.HttpError = type('HttpError', (Exception,), {})

stub_modules = {
    'openai': types.ModuleType('openai'),
    'pandas': types.ModuleType('pandas'),
    'googleapiclient': types.ModuleType('googleapiclient'),
    'googleapiclient.discovery': types.ModuleType('googleapiclient.discovery'),
    'googleapiclient.errors': googleapiclient_errors,
}
# google.oauth2.service_account has nested modules
google_module = types.ModuleType('google')
oauth2_module = types.ModuleType('google.oauth2')
service_account_module = types.ModuleType('google.oauth2.service_account')
oauth2_module.service_account = service_account_module
google_module.oauth2 = oauth2_module
stub_modules.update({
    'google': google_module,
    'google.oauth2': oauth2_module,
    'google.oauth2.service_account': service_account_module,
})

for name, mod in stub_modules.items():
    sys.modules.setdefault(name, mod)

# Now import the module under test
recipe_generator = importlib.import_module('recipe_generator')


def test_choose_assets_filters_unknown_and_selects(monkeypatch):
    assets = [
        {'Matched Audience': 'Gamers', 'id': 1},
        {'Matched Audience': 'unknown', 'id': 2},
        {'Matched Audience': 'Parents', 'id': 3},
    ]

    def fake_sample(seq, count):
        # After filtering, only assets[0] and assets[2] should remain
        assert seq == [assets[0], assets[2]]
        assert count == 1
        return [assets[2]]

    monkeypatch.setattr(recipe_generator.random, 'sample', fake_sample)
    selected, needs_generation = recipe_generator.choose_assets(assets, count=1)
    assert selected == [assets[2]]
    assert needs_generation is False


def test_choose_assets_insufficient_assets():
    assets = [
        {'Matched Audience': 'Unknown', 'id': 1},
        {'Matched Audience': 'unknown', 'id': 2},
    ]
    selected, needs_generation = recipe_generator.choose_assets(assets, count=1)
    assert selected == []
    assert needs_generation is True

def test_generate_recipe_copy_returns_cleaned(monkeypatch):
    response_text = '  "Great copy!"  '

    class FakeCompletions:
        def create(self, *args, **kwargs):
            message = types.SimpleNamespace(content=response_text)
            choice = types.SimpleNamespace(message=message)
            return types.SimpleNamespace(choices=[choice])

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key=None):
            self.chat = FakeChat()

    monkeypatch.setattr(recipe_generator.openai, 'OpenAI', FakeOpenAI)

    asset = {
        'Matched Product': 'Widget',
        'Matched Audience': 'Gamers',
        'Matched Angle': 'Excitement',
        'Descriptors': ''
    }
    layout = {'Name': 'L1', 'Use Case': 'Test'}
    copy_format = {'Name': 'C1', 'Use Case': 'Test', 'Prompt Style': 'fun'}
    brand = {'Copy Tone': 'neutral', 'Keywords': ''}

    result = recipe_generator.generate_recipe_copy(asset, layout, copy_format, brand)
    assert result == 'Great copy!'


def test_generate_recipes_filters_layouts_and_copy(monkeypatch):
    selected_layout = 'Layout B'
    selected_copy = 'Copy Y'

    sheet_id = 'SHEET123'
    folder_id = 'FOLDER456'
    brand_sheet_id = 'BRAND789'

    layouts_rows = [
        {'Name': 'Layout A', 'Use Case': 'A', 'Asset Count': '1'},
        {'Name': 'Layout B', 'Use Case': 'B', 'Asset Count': '1'},
    ]
    copy_rows = [
        {'Name': 'Copy X', 'Use Case': 'X', 'Prompt Style': 'x'},
        {'Name': 'Copy Y', 'Use Case': 'Y', 'Prompt Style': 'y'},
    ]
    asset_rows = [
        {'Image Name': 'img', 'Matched Audience': 'Gamers', 'Matched Product': 'P', 'Matched Angle': 'Fun'}
    ]

    class FakeSeries(list):
        def isin(self, values):
            return [v in values for v in self]

    class FakeDF:
        def __init__(self, rows):
            self.rows = list(rows)

        def __getitem__(self, key):
            if isinstance(key, str):
                return FakeSeries([r.get(key) for r in self.rows])
            elif isinstance(key, list):
                filtered = [r for r, keep in zip(self.rows, key) if keep]
                return FakeDF(filtered)
            raise TypeError

        def to_dict(self, orient='records'):
            assert orient == 'records'
            return self.rows

    captured = {}

    def fake_read_sheet(service, sid, sheet_name):
        captured.setdefault('sheet_ids', set()).add(sid)
        if sheet_name == 'layouts':
            return FakeDF(layouts_rows)
        if sheet_name == 'copy_formats':
            return FakeDF(copy_rows)
        if sheet_name == 'Sheet1':
            return FakeDF(asset_rows)
        return FakeDF([])

    def fake_get_brand_profile(df, code):
        return {'Copy Tone': 'neutral', 'Keywords': ''}

    def fake_choose_recipe_components(l_df, c_df):
        # Ensure filtering happened
        assert [r['Name'] for r in l_df.rows] == [selected_layout]
        assert [r['Name'] for r in c_df.rows] == [selected_copy]
        return l_df.rows[0], c_df.rows[0]

    def fake_choose_assets(tagged, count):
        return [asset_rows[0]], False

    def fake_get_asset_link(service, file_name, folder_id):
        captured['folder_id'] = folder_id
        return 'link'

    def fake_generate_recipe_copy(*args, **kwargs):
        return 'copy'

    class FakeUpdate:
        def execute(self):
            pass
    class FakeValues:
        def update(self, **kwargs):
            return FakeUpdate()
    class FakeSpreadsheets:
        def values(self):
            return FakeValues()
        def get(self, spreadsheetId):
            class FakeGet:
                def execute(self_inner):
                    return {"sheets": [{"properties": {"title": "recipes"}}]}
            return FakeGet()
        def batchUpdate(self, **kwargs):
            class FakeBatch:
                def execute(self_inner):
                    pass
            return FakeBatch()
    class FakeSheetsService:
        def spreadsheets(self):
            return FakeSpreadsheets()
    def fake_get_google_service(info):
        return FakeSheetsService(), object()

    monkeypatch.setattr(recipe_generator, 'read_sheet', fake_read_sheet)
    monkeypatch.setattr(recipe_generator, 'get_brand_profile', fake_get_brand_profile)
    monkeypatch.setattr(recipe_generator, 'choose_recipe_components', fake_choose_recipe_components)
    monkeypatch.setattr(recipe_generator, 'choose_assets', fake_choose_assets)
    monkeypatch.setattr(recipe_generator, 'get_asset_link', fake_get_asset_link)
    monkeypatch.setattr(recipe_generator, 'generate_recipe_copy', fake_generate_recipe_copy)
    monkeypatch.setattr(recipe_generator, 'get_google_service', fake_get_google_service)

    output = recipe_generator.generate_recipes(
        sheet_id,
        {},
        folder_id,
        'BR',
        brand_sheet_id,
        num_recipes=1,
        selected_layouts=[selected_layout],
        selected_copy_formats=[selected_copy],
    )

    header = output[0]
    asset_columns = [c for c in header if c.startswith('Asset')]
    assert asset_columns[:3] == ['Asset 1 Link', 'Asset 2 Link', 'Asset 3 Link']
    assert len(asset_columns) >= 3

    assert output[1][1] == selected_layout
    assert output[1][2] == selected_copy
    assert 'SHEET123' in captured['sheet_ids']
    assert 'BRAND789' in captured['sheet_ids']
    assert captured['folder_id'] == 'FOLDER456'


def test_read_sheet_handles_mismatched_rows(monkeypatch):
    rows = [
        ["A", "B", "C"],
        ["1", "2"],
        ["3", "4", "5", "6"],
    ]

    def make_service(values):
        def execute():
            return {"values": values}

        def get(spreadsheetId=None, range=None):
            return types.SimpleNamespace(execute=execute)

        values_obj = types.SimpleNamespace(get=get)
        spreadsheets_obj = types.SimpleNamespace(values=lambda: values_obj)
        return types.SimpleNamespace(spreadsheets=lambda: spreadsheets_obj)

    class FakeDataFrame:
        def __init__(self, data, columns=None):
            self.data = list(data)
            self.columns = list(columns or [])

    fake_pd = types.SimpleNamespace(
        DataFrame=lambda data, columns=None: FakeDataFrame(data, columns)
    )

    service = make_service(rows)
    monkeypatch.setattr(recipe_generator, "pd", fake_pd)

    df = recipe_generator.read_sheet(service, "sid", "sheet")

    assert df.columns == ["A", "B", "C"]
    assert df.data == [["1", "2", ""], ["3", "4", "5"]]
