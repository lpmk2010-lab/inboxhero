# Roll number: cert-aai-2026-06-0039
# sending mail and storing a standing preference both stop here for a human y/n, or only print under --dry-run
import json
import os
import memory
from tracelog import log

OUTBOX_DIR = "outbox"


def approve(question, proposal, dry_run):
    print(proposal)
    if dry_run:
        return False, "dry-run"
    try:
        answer = input(f"{question} [y/n] ").strip().lower()
    except EOFError:
        answer = "no answer"
    return answer == "y", answer


def send(d, dry_run):
    path = f"{OUTBOX_DIR}/{d['msg']}.json"
    if os.path.exists(path):
        print(f"\n{path} already sent, not sending it twice")
        return False
    mail = {"to": d["to"], "cc": d["cc"], "subject": d["subject"], "body": d["body"]}
    ok, answer = approve("Send it?", f"\nProposed send, would write {path}:\n{json.dumps(mail, indent=2)}", dry_run)
    if ok:
        os.makedirs(OUTBOX_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump({**mail, "in_reply_to": d["msg"], "cited": d["cited"]}, f, indent=2)
    result = f"wrote {path}" if ok else f"not sent ({answer})"
    log("gate", msg=d["msg"], action="send", proposed=mail, human=answer, result=result)
    print(result)
    return ok


def remember(msg_id, preference, source, dry_run):
    ok, answer = approve("Remember it?", f"\n{msg_id} from {source} states a standing preference:\n  {preference}", dry_run)
    if ok:
        memory.remember(msg_id, preference, source)
    result = "stored in memory.json" if ok else f"not stored ({answer})"
    log("gate", msg=msg_id, action="remember", proposed=preference, human=answer, result=result)
    print(result)
    return ok


def sent():
    if not os.path.exists(OUTBOX_DIR):
        return []
    mails = []
    for name in sorted(os.listdir(OUTBOX_DIR)):
        with open(f"{OUTBOX_DIR}/{name}") as f:
            mails.append(json.load(f))
    return mails
