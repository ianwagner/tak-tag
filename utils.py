import json
import os
import re

HISTORY_FILE = '.tak_history.json'

def parse_google_id(value: str) -> str:
    """Return the Google ID found in a full URL or raw ID string."""
    if not value:
        return ''
    value = value.strip()
    if 'http' not in value:
        return value
    patterns = [
        r'/d/([A-Za-z0-9_-]+)',
        r'/folders/([A-Za-z0-9_-]+)',
        r'id=([A-Za-z0-9_-]+)'
    ]
    for pat in patterns:
        match = re.search(pat, value)
        if match:
            return match.group(1)
    return value

def load_history(path: str = HISTORY_FILE) -> dict:
    """Load saved sheet and folder references."""
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {'sheets': [], 'folders': []}
    return {'sheets': [], 'folders': []}

def save_history(history: dict, path: str = HISTORY_FILE) -> None:
    """Persist history data to disk."""
    with open(path, 'w') as f:
        json.dump(history, f)
