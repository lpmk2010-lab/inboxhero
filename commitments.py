# Roll number: cert-aai-2026-06-0039
import calendar
import re
from datetime import datetime, timedelta
from llm import ask
from mailstore import BY_ID, INBOX, grounded
from tracelog import log

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_WORDS = re.compile(r"\d|" + "|".join(WEEKDAYS) + "|month|today|tomorrow", re.I)
DAY_OF_MONTH = re.compile(r"\b\d{1,2}(st|nd|rd|th)\b|(" + "|".join(calendar.month_name[1:]) + r") \d", re.I)

TASK = (
    "List every commitment in these emails that Sam has to keep or decide on: "
    "meetings, appointments, deadlines and obligations that have a date. When "
    "several emails mention the same event, make one entry. Return "
    '{"commitments": [{"what": "<short title>", "date": "YYYY-MM-DD", '
    '"time": "HH:MM" or null, '
    '"what_source": {"id": "<email id>", "quote": "<exact words saying what has to happen>"}, '
    '"date_source": {"id": "<email id>", "quote": "<exact words that contain the day: a '
    'number or a weekday name>"}}]}. Quotes are copied exactly. If the email with the '
    "task has no such words because its date is relative to another event (for "
    "example 'two days before the launch'), date_source must quote the other email "
    "that gives that event's day."
)


# the model miscounts weekdays, so a quote that only names a weekday is counted forward from the day it was sent
def resolve(date, quote, sent):
    q = quote.lower()
    named = [w for w in WEEKDAYS if w in q]
    if named and not DAY_OF_MONTH.search(quote):
        day = max(named, key=q.rfind)
        return (sent + timedelta(days=(WEEKDAYS.index(day) - sent.weekday()) % 7)).isoformat()
    return date


def extract(decisions):
    emails = [m for m in INBOX if decisions[m["id"]]["disposition"] in ("reply", "defer", "escalate")]
    print(f"Asking the model for commitments in {len(emails)} messages ...", flush=True)
    found = ask(TASK, emails).get("commitments", [])
    ids = {m["id"] for m in emails}
    kept, dropped = [], []
    for c in found:
        c["sources"] = [c.get("what_source") or {}, c.get("date_source") or {}]
        if c.get("date") and grounded(c["sources"], ids) and DAY_WORDS.search(c["sources"][1]["quote"]):
            sent = datetime.fromisoformat(BY_ID[c["sources"][1]["id"]]["timestamp"]).date()
            c["date"] = resolve(c["date"], c["sources"][1]["quote"], sent)
            c["cited"] = sorted({s["id"] for s in c["sources"]})
            kept.append(c)
            log("commitment", what=c["what"], date=c["date"], time=c.get("time"), cited=c["cited"])
        else:
            dropped.append(c)
            log("ungrounded_commitment", what=c.get("what"), sources=c["sources"])
    return sorted(kept, key=lambda c: (c["date"], c.get("time") or "")), dropped


def conflicts(items):
    slots = {}
    for c in items:
        if c.get("time"):
            slots.setdefault((c["date"], c["time"]), []).append(c)
    return [{"date": d, "time": t, "items": cs} for (d, t), cs in slots.items() if len(cs) > 1]
