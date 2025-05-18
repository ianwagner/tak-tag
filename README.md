# TAK Tag

TAK Tag provides utilities for tagging image assets and generating ad recipes using Google Cloud and OpenAI services.

## Installation

1. Create a Python 3 environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

After installing the requirements you can run the test suite:

```bash
python -m pytest -q
```

## Required Environment Variables

- `OPENAI_API_KEY` – API key for accessing OpenAI models.
- `GOOGLE_SERVICE_ACCOUNT` – path to a Google service account JSON or the JSON string itself.

## `secrets.toml` Format

A `secrets.toml` file must live in the project root and contain your app password and Google credentials. Example:

```toml
app_password = "your-password"

[google]
service_account = """
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account@my-project.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "token_uri": "https://oauth2.googleapis.com/token"
}
"""
```

## Usage

### Streamlit App

Run the interactive tagging and recipe builder UI:

```bash
streamlit run tagger_app.py
```

You can paste entire Google Sheet or Drive URLs into the form fields. The
Streamlit app writes previously used sheet and folder names to
`.tak_history.json` located in the project root and provides them in dropdown
menus for quick reuse. Edit or delete this file if you need to clear your
history.

### CLI Example

You can call the utility functions from the command line. For example, to tag images:

```bash
python - <<'PY'
from main_tagger import run_tagger
run_tagger('SHEET_ID', 'FOLDER_ID', ['shoes', 'accessories'])
PY
```

Both raw IDs and full Google URLs work for the sheet and folder arguments. This writes tag results to the provided Google Sheet. Recipes can be generated in a similar manner using `generate_recipes` from `recipe_generator.py`.

## Customizing the Streamlit Theme

The app looks for a `.streamlit/config.toml` file to control colors and fonts. Edit this file to change the theme applied across all pages.

Example configuration:

```toml
[theme]
base = "light"
primaryColor = "#00aaad"
backgroundColor = "#f5f5f5"
secondaryBackgroundColor = "#ffffff"
textColor = "#000000"
font = "sans serif"
```

Updates to this file take effect the next time you run `streamlit run tagger_app.py`.
