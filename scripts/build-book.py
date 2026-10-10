#!/usr/bin/env python3
"""Build the static book website in frontend/ from the topic pages.

Reads scripts/book.json for the chapter/topic/page order, copies each topic
page into frontend/<chapter>/<topic>/<slug>.html wrapped in the book chrome
(contents drawer, breadcrumb, previous/next), rewrites links between pages to
relative site links, and writes frontend/index.html (the contents page).

Run from anywhere:  python3 scripts/build-book.py
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "frontend")
BOOK = json.load(open(os.path.join(ROOT, "scripts", "book.json")))

HEAD_RE = re.compile(r"\A(\s*(?:<title>.*?</title>|<link[^>]*>|<style>.*?</style>))+", re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
PUBLISHED_RE = re.compile(r"https://claude\.ai/artifact/([A-Za-z0-9]+)")
LINKS_LINE_RE = re.compile(r"https://claude\.ai/artifact/([A-Za-z0-9]+)\s+—\s+(\S+\.html)")
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"
esc = html.escape
ICON = ('<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E'
        '%3Crect width=%2732%27 height=%2732%27 rx=%277%27 fill=%27%232f55e4%27/%3E%3Cpath d=%27M9 9h14M9 16h14M9 23h9%27 '
        'stroke=%27white%27 stroke-width=%273%27 stroke-linecap=%27round%27/%3E%3C/svg%3E">')


def collect_pages():
    pages = []
    for ch in BOOK["chapters"]:
        for tp in ch.get("topics", []):
            for i, pg in enumerate(tp["pages"]):
                src = os.path.join(ROOT, tp["src"], pg["file"])
                text = open(src, encoding="utf-8").read()
                title = TITLE_RE.search(text).group(1).strip()
                pages.append({
                    "chapter": ch, "topic": tp, "index": i, "src": src, "text": text, "title": title,
                    "kind": pg["kind"], "path": f'{ch["dir"]}/{tp["slug"]}/{pg["slug"]}.html',
                    "id": f'{ch["dir"]}/{tp["slug"]}/{pg["slug"]}',
                })
    return pages


def published_map(pages):
    """Map each published page id (from a topic's links.md) to its site path."""
    by_src = {p["src"]: p["path"] for p in pages}
    mapping = {}
    for tp_dir in {os.path.dirname(p["src"]) for p in pages}:
        links = os.path.join(tp_dir, "links.md")
        if not os.path.exists(links):
            continue
        for pub_id, fname in LINKS_LINE_RE.findall(open(links, encoding="utf-8").read()):
            target = os.path.join(tp_dir, fname)
            if target in by_src:
                mapping[pub_id] = by_src[target]
    return mapping


def rel(from_path, to_path):
    return os.path.relpath(to_path, os.path.dirname(from_path) or ".").replace(os.sep, "/")


def toc_html(pages, current_path):
    out = []
    for ch in BOOK["chapters"]:
        if not ch.get("topics"):
            continue
        out.append(f'<p class="bk-toc-ch">Chapter {ch["num"]} · {esc(ch["title"])}</p>')
        for tp in ch["topics"]:
            out.append(f'<p class="bk-toc-tp">{esc(tp["title"])}</p><ol class="bk-toc-list">')
            for p in pages:
                if p["topic"] is tp:
                    cur = ' aria-current="page"' if p["path"] == current_path else ""
                    out.append(f'<li><a href="{rel(current_path, p["path"])}"{cur} data-page="{p["id"]}">'
                               f'<span class="bk-kind">{p["kind"]}</span>{esc(p["title"])}</a></li>')
            out.append("</ol>")
    return "\n".join(out)


def nav_card(p, cur_path, label, cls):
    if not p:
        return f'<span class="bk-nav-card bk-nav-empty {cls}"></span>'
    return (f'<a class="bk-nav-card {cls}" href="{rel(cur_path, p["path"])}" data-nav="{cls}">'
            f'<span class="bk-nav-label">{label}</span><span class="bk-nav-title">{esc(p["title"])}</span>'
            f'<span class="bk-nav-meta">Chapter {p["chapter"]["num"]} · {esc(p["topic"]["title"])} · {p["kind"]}</span></a>')


def build_page(p, pages, pos, links):
    text = PUBLISHED_RE.sub(lambda m: rel(p["path"], links[m.group(1)]) if m.group(1) in links
                            else sys.exit(f'{p["src"]}: unknown published link {m.group(0)}'), p["text"])
    m = HEAD_RE.match(text)
    head = TITLE_RE.sub("", m.group(0)) if m else ""
    body = text[m.end():] if m else text
    root = rel(p["path"], "index.html").rsplit("index.html", 1)[0]
    prev_p = pages[pos - 1] if pos > 0 else None
    next_p = pages[pos + 1] if pos + 1 < len(pages) else None
    topic_pages = [q for q in pages if q["topic"] is p["topic"]]
    mermaid = (f'<script src="{MERMAID}"></script>\n<script>mermaid.initialize({{ startOnLoad: true, '
               f'theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "neutral" }});</script>'
               if 'class="mermaid"' in body else "")
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(p["title"])} · {esc(BOOK["title"])}</title>
{ICON}
<link rel="stylesheet" href="{root}assets/book.css">
{head.strip()}
</head>
<body data-page="{p["id"]}">
<div class="bk-bar">
  <a class="bk-home" href="{root}index.html">{esc(BOOK["title"])}</a>
  <span class="bk-crumb">Chapter {p["chapter"]["num"]} · {esc(p["topic"]["title"])} · page {p["index"] + 1} of {len(topic_pages)}</span>
  <button class="bk-toc-btn" type="button" aria-expanded="false" aria-controls="bk-drawer">Contents</button>
  <div class="bk-progress" aria-hidden="true"><i style="width:{(pos + 1) / len(pages) * 100:.1f}%"></i></div>
</div>
<div class="bk-drawer" id="bk-drawer" hidden>
  <div class="bk-drawer-inner">
    <div class="bk-drawer-head"><b>Contents</b><button class="bk-close" type="button">Close</button></div>
    <a class="bk-drawer-home" href="{root}index.html">All chapters</a>
    {toc_html(pages, p["path"])}
  </div>
</div>
<main class="bk-page">
{body.strip()}
</main>
<div class="bk-nav">
  {nav_card(prev_p, p["path"], "← Previous", "prev")}
  {nav_card(next_p, p["path"], "Next →", "next")}
</div>
<p class="bk-foot">Use ← and → keys to turn pages.</p>
<script src="{root}assets/book.js"></script>
{mermaid}
</body>
</html>
'''


def build_index(pages):
    first = {}
    rows = []
    for ch in BOOK["chapters"]:
        topics = ch.get("topics", [])
        if not topics:
            rows.append(f'<li class="ix-ch ix-later"><span class="ix-num">{ch["num"]:02d}</span>'
                        f'<span class="ix-title">{esc(ch["title"])}</span><span class="ix-state">Not started</span></li>')
            continue
        tps = []
        for tp in topics:
            items = "".join(
                f'<li><a href="{p["path"]}" data-page="{p["id"]}"><span class="bk-kind">{p["kind"]}</span>'
                f'<span>{esc(p["title"])}</span><span class="ix-seen" aria-label="visited"></span></a></li>'
                for p in pages if p["topic"] is tp)
            tps.append(f'<div class="ix-topic"><h3>{esc(tp["title"])}</h3><ol>{items}</ol></div>')
        count = sum(1 for p in pages if p["chapter"] is ch)
        rows.append(f'<li class="ix-ch ix-open"><span class="ix-num">{ch["num"]:02d}</span>'
                    f'<span class="ix-title">{esc(ch["title"])}</span><span class="ix-state">{len(topics)} topics · {count} pages</span>'
                    f'<div class="ix-topics">{"".join(tps)}</div></li>')
    start = pages[0]["path"]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(BOOK["title"])}</title>
<meta name="description" content="{esc(BOOK["subtitle"])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
{ICON}
<link rel="stylesheet" href="assets/book.css">
</head>
<body class="ix" data-page="index">
<main class="ix-wrap">
  <header class="ix-cover">
    <span class="ix-eyebrow">A study book · {len(pages)} pages so far</span>
    <h1>{esc(BOOK["title"])}</h1>
    <p>{esc(BOOK["subtitle"])}</p>
    <div class="ix-actions">
      <a class="ix-btn ix-primary" href="{start}">Start from page 1</a>
      <a class="ix-btn" id="ix-continue" href="{start}" hidden>Continue where you left off</a>
    </div>
    <div class="ix-how">
      <span><b class="bk-kind">Read</b> the idea in plain words</span>
      <span><b class="bk-kind">Try</b> it in a hands-on lab</span>
      <span><b class="bk-kind">Test</b> yourself with interview questions</span>
    </div>
  </header>
  <h2 class="ix-h2">Contents</h2>
  <ol class="ix-list">
    {"".join(rows)}
  </ol>
</main>
<script src="assets/book.js"></script>
</body>
</html>
'''


def main():
    pages = collect_pages()
    links = published_map(pages)
    for d in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if re.fullmatch(r"ch\d+", d):
            shutil.rmtree(os.path.join(OUT, d))
    for pos, p in enumerate(pages):
        dest = os.path.join(OUT, p["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(build_page(p, pages, pos, links))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(build_index(pages))
    for root, _, files in os.walk(OUT):
        for f in files:
            if "claude" in open(os.path.join(root, f), encoding="utf-8").read().lower():
                sys.exit(f"'claude' found in {os.path.join(root, f)}")
    print(f"Built {len(pages)} pages into {OUT}")


if __name__ == "__main__":
    main()
