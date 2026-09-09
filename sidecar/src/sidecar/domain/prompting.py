"""What the answer model is told, and how the pages are handed to it.

Here rather than in an adapter because every provider gets the same
instruction and the same evidence. An adapter's whole job is wire format, so
a second provider must not be able to change what the model was asked.
"""

from __future__ import annotations

from sidecar.domain.answers import PageImage

# Written as rules the model can follow one at a time. The order matters: the
# grounding rule comes before the citation rule, because a model that cites
# correctly while inventing content is worse than one that refuses.
SYSTEM_PROMPT = "\n\n".join(
    [
        "You answer questions about pages from someone's own files.",
        "Use only what is visible in the pages you are given."
        " You have no other source, and what you happen to know about the world"
        " is not evidence about these files.",
        "Cite every claim with the page it came from, written as [n], where n is"
        " the number labelling that page. Put the citation right after the"
        " sentence it supports.",
        "When the pages do not contain the answer, say so in one sentence and"
        " cite nothing. Do not offer what the pages do say instead unless it"
        " answers a question that was actually asked. A wrong answer with a"
        " citation is worse than no answer, because the citation makes it look"
        " checked.",
        "Read numbers exactly as they appear. Do not round, convert, or reconcile"
        " figures that disagree; report what is on the page.",
        "Answer in a few sentences. No preamble, no restating the question.",
    ]
)


def page_label(page: PageImage) -> str:
    """The line that precedes a page image, telling the model what to cite it as."""
    return f"Page [{page.index}]"


def question_block(question: str) -> str:
    """The user turn, after the pages.

    The question goes last because the pages are context and the question is
    the instruction, and a model attends most to what it read most recently.
    """
    return f"Question: {question}"
