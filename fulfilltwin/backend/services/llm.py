from __future__ import annotations

import os
from typing import Any

from fulfilltwin.config import Settings


class LLMProvider:
    """Optional Groq/Gemini narrative layer with deterministic local fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available_models(self) -> dict[str, Any]:
        return {
            "LOCAL": ["expert-system-v1"],
            "GROQ": list(self.settings.groq_models),
            "GEMINI": list(self.settings.gemini_models),
            "keys_configured": {
                "GROQ": bool(self.settings.groq_api_key),
                "GEMINI": bool(self.settings.gemini_api_key),
            },
        }

    def generate(self, provider: str, model: str, prompt: str, local_fallback: str) -> dict[str, Any]:
        provider = (provider or "LOCAL").upper()
        if provider == "LOCAL":
            return {"provider": "LOCAL", "model": "expert-system-v1", "text": local_fallback, "fallback": False, "tokens": 0}
        try:
            if provider == "GROQ":
                return self._groq(model, prompt)
            if provider == "GEMINI":
                return self._gemini(model, prompt)
            raise ValueError(f"Unsupported provider: {provider}")
        except Exception as exc:
            return {
                "provider": "LOCAL",
                "requested_provider": provider,
                "model": "expert-system-v1",
                "text": local_fallback,
                "fallback": True,
                "warning": f"{provider} was unavailable; deterministic local brief used. {type(exc).__name__}: {exc}",
            }

    def _groq(self, model: str, prompt: str) -> dict[str, Any]:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        from groq import Groq

        client = Groq(api_key=self.settings.groq_api_key)
        completion = client.chat.completions.create(
            model=model or self.settings.groq_models[0],
            messages=[
                {
                    "role": "system",
                    "content": "You are a fulfillment-center incident commander. Preserve all numeric evidence and do not invent facts. However, write your response in a natural, conversational, and professional executive briefing tone. Explain the reasoning clearly like a human expert, rather than just reciting numbers robotically. Keep human approval explicit.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_completion_tokens=900,
        )
        tokens = getattr(completion.usage, "total_tokens", 0) if hasattr(completion, "usage") else 0
        return {
            "provider": "GROQ",
            "model": model,
            "text": completion.choices[0].message.content or "",
            "fallback": False,
            "tokens": tokens,
        }

    def _gemini(self, model: str, prompt: str) -> dict[str, Any]:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai

        client = genai.Client(api_key=self.settings.gemini_api_key)
        selected = model or self.settings.gemini_models[0]
        if hasattr(client, "interactions"):
            interaction = client.interactions.create(model=selected, input=prompt)
            text = interaction.output_text
        else:  # compatibility with earlier google-genai releases
            response = client.models.generate_content(model=selected, contents=prompt)
            text = response.text
        
        tokens = 0
        if hasattr(client, "interactions") and hasattr(interaction, "usage_metadata"):
            tokens = getattr(interaction.usage_metadata, "total_token_count", 0)
        elif not hasattr(client, "interactions") and hasattr(response, "usage_metadata"):
            tokens = getattr(response.usage_metadata, "total_token_count", 0)
            
        return {"provider": "GEMINI", "model": selected, "text": text or "", "fallback": False, "tokens": tokens}
