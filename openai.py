class OpenAI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"create": lambda *a, **k: None})()})()
