"""
ai_assistant.py
AI chatbot that answers business questions about the uploaded sales dataset.

Supports:
  - Google Gemini  (free tier, requires GEMINI_API_KEY)
  - OpenAI  (requires OPENAI_API_KEY)
  - Fallback rule-based engine (works with no API key — useful for demos)
"""

from __future__ import annotations

import os
import re
from typing import Generator, Optional

SYSTEM_PROMPT_TEMPLATE = """You are an expert Sales & Profit Analyst AI assistant.
You have been given a summary of a company's sales dataset below.
Answer the user's questions using ONLY the data provided.
Be concise, specific, and always back your answers with numbers from the data.
When relevant, suggest actionable business recommendations.

{context}
"""


# ─────────────────────────────────────────────
# OpenAI client
# ─────────────────────────────────────────────
def _build_openai_client():
    try:
        from openai import OpenAI  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


# ─────────────────────────────────────────────
# Google Gemini client
# ─────────────────────────────────────────────
def _build_gemini_client():
    try:
        from google import genai  # type: ignore
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        return None


# ─────────────────────────────────────────────
# Main assistant class
# ─────────────────────────────────────────────
class SalesAIAssistant:
    """
    Wraps AI chat completions (Gemini or OpenAI) with a dataset context injected
    into the system prompt. Falls back to a rule-based responder when no API key
    is configured, so the app is always demo-able.
    """

    OPENAI_MODEL = "gpt-3.5-turbo"
    GEMINI_MODEL = "gemini-2.5-flash"

    def __init__(self, context_summary: str):
        self.context        = context_summary
        self.gemini_client  = _build_gemini_client()
        self.openai_client  = _build_openai_client()
        self.history: list[dict] = []          # rolling conversation history
        self.provider       = None

        if self.gemini_client:
            self.provider = "gemini"
        elif self.openai_client:
            self.provider = "openai"

    # ── public API ─────────────────────────────
    def chat(self, user_message: str) -> str:
        """Return the full assistant reply as a string."""
        if self.provider == "gemini":
            return self._gemini_chat(user_message)
        elif self.provider == "openai":
            return self._openai_chat(user_message)
        return self._rule_based_chat(user_message)

    def stream(self, user_message: str) -> Generator[str, None, None]:
        """Yield reply tokens one by one (streaming).  Falls back to single chunk."""
        if self.provider == "gemini":
            yield from self._gemini_stream(user_message)
        elif self.provider == "openai":
            yield from self._openai_stream(user_message)
        else:
            yield self._rule_based_chat(user_message)

    def reset_history(self):
        self.history = []

    # ── Google Gemini path ─────────────────────
    def _gemini_chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        # Build full prompt with context
        system_context = SYSTEM_PROMPT_TEMPLATE.format(context=self.context)

        # Convert history to Gemini format
        prompt_parts = [system_context, "\n\n"]
        for msg in self.history[-20:]:  # keep last 20 turns
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}\n")
        prompt_parts.append("Assistant: ")

        full_prompt = "".join(prompt_parts)

        response = self.gemini_client.models.generate_content(
            model=self.GEMINI_MODEL,
            contents=full_prompt,
            config={
                'temperature': 0.3,
                'max_output_tokens': 800,
            }
        )
        reply = response.text.strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _gemini_stream(self, user_message: str) -> Generator[str, None, None]:
        self.history.append({"role": "user", "content": user_message})

        # Build full prompt with context
        system_context = SYSTEM_PROMPT_TEMPLATE.format(context=self.context)

        # Convert history to Gemini format
        prompt_parts = [system_context, "\n\n"]
        for msg in self.history[-20:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}\n")
        prompt_parts.append("Assistant: ")

        full_prompt = "".join(prompt_parts)

        response = self.gemini_client.models.generate_content_stream(
            model=self.GEMINI_MODEL,
            contents=full_prompt,
            config={
                'temperature': 0.3,
                'max_output_tokens': 800,
            }
        )

        collected = []
        for chunk in response:
            if chunk.text:
                collected.append(chunk.text)
                yield chunk.text

        self.history.append({"role": "assistant", "content": "".join(collected)})

    # ── OpenAI path ────────────────────────────
    def _system_message(self) -> dict:
        return {
            "role": "system",
            "content": SYSTEM_PROMPT_TEMPLATE.format(context=self.context),
        }

    def _openai_chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        messages = [self._system_message()] + self.history[-20:]   # keep last 20 turns

        response = self.openai_client.chat.completions.create(
            model=self.OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )
        reply = response.choices[0].message.content.strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _openai_stream(self, user_message: str) -> Generator[str, None, None]:
        self.history.append({"role": "user", "content": user_message})
        messages = [self._system_message()] + self.history[-20:]

        stream = self.openai_client.chat.completions.create(
            model=self.OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            stream=True,
        )
        collected = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            collected.append(delta)
            yield delta

        self.history.append({"role": "assistant", "content": "".join(collected)})

    # ── Rule-based fallback ─────────────────────
    def _rule_based_chat(self, user_message: str) -> str:
        """
        Keyword-driven responder — works without any API key.
        Parses the context summary string to extract answers.
        """
        q = user_message.lower()

        # ── best / worst month ──────────────────
        if any(w in q for w in ("highest profit", "best profit", "most profit")):
            m = re.search(r"Best profit month\s*:\s*(.+)", self.context)
            return (
                f"The month with the **highest profit** was **{m.group(1).strip()}**."
                if m else "Could not determine the best profit month from the data."
            )

        if any(w in q for w in ("highest revenue", "best revenue", "most revenue", "best month")):
            m = re.search(r"Best revenue month\s*:\s*(.+)", self.context)
            return (
                f"The month with the **highest revenue** was **{m.group(1).strip()}**."
                if m else "Could not determine the best revenue month from the data."
            )

        if any(w in q for w in ("lowest", "worst month", "least revenue")):
            m = re.search(r"Lowest revenue month\s*:\s*(.+)", self.context)
            return (
                f"The month with the **lowest revenue** was **{m.group(1).strip()}**."
                if m else "Could not determine the worst revenue month from the data."
            )

        # ── top product ─────────────────────────
        if any(w in q for w in ("top product", "best product", "most sold", "highest selling", "sells the most")):
            m = re.search(r"Top 5 Products.*?\n\s+(\S[^\n:]+):", self.context)
            if not m:
                m = re.search(r"---\n\s+(.+?):", self.context)
            return (
                f"The top-selling product by revenue is **{m.group(1).strip()}**."
                if m else "Could not identify the top product from the data."
            )

        # ── top customer ────────────────────────
        if any(w in q for w in ("top customer", "best customer", "biggest customer")):
            m = re.search(r"Top 5 Customers.*?\n\s+(\S[^\n:]+):", self.context)
            return (
                f"The top customer by revenue is **{m.group(1).strip()}**."
                if m else "Could not identify the top customer from the data."
            )

        # ── total revenue / profit ───────────────
        if re.search(r"total revenue", q):
            m = re.search(r"Total revenue\s*:\s*(\S+)", self.context)
            return f"Total revenue across the entire dataset is **{m.group(1)}**." if m else "N/A"

        if re.search(r"total profit", q):
            m = re.search(r"Total profit\s*:\s*(\S+)", self.context)
            return f"Total profit across the entire dataset is **{m.group(1)}**." if m else "N/A"

        if re.search(r"profit margin", q):
            m = re.search(r"Profit margin\s*:\s*(\S+)", self.context)
            return f"The overall profit margin is **{m.group(1)}**." if m else "N/A"

        # ── monthly breakdown ───────────────────
        if any(w in q for w in ("monthly", "each month", "by month", "month by month", "trend")):
            months_block = re.search(
                r"--- Monthly Snapshot ---(.*?)---", self.context, re.DOTALL
            )
            if months_block:
                return (
                    "**Monthly breakdown:**\n```\n"
                    + months_block.group(1).strip()
                    + "\n```"
                )

        # ── revenue change between months ───────
        if any(w in q for w in ("revenue change", "why did revenue", "revenue drop", "revenue increase")):
            months_block = re.search(
                r"--- Monthly Snapshot ---(.*?)---", self.context, re.DOTALL
            )
            if months_block:
                return (
                    "Here is the month-over-month revenue data. "
                    "Differences in revenue between months can stem from seasonality, "
                    "promotional campaigns, or shifts in product mix:\n"
                    "```\n" + months_block.group(1).strip() + "\n```\n\n"
                    "_Note: For deeper causal analysis, upload an OpenAI API key._"
                )

        # ── generic fallback ────────────────────
        return (
            "I can answer questions about:\n"
            "- Best/worst revenue or profit **months**\n"
            "- **Top products** and **top customers**\n"
            "- **Total revenue**, profit, and margin\n"
            "- **Monthly trends** and revenue changes\n\n"
            "For free-form analysis, add your `OPENAI_API_KEY` to `.env`."
        )
