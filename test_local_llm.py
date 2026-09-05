"""
Local LM Studio connection and performance test.
Run: .\.venv\Scripts\python.exe test_local_llm.py
"""
from __future__ import annotations
import os, time, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY  = os.getenv("OPENAI_API_KEY", "lm-studio")
MODEL    = os.getenv("OPENAI_MODEL", "qwen/qwen3.5-9b")

print(f"BASE_URL : {BASE_URL}")
print(f"MODEL    : {MODEL}")
print()

from openai import OpenAI
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ── Test 1: Model listesi ──────────────────────────────────────────────────
print("=== Test 1: Available models ===")
try:
    models = client.models.list()
    for m in models.data:
        print(f"  {m.id}")
except Exception as e:
    print(f"  ERROR: {e}")
print()

# ── Test helper ───────────────────────────────────────────────────────────
def call(label: str, system: str, user: str, extra_body: dict | None = None) -> None:
    print(f"--- {label} ---")
    kwargs = dict(
        model=MODEL,
        messages=[
            *([ {"role": "system", "content": system}] if system else []),
            {"role": "user", "content": user},
        ],
        max_tokens=200,
        temperature=0.7,
    )
    if extra_body:
        kwargs["extra_body"] = extra_body

    t0 = time.time()
    try:
        r = client.chat.completions.create(**kwargs)
        elapsed = round(time.time() - t0, 2)
        content = r.choices[0].message.content
        tokens  = r.usage.completion_tokens
        print(f"  Time   : {elapsed}s")
        print(f"  Tokens : {r.usage.prompt_tokens}p + {tokens}c = {r.usage.total_tokens} total")
        print(f"  TPS    : {round(tokens/elapsed, 1)} tok/s")
        print(f"  Reply  : {content[:200]}")
        # thinking check
        if "<think>" in (content or ""):
            print("  WARNING: <think> block detected — thinking mode is ON")
        else:
            print("  OK: No <think> block")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"  ERROR after {elapsed}s: {e}")
    print()

# ── Test 2: Basit cevap ───────────────────────────────────────────────────
call(
    "Test 2: Simple reply",
    system="",
    user="Reply with exactly: hello",
)

# ── Test 3: /no_think ile ─────────────────────────────────────────────────
call(
    "Test 3: /no_think system prompt",
    system="/no_think",
    user="Reply with exactly: hello",
)

# ── Test 4: enable_thinking=False extra_body ──────────────────────────────
call(
    "Test 4: enable_thinking=False via extra_body",
    system="",
    user="Reply with exactly: hello",
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

# ── Test 5: Oyun benzeri kısa karar ───────────────────────────────────────
call(
    "Test 5: Game-like decision (name only)",
    system="You are playing a social deduction game. Follow instructions exactly.",
    user="Choose ONE player to eliminate from: Alice, Bob, Carol\nReply with only the player's name, nothing else.",
)

# ── Test 6: Uzun context ile ──────────────────────────────────────────────
long_history = "\n".join([
    f"Player{i} said: I think Player{(i+1)%8} is suspicious because of their behavior in round {i//8+1}."
    for i in range(40)
])
call(
    "Test 6: Long context (~800 tokens)",
    system="You are playing Werewolf. You are a villager.",
    user=f"Game history:\n{long_history}\n\nWho do you vote to eliminate? Reply with only: Alice, Bob, or Carol.",
)

print("=== All tests done ===")
