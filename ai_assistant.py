"""
ai_assistant.py
AI chatbot that answers business questions about retail & e-commerce sales data.

Supports:
  - Google Gemini  (free tier, requires GEMINI_API_KEY)
  - OpenAI  (requires OPENAI_API_KEY)
  - Fallback rule-based engine (works with no API key)
"""

from __future__ import annotations

import os
import re
from typing import Generator, Optional

SYSTEM_PROMPT_TEMPLATE = """You are RetailBrain AI — an expert Business Analytics & Management Assistant.
You specialize in retail, gym, coaching, and service business analytics.
You have been given a summary of the business data below.

Answer questions using ONLY the data provided. Be specific, actionable, and business-focused.
Provide practical recommendations tailored to the business type and current performance.

Key areas you can help with:
- Revenue and profit analysis
- Product/service performance optimization
- Inventory management advice
- Customer insights and retention
- Pricing strategies
- Business growth recommendations
- Operational efficiency tips

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
    is configured.
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
        Enhanced business-focused keyword-driven responder.
        Provides helpful insights without requiring API keys.
        """
        q = user_message.lower()

        # ── business insights ───────────────────────
        if any(w in q for w in ("insight", "recommendation", "advice", "improve", "grow", "help")):
            # Extract basic metrics from context
            revenue_match = re.search(r"Total Revenue:\s*\$?([0-9,]+\.?\d*)", self.context)
            profit_match = re.search(r"Total Profit:\s*\$?([0-9,]+\.?\d*)", self.context)
            margin_match = re.search(r"Profit Margin:\s*([0-9.]+)%", self.context)

            insights = ["**Business Insights & Recommendations:**\n"]

            if margin_match:
                margin = float(margin_match.group(1))
                if margin < 10:
                    insights.append("🔍 **Low Profit Margin Alert** - Consider reviewing your pricing strategy or reducing costs")
                elif margin > 25:
                    insights.append("💚 **Healthy Profit Margins** - Great job! Focus on scaling successful products")
                else:
                    insights.append("📊 **Moderate Profit Margins** - Look for opportunities to optimize pricing")

            insights.extend([
                "📈 **Growth Strategies:**",
                "- Track your top-performing products and promote them more",
                "- Monitor inventory levels to avoid stockouts",
                "- Analyze customer buying patterns for upselling opportunities",
                "- Consider seasonal promotions during slow periods",
                "",
                "🎯 **Operational Tips:**",
                "- Set up low-stock alerts for key products",
                "- Review and optimize your pricing regularly",
                "- Focus on high-margin products",
                "- Track daily/weekly sales patterns"
            ])

            return "\n".join(insights)

        # ── inventory management ────────────────────
        if any(w in q for w in ("inventory", "stock", "reorder", "out of stock", "low stock")):
            return (
                "📦 **Inventory Management Tips:**\n\n"
                "**Stock Optimization:**\n"
                "- Set minimum stock levels for each product\n"
                "- Monitor your top-selling items closely\n"
                "- Track seasonal demand patterns\n"
                "- Consider ABC analysis (A=high value, C=low value)\n\n"
                "**Reorder Strategy:**\n"
                "- Calculate lead times for suppliers\n"
                "- Set up automated low-stock alerts\n"
                "- Review stock levels weekly\n"
                "- Focus on fast-moving inventory\n\n"
                "_Use the Inventory tab to monitor stock levels and set alerts._"
            )

        # ── pricing strategy ────────────────────────
        if any(w in q for w in ("pricing", "price", "margin", "profit margin", "cost")):
            margin_match = re.search(r"Profit Margin:\s*([0-9.]+)%", self.context)

            response = "💰 **Pricing Strategy Guide:**\n\n"

            if margin_match:
                margin = float(margin_match.group(1))
                response += f"**Current Margin: {margin:.1f}%**\n\n"

                if margin < 15:
                    response += "🚨 **Action Needed:** Your margins are below industry average\n"
                elif margin > 30:
                    response += "🎯 **Excellent Margins:** You're pricing effectively\n"
                else:
                    response += "📊 **Good Margins:** Consider optimization opportunities\n"

            response += (
                "\n**Pricing Best Practices:**\n"
                "- Research competitor pricing regularly\n"
                "- Test price increases on low-elasticity items\n"
                "- Bundle complementary products\n"
                "- Consider value-based pricing for services\n"
                "- Monitor customer price sensitivity\n\n"
                "**Margin Improvement:**\n"
                "- Negotiate better supplier terms\n"
                "- Focus on high-margin products\n"
                "- Reduce operational costs\n"
                "- Add premium service options"
            )

            return response

        # ── customer retention ──────────────────────
        if any(w in q for w in ("customer", "retention", "loyalty", "repeat", "churn")):
            return (
                "👥 **Customer Retention Strategies:**\n\n"
                "**Build Loyalty:**\n"
                "- Implement a rewards program\n"
                "- Send personalized follow-up messages\n"
                "- Track customer purchase frequency\n"
                "- Offer exclusive member discounts\n\n"
                "**Improve Experience:**\n"
                "- Collect and act on customer feedback\n"
                "- Ensure consistent service quality\n"
                "- Reduce wait times and friction\n"
                "- Train staff on customer service\n\n"
                "**Re-engagement:**\n"
                "- Identify customers who haven't purchased recently\n"
                "- Send targeted offers to win them back\n"
                "- Create seasonal promotions\n"
                "- Use email marketing for updates"
            )

        # ── sales performance ───────────────────────
        if any(w in q for w in ("sales", "performance", "revenue", "growth", "increase")):
            revenue_match = re.search(r"Total Revenue:\s*\$?([0-9,]+\.?\d*)", self.context)

            response = "📈 **Sales Performance Analysis:**\n\n"

            if revenue_match:
                revenue = revenue_match.group(1)
                response += f"**Current Revenue: ${revenue}**\n\n"

            response += (
                "**Sales Growth Tactics:**\n"
                "- Analyze your best-selling products and push them more\n"
                "- Cross-sell related items to existing customers\n"
                "- Create urgency with limited-time offers\n"
                "- Optimize your product placement and displays\n\n"
                "**Performance Tracking:**\n"
                "- Monitor daily/weekly sales trends\n"
                "- Track average transaction value\n"
                "- Identify peak sales periods\n"
                "- Set monthly revenue targets\n\n"
                "**Revenue Optimization:**\n"
                "- Focus marketing on high-value customers\n"
                "- Increase order frequency vs. order size\n"
                "- Test different pricing strategies\n"
                "- Expand successful product lines"
            )

            return response

        # ── Original basic responses ────────────────
        if any(w in q for w in ("highest profit", "best profit", "most profit")):
            if "Top Products:" in self.context:
                products_section = self.context.split("Top Products:")[1].split("\n")[1:4]
                if products_section:
                    return f"Based on your sales data, your **top profit-generating products** are:\n" + "\n".join(f"- {p.strip()}" for p in products_section if p.strip())
            return "To see your most profitable products, check the Analytics tab for detailed insights."

        if any(w in q for w in ("top product", "best product", "most sold", "highest selling")):
            if "Top Products:" in self.context:
                products_section = self.context.split("Top Products:")[1].split("\n")[1]
                if products_section:
                    return f"Your **top-performing product** is: {products_section.strip()}"
            return "Check your Products & Services tab or Analytics section to see your best sellers."

        if re.search(r"total revenue", q):
            revenue_match = re.search(r"Total Revenue:\s*(\$?[0-9,]+\.?\d*)", self.context)
            if revenue_match:
                return f"Your **total revenue** is **{revenue_match.group(1)}**."
            return "You can view your total revenue in the Dashboard or Analytics section."

        if re.search(r"total profit", q):
            profit_match = re.search(r"Total Profit:\s*(\$?[0-9,]+\.?\d*)", self.context)
            if profit_match:
                return f"Your **total profit** is **{profit_match.group(1)}**."
            return "Check the Dashboard for your current profit figures."

        if re.search(r"profit margin", q):
            margin_match = re.search(r"Profit Margin:\s*([0-9.]+)%", self.context)
            if margin_match:
                margin = float(margin_match.group(1))
                assessment = "excellent" if margin > 25 else "good" if margin > 15 else "needs improvement"
                return f"Your **profit margin is {margin:.1f}%** - this is {assessment} for most businesses."
            return "You can find your profit margin analysis in the Dashboard section."

        # ── Enhanced generic help ───────────────────
        return (
            "🤖 **I'm your RetailBrain AI assistant!** I can help with:\n\n"
            "**Business Analytics:**\n"
            "- Revenue and profit analysis\n"
            "- Product performance insights\n"
            "- Sales trends and patterns\n\n"
            "**Business Growth:**\n"
            "- Pricing strategy advice\n"
            "- Inventory optimization tips\n"
            "- Customer retention strategies\n\n"
            "**Quick Questions to Try:**\n"
            "- \"How can I improve my business?\"\n"
            "- \"What's my profit margin?\"\n"
            "- \"Give me inventory management tips\"\n"
            "- \"How can I increase sales?\"\n\n"
            "_For advanced AI analysis, add your API key in the sidebar._"
        )
