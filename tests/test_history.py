import importlib
import sys
import types
import io
import builtins

import pytest

from utils import load_history, save_history, build_history_options


def test_save_and_load_history_roundtrip(tmp_path):
    path = tmp_path / "hist.json"
    data = {"sheets": [{"id": "1", "name": "S"}], "folders": [{"id": "2", "name": "F"}]}
    save_history(data, path)
    assert load_history(path) == data


def test_load_history_bad_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json")
    assert load_history(path) == {"sheets": [], "folders": []}


def test_build_history_options_handles_duplicates():
    entries = [
        {"id": "1", "name": "Sheet"},
        {"id": "2", "name": "Sheet"},
    ]
    opts = build_history_options(entries)
    assert list(opts.values()) == ["1", "2"]
    assert "Sheet" in opts
    assert "Sheet (2)" in opts


def import_tagger_app(monkeypatch, history=None):
    if history is None:
        history = {"sheets": [], "folders": []}

    fake_st = types.SimpleNamespace(session_state={})
    # placeholders to be replaced in individual tests
    fake_st.selectbox = lambda *a, **k: None
    fake_st.text_input = lambda *a, **k: None

    fake_tags = types.ModuleType('streamlit_tags')
    fake_tags.st_tags = lambda *a, **k: None

    stub_modules = {
        'streamlit': fake_st,
        'streamlit_tags': fake_tags,
        'googleapiclient': types.ModuleType('googleapiclient'),
        'googleapiclient.discovery': types.ModuleType('googleapiclient.discovery'),
        'google.oauth2': types.ModuleType('google.oauth2'),
        'google.oauth2.service_account': types.ModuleType('google.oauth2.service_account'),
        'main_tagger': types.ModuleType('main_tagger'),
        'recipe_generator': types.ModuleType('recipe_generator'),
        'toml': types.ModuleType('toml'),
    }
    stub_modules['googleapiclient.discovery'].build = lambda *a, **k: object()
    stub_modules['google.oauth2'].service_account = stub_modules['google.oauth2.service_account']
    stub_modules['toml'].load = lambda f: {"app_password": "pw", "google": {"service_account": "{}"}}
    stub_modules['recipe_generator'].generate_recipes = lambda *a, **k: None
    stub_modules['recipe_generator'].read_sheet = lambda *a, **k: None
    stub_modules['recipe_generator'].LAYOUT_COPY_SHEET_ID = ''

    for name, mod in stub_modules.items():
        sys.modules.setdefault(name, mod)

    import utils as real_utils
    monkeypatch.setattr(real_utils, 'load_history', lambda path=real_utils.HISTORY_FILE: history)

    _open = builtins.open
    def fake_open(path, *a, **k):
        if path == 'secrets.toml':
            return io.StringIO('')
        return _open(path, *a, **k)
    builtins.open = fake_open
    app = importlib.import_module('tagger_app')
    builtins.open = _open
    return app, fake_st


def test_history_input_select(monkeypatch):
    app, st_mod = import_tagger_app(monkeypatch)
    st_mod.selectbox = lambda *a, **k: 'First'
    result = app.history_input('label', {'First': 'ID1'}, 'key')
    assert result == 'ID1'


def test_history_input_add_new(monkeypatch):
    app, st_mod = import_tagger_app(monkeypatch)
    calls = {'step': 0}
    def sel(label, options, key):
        calls['step'] += 1
        return 'Add new...'
    def inp(label, key):
        calls['step'] += 1
        return 'ID2'
    st_mod.selectbox = sel
    st_mod.text_input = inp
    result1 = app.history_input('label', {}, 'key')
    assert result1 == ''
    assert st_mod.session_state['key_mode'] == 'input'
    result2 = app.history_input('label', {}, 'key')
    assert result2 == 'ID2'
    assert st_mod.session_state['key_mode'] == 'select'

def test_full_history_workflow(tmp_path, monkeypatch):
    history = {
        "sheets": [
            {"id": "1", "name": "S"},
            {"id": "2", "name": "S"},
        ],
        "folders": []
    }
    path = tmp_path / "hist.json"
    save_history(history, path)
    loaded = load_history(path)
    assert loaded == history
    opts = build_history_options(loaded["sheets"])
    assert list(opts.values()) == ["1", "2"]
