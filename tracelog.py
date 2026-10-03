# Roll number: cert-aai-2026-06-0039
import json
from datetime import datetime

TRACE_FILE = "trace.jsonl"
CAP = None


def log(event, **fields):
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "cap": CAP, "event": event, **fields}
    with open(TRACE_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
