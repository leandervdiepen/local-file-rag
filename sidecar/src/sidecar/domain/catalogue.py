"""What a provider says it can offer today.

The registry in `providers.py` says which places answers can come from. This
says which models each of them actually has, and it is read from the provider
rather than written down here, because a price typed into a source file is
wrong the week after it is typed. Measured 2026-09-09: the hardcoded price for
DeepSeek V4 Flash Vision understated its completion rate by three times.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sidecar.domain.providers import ProviderId


@dataclass(frozen=True)
class OfferedModel:
    """One model a provider is offering now.

    `sees_images` is `None` when the provider's API does not say. That is not
    the same as False: it means nobody can tell from here, and the caller has
    to decide whether to offer it with a warning or not at all.

    Prices are per million tokens, or `None` when the provider does not
    publish them through its API. `None` is never rendered as free.
    """

    provider: ProviderId
    id: str
    label: str
    sees_images: bool | None
    usd_per_m_input: float | None
    usd_per_m_output: float | None
    context_tokens: int | None = None

    @property
    def price_known(self) -> bool:
        return self.usd_per_m_input is not None and self.usd_per_m_output is not None

    @property
    def is_free(self) -> bool:
        return self.usd_per_m_input == 0.0 and self.usd_per_m_output == 0.0


def can_answer(model: OfferedModel) -> bool:
    """Whether this model may be offered at all.

    D37: every answer is grounded in page images, so a model that cannot see
    is not a slower option, it is a wrong one. A model whose provider does not
    say is offered, because refusing everything a vendor is quiet about would
    leave OpenAI and Anthropic with empty lists.
    """
    return model.sees_images is not False


def offerable(models: Sequence[OfferedModel]) -> list[OfferedModel]:
    """The models that may be offered, cheapest known price first, then by name."""
    kept = [model for model in models if can_answer(model)]
    return sorted(kept, key=lambda model: (model.usd_per_m_input is None, model.usd_per_m_input or 0.0, model.label))


def cost_usd(model: OfferedModel, input_tokens: int, output_tokens: int) -> float | None:
    """Dollars for one exchange, or `None` when the provider publishes no price."""
    if model.usd_per_m_input is None or model.usd_per_m_output is None:
        return None
    return (input_tokens * model.usd_per_m_input + output_tokens * model.usd_per_m_output) / 1_000_000
