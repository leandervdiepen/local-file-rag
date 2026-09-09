"""Which answer models exist, and what each one can actually do.

Every answer this app gives is grounded in page images, so a model that
cannot see is not a slower option, it is a wrong one. A text-only model
handed a question about a chart will answer confidently from the question
alone, which is worse than an error. `sees_images` is therefore a hard
filter on what the settings screen may offer, not a badge next to a name.

Prices are dollars per million tokens, recorded with the date they were
read, because they move and a stale price shown in the chat footer is a
number this app made up.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PRICES_READ_ON = "2026-09-07"


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


@dataclass(frozen=True)
class AnswerModel:
    """One model on one provider, with what it costs and whether it can see."""

    provider: ProviderId
    id: str
    label: str
    sees_images: bool
    usd_per_m_input: float
    usd_per_m_output: float
    context_tokens: int

    @property
    def is_free(self) -> bool:
        return self.usd_per_m_input == 0.0 and self.usd_per_m_output == 0.0


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

MODELS: tuple[AnswerModel, ...] = (
    AnswerModel(ProviderId.ANTHROPIC, "claude-opus-5", "Claude Opus 5", True, 0.0, 0.0, 200_000),
    AnswerModel(ProviderId.OPENROUTER, "openrouter/free", "OpenRouter free", True, 0.0, 0.0, 200_000),
    AnswerModel(ProviderId.OPENROUTER, "google/gemini-3.8-flash", "Gemini 3.8 Flash", True, 0.75, 3.75, 1_048_576),
    AnswerModel(
        ProviderId.OPENROUTER,
        "deepseek/deepseek-v4-flash-vision-exp",
        "DeepSeek V4 Flash Vision",
        True,
        0.22,
        0.22,
        128_000,
    ),
    AnswerModel(ProviderId.GEMINI, "gemini-3.8-flash", "Gemini 3.8 Flash", True, 0.75, 3.75, 1_048_576),
    # Local, so free, and a vision model because a text-only one would answer
    # from the question alone (D37). The user installs and pulls it themselves.
    AnswerModel(ProviderId.OLLAMA, "qwen2.5vl:7b", "Qwen2.5 VL 7B, on this Mac", True, 0.0, 0.0, 128_000),
)

DEFAULT_MODEL_ID = "openrouter/free"


def provider_for(model: AnswerModel) -> Provider:
    return next(p for p in PROVIDERS if p.id is model.provider)


def selectable_models() -> tuple[AnswerModel, ...]:
    """The models the settings screen may offer.

    A model that cannot see page images cannot answer this app's questions,
    so it never reaches the list rather than being offered and failing later.
    """
    return tuple(m for m in MODELS if m.sees_images)


def find_model(model_id: str) -> AnswerModel | None:
    return next((m for m in MODELS if m.id == model_id), None)


def cost_usd(model: AnswerModel, input_tokens: int, output_tokens: int) -> float:
    """Dollars for one exchange, from the prices recorded above."""
    return (input_tokens * model.usd_per_m_input + output_tokens * model.usd_per_m_output) / 1_000_000


def runs_locally(provider: Provider) -> bool:
    """True when choosing this provider means nothing leaves the machine at all.

    The README's privacy sentence has an exception clause for the answer call.
    With a local provider selected there is no call to except, and the settings
    screen says so rather than leaving the user to work it out.
    """
    return provider.base_url.startswith(("http://localhost", "http://127.0.0.1"))
