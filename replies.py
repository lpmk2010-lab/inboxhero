# Roll number: cert-aai-2026-06-0039
import json
import os
import memory
from llm import ask
from mailstore import BY_ID, INBOX, thread_before, grounded
from tracelog import log

DRAFTS_DIR = "drafts"

DRAFT_TASK = (
    "You draft a reply for Sam to the LAST email in the list. The earlier emails "
    "are its thread, and these emails are your only source of facts: never invent "
    "a fact, link, name, date or number that is not written in them, and never "
    "promise, accept, agree to or claim progress on anything for Sam (no 'I will'), "
    "since Sam decides that himself. If the email asks about something these "
    "emails do not describe, or answering needs Sam to accept, decline, propose "
    "or decide anything his standing preferences below do not already settle, the "
    "facts are missing; do not write a reply that only asks what they mean. Apply Sam's "
    "standing preferences below, including anyone they say to copy, and if the "
    "email asks for a meeting at a time they rule out, decline that time and "
    "propose three times that respect them. If the facts "
    'the reply needs are there, return {"found": true, "reply": "<reply body>", '
    '"cc": [<addresses to copy>], "sources": [{"id": "<email id>", "quote": '
    '"<exact words copied from that email>"}]} with one source for every email the '
    "reply draws on (preferences need no source). If they are not, return "
    '{"found": false, "missing": "<what is missing>"} and write no reply.'
)


def draft(msg_id):
    msg = BY_ID[msg_id]
    earlier = thread_before(msg)
    for m in earlier:
        log("read", msg=m["id"], for_msg=msg_id)
    prefs = memory.summary()
    out = ask(DRAFT_TASK, earlier + [msg], trusted=prefs)
    read = {m["id"] for m in earlier} | {msg_id}

    if out.get("found") and grounded(out.get("sources"), read):
        d = {
            "msg": msg_id,
            "to": msg["from"],
            "cc": [a for a in out.get("cc") or [] if a in prefs],
            "subject": msg["subject"] if msg["subject"].startswith("Re:") else "Re: " + msg["subject"],
            "body": out["reply"],
            "cited": sorted({s["id"] for s in out["sources"]}),
            "sources": out["sources"],
        }
        log("draft", msg=msg_id, cited=d["cited"], cc=d["cc"])
    else:
        missing = out.get("missing") if not out.get("found") else "the draft quoted something not in the emails it read"
        d = {"msg": msg_id, "body": None, "missing": missing}
        log("no_draft", msg=msg_id, missing=missing)

    os.makedirs(DRAFTS_DIR, exist_ok=True)
    with open(f"{DRAFTS_DIR}/{msg_id}.json", "w") as f:
        json.dump(d, f, indent=2)
    return d


OPEN_TASK = (
    "These emails are one thread, oldest first. Find the one request in it that is "
    "still waiting on Sam himself, ignoring updates that need nothing from him. "
    'Return {"open_question": "<one sentence>", "due": "<date or null>", '
    '"sources": [{"id": "<email id>", "quote": "<exact words copied from that email>"}]}.'
)


def open_question(thread_id):
    emails = sorted((m for m in INBOX if m["thread_id"] == thread_id), key=lambda m: m["timestamp"])
    out = ask(OPEN_TASK, emails)
    ok = grounded(out.get("sources"), {m["id"] for m in emails})
    cited = sorted({s.get("id") for s in out.get("sources") or []})
    log("open_question", thread=thread_id, read=[m["id"] for m in emails],
        question=out.get("open_question"), cited=cited, grounded=ok)
    return {**out, "read": len(emails), "cited": cited, "grounded": ok}


def load_drafts():
    if not os.path.exists(DRAFTS_DIR):
        return []
    drafts = []
    for name in sorted(os.listdir(DRAFTS_DIR)):
        with open(f"{DRAFTS_DIR}/{name}") as f:
            drafts.append(json.load(f))
    return drafts
