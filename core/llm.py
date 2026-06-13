import requests
import json
import re

from config import LLM_MODEL, LLM_URL


class LLM:
    def __init__(self, model=None, url=None):
        self.model = model or LLM_MODEL
        self.url = url or LLM_URL

    def generate(self, prompt, temperature=0.7):
        try:
            r = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "temperature": temperature},
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.RequestException as e:
            return f"LLM error: {e}"

    def generate_json(self, prompt):
        raw = self.generate(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
