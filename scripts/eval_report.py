"""Renders report.html for one eval run: a single file, inline CSS and JS, thumbnails as data URIs.

Ink on paper with one accent, per docs/conventions/design.md. Colour appears
only on a delta and on a regression, because those are the two things a reader
opens the report to find.
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any

Split = dict[str, Any]

SPLIT_LINES = (
    ("by_text_free", "true", "text_free"),
    ("by_text_free", "false", "not text_free"),
    ("by_match_channel", "visual", "visual"),
    ("by_match_channel", "filename", "filename"),
    ("by_match_channel", "content", "content"),
)
IDENTITY_ROWS = (
    ("git_sha", "git sha"),
    ("dirty", "dirty"),
    ("corpus_manifest_hash", "corpus hash"),
    ("corpus_seed", "corpus seed"),
    ("retrieval", "retrieval"),
    ("answer_model", "answer model"),
    ("judge_model", "judge model"),
    ("prices_read_on", "prices read on"),
    ("started_at", "started"),
)
TABLE_COLUMNS = (
    "id", "match_channel", "text_free", "query", "expected", "candidates", "stage1_rank", "rank",
    "hit1", "hit5", "hit10", "cap_miss", "visual_only", "stage1_ms", "stage2_ms", "cold_pages",
)  # fmt: skip

CSS = """
:root{--paper:#faf9f7;--ink:#1c1b19;--ink-2:#6b6862;--line:#e4e1db;--accent:#2f5bd8;--status:#b3261e}
@media(prefers-color-scheme:dark){:root{--paper:#171614;--ink:#ebe8e2;--ink-2:#9a968e;--line:#2c2a26;--accent:#7d9cf0;--status:#f28b82}}
body{margin:0;padding:32px 40px 64px;background:var(--paper);color:var(--ink);font:14px/1.5 Inter,system-ui,sans-serif;max-width:1400px}
h1,h2{font-weight:600;margin:0 0 8px}h1{font-size:20px}h2{font-size:14px;color:var(--ink-2);margin-top:40px}
.mono,td.n,th.n,.id,.delta,.big{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 12px 6px 0;vertical-align:top;border-bottom:1px solid var(--line)}
th{font-weight:500;color:var(--ink-2)}th.sort{cursor:pointer}th.sort:hover{color:var(--ink)}td.n,th.n{text-align:right}
.identity td:first-child{color:var(--ink-2);width:140px}.identity td{padding-right:32px}
.headline{display:flex;gap:48px;margin:24px 0 8px}.big{font-size:40px;line-height:1;font-weight:600}.label{color:var(--ink-2)}
.prev{color:var(--ink-2)}.delta.down{color:var(--status)}.delta.up{font-weight:600}
.splits div{display:grid;grid-template-columns:140px 80px 100px 60px;padding:4px 0}
details summary{cursor:pointer;font-weight:600}.reg{display:grid;grid-template-columns:1fr 200px 200px;gap:24px;padding:16px 0;border-bottom:1px solid var(--line)}
.reg .id{color:var(--status)}.reg img{width:200px;border:1px solid var(--line);display:block}.reg .cap{color:var(--ink-2);font-size:12px}
a{color:var(--accent)}.miss{color:var(--status)}
"""

JS = """
document.querySelectorAll('th.sort').forEach((th,i)=>th.addEventListener('click',()=>{
  const body=th.closest('table').tBodies[0],rows=[...body.rows],dir=th.dataset.dir==='asc'?-1:1;
  th.dataset.dir=dir===1?'asc':'desc';
  const val=r=>{const c=r.cells[i];const d=c.dataset.v;return d===undefined?c.textContent:(d===''?null:Number(d))};
  rows.sort((a,b)=>{const x=val(a),y=val(b);if(x===null)return 1;if(y===null)return -1;return (x>y?1:x<y?-1:0)*dir});
  rows.forEach(r=>body.appendChild(r));
}));
"""


def render_report(run: dict[str, Any], queries: list[dict[str, Any]], previous: dict[str, Any] | None, root: Path) -> str:
    aggregates, before = run["aggregates"], (previous or {}).get("aggregates")
    data = json.dumps({"run": run, "queries": queries}).replace("</", "<\\/")
    parts = [
        f"<title>Eval {esc(run['run_id'])}</title><style>{CSS}</style>",
        f"<h1>Eval run <span class=mono>{esc(run['run_id'])}</span></h1>",
        identity_strip(run, previous),
        headline(aggregates["overall"], before["overall"] if before else None),
        splits(aggregates, before),
        regressions_section(run["regressions"], queries, root),
        query_table(queries),
        f'<script id="run-data" type="application/json">{data}</script><script>{JS}</script>',
    ]
    return "\n".join(parts)


def esc(value: Any) -> str:
    return html.escape("-" if value is None else str(value))


def identity_strip(run: dict[str, Any], previous: dict[str, Any] | None) -> str:
    def cell(source: dict[str, Any] | None, key: str) -> str:
        value = None if source is None else source.get(key)
        if key == "retrieval" and isinstance(value, dict):
            value = " ".join(f"{k}={v}" for k, v in sorted(value.items()) if v is not None) or None
        return f"<td class=mono>{esc(value)}</td>"

    header = f"<tr><td></td><td>this run</td><td>previous {esc(previous['run_id'] if previous else None)}</td></tr>"
    rows = "".join(f"<tr><td>{label}</td>{cell(run, key)}{cell(previous, key)}</tr>" for key, label in IDENTITY_ROWS)
    return f"<table class=identity>{header}{rows}</table>"


def ratio(split: Split | None, key: str) -> str:
    if not split or split["count"] == 0:
        return "-"
    return f"{round(split[key] * split['count'])}/{split['count']}"


def delta(now: Split | None, before: Split | None, key: str) -> str:
    """A signed count difference when both runs have the split, nothing to say otherwise."""
    if not now or not before or not now["count"] or not before["count"]:
        return ""
    diff = round(now[key] * now["count"]) - round(before[key] * before["count"])
    css = "down" if diff < 0 else "up" if diff > 0 else ""
    return f"<span class='delta {css}'>{diff:+d}</span>"


def headline(now: Split, before: Split | None) -> str:
    mrr, mrr_before = now.get("mrr10"), None if before is None else before.get("mrr10")
    return (
        "<div class=headline>"
        f"<div><div class=label>hit@5</div><div class=big>{ratio(now, 'hit5')}</div>"
        f"<div class=prev>previous {ratio(before, 'hit5')} {delta(now, before, 'hit5')}</div></div>"
        f"<div><div class=label>mrr@10</div><div class=big>{esc(None if mrr is None else f'{mrr:.3f}')}</div>"
        f"<div class=prev>previous {esc(None if mrr_before is None else f'{mrr_before:.3f}')}</div></div></div>"
    )


def splits(aggregates: dict[str, Any], before: dict[str, Any] | None) -> str:
    lines = []
    for group, value, label in SPLIT_LINES:
        now, prev = aggregates[group][value], None if before is None else before[group][value]
        lines.append(
            f"<div><span>{label}</span><span class=mono>{ratio(now, 'hit5')}</span>"
            f"<span class=prev>previous {ratio(prev, 'hit5')}</span>{delta(now, prev, 'hit5')}</div>"
        )
    return f"<h2>hit@5 by split</h2><div class=splits>{''.join(lines)}</div>"


def data_uri(root: Path, relative: str | None) -> str | None:
    if relative is None or not (root / relative).exists():
        return None
    return "data:image/png;base64," + base64.b64encode((root / relative).read_bytes()).decode("ascii")


def regressions_section(ids: list[str], queries: list[dict[str, Any]], root: Path) -> str:
    by_id = {row["id"]: row for row in queries}
    items = []
    for query_id in ids:
        row = by_id[query_id]
        thumbs = row.get("thumbnails") or {}
        expected = f"{row['expected']['file']} p{row['expected']['page']}"
        top = row["top10"][0] if row["top10"] else None
        items.append(
            f"<div class=reg><div><span class=id>{esc(query_id)}</span> {esc(row['query'])}"
            f"<div class=cap>expected {esc(expected)}, rank {esc(row['rank'])}, "
            f"<a href='queries/{esc(query_id)}.json'>json</a></div></div>"
            f"{thumb(data_uri(root, thumbs.get('expected')), 'expected page')}"
            f"{thumb(data_uri(root, thumbs.get('rank1')), f'rank 1: {top['file']} p{top['page']}' if top else 'rank 1: nothing')}"
            "</div>"
        )
    state = " open" if ids else ""
    return f"<details{state}><summary>Regressions: {len(ids)}</summary>{''.join(items)}</details>"


def thumb(uri: str | None, caption: str) -> str:
    image = f"<img src='{uri}' alt=''>" if uri else "<div class=cap>no thumbnail</div>"
    return f"<div>{image}<div class=cap>{esc(caption)}</div></div>"


def query_table(queries: list[dict[str, Any]]) -> str:
    numeric = {"candidates", "stage1_rank", "rank", "stage1_ms", "stage2_ms", "cold_pages"}
    head = "".join(f"<th class='sort{' n' if c in numeric else ''}'>{c}</th>" for c in TABLE_COLUMNS)
    rows = []
    for row in queries:
        cells = []
        for column in TABLE_COLUMNS:
            value = f"{row['expected']['file']} p{row['expected']['page']}" if column == "expected" else row[column]
            if column in numeric:
                cells.append(f"<td class=n data-v='{esc('' if value is None else value)}'>{esc(value)}</td>")
            elif isinstance(value, bool):
                miss = " class=miss" if column == "hit5" and not value else ""
                cells.append(f"<td{miss} data-v='{int(value)}'>{'yes' if value else 'no'}</td>")
            else:
                cells.append(f"<td class={'id' if column == 'id' else 'mono' if column == 'expected' else ''}>{esc(value)}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<h2>Every query</h2><table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
