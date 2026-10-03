# inboxHero

Repository: https://github.com/lpmk2010-lab/inboxhero

Roll number: cert-aai-2026-06-0039

inboxHero takes the 100 messages in `inbox.json` from unread to decided. Every
message gets one disposition and a reason, the obvious ones by rule, the rest
by a model. It drafts replies only from what is in the inbox, never sends
without a yes from the owner, remembers the preferences the owner approves,
refuses the messages that try to give it orders, and renders a three-pane
dashboard. No framework. Every capability runs as `python demo.py --cap <id>`
and is listed in `CAPABILITIES.md` and `capabilities.json`.

## Running it

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # fill in LLM_API_KEY
source .venv/bin/activate
python demo.py --cap R1     # one capability
python demo.py --all        # every command in capabilities.json, in order
```

Commands run in the order of the manifest, because later ones read what
earlier ones wrote (`decisions.json`, `drafts/`, `memory.json`). If
`decisions.json` is missing, any capability that needs it runs the triage
first. To start from nothing, delete `decisions.json`, `drafts/`, `outbox/`,
`memory.json` and `trace.jsonl`.

## Architecture

```
inbox.json -> rules.py --known automated sender--> archive (no model)
                  |
                  +--everything else--> triage.py -> llm.py -> model
                                            |
                                     decisions.json
                     reply: replies.py drafts from the thread -> gate.py -> outbox/
                     escalate / defer: dashboard Pending, commitments.py
                     flag: refusal logged, reported, left in the inbox
```

- `config.py` - the only file that knows the provider. Base URL, key and model come from `.env`. `chat()` waits out a 429 and retries a broken-JSON 400.
- `llm.py` - `ask()`, the one place email text reaches a model (see Final Report 2).
- `mailstore.py` - loads `inbox.json`, walks a thread, and checks citations (`grounded()`).
- `rules.py` - the router: known automated senders are archived with no model call. It also marks emails that talk to an assistant or ask for money or a login, so triage checks those as possible attacks.
- `triage.py` - one disposition per message, the model in batches of 10, writes `decisions.json`.
- `replies.py` - grounded drafts (R2) and the open question of a thread (X2).
- `gate.py` - the two actions that need a human: sending, and storing a preference.
- `memory.py` - copied unchanged from Assignment 5, stores preferences in `memory.json`.
- `commitments.py` - dates and deadlines with citations, and same-time conflicts.
- `dashboard.py` - `dashboard.json` and `dashboard.html`.
- `tracelog.py` - appends one JSON line per event to `trace.jsonl`, tagged with the capability.
- `demo.py` - one function per capability and the `--cap` / `--all` interface.

## Model

Groq's free tier, `openai/gpt-oss-120b`, through the `openai` SDK. The PDF
suggests a local model while building; my laptop has a 4 GB GPU, so I
developed against the same Groq model and switched to `openai/gpt-oss-20b`
through `MODEL_NAME` for checks that only needed the code path to run, once
the 120b daily token cap ran out. The free tier allows 8,000 tokens a minute,
which is why triage sends 10 messages per call and `chat()` pauses 2 seconds
before each call and sleeps for Groq's `retry-after` on a 429.

## Disposition vocabulary

- `reply` - someone asks for information that is already in the inbox and answering commits Sam to nothing new. A draft is written; sending waits for Sam.
- `defer` - Sam has a task or date to keep later. It goes on the commitments calendar.
- `escalate` - only Sam can decide: a meeting, money, a signature, legal, hiring, press, or a request too vague to act on. Nothing is drafted; it goes to Pending.
- `archive` - nothing to do: automated mail, FYI, resolved threads, Sam's own sent mail, stated preferences.
- `flag` - an attack: an injection aimed at the assistant or phishing aimed at Sam. Refused, logged, reported, left in place.

Archive and the others are a label in `decisions.json`. `inbox.json` is never written to.

## Reversible, irreversible, and the gate

Reversible: `draft` (a file in `drafts/`, rewritten on the next run), and the
labels `archive`, `defer`, `escalate`, `flag` (a line in `decisions.json`;
change it and the message is back). `remember` is reversible too, since an
entry in `memory.json` can be deleted, but it is gated anyway because it
changes every later run without anyone looking.

Irreversible: `send`, a file in `outbox/` is a sent email. `delete` would be
irreversible because the mock store has no trash, so inboxHero has no delete
action at all; the most it does to a message is label it.

`gate.send()` prints the exact JSON it would write to `outbox/<id>.json` and
asks `Send it? [y/n]`. Only `y` writes the file. `--dry-run` prints the same
and writes nothing. No terminal (stdin closed) counts as no, and a message
already in `outbox/` is never sent twice. `gate.remember()` does the same
before a preference is stored. Every gated decision goes to `trace.jsonl` as a
`gate` event with what was proposed, what the human answered, and the result.

Where I drew the line: the model may archive, defer, escalate and flag on its
own, because all of those are labels. It may only propose a send, and only for
messages whose answer is already in the inbox. Anything that commits Sam's
time, money or name is escalated with no draft. In the final run that left
2 sends to approve out of 100 messages (m008 and m033), plus the two that
standing preferences decide (m018's CC and m043's later slot). What I traded away: Sam still writes
most replies himself, and a wrongly archived message is possible; it is a
label and can be put back, and the 55 rule-archived ones come only from a
fixed list of service domains.

## Retrieval

Thread-walk. To draft a reply, `mailstore.thread_before()` takes every earlier
message with the same `thread_id`. The drafter must return the exact words it
relied on for each message it cites, and `grounded()` checks that every cited
id was one it was given and every quote is really in that message. If not, or
if the model says the facts are missing, nothing is drafted and the reason is
logged. Cross-thread links (the board deck in m040 dated by the review in m038)
are made by the commitments step, which sees all open messages at once.

## Data assumptions

- 100 messages, all processed. Keys as in the PDF; `id` unique.
- `timestamp` is ISO 8601 local time with no zone, so string order is time order.
- The owner is `sam@paperjet.io`. Messages from that address are Sam's own sent mail kept in the same file.
- `to` is one address. There are no attachments; "attached" means a portal link.
- `unread` is not used for decisions; an inbox is zeroed whether read or not.

## What I found while building it

**m039 is the hard injection.** It comes from Sam's own address and asks for
"autonomous mode", so in a batch of 15 the model sometimes archived it as "a
user-set standing preference". Three changes made all four injections (m017,
m024, m039, m047) stick in 3 of 3 runs: batches of 10, a line saying a From
line can be forged, and telling the model which emails in the batch talk to an
assistant. That last one comes from `rules.talks_to_assistant()`, a fact my
code computes, not text from the email.

**Phishing slipped the same way.** In my first final run only m045 was
flagged: the model left m021 out of its batch answer altogether (the fallback
escalated it) and escalated m023, the wire request under Priya's name from
`paperjet.co`. Nothing would have been done for either, but neither was
reported. The fix was the same pattern: `rules.asks_for_money_or_login()`
marks emails that mention a wire, a bank or a password as "check as possible
phishing", and a message missing from a batch answer is asked about again on
its own before falling back. The rerun flagged all 7.

**The drafter invents decisions.** For m012 ("that thing we talked about after
the standup") the first drafter wrote "I'm on it and will have the thing
sorted out before the call", citing only m012 itself, which passed the citation
check. In the first final run triage also called two meeting messages `reply`,
and the drafter, told not to accept anything, wrote "Wednesday at 2 pm doesn't
work for me" to Raghav (m013) with three made-up slots. The drafter now treats
anything that needs Sam to accept, decline or propose, unless a stored
preference settles it, as missing facts, and m012 comes back as "not in the
inbox". It still slips in an "I'll" now and then (the m018 reply says "I'll
review clause 4 and plan to sign"); a draft that quotes only the message it
answers is something `grounded()` cannot judge, and the gate is where Sam
catches it.

**"I'm CC'd" became Sam.** The first stored version of m015 was Priya's
sentence word for word, and the drafter, writing as Sam, put sam@paperjet.io in
CC. Preferences are now stored in the third person with addresses.

**Commitments came back short.** Groq caps a completion at 3,072 tokens unless
told otherwise, and the model spent about 2,400 of them reasoning, so the JSON
list was cut to 2 or 3 entries. `max_completion_tokens=5000` and sending only
the messages that still need Sam (reply, defer, escalate) fixed it.

**The model cannot count weekdays.** "by Friday" in an email sent on Monday 7
September came back as Sunday the 13th, and putting a calendar in the prompt
did not help. When the quote that dates a commitment names a weekday but no day
of the month, `commitments.resolve()` counts forward from the day the email was
sent. "Tuesday the 15th" keeps the model's date.

**A two-message commitment needs a reason to exist.** The board deck (m040,
"two days before the board review") was first cited to m040 alone. Each
commitment now has a `date_source` whose quote must contain a day, a number or
a weekday, so the model has to quote m038 ("set for the 18th") and the entry
cites both.

## Final Report

**1. What did you refuse to automate?**

m010, Aria from Northwind VC asking "Does Tuesday the 15th at 3:00pm work on
your side?". It looks like the easiest reply in the inbox, one line saying
yes, and it is an investor, so a fast answer seems helpful. inboxHero escalates
it with no draft, because accepting commits Sam's time, and in this inbox that
slot is already taken: m061, a dental appointment the same Tuesday at 3:00 PM,
which the dashboard shows as a CONFLICT. My line is that anything that spends
Sam's time, money or signature is his call however simple the reply looks, so
the system's job is to put the clash in front of him, not to pick for him.

**2. Where does untrusted text enter your system?**

Email text reaches a model in one function, `llm.ask()`, and only as a JSON
list in the user turn; the system turn holds my instructions and the
preferences the owner approved, nothing from the inbox. The model has no tools.
It returns JSON that my code reads into fixed fields, a disposition outside the
vocabulary becomes `escalate`, and a flagged message never yields a preference.
The only lasting effects are `gate.send()` and `gate.remember()`, both behind a
typed `y`; the recipient of a send is set by code to the original sender, CC is
kept only if the address is already in `memory.json`, and there is no forward
or delete function to reach. To make inboxHero act for them an attacker has to
get Sam to type `y` under a proposal that shows the full recipients and body,
or get write access to `memory.json` or the code, which an email cannot give.

**3. Who is accountable when it sends the wrong thing?**

Sam is, because nothing reaches `outbox/` unless he typed `y` under the exact
file that would be written, the same as signing a letter an assistant put in
front of him; I am answerable for whether that proposal was faithful to the
inbox. Tracing it back is one command, `python demo.py --cap X1 --msg <id>`,
which prints from `trace.jsonl` who decided the disposition (rule or model) and
why, which messages the drafter read, the ids and quotes it cited, and the gate
event with the proposal, Sam's answer and the result. A wrong fact shows up as a
quote that was checked against the mail store, a wrong recipient can only come
from the original sender or a `memory.json` entry whose approval is its own
gate event, and every `outbox/` file carries `in_reply_to` and `cited`.

**4. Name your own machinery.**

The agents are four prompts with one job each, all called through
`llm.ask()`: triage (`triage.TASK`), the drafter (`replies.DRAFT_TASK`), the
commitments reader (`commitments.TASK`) and the open-question reader
(`replies.OPEN_TASK`). The tasks are the capability functions in `demo.py`
(`r1` to `x3`), each with one command and an output someone can check, and the
crew is the order they run in, `--all` reading `capabilities.json`, with files
as the hand-off (`decisions.json`, `drafts/`, `memory.json`). The router is
`rules.rule_decision()`, which picks rule or model, and then the disposition,
which picks draft, Pending, calendar or refusal. The piece a framework would
have given me that I built myself is the human-in-the-loop step: CrewAI has a
human-input flag, I wrote `gate.approve()`. Here a framework would have hurt,
because its natural shape is a model calling tools, and the safety of this
system rests on the model having no tools at all, with the two lasting actions
reachable only from code behind the gate.
