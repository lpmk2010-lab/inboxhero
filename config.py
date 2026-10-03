# Roll number: cert-aai-2026-06-0039
# provider-specific bit lives here - everything comes from .env, swap it to switch providers
import os
import time
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError, RateLimitError

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

# the SDK retries a 429 on its own without printing anything, so turn that off and do it in chat()
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    max_retries=0,
)


def chat(**kwargs):
    for _ in range(5):
        time.sleep(2)
        try:
            return client.chat.completions.create(model=MODEL_NAME, **kwargs)
        except RateLimitError as e:
            wait = float(e.response.headers.get("retry-after", 10))
            print(f"Rate limit hit, waiting {wait:.0f}s ...", flush=True)
            time.sleep(wait)
        except BadRequestError as e:
            if e.code != "json_validate_failed":
                raise
            print("Model returned broken JSON, asking again ...", flush=True)
    return client.chat.completions.create(model=MODEL_NAME, **kwargs)
