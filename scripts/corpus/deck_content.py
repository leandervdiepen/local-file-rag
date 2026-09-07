"""Slide data for the 10 decks. Five carry hand-fixed golden content, five
are filler built from the word banks. One slide per deck (never chart text)
uses the words the golden set searches for; chart-only pages stay clean."""

from __future__ import annotations

import random

from corpus.rng import BIZ_WORDS, PRODUCTS, make_rng, paragraph, pick

Slide = dict[str, object]
Deck = dict[str, object]


def _title(text: str, subtitle: str = "") -> Slide:
    return {"kind": "title", "title": text, "subtitle": subtitle}


def _bullets(title: str, items: list[str]) -> Slide:
    return {"kind": "bullets", "title": title, "items": items}


def _chart(kind: str, **kw: object) -> Slide:
    return {"kind": "chart", "chart": {"kind": kind, **kw}}


def funnel_deck() -> Deck:
    slides = [
        _title("Growth metrics review", "Q1 2026"),
        _bullets("Acquisition", ["Paid spend down 12%", "Organic share up 9 points"]),
        _bullets("Retention", ["90-day retention holds at 61%", "Churn flat quarter over quarter"]),
        {
            "kind": "chart_bare",
            "title": "Where signups drop off",
            "chart": {"kind": "funnel",
                      "stages": ["Visitors", "Signups", "Activated", "Paid"],
                      "values": [42000, 9800, 4100, 1250]},
        },
        _bullets("Expansion", ["Three new regions opened", "Partner-sourced pipeline up"]),
        _bullets("Risks", ["Support backlog rising", "Onboarding time still too long"]),
        _chart("bar", labels=["Team A", "Team B", "Team C"], values=[62, 74, 51],
               title="NPS by team", ylabel="score"),
        _bullets("Team", ["Two open reqs in platform", "One backfill in support"]),
        _title("Thank you", "Questions"),
    ]
    return {"filename": "growth-metrics-review-q1-2026.pdf", "slides": slides}


def hockey_stick_deck() -> Deck:
    slides = [
        _title("Board narrative", "Q3 2026"),
        _bullets("Highlights", ["Landed two enterprise logos", "Gross margin up 4 points"]),
        _bullets("Headwinds", ["Sales cycle lengthened", "One churned logo in EMEA"]),
        {"kind": "chart_bare", "title": "", "chart": {
            "kind": "line", "labels": ["Q1", "Q2", "Q3", "Q4"],
            "series": {"a": [80, 95, 260, 540]}, "title": "", "ylabel": "",
        }},
        _bullets("Hiring", ["Two senior engineers start in April", "One open req in sales"]),
        _bullets("Product", ["Shipped the new billing flow", "Mobile app in private beta"]),
        _chart("bar", labels=["NA", "EMEA", "APAC"], values=[210, 140, 60],
               title="ARR by region ($k)", ylabel="$k"),
        _bullets("Risks", ["Vendor renewal due in Q4", "Headcount plan is tight"]),
        _title("Thank you", "Questions"),
    ]
    return {"filename": "board-narrative-q3-2026.pdf", "slides": slides}


def roadmap_deck() -> Deck:
    slides = [
        _title("Product roadmap", "2026"),
        _bullets("Now", ["Ship the billing redesign", "Close the top support tickets"]),
        _bullets("Next", ["Deprecate the v1 API in Q4", "Start the mobile beta"]),
        _bullets("Later", ["Explore a partner marketplace", "Evaluate a second region"]),
        _chart("bar", labels=["v1 API", "v2 API"], values=[80, 20],
               title="Traffic share", ylabel="%"),
        _bullets("Dependencies", ["Needs the auth migration done first"]),
        _bullets("Owners", ["Platform team owns the API cutover"]),
        _title("Thank you", "Questions"),
    ]
    return {"filename": "product-roadmap-2026.pdf", "slides": slides}


def hiring_deck() -> Deck:
    slides = [
        _title("Hiring plan", "2026"),
        _bullets("Current headcount", ["58 full time", "6 contractors"]),
        _bullets("Freeze", ["Hiring freeze extended through Q3", "Backfills only, case by case"]),
        _bullets("Backfills", ["One support backfill approved", "One platform backfill pending"]),
        _chart("bar", labels=["Eng", "Sales", "Support"], values=[28, 14, 16],
               title="Headcount by team", ylabel="people"),
        _bullets("Budget", ["Comp budget flat versus last year"]),
        _title("Thank you", "Questions"),
    ]
    return {"filename": "hiring-plan-2026.pdf", "slides": slides}


def partnerships_deck() -> Deck:
    slides = [
        _title("Partnerships review", "2026"),
        _bullets("Active partners", ["12 active integration partners"]),
        _bullets("Referral program", [
            "Northwind Analytics referral program renewed for another year",
            "Referral revenue up 22%",
        ]),
        _bullets("Pipeline", ["Two new partners in legal review"]),
        _chart("pie", labels=["Direct", "Referral", "Partner"], values=[55, 25, 20],
               title="Revenue by source"),
        _bullets("Risks", ["One partner integration is out of date"]),
        _title("Thank you", "Questions"),
    ]
    return {"filename": "partnerships-review-2026.pdf", "slides": slides}


FILLER_TOPICS = [
    ("fundraising-update-2026.pdf", "Fundraising update"),
    ("security-posture-review.pdf", "Security posture review"),
    ("customer-success-metrics.pdf", "Customer success metrics"),
    ("platform-reliability-q2-2026.pdf", "Platform reliability"),
    ("sales-pipeline-review.pdf", "Sales pipeline review"),
]


def filler_deck(seed: int, filename: str, title: str) -> Deck:
    rng = make_rng(seed, f"deck-filler:{filename}")
    n_slides = rng.randint(6, 12)
    slides: list[Slide] = [_title(title, pick(rng, ["2026", "H1 2026", "H2 2026"]))]
    for _ in range(n_slides - 2):
        if rng.random() < 0.3:
            values = [round(rng.uniform(10, 300), 1) for _ in range(4)]
            slides.append(_chart("bar", labels=["A", "B", "C", "D"], values=values,
                                  title=pick(rng, BIZ_WORDS).capitalize(), ylabel="value"))
        else:
            heading = pick(rng, BIZ_WORDS).capitalize()
            items = [paragraph(rng, 1) for _ in range(2)]
            slides.append(_bullets(heading, items))
    slides.append(_title("Thank you", "Questions"))
    return {"filename": filename, "slides": slides}


def all_decks(seed: int) -> list[Deck]:
    fixed = [funnel_deck(), hockey_stick_deck(), roadmap_deck(), hiring_deck(),
             partnerships_deck()]
    filler = [filler_deck(seed, fname, title) for fname, title in FILLER_TOPICS]
    return fixed + filler
