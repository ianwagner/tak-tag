import importlib
import sys
import types

# Stub external dependencies not installed during tests
stub_modules = {
    'openai': types.ModuleType('openai'),
    'pandas': types.ModuleType('pandas'),
    'googleapiclient': types.ModuleType('googleapiclient'),
    'googleapiclient.discovery': types.ModuleType('googleapiclient.discovery'),
    'googleapiclient.errors': types.ModuleType('googleapiclient.errors'),
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
