"""Filler content for the screenshots outside golden-critical instances."""

from __future__ import annotations

import random

from corpus.rng import PEOPLE, PRODUCTS, pick

Instance = dict[str, object]

FILLER_TERMINAL = [
    (["$ docker build -t {p}-api .", "Step 6/6 : CMD [\"serve\"]",
      "Successfully built {h}", "Successfully tagged {p}-api:latest"]),
    (["$ git rebase main", "Successfully rebased and updated refs/heads/{p}"]),
    (["$ pytest -q", "{n} passed in {s}s"]),
    (["$ ssh deploy@{p}.internal", "Last login: Tue Mar 3", "deploy@{p}:~$"]),
]

FILLER_DASHBOARD_TITLES = ["Revenue Overview", "Latency Watch", "Headcount", "Signups"]
FILLER_CHAT_APPS = ["Slack - #incidents", "Slack - #standup", "Messages", "Teams"]
FILLER_SETTINGS_SECTIONS = ["Notifications", "Privacy", "Billing", "Appearance"]
FILLER_CODE_FILES = ["schema.sql", "component.tsx", "config.yaml", "server.go"]
FILLER_CONSOLE_PROVIDERS = ["S3 Buckets", "Billing", "IAM Users", "Load Balancer"]
FILLER_MOBILE_TINTS = ["#1c7ed6", "#495057", "#087f5b", "#5f3dc4"]


def filler(category: str, rng: random.Random) -> Instance:
    product = pick(rng, PRODUCTS).lower()
    person = pick(rng, PEOPLE).split()[0]
    if category == "terminal":
        lines = pick(rng, FILLER_TERMINAL)
        filled = [
            ln.format(p=product, h=rng.randint(1000, 9999) * 7,
                      n=rng.randint(20, 140), s=rng.randint(2, 40))
            for ln in lines
        ]
        return {"params": dict(title=f"zsh - {product}", lines=filled)}
    if category == "dashboard":
        bars = [rng.uniform(200, 900) for _ in range(6)]
        return {"params": dict(
            app=f"{product.capitalize()} {pick(rng, FILLER_DASHBOARD_TITLES)}",
            chart_title="Weekly trend",
            kpis=[("Active users", str(rng.randint(800, 9000))),
                  ("Churn", f"{rng.uniform(0.5, 4):.1f}%")],
            bars=bars, accent="#3b5bdb",
        )}
    if category == "chat":
        return {"params": dict(
            app=pick(rng, FILLER_CHAT_APPS),
            messages=[(person, "on it", False), ("You", "thanks", True)],
        )}
    if category == "settings":
        section = pick(rng, FILLER_SETTINGS_SECTIONS)
        return {"params": dict(app=f"{product.capitalize()} Settings", sections=[
            (section, [("Email digests", bool(rng.getrandbits(1))),
                       ("Dark mode", bool(rng.getrandbits(1)))]),
        ])}
    if category == "code_editor":
        return {"params": dict(
            filename=pick(rng, FILLER_CODE_FILES),
            lines=[f"# revision {rng.randint(1, 99)}", "def handler(event):",
                   "    return process(event)"],
        )}
    if category == "cloud_console":
        return {"params": dict(
            provider=pick(rng, FILLER_CONSOLE_PROVIDERS),
            columns=["Name", "Region", "Status"],
            rows=[[f"{product}-{i}", "us-west-2", "ok"] for i in range(3)],
            metric_label="Monthly spend", metric_pct=rng.randint(20, 70),
        )}
    if category == "mobile":
        return {"params": dict(
            status_pct=rng.randint(30, 95), tint=pick(rng, FILLER_MOBILE_TINTS),
            body_inner='<div style="text-align:center;margin-top:300px;color:white;'
                       f'font-size:22px">{product.capitalize()}</div>',
        )}
    if category == "error_dialog":
        return {"params": dict(
            app="System", title=pick(rng, ["Permission denied", "Sync failed",
                                            "Payment declined"]),
            lines=[f"Reference: {rng.randint(100000, 999999)}"], border="#e03131",
        )}
    raise ValueError(category)
