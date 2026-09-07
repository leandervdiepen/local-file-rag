"""The 40 screenshot instances: golden-critical ones fixed, the rest filler."""

from __future__ import annotations

from corpus.rng import make_rng
from corpus.screenshot_filler import Instance, filler


def _fixed_instances() -> dict[str, list[Instance]]:
    """Instances with exact, hand-verified text: the hero and golden targets."""
    return {
        "error_dialog": [
            {
                "force_filename": "IMG_4821.png",
                "params": dict(
                    app="Stripe Dashboard", title="Webhook delivery failed",
                    lines=[
                        "Endpoint: POST /v1/webhooks/stripe",
                        "HTTP 500",
                        "signature verification failed",
                    ],
                    border="#e03131",
                ),
            },
            {
                "force_filename": "Screenshot 2026-02-18 at 09.14.02.png",
                "params": dict(
                    app="DataGrip", title="Connection timed out",
                    lines=[
                        "Host: db-prod-3.internal:5432",
                        "The primary replica did not respond within 30s",
                    ],
                    border="#e03131",
                ),
            },
        ],
        "terminal": [
            {
                "force_filename": "CleanShot 2026-04-02.png",
                "params": dict(
                    title="zsh - acme-web",
                    lines=[
                        "$ npm install",
                        "npm ERR! ERESOLVE unable to resolve dependency tree",
                        "npm ERR! Found: react@18.2.0",
                        'npm ERR! Could not resolve dependency:',
                        'npm ERR! peer react@"^19.0.0" from acme-web@2.4.1',
                    ],
                ),
            },
        ],
        "dashboard": [
            {
                "force_filename": "Screenshot 2026-06-10 at 08.02.11.png",
                "params": dict(
                    app="Northline Ops", chart_title="Requests per minute",
                    kpis=[("Error rate", "0.4%"), ("P95 latency", "212ms"),
                          ("Active nodes", "18")],
                    bars=[420, 460, 440, 500, 480, 510, 890],
                    accent="#3b5bdb",
                    bar_colors=["#3b5bdb"] * 6 + ["#e03131"],
                ),
            },
        ],
        "chat": [
            {
                "force_filename": "IMG_5310.png",
                "params": dict(
                    app="Slack - #growth",
                    messages=[
                        ("Marcus Ellery", "bump it to $49", False),
                        ("Priya Chandran", "🚀", True),
                    ],
                ),
            },
        ],
        "settings": [
            {
                "force_filename": "CleanShot 2026-01-22.png",
                "params": dict(
                    app="Acme Account", sections=[
                        ("Security", [
                            ("Two-factor authentication", True),
                            ("Login alerts", True),
                            ("Recovery codes generated", False),
                        ]),
                    ],
                ),
            },
        ],
        "code_editor": [
            {
                "force_filename": "Screenshot 2026-07-03 at 14.28.55.png",
                "params": dict(
                    filename="utils.py",
                    lines=[
                        "def total(price):",
                        "<<<<<<< HEAD",
                        "    return price * 1.08",
                        "=======",
                        "    return price * TAX_RATE",
                        ">>>>>>> feature/pricing-refactor",
                    ],
                ),
            },
        ],
        "cloud_console": [
            {
                "force_filename": "IMG_7742.png",
                "params": dict(
                    provider="Compute Overview",
                    columns=["Instance", "Type", "CPU", "Status"],
                    rows=[
                        ["i-0a3f", "c6g.xlarge", "97%", "throttled"],
                        ["i-0b91", "c6g.xlarge", "94%", "throttled"],
                        ["i-0c22", "c6g.large", "61%", "ok"],
                    ],
                    metric_label="CPU utilization · us-east-2",
                    metric_pct=97,
                ),
            },
        ],
        "mobile": [
            {
                "force_filename": "CleanShot 2026-08-14.png",
                "params": dict(
                    status_pct=2, tint="#111318",
                    body_inner=(
                        '<div style="text-align:center;margin-top:210px;color:white">'
                        '<div style="font-size:74px;font-weight:200">6:42</div>'
                        '<div style="font-size:15px;opacity:0.7;margin-top:6px">'
                        'Thursday, 12 March</div></div>'
                        '<div style="position:absolute;top:14px;right:26px;width:22px;'
                        'height:11px;border:1.5px solid #e03131;border-radius:3px">'
                        '<div style="width:4px;height:100%;background:#e03131"></div>'
                        '</div>'
                    ),
                ),
            },
            {
                "force_filename": "IMG_9013.png",
                "params": dict(
                    status_pct=84, tint="#2c2f36",
                    body_inner=(
                        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
                        'gap:22px;padding:90px 24px">'
                        + "".join(
                            f'<div style="position:relative;width:56px;height:56px;'
                            f'border-radius:14px;background:#{c}">'
                            f'<div style="position:absolute;top:-6px;right:-6px;'
                            f'background:#e03131;color:white;font-size:11px;'
                            f'border-radius:9px;padding:1px 6px">{n}</div></div>'
                            for c, n in [
                                ("4c6ef5", 12), ("f76707", 3), ("2f9e44", 47),
                                ("ae3ec9", 1), ("1098ad", 8), ("e8590c", 2),
                            ]
                        ) + "</div>"
                    ),
                ),
            },
        ],
    }


def build_instances(seed: int) -> list[tuple[str, Instance]]:
    """Return 40 (category, instance) pairs, 5 per category, fixed ones first."""
    fixed = _fixed_instances()
    out: list[tuple[str, Instance]] = []
    for category in ["error_dialog", "terminal", "dashboard", "chat", "settings",
                      "code_editor", "cloud_console", "mobile"]:
        instances = list(fixed.get(category, []))
        rng = make_rng(seed, f"screenshot-filler:{category}")
        while len(instances) < 5:
            instances.append(filler(category, rng))
        out.extend((category, inst) for inst in instances[:5])
    return out
