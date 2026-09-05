from __future__ import annotations
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import litellm
litellm.suppress_debug_info = True

# Bedrock credentials — litellm picks these up automatically from env
if os.getenv("AWS_ACCESS_KEY_ID"):
    os.environ["AWS_ACCESS_KEY_ID"]     = os.getenv("AWS_ACCESS_KEY_ID")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
    os.environ["AWS_DEFAULT_REGION"]    = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

_raw_model    = os.getenv("DEEPSEEK_MODEL") or os.getenv("BEDROCK_MODEL") or os.getenv("TOGETHER_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_base_url     = os.getenv("OPENAI_BASE_URL")
_together_key = os.getenv("TOGETHER_AI_KEY")
_deepseek_key = os.getenv("DEEPSEEK_API_KEY")

if _together_key:
    os.environ["TOGETHERAI_API_KEY"] = _together_key

if _deepseek_key:
    os.environ["DEEPSEEK_API_KEY"] = _deepseek_key

# Model prefix logic
if _deepseek_key and not _raw_model.startswith("deepseek/"):
    MODEL = f"deepseek/{_raw_model}"
elif _base_url and not _raw_model.startswith(("openai/", "bedrock/", "together_ai/")):
    # LM Studio / local OpenAI-compatible server
    MODEL = f"openai/{_raw_model}"
elif _together_key and not _raw_model.startswith(("openai/", "bedrock/", "together_ai/")):
    MODEL = f"together_ai/{_raw_model}"
else:
    MODEL = _raw_model

# Per-call metrics accumulated here; reset each game by the engine
_call_log: list[dict] = []


def reset_call_log() -> None:
    _call_log.clear()


def get_call_log() -> list[dict]:
    return list(_call_log)


def call_llm(caller: str, prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    t0 = time.time()
    kwargs = {"model": MODEL, "messages": messages}
    if _base_url:
        kwargs["api_base"] = _base_url
        kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}
    elif _deepseek_key:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    response = litellm.completion(**kwargs)
    elapsed = round(time.time() - t0, 2)

    content = response.choices[0].message.content.strip()
    usage = response.usage

    _call_log.append({
        "caller": caller,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "elapsed_sec": elapsed,
        "system": system,
        "prompt": prompt,
        "response": content,
    })

    return content
