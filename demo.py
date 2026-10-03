# Roll number: cert-aai-2026-06-0039
import argparse
import json
import re
import subprocess
from collections import Counter
import commitments
import dashboard
import gate
import memory
import replies
import tracelog
import triage
from mailstore import BY_ID, INBOX


def report_threats(decisions):
    flagged = {i: d for i, d in decisions.items() if d["threat"]}
    print(f"\nRefused and flagged {len(flagged)} messages (none deleted, nothing sent for them):")
    for msg_id, d in flagged.items():
        print(f"  FLAGGED {msg_id} ({d['threat']}): {d['attempted']}")


def r1(args):
    decisions = triage.run()
    for msg_id, d in decisions.items():
        print(f"{msg_id:5} {d['by']:5} {d['disposition']:8} {d['reason']}")
    undecided = [m["id"] for m in INBOX if decisions.get(m["id"], {}).get("disposition") not in triage.VOCAB]
    by = Counter(d["by"] for d in decisions.values())
    print(f"\nmessages: {len(INBOX)}  undecided: {len(undecided)}")
    print(f"rule-handled (no model call): {by['rule']}  model-handled: {by['model']}")
    print("dispositions:", dict(Counter(d["disposition"] for d in decisions.values())))
    report_threats(decisions)


def show(d):
    if d["body"] is None:
        print(f"\n{d['msg']}: not in the inbox: {d['missing']}. No draft written.")
        return
    print(f"\nDraft reply to {d['msg']}\nTo: {d['to']}\nCc: {', '.join(d['cc']) or '-'}\nSubject: {d['subject']}\n")
    print(d["body"])
    print(f"\ncited: {d['cited']}")
    for s in d["sources"]:
        print(f'  {s["id"]}: "{s["quote"]}"')


def r2(args):
    for msg_id in args.msg:
        show(replies.draft(msg_id))


def r3(args):
    drafted = {d["msg"] for d in replies.load_drafts()}
    for msg_id, d in triage.load().items():
        if d["disposition"] == "reply" and msg_id not in drafted:
            replies.draft(msg_id)
    writes = sum(gate.send(d, args.dry_run) for d in replies.load_drafts() if d["body"])
    print(f"\noutbox/ writes: {writes}")


def draft_and_hold(msg_id, dry_run):
    print("Standing preferences in memory.json:\n" + memory.summary())
    d = replies.draft(msg_id)
    show(d)
    if d["body"]:
        gate.send(d, dry_run)


def r4(args):
    if not args.learn:
        draft_and_hold(args.msg[0] if args.msg else "m018", args.dry_run)
        return
    for msg_id, d in triage.load().items():
        if d["preference"]:
            gate.remember(msg_id, d["preference"], BY_ID[msg_id]["from"], args.dry_run)
    print("\nmemory.json now holds:\n" + memory.summary())
    print("Process exiting. The next run starts fresh and reads memory.json from disk.")


def r5(args):
    decisions = triage.load()
    report_threats(decisions)
    flagged = [i for i, d in decisions.items() if d["threat"]]
    for msg_id in flagged:
        tracelog.log("refusal", msg=msg_id, attempted=decisions[msg_id]["attempted"],
                     done="nothing sent, nothing deleted, flagged and left in the inbox")
    attacker = {a for i in flagged for a in [BY_ID[i]["from"], *re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", BY_ID[i]["body"])]}
    hits = [m for m in gate.sent() if {m["to"], *m["cc"]} & attacker]
    print(f"\noutbox/ files to a flagged sender or an address named in a flagged message: {len(hits)}")
    print(f"flagged messages still in inbox.json: {sum(i in BY_ID for i in flagged)} of {len(flagged)}")


def r6(args):
    decisions = triage.load()
    items, dropped = commitments.extract(decisions)
    clashes = commitments.conflicts(items)
    sent_ids = {m["in_reply_to"] for m in gate.sent()}
    data = dashboard.panes(decisions, replies.load_drafts(), sent_ids, items, dropped, clashes)
    dashboard.build(data)
    tracelog.log("dashboard", pending=len(data["pending"]), flagged=len(data["flagged"]),
                 commitments=len(items), conflicts=len(clashes))
    for c in items:
        print(f"{c['date']} {c.get('time') or '     '} {c['what']} {c['cited']}")
    for c in clashes:
        print(f"CONFLICT {c['date']} {c['time']}: " + " vs ".join(f"{i['what']} {i['cited']}" for i in c["items"]))
    print(f"\nWrote dashboard.html and dashboard.json: {len(data['pending'])} pending, "
          f"{len(data['flagged'])} flagged, {len(items)} commitments, {len(clashes)} conflicts")


def x1(args):
    msg_id = args.msg[0]
    m, d = BY_ID[msg_id], triage.load()[msg_id]
    tracelog.log("why", msg=msg_id)
    print(f"{msg_id} from {m['from']}: {m['subject']}")
    print(f"decided by {d['by']}: {d['disposition']} - {d['reason']}")
    with open(tracelog.TRACE_FILE) as f:
        for line in f:
            e = json.loads(line)
            if msg_id in (e.get("msg"), e.get("for_msg")) or msg_id in e.get("cited", []):
                rest = {k: v for k, v in e.items() if k not in ("ts", "cap", "event") and e[k] != msg_id}
                print(f"  {e['ts']} [{e['cap']}] {e['event']} {json.dumps(rest)}")


def x2(args):
    out = replies.open_question(args.thread)
    print(f"Read {out['read']} messages in {args.thread}.")
    print(f"Open for Sam: {out.get('open_question')}")
    print(f"Due: {out.get('due')}")
    print(f"cited: {out['cited']} (quotes checked against the mail store: {'ok' if out['grounded'] else 'FAILED'})")
    for s in out.get("sources") or []:
        print(f'  {s.get("id")}: "{s.get("quote")}"')


def x3(args):
    draft_and_hold(args.msg[0], args.dry_run)


def run_all():
    with open("capabilities.json") as f:
        for cap in json.load(f)["capabilities"]:
            print(f"\n===== {cap['id']} {cap['name']}: {cap['command']}", flush=True)
            subprocess.run(cap["command"], shell=True)


CAPS = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "R6": r6, "X1": x1, "X2": x2, "X3": x3}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", choices=CAPS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--msg", nargs="+")
    parser.add_argument("--thread")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--learn", action="store_true")
    args = parser.parse_args()
    if args.all:
        run_all()
    else:
        tracelog.CAP = args.cap
        CAPS[args.cap](args)
