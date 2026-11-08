"""Minimal LLM client. Temporary until B's shared client exists.

Config from environment (see .env.example):
  LLM_PROVIDER = anthropic | openai | deepseek
  LLM_MODEL    = model name
  LLM_API_KEY  = key
"""

import os


class AnthropicLLM:
    def __init__(self, model: str, api_key: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete_json(self, system: str, user: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")


class OpenAILLM:
    def __init__(self, model: str, api_key: str):
        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def complete_json(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content


class DeepSeekLLM:
    """DeepSeek is OpenAI-compatible; only the base_url differs."""

    def __init__(self, model: str, api_key: str):
        import openai

        self.client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model

    def complete_json(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content


class FileLLM:
    """Returns a saved JSON answer. For tests and offline demos."""

    def __init__(self, path: str):
        self.path = path

    def complete_json(self, system: str, user: str) -> str:
        with open(self.path, encoding="utf-8") as f:
            return f.read()


def make_llm():
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    model = os.environ["LLM_MODEL"]
    key = os.environ["LLM_API_KEY"]
    if provider == "anthropic":
        return AnthropicLLM(model, key)
    if provider == "openai":
        return OpenAILLM(model, key)
    if provider == "deepseek":
        return DeepSeekLLM(model, key)
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")
