"""Deterministic randomness and word banks shared by every corpus group."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

# Fixed so mtimes do not drift with wall-clock run date.
ANCHOR_DATE = datetime(2026, 9, 7, tzinfo=timezone.utc)
SPREAD_DAYS = 548  # about 18 months

COMPANIES = [
    "Northwind Analytics", "Ferro Logistics", "Basalt Cloud", "Quillview",
    "Marrow Systems", "Coldstream Data", "Ampere Robotics", "Voxel Health",
    "Driftline", "Pallet Freight", "Kernel Metrics", "Sable Finance",
    "Amberpath", "Ridgeback Security", "Lumenworks",
]

PEOPLE = [
    "Priya Chandran", "Marcus Ellery", "Devon Nakashima", "Sofia Renaud",
    "Owen Farrow", "Aisha Bakr", "Tomas Novak", "Ruth Okafor",
    "Ines Vidal", "Callum Reyes", "Naomi Strand", "Jonas Ahlberg",
    "Wei Lin", "Grace Odom", "Farid Hassan",
]

PRODUCTS = [
    "Beacon", "Northline", "Vantage", "Ridgeline", "Fathom",
    "Overlook", "Tideway", "Crossbar", "Hollowpoint", "Slate",
]

BIZ_WORDS = [
    "onboarding", "retention", "throughput", "latency", "checkout",
    "activation", "provisioning", "billing", "rollout", "migration",
    "compliance", "uptime", "backlog", "headcount", "runway",
    "attrition", "cohort", "funnel stage", "conversion", "capacity",
]

VERBS = [
    "reduced", "increased", "stabilized", "audited", "migrated",
    "refactored", "shipped", "deprecated", "escalated", "reconciled",
]


def make_rng(seed: int, salt: str) -> random.Random:
    """Derive an independent, reproducible stream for one file or decision."""
    digest = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def mtime_for(seed: int, salt: str) -> float:
    """Pick a plausible timestamp within the last 18 months, seed-derived."""
    rng = make_rng(seed, f"mtime:{salt}")
    offset_days = rng.uniform(0, SPREAD_DAYS)
    offset_seconds = rng.uniform(0, 86400)
    stamp = ANCHOR_DATE - timedelta(days=offset_days, seconds=-offset_seconds)
    return stamp.timestamp()


def pick(rng: random.Random, options: list[str]) -> str:
    return options[rng.randrange(len(options))]


def sentence(rng: random.Random) -> str:
    subject = pick(rng, PEOPLE).split()[0]
    verb = pick(rng, VERBS)
    topic = pick(rng, BIZ_WORDS)
    product = pick(rng, PRODUCTS)
    pct = rng.randint(4, 63)
    templates = [
        f"{subject} {verb} {topic} on {product} by {pct} percent.",
        f"{topic.capitalize()} on {product} {verb} after the last release.",
        f"The {topic} number moved because {subject} {verb} the pipeline.",
        f"{product} {topic} is the open item {subject} owns this cycle.",
    ]
    return pick(rng, templates)


def paragraph(rng: random.Random, sentences: int) -> str:
    return " ".join(sentence(rng) for _ in range(sentences))


def money(rng: random.Random, low: int, high: int) -> float:
    return round(rng.uniform(low, high), 2)
