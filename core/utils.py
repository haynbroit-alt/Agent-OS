import json


def pretty(result):
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
