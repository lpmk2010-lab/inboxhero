# Roll number: cert-aai-2026-06-0039
import calendar
import json
from html import escape
from mailstore import BY_ID

CSS = """
body { font-family: sans-serif; margin: 24px; color: #222; }
section { border: 1px solid #ccc; border-radius: 6px; padding: 12px 16px; margin-bottom: 24px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #f3f3f3; }
.cal td { width: 14%; height: 70px; }
.item { background: #e8f0fe; margin-top: 4px; padding: 2px 4px; border-radius: 3px; font-size: 12px; }
.clash { background: #fde2e1; color: #a00; font-weight: bold; margin-top: 4px; padding: 2px 4px; border-radius: 3px; font-size: 12px; }
"""


def _label(msg_id):
    m = BY_ID[msg_id]
    return f"{msg_id} {m['from']}: {m['subject']}"


def panes(decisions, drafts, sent_ids, items, dropped, clashes):
    pending = [
        {"message": _label(d["msg"]), "action": "send reply to " + ", ".join([d["to"], *d["cc"]]),
         "why": "mail in Sam's name is never sent without his yes"}
        for d in drafts if d["body"] and d["msg"] not in sent_ids
    ] + [
        {"message": _label(i), "action": "hold for Sam, take no action", "why": d["reason"]}
        for i, d in decisions.items() if d["disposition"] == "escalate"
    ]
    flagged = [
        {"message": _label(i), "attempted": f"{d['threat']}: {d['attempted']}",
         "instead": "refused: nothing sent or deleted, left in the inbox, reported in the run summary"}
        for i, d in decisions.items() if d["threat"]
    ] + [
        {"message": _label(d["msg"]), "attempted": "draft a reply",
         "instead": f"no draft, not in the inbox: {d['missing']}"}
        for d in drafts if not d["body"]
    ] + [
        {"message": ", ".join(str(s.get("id")) for s in c.get("sources") or []),
         "attempted": f"put '{c.get('what')}' on the calendar",
         "instead": "left off the calendar, its quote is not in the cited email"}
        for c in dropped
    ]
    return {"pending": pending, "flagged": flagged, "commitments": items, "conflicts": clashes}


def _table(rows, cols):
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(r[c]))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def _calendar(items, clashes):
    clash = {(c["date"], c["time"]) for c in clashes}
    by_day = {}
    for c in items:
        by_day.setdefault(c["date"], []).append(c)
    html = ""
    for ym in sorted({c["date"][:7] for c in items}):
        year, month = int(ym[:4]), int(ym[5:])
        rows = ""
        for week in calendar.monthcalendar(year, month):
            cells = ""
            for day in week:
                date = f"{ym}-{day:02d}"
                entries = "".join(
                    f'<div class="{"clash" if (date, c.get("time")) in clash else "item"}">'
                    f'{c.get("time") or ""} {escape(c["what"])} [{", ".join(c["cited"])}]</div>'
                    for c in by_day.get(date, [])
                )
                cells += f"<td><b>{day}</b>{entries}</td>" if day else "<td></td>"
            rows += f"<tr>{cells}</tr>"
        days = "".join(f"<th>{d}</th>" for d in calendar.day_abbr)
        html += f"<h3>{calendar.month_name[month]} {year}</h3><table class='cal'><tr>{days}</tr>{rows}</table>"
    return html


def build(data):
    with open("dashboard.json", "w") as f:
        json.dump(data, f, indent=2)
    clash_lines = "".join(
        f"<p class='clash'>CONFLICT {c['date']} {c['time']}: "
        + " vs ".join(f"{escape(i['what'])} [{', '.join(i['cited'])}]" for i in c["items"]) + "</p>"
        for c in data["conflicts"]
    )
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'><title>inboxHero dashboard</title>"
        f"<style>{CSS}</style></head><body><h1>inboxHero</h1>"
        f"<section><h2>Pending actions ({len(data['pending'])})</h2>"
        f"{_table(data['pending'], ['message', 'action', 'why'])}</section>"
        f"<section><h2>Flagged ({len(data['flagged'])})</h2>"
        f"{_table(data['flagged'], ['message', 'attempted', 'instead'])}</section>"
        f"<section><h2>Commitments ({len(data['commitments'])})</h2>{clash_lines}"
        f"{_calendar(data['commitments'], data['conflicts'])}</section>"
        "</body></html>"
    )
    with open("dashboard.html", "w") as f:
        f.write(html)
