"""HTML builders for each screenshot category. One function per category."""

from __future__ import annotations

BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { width: 1440px; height: 900px; font-family: -apple-system, "SF Pro Text",
  "Segoe UI", Helvetica, Arial, sans-serif; overflow: hidden; }
"""


def _page(body: str, background: str = "#f4f4f5") -> str:
    return f"<html><head><style>{BASE_CSS}</style></head>" \
           f'<body style="background:{background}">{body}</body></html>'


def _titlebar(app: str) -> str:
    return (
        '<div style="height:36px;background:#e9e9eb;display:flex;'
        'align-items:center;padding:0 14px;border-bottom:1px solid #d4d4d8">'
        '<div style="display:flex;gap:8px">'
        '<div style="width:12px;height:12px;border-radius:50%;background:#ff5f57"></div>'
        '<div style="width:12px;height:12px;border-radius:50%;background:#febc2e"></div>'
        '<div style="width:12px;height:12px;border-radius:50%;background:#28c840"></div>'
        '</div>'
        f'<div style="flex:1;text-align:center;font-size:13px;color:#52525b">{app}</div>'
        '</div>'
    )


def error_dialog(app: str, title: str, lines: list[str], border: str) -> str:
    body_lines = "".join(
        f'<div style="margin-top:10px;font-size:14px;color:#3f3f46;'
        f'font-family:ui-monospace,Menlo,monospace">{ln}</div>'
        for ln in lines
    )
    modal = (
        f'<div style="position:absolute;top:260px;left:420px;width:600px;'
        f'background:white;border:2px solid {border};border-radius:10px;'
        f'box-shadow:0 20px 60px rgba(0,0,0,0.25);padding:28px">'
        f'<div style="font-size:19px;font-weight:600;color:#18181b">{title}</div>'
        f'{body_lines}'
        f'<div style="margin-top:20px;display:flex;justify-content:flex-end;gap:10px">'
        f'<div style="padding:8px 16px;border-radius:6px;background:#f4f4f5;'
        f'font-size:13px;color:#3f3f46">Dismiss</div>'
        f'<div style="padding:8px 16px;border-radius:6px;background:{border};'
        f'color:white;font-size:13px">Retry</div></div></div>'
    )
    frame = f'<div style="position:relative;width:1440px;height:900px">' \
            f'{_titlebar(app)}{modal}</div>'
    return _page(frame, "#d4d4d8")


def terminal(title: str, lines: list[str]) -> str:
    rows = "".join(
        f'<div style="margin-top:6px">{ln}</div>' for ln in lines
    )
    body = (
        f'<div style="width:1440px;height:900px;background:#1e1e2e;'
        f'color:#cdd6f4;font-family:ui-monospace,Menlo,monospace;'
        f'font-size:14px;padding:0">'
        f'{_titlebar(title)}'
        f'<div style="padding:20px">{rows}</div></div>'
    )
    return _page(body, "#1e1e2e")


def dashboard(app: str, kpis: list[tuple[str, str]], bars: list[float],
              chart_title: str, accent: str,
              bar_colors: list[str] | None = None) -> str:
    cards = "".join(
        f'<div style="flex:1;background:white;border-radius:10px;padding:18px;'
        f'margin-right:14px;box-shadow:0 1px 3px rgba(0,0,0,0.08)">'
        f'<div style="font-size:12px;color:#71717a">{label}</div>'
        f'<div style="font-size:26px;font-weight:600;margin-top:6px">{value}</div>'
        f'</div>' for label, value in kpis
    )
    max_bar = max(bars) if bars else 1
    colors = bar_colors or [accent] * len(bars)
    bar_els = "".join(
        f'<div style="width:34px;height:{int(200 * b / max_bar)}px;'
        f'background:{colors[i]};border-radius:4px 4px 0 0;margin-right:10px"></div>'
        for i, b in enumerate(bars)
    )
    body = (
        f'<div style="padding:28px;font-family:inherit">'
        f'<div style="font-size:20px;font-weight:600;margin-bottom:18px">{app}</div>'
        f'<div style="display:flex;margin-bottom:24px">{cards}</div>'
        f'<div style="background:white;border-radius:10px;padding:20px">'
        f'<div style="font-size:13px;color:#71717a;margin-bottom:14px">{chart_title}</div>'
        f'<div style="display:flex;align-items:flex-end;height:200px">{bar_els}</div>'
        f'</div></div>'
    )
    return _page(body)


def chat(app: str, messages: list[tuple[str, str, bool]]) -> str:
    rows = ""
    for sender, text, mine in messages:
        align = "flex-end" if mine else "flex-start"
        bg = "#3b5bdb" if mine else "#e4e4e7"
        color = "white" if mine else "#18181b"
        rows += (
            f'<div style="display:flex;flex-direction:column;align-items:{align};'
            f'margin-bottom:14px">'
            f'<div style="font-size:11px;color:#a1a1aa;margin-bottom:3px">{sender}</div>'
            f'<div style="background:{bg};color:{color};padding:10px 14px;'
            f'border-radius:14px;max-width:420px;font-size:14px">{text}</div></div>'
        )
    body = (
        f'<div style="width:1440px;height:900px;background:white">'
        f'{_titlebar(app)}'
        f'<div style="padding:28px;max-width:640px">{rows}</div></div>'
    )
    return _page(body)


def settings(app: str, sections: list[tuple[str, list[tuple[str, bool]]]]) -> str:
    blocks = ""
    for title, rows in sections:
        row_html = "".join(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:12px 16px;border-bottom:1px solid #f1f1f3">'
            f'<span style="font-size:14px">{label}</span>'
            f'<div style="width:38px;height:22px;border-radius:11px;'
            f'background:{"#3b5bdb" if on else "#d4d4d8"};position:relative">'
            f'<div style="width:18px;height:18px;border-radius:50%;background:white;'
            f'position:absolute;top:2px;left:{18 if on else 2}px"></div></div></div>'
            for label, on in rows
        )
        blocks += (
            f'<div style="font-size:12px;color:#71717a;margin:22px 0 8px 16px;'
            f'text-transform:uppercase">{title}</div>'
            f'<div style="background:white;border-radius:10px;overflow:hidden">'
            f'{row_html}</div>'
        )
    body = f'<div style="width:1440px;height:900px">{_titlebar(app)}' \
           f'<div style="padding:10px 200px">{blocks}</div></div>'
    return _page(body)


def code_editor(filename: str, lines: list[str]) -> str:
    rows = "".join(
        f'<div style="display:flex"><div style="width:44px;color:#5c5f77;'
        f'text-align:right;padding-right:14px">{i + 1}</div>'
        f'<div style="white-space:pre">{ln}</div></div>'
        for i, ln in enumerate(lines)
    )
    body = (
        f'<div style="width:1440px;height:900px;background:#1e1e2e;color:#cdd6f4;'
        f'font-family:ui-monospace,Menlo,monospace;font-size:14px">'
        f'{_titlebar(filename)}<div style="padding:16px 0">{rows}</div></div>'
    )
    return _page(body, "#1e1e2e")


def cloud_console(provider: str, columns: list[str], rows: list[list[str]],
                   metric_label: str, metric_pct: int) -> str:
    head = "".join(f'<th style="text-align:left;padding:10px;font-size:12px;'
                    f'color:#71717a">{c}</th>' for c in columns)
    body_rows = "".join(
        "<tr>" + "".join(f'<td style="padding:10px;font-size:13px;border-top:'
                          f'1px solid #f1f1f3">{cell}</td>' for cell in r) + "</tr>"
        for r in rows
    )
    body = (
        f'<div style="padding:26px">'
        f'<div style="font-size:18px;font-weight:600;margin-bottom:6px">{provider}</div>'
        f'<div style="font-size:12px;color:#71717a;margin-bottom:4px">{metric_label}</div>'
        f'<div style="width:400px;height:10px;background:#e4e4e7;border-radius:5px;'
        f'margin-bottom:22px"><div style="width:{metric_pct}%;height:10px;'
        f'border-radius:5px;background:{"#e03131" if metric_pct > 85 else "#3b5bdb"}">'
        f'</div></div>'
        f'<table style="width:100%;border-collapse:collapse"><thead><tr>{head}'
        f'</tr></thead><tbody>{body_rows}</tbody></table></div>'
    )
    return _page(body, "white")


def mobile(status_pct: int, tint: str, body_inner: str) -> str:
    phone = (
        f'<div style="width:390px;height:844px;background:black;border-radius:52px;'
        f'padding:14px;margin:28px auto">'
        f'<div style="width:100%;height:100%;background:{tint};border-radius:38px;'
        f'overflow:hidden;position:relative">'
        f'<div style="display:flex;justify-content:space-between;padding:16px 26px 0;'
        f'font-size:15px;color:white;font-weight:600">'
        f'<span>9:41</span><span>{status_pct}%</span></div>'
        f'{body_inner}</div></div>'
    )
    return _page(phone, "#e4e4e7")
