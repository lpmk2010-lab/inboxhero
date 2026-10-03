# Roll number: cert-aai-2026-06-0039
import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"


def _load():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE) as f:
        return json.load(f)


def _save(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def _norm(text):
    return text.strip().lower().replace("-", "_").replace(" ", "_")


def remember(key, value, source):
    memory = _load()
    key = _norm(key)
    old = memory.get(key)
    memory[key] = {"value": value, "source": source, "updated_at": datetime.now().isoformat(timespec="seconds")}
    _save(memory)
    if old and old["value"] != value:
        return {"status": "updated", "key": key, "old_value": old["value"], "value": value}
    return {"status": "stored", "key": key, "value": value}


def recall(query):
    q = _norm(query)
    matches = [
        {"key": k, **entry} for k, entry in _load().items()
        if q in k or q in _norm(str(entry["value"]))
    ]
    return {"count": len(matches), "matches": matches}


def summary():
    memory = _load()
    if not memory:
        return "(nothing stored yet)"
    return "\n".join(f"- {k}: {e['value']} (source: {e['source']})" for k, e in memory.items())
