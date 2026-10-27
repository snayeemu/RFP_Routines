#!/usr/bin/env python3
"""MyBidMatch helpers (public pages, no login).

  mybidmatch.py list <day-url>       -> JSON list of articles on a day page (go?doc=...)
  mybidmatch.py article <article-url> -> JSON with article text and every URL found in it

Article "URL:" anchors are sometimes malformed HTML (e.g. `...viewa>`), so URLs are
pulled from the raw HTML with a regex, not only from <a> tags.
"""
import html
import json
import re
import subprocess
import sys
import urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE = "https://mybidmatch.outreachsystems.com"
NOISE = ("outreachsystems.com/resources", "neoserra.com", "support.outreachsystems.com")


def fetch(url):
    # curl, not urllib: this Python build cannot verify HTTPS certificates on this Mac.
    out = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "60", "-A", UA["User-Agent"], url],
                         capture_output=True, timeout=90)
    if out.returncode:
        raise RuntimeError(f"curl {url}: {out.stderr.decode('utf-8', 'replace').strip()}")
    return out.stdout.decode("utf-8", "replace")


def strip(fragment):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def list_day(url):
    page = fetch(url)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
        link = re.search(r'href="([^"]*article\?doc=[^"]+)"', tr)
        if len(cells) < 6 or not link:
            continue
        rows.append({
            "seq": strip(cells[0]),
            "source": strip(cells[1]),
            "agency": strip(cells[2]),
            "fsg": strip(cells[3]),
            "title": strip(cells[4]),
            "keywords": strip(cells[5]),
            "article_url": urllib.parse.urljoin(BASE, html.unescape(link.group(1))),
        })
    return {"day_url": url, "count": len(rows), "articles": rows}


def article(url):
    page = fetch(url)
    text = strip(page)
    marker = text.find("272-6000")
    body = text[marker + 8:] if marker >= 0 else text
    # Malformed anchors end the visible URL with "a>" instead of "</a>" (e.g. `.../viewa>`).
    page = re.sub(r"(https?://[^\s\"'<>]+?)a>", r"\1 ", page)
    urls = []
    for u in re.findall(r"https?://[^\s\"'<>]+", page):
        u = html.unescape(u).rstrip(".,;)")
        if any(n in u for n in NOISE) or "mybidmatch.outreachsystems.com" in u:
            continue
        if u not in urls:
            urls.append(u)
    # Visible link text is often truncated (".js", ".ph"); keep the longest variant of each URL.
    urls = [u for u in urls if not any(o != u and o.startswith(u) for o in urls)]
    sam = [u for u in urls if "sam.gov/opp/" in u]
    return {"article_url": url, "text": body.strip(), "urls": urls, "sam_urls": sam}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("list", "article"):
        sys.exit(__doc__)
    fn = list_day if sys.argv[1] == "list" else article
    print(json.dumps(fn(sys.argv[2]), indent=2, ensure_ascii=False))
