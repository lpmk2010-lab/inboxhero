# CAPABILITIES.md

**Student:** Prasanna M Lakshmipathy, cert-aai-2026-06-0039
**Repository:** https://github.com/lpmk2010-lab/inboxhero

Run everything through one entry point:

```
python demo.py --cap R1        # one capability
python demo.py --all           # all of them, in the order below
```

---

## The system, in one paragraph

A Python pipeline, no framework. All 100 messages are loaded from
`inbox.json`. 55 come from a fixed list of known service domains (receipts,
newsletters, alerts) and are archived by rule with no model call, unless their
text talks to an assistant. Rules also mark the emails that talk to an assistant or
ask for money or a login, so the model checks those as possible attacks. The other 45 go to the model in batches of 10, which
gives each one a disposition, a reason, and whether it is an attack or states a
standing preference. `reply` messages get a draft built from their own thread
and checked against the mail store, and a send only happens after a `y` at the
terminal. Approved preferences live in `memory.json`, every event goes to
`trace.jsonl`, and a last pass builds the dashboard from those files.

## Design choices you were asked to state

- **Messages processed: 100.** Assumptions: `id` is unique, `thread_id` groups a conversation, `timestamp` is ISO 8601 local time with no zone, `to` is one address, the owner is `sam@paperjet.io` and his sent mail is in the same file, bodies are plain text with no attachments, and `unread` does not change a decision.
- **Rule-handled: 55 of 100** never reach a model.
- **Dispositions:** `reply` (answer is already in the inbox, commits Sam to nothing; drafted, send gated), `defer` (a task or date for later; goes on the calendar), `escalate` (only Sam can decide: meetings, money, signatures, legal, hiring, press, vague requests; no draft), `archive` (nothing to do), `flag` (injection or phishing; refused, logged, reported, left in place).
- **Framework: none.** The work is a fixed sequence with one branch (rule or model) and one fork per disposition. The parts that matter, the gate and the citation check, are a few lines of plain code I want to read, and a framework's tool calling is exactly what I did not want the model to have. See Final Report Q4.
- **Retrieval: thread-walk.** Every message carries a `thread_id`, so the earlier messages in the thread are the context for a reply. That is exact and needs no index. The m008 reply needs m003 from the same thread. Cross-thread links (m038 dates the board deck in m040) are made by the commitments step, which reads all open messages at once.
- **Reversible vs irreversible.** `send` is irreversible: a file in `outbox/` is a sent email. `delete` would be irreversible because the mock store has no trash, so there is no delete action at all. `draft` and the labels `archive`, `defer`, `escalate`, `flag` are reversible: a file rewritten on the next run and a line in `decisions.json`; `inbox.json` is never written. `remember` is reversible but gated, because a stored preference changes every later run.
- **Where the gate sits.** `gate.py` holds the only two functions with a lasting effect, `send()` and `remember()`, and both call `approve()`: under `--dry-run` it prints and returns no, otherwise it needs a typed `y`, and a closed stdin counts as no. The model has no tools. Its output is JSON that code reads, and the recipient of a send is set by code (the original sender), with CC kept only if the address is in owner-approved `memory.json`. That is also the Part 6 defence: a hostile message can at worst shape a draft that Sam then reads before anything leaves.
- **Escalation line.** Only sends and preferences ask for approval; labels are automatic. Only messages whose answer is already in the inbox get a draft, so the final run asked about 2 sends (m008, m033) plus the two that preferences decide (m018, m043) instead of dozens. The trade-off: Sam writes most replies himself, and an archive can be wrong (it is a label and can be undone).
- **Standing preference honoured:** m015, Priya asks to be CC'd on everything from Hartwell & Cho. After it is approved in one process, a new process drafts the reply to m018 (Marcus Cho, SAFE amendment) with `Cc: priya@paperjet.io`. m041 (no meetings before 11:00) is stored the same way and drives X3.

## Capabilities

| id | name | tier | one-line claim |
|----|------|------|----------------|
| R1 | Zero the inbox | B | every message gets one disposition + reason, 55 by rule, none left |
| R2 | Grounded reply | B | drafts cite the earlier message and the exact words used, or nothing is drafted |
| R3 | Gate the irreversible | C | no send without a typed y, or --dry-run that only prints |
| R4 | Persistent preference | C | an approved preference survives a restart and changes the CC on m018 |
| R5 | Refuse embedded instructions | C | finds, refuses, logs and reports injections and phishing, deletes nothing |
| R6 | Dashboard | B | three panes, commitments cited, a two-message deadline, conflicts called out |
| X1 | Why did you do that? | A | the decision and every logged event for one message |
| X2 | Long thread to the open question | B | the one request in a thread still waiting on Sam, cited |
| X3 | Meeting request vs standing preference | C | declines a 9:00 slot, proposes three that respect the rule, holds the reply |

The exact command, observable outcome and evidence for each is in
`capabilities.json`. That file is the machine-readable version and is what a
marking script reads; this file is for a human. The two are kept in step.

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
