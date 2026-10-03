# Roll number: cert-aai-2026-06-0039
KNOWN_SENDERS = [
    "dropbox.com", "slack.com", "vercel.com", "1password.com", "amazon.com", "netflix.com",
    "google.com", "apple.com", "spotify.com", "coursera.org", "lyft.com", "github.com",
    "figma.com", "bluebottlecoffee.com", "pagerduty.com", "producthunt.com", "sentry.io",
    "postmarkapp.com", "datadoghq.com", "openai.com", "notion.so", "cloudflare.com",
    "pragmaticengineer.com", "robinhood.com", "mailchimp.com", "zoom.us", "digitalocean.com",
    "twitter.com", "medium.com", "substack.com", "stripe.com", "intercom.io", "chase.com",
    "instacart.com", "swiggy.in", "ramp.com", "linkedin.com", "doordash.com",
    "hackernewsletter.com", "uber.com", "todoist.com", "grammarly.com", "united.com",
    "namecheap.com", "calendly.com",
]

# a From line is easy to fake, so anything that talks to an assistant goes to the model even from a known sender
TRIPWIRE = ("assistant", "ai agent", "instruction")
MONEY_OR_LOGIN = ("wire", "remit", "bank", "routing", "password", "credentials")


def _has(msg, words):
    text = (msg["subject"] + " " + msg["body"]).lower()
    return any(w in text for w in words)


def talks_to_assistant(msg):
    return _has(msg, TRIPWIRE)


def asks_for_money_or_login(msg):
    return _has(msg, MONEY_OR_LOGIN)


def rule_decision(msg):
    domain = msg["from"].split("@")[1]
    if talks_to_assistant(msg):
        return None
    if any(domain == d or domain.endswith("." + d) for d in KNOWN_SENDERS):
        return {"disposition": "archive", "reason": f"automated mail from {domain}, nothing to answer"}
    return None
