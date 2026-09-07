"""The 50 markdown and text files: 8 hand-written golden targets, 42 filler."""

from __future__ import annotations

from pathlib import Path

from corpus.manifest import Manifest
from corpus.rng import BIZ_WORDS, PEOPLE, PRODUCTS, make_rng, paragraph, pick

FIXED: list[tuple[str, str, str]] = [
    ("meetings/2026-02-11-pricing-sync.md",
     "# Pricing sync - 2026-02-11\n\n",
     "Attendees: Priya Chandran, Marcus Ellery.\n\n"
     "We agreed to grandfather existing customers at the old rate. "
     "New signups move to the new tier starting next month.\n"),
    ("specs/rate-limit-spec.md",
     "# API rate limit spec\n\n",
     "Requests are limited to 100 per minute per API key. "
     "Exceeding the limit returns HTTP 429 with a Retry-After header.\n"),
    ("changelog/CHANGELOG-beacon.md",
     "# Beacon changelog\n\n",
     "## 2026-03-02\n\n"
     "- Fixed a bug where exports over 10k rows timed out.\n"
     "- Minor styling fixes to the settings pane.\n"),
    ("todo/leander-todo.md",
     "# Todo\n\n",
     "- Renew the SSL cert before it expires\n"
     "- Reply to Devon about the staging outage\n"
     "- Book the offsite venue\n"),
    ("readmes/ingest-service-README.md",
     "# Ingest service\n\n",
     "This service polls the queue every 30 seconds and retries failed "
     "jobs three times before moving them to the dead-letter queue.\n"),
    ("config/nginx-snippet.conf",
     "",
     "server {\n"
     "    listen 443 ssl;\n"
     "    client_max_body_size 25m;\n"
     "    proxy_read_timeout 60s;\n"
     "}\n"),
    ("meetings/2026-05-04-incident-review.md",
     "# Incident review - 2026-05-04\n\n",
     "Summary: checkout errors spiked for twenty minutes.\n\n"
     "Root cause was a stale DNS cache on the load balancer. "
     "Fix was a forced cache flush and a shorter TTL going forward.\n"),
    ("specs/onboarding-flow-spec.md",
     "# Onboarding flow spec\n\n",
     "New users must verify their email before accessing the dashboard. "
     "Verification links expire after 24 hours.\n"),
]

CATEGORIES = ["meetings", "specs", "changelog", "todo", "readmes", "config"]

FILLER_TITLES = {
    "meetings": "Sync notes",
    "specs": "Spec",
    "changelog": "Changelog",
    "todo": "Todo",
    "readmes": "README",
    "config": "Config notes",
}


def _filler_body(rng, category: str, long: bool) -> str:
    if category == "todo":
        n = rng.randint(2, 6)
        return "\n".join(f"- {paragraph(rng, 1)}" for _ in range(n)) + "\n"
    if category == "config":
        product = pick(rng, PRODUCTS).lower()
        return (
            f"[{product}]\n"
            f"timeout = {rng.randint(5, 60)}\n"
            f"retries = {rng.randint(1, 5)}\n"
            f"region = us-west-2\n"
        )
    if category == "changelog":
        n = rng.randint(1, 4)
        entries = "\n".join(f"- {paragraph(rng, 1)}" for _ in range(n))
        return f"## {pick(rng, ['2026-01-14', '2026-04-09', '2026-06-20'])}\n\n{entries}\n"
    sentences = 6 if long else 2
    return paragraph(rng, sentences) + "\n"


def _filler_note(seed: int, index: int) -> tuple[str, str]:
    rng = make_rng(seed, f"note-filler:{index}")
    category = CATEGORIES[index % len(CATEGORIES)]
    person = pick(rng, PEOPLE).split()[0].lower()
    topic = pick(rng, BIZ_WORDS).replace(" ", "-")
    ext = "conf" if category == "config" else "md"
    rel = f"{category}/{person}-{topic}-{index}.{ext}"
    long = rng.random() < 0.4
    heading = f"# {FILLER_TITLES[category]}: {topic}\n\n" if ext == "md" else ""
    body = _filler_body(rng, category, long)
    return rel, heading + body


def generate(seed: int, root: Path, manifest: Manifest) -> int:
    out_dir = root / "notes"
    count = 0
    for rel, heading, body in FIXED:
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(heading + body)
        manifest.add_indexed(path, "notes")
        count += 1
    for i in range(50 - len(FIXED)):
        rel, content = _filler_note(seed, i)
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        manifest.add_indexed(path, "notes")
        count += 1
    return count
