"""LLM packet generation."""

from __future__ import annotations

import os

from openai import OpenAI

from virucontext.europepmc import Paper
from virucontext.prompt import SYSTEM_PROMPT, user_prompt


class SummarizerNotConfigured(Exception):
    pass


def make_packet(paper: Paper, virus_of_interest: str | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-replace"):
        raise SummarizerNotConfigured(
            "No OPENAI_API_KEY in the environment. Copy .env.example to .env and add a key. "
            "Until this app is hosted with a key, use the chat that designed ViruContext."
        )

    model = os.getenv("VIRUCONTEXT_MODEL", "gpt-4o")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=4500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt(paper.meta_block(), paper.full_text, virus_of_interest),
            },
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Model returned an empty packet.")
    return text
