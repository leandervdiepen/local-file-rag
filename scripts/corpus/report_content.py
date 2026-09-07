"""Structured data for the 30 report PDFs. Rendering lives in reports.py."""

from __future__ import annotations

import random

from corpus.rng import BIZ_WORDS, COMPANIES, PRODUCTS, make_rng, paragraph, pick

Report = dict[str, object]


def quarterly(rng: random.Random, seed: int, idx: int) -> Report:
    company = pick(rng, COMPANIES)
    quarter = pick(rng, ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2025"])
    months = ["Jan", "Feb", "Mar"] if "Q1" in quarter else ["Apr", "May", "Jun"]
    revenue = [round(rng.uniform(80, 400), 1) for _ in months]
    rows = [["Metric", "Value"],
            ["Revenue", f"${sum(revenue):.1f}k"],
            ["New customers", str(rng.randint(12, 140))],
            ["Net revenue retention", f"{rng.randint(96, 128)}%"]]
    return {
        "title": f"{company} - {quarter} business review",
        "intro": paragraph(rng, 3),
        "table": rows,
        "chart": {"kind": "bar", "labels": months, "values": revenue,
                  "title": "Monthly revenue ($k)", "ylabel": "$k"},
        "outro": paragraph(rng, 2),
    }


def infra_cost(rng: random.Random, seed: int, idx: int) -> Report:
    product = pick(rng, PRODUCTS)
    services = ["Compute", "Storage", "Networking", "Managed DB", "CDN"]
    values = [round(rng.uniform(400, 6000), 2) for _ in services]
    rows = [["Service", "Monthly cost"]] + [
        [s, f"${v:,.2f}"] for s, v in zip(services, values)
    ]
    return {
        "title": f"{product} infrastructure cost breakdown",
        "intro": paragraph(rng, 2),
        "table": rows,
        "chart": {"kind": "pie", "labels": services, "values": values,
                  "title": "Cost share by service"},
        "outro": paragraph(rng, 2),
    }


def experiment(rng: random.Random, seed: int, idx: int,
               force_signup_jump: bool = False) -> Report:
    company = pick(rng, COMPANIES)
    metric = "signups" if force_signup_jump else pick(rng, BIZ_WORDS)
    weeks = [f"W{n}" for n in range(1, 7)]
    if force_signup_jump:
        values = [140, 152, 148, 310, 322, 305]
        # Chart-only page must stay clear of the golden query's words
        # (signups, jump, new, landing, page, redesign) so only visual
        # retrieval can find it; the plain-language narrative sits later.
        chart_title = "Account growth"
        chart_series_label = "Total"
        narrative = (
            "We shipped a redesigned landing page in week four and watched "
            "signups roughly double against the prior baseline. "
            f"{paragraph(rng, 2)}"
        )
    else:
        values = [round(rng.uniform(20, 400), 1) for _ in weeks]
        chart_title = f"{metric.capitalize()} over time"
        chart_series_label = metric.capitalize()
        narrative = paragraph(rng, 3)
    return {
        "title": f"{company} experiment writeup - {metric}",
        "intro": paragraph(rng, 2),
        "chart_only_page": True,
        "chart": {"kind": "line", "labels": weeks,
                  "series": {chart_series_label: values},
                  "title": chart_title, "ylabel": "count"},
        "narrative": narrative,
    }


def board_update(rng: random.Random, seed: int, idx: int) -> Report:
    company = pick(rng, COMPANIES)
    rows = [["Area", "Status", "Owner"]]
    for _ in range(4):
        rows.append([pick(rng, BIZ_WORDS).capitalize(),
                     pick(rng, ["On track", "At risk", "Blocked", "Done"]),
                     pick(rng, ["Priya", "Marcus", "Devon", "Sofia"])])
    values = [round(rng.uniform(50, 500), 1) for _ in range(4)]
    return {
        "title": f"{company} board update",
        "intro": paragraph(rng, 3),
        "table": rows,
        "chart": {"kind": "bar", "labels": ["Q1", "Q2", "Q3", "Q4"],
                  "values": values, "title": "ARR by quarter ($k)",
                  "ylabel": "$k"},
        "outro": paragraph(rng, 2),
    }


_INVOICE_LINES_HERO = [
    ("Compute (vCPU-hours)", 2400, 2.10),
    ("Storage (GB-month)", 8200, 0.09),
    ("Data egress (TB)", 18.4, 80.00),
    ("Support (flat)", 1, 450.00),
]


def invoice(rng: random.Random, seed: int, idx: int, hero: bool = False,
            period: str = "") -> Report:
    if hero:
        company = "Basalt Cloud"
        period = "Q2 2026"
        lines = _INVOICE_LINES_HERO
    else:
        company = pick(rng, COMPANIES)
        lines = [
            ("Compute (vCPU-hours)", rng.randint(500, 3000), round(rng.uniform(1.5, 3), 2)),
            ("Storage (GB-month)", rng.randint(1000, 9000), round(rng.uniform(0.05, 0.12), 2)),
            ("Support (flat)", 1, round(rng.uniform(200, 600), 2)),
        ]
    rows = [["Line item", "Quantity", "Unit price", "Amount"]]
    total = 0.0
    for name, qty, price in lines:
        amount = round(qty * price, 2)
        total += amount
        rows.append([name, str(qty), f"${price:,.2f}", f"${amount:,.2f}"])
    rows.append(["", "", "Total", f"${total:,.2f}"])
    return {
        "title": f"{company} - hosting invoice, {period}",
        "intro": f"Invoice for cloud hosting services rendered in {period}.",
        "table": rows,
    }
