# Roll number: cert-aai-2026-06-0039
import json

OWNER = "sam@paperjet.io"

with open("inbox.json") as f:
    INBOX = json.load(f)

BY_ID = {m["id"]: m for m in INBOX}


def _flat(text):
    return " ".join(text.lower().split())


def thread_before(msg):
    earlier = [m for m in INBOX if m["thread_id"] == msg["thread_id"] and m["timestamp"] < msg["timestamp"]]
    return sorted(earlier, key=lambda m: m["timestamp"])


def grounded(sources, allowed_ids):
    if not sources:
        return False
    for s in sources:
        if s.get("id") not in allowed_ids or not s.get("quote"):
            return False
        m = BY_ID[s["id"]]
        if _flat(s["quote"]) not in _flat(m["subject"] + " " + m["body"]):
            return False
    return True
