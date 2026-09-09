"""Where answers can come from: the places, not the models.

Which models each provider has is asked of the provider at runtime, and lives
in `domain/catalogue.py`. This file used to hold a hardcoded model list with
hardcoded prices, and by the time anyone read it one of those prices
understated a rate by three times (D52). A place changes about once a year; a
price list changes weekly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProviderId(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Provider:
    """One place answers can come from.

    `wire` names the request format, not the vendor. Everything except
    Anthropic speaks the OpenAI chat completions shape, including Gemini's
    compatibility endpoint, OpenRouter, Ollama and LM Studio, so one adapter
    serves all of them and the differences live here as data.
    """

    id: ProviderId
    label: str
    wire: str
    base_url: str
    env_var: str
    needs_key: bool = True


PROVIDERS: tuple[Provider, ...] = (
    Provider(ProviderId.ANTHROPIC, "Anthropic", "anthropic", "https://api.anthropic.com", "ANTHROPIC_API_KEY"),
    Provider(ProviderId.OPENAI, "OpenAI", "openai", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    Provider(
        ProviderId.GEMINI,
        "Google Gemini",
        "openai",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "GEMINI_API_KEY",
    ),
    Provider(ProviderId.OPENROUTER, "OpenRouter", "openai", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    # The only provider that needs no key and reaches no network. With it
    # selected, the privacy line in the README loses its exception clause.
    Provider(ProviderId.OLLAMA, "Ollama", "openai", "http://localhost:11434/v1", "", needs_key=False),
    # A base URL the user supplies: a local server, a proxy, or the stub the
    # end to end chat test runs against.
    Provider(ProviderId.CUSTOM, "Custom endpoint", "openai", "", "CUSTOM_API_KEY", needs_key=False),
)

DEFAULT_PROVIDER_ID = "openrouter"

# The router that picks among whatever is free today, so a first question works
# as soon as a key is in. Which models exist beyond this one is asked of the
# provider rather than listed here (D52).
DEFAULT_MODEL_ID = "openrouter/free"


def runs_locally(provider: Provider) -> bool:
    """True when choosing this provider means nothing leaves the machine at all.

    The README's privacy sentence has an exception clause for the answer call.
    With a local provider selected there is no call to except, and the settings
    screen says so rather than leaving the user to work it out.
    """
    return provider.base_url.startswith(("http://localhost", "http://127.0.0.1"))
