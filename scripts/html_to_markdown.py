# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""
Download or read an HTML/MHTML page and convert it to Markdown.

Usage:
    pyve run python scripts/html_to_markdown.py <url> [-o OUTFILE]
    pyve run python scripts/html_to_markdown.py --file <path> [-o OUTFILE]
        [--extract-images] [--min-image-size BYTES]

Default rendering uses trafilatura for clean article-body extraction. With
--extract-images, embedded images in MHTML are written to <outfile-stem>_assets/
and the markdown references them by relative path; rendering switches to
markdownify (which preserves <img> tags) scoped to <article>/<main> when
present.

For sites that require auth or render content via JavaScript (e.g. IEEE
Xplore), save the page from your browser as MHTML and pass it via --file.
"""

from __future__ import annotations

import argparse
import email
import re
import sys
from email import policy
from pathlib import Path
from urllib.parse import urlparse

import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

EXT_BY_CTYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}


def fetch(url: str, timeout: int = 30) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _safe_filename(url: str, ctype: str, seen: set[str]) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "image"
    expected_ext = EXT_BY_CTYPE.get(ctype, "")
    if expected_ext and not name.lower().endswith(expected_ext):
        name += expected_ext
    name = re.sub(r"[^\w.-]", "_", name)
    candidate = name
    base, dot, ext = name.rpartition(".")
    i = 1
    while candidate in seen:
        candidate = f"{base}-{i}.{ext}" if dot else f"{name}-{i}"
        i += 1
    return candidate


def read_local(
    path: Path,
) -> tuple[str, str, dict[str, tuple[str, bytes, str]]]:
    """Return (html, source_url, resources).

    resources maps content_location URL -> (filename, bytes, content_type).
    Empty for non-MHTML inputs.
    """
    raw = path.read_bytes()
    if path.suffix.lower() not in {".mhtml", ".mht"}:
        return raw.decode("utf-8", errors="replace"), "", {}

    msg = email.message_from_bytes(raw, policy=policy.default)
    source_url = (
        msg.get("Snapshot-Content-Location") or msg.get("Content-Location") or ""
    )
    html = ""
    resources: dict[str, tuple[str, bytes, str]] = {}
    seen: set[str] = set()
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        loc = part.get("Content-Location", "") or ""
        if ctype == "text/html" and not html:
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            html = payload.decode(charset, errors="replace")
        elif ctype.startswith("image/") and loc:
            payload = part.get_payload(decode=True) or b""
            filename = _safe_filename(loc, ctype, seen)
            seen.add(filename)
            resources[loc] = (filename, payload, ctype)
    if not html:
        sys.exit(f"No text/html part found in MHTML: {path}")
    return html, source_url, resources


def extract_images(
    html: str,
    resources: dict[str, tuple[str, bytes, str]],
    assets_dir: Path,
    min_size: int,
) -> tuple[str, int]:
    """Write image parts >= min_size to assets_dir, rewrite <img src> to
    relative paths. Returns (rewritten_html, num_written).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        sys.exit("BeautifulSoup is required for --extract-images: `pyve run pip install beautifulsoup4`")

    soup = BeautifulSoup(html, "html.parser")
    written: dict[str, bytes] = {}
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src not in resources:
            continue
        filename, data, _ctype = resources[src]
        if len(data) < min_size:
            img.decompose()
            continue
        rel = f"{assets_dir.name}/{filename}"
        img["src"] = rel
        written[filename] = data

    if written:
        assets_dir.mkdir(parents=True, exist_ok=True)
        for filename, data in written.items():
            (assets_dir / filename).write_bytes(data)
    return str(soup), len(written)


def render_with_markdownify(html: str) -> str:
    """Markdownify, narrowed to <article>/<main> when present (skips nav/footer)."""
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify
    except ImportError:
        sys.exit("`pyve run pip install beautifulsoup4 markdownify`")
    soup = BeautifulSoup(html, "html.parser")
    scope = soup.find("article") or soup.find("main") or soup.body or soup
    return markdownify(str(scope), heading_style="ATX")


def render_with_trafilatura(html: str, url: str) -> str:
    try:
        import trafilatura
    except ImportError:
        return ""
    md = trafilatura.extract(
        html,
        url=url or None,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        include_comments=False,
    )
    return md or ""


def to_markdown(html: str, url: str, with_images: bool) -> str:
    if with_images:
        return render_with_markdownify(html)
    md = render_with_trafilatura(html, url)
    if md.strip():
        return md
    return render_with_markdownify(html)


def default_outfile(url_or_path: str) -> Path:
    if "://" in url_or_path:
        parsed = urlparse(url_or_path)
        slug = (parsed.path.strip("/").replace("/", "-") or parsed.netloc) or "page"
    else:
        slug = Path(url_or_path).stem
    return Path(f"{slug}.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("url", nargs="?", help="URL to fetch")
    src.add_argument("--file", type=Path, help="Local .html or .mhtml file")
    parser.add_argument(
        "-o",
        "--outfile",
        type=Path,
        help="Output file path (default: <slug>.md in cwd)",
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        help="(MHTML only) Write embedded images to <outfile-stem>_assets/ and reference by relative path.",
    )
    parser.add_argument(
        "--min-image-size",
        type=int,
        default=5000,
        help="Skip images smaller than this many bytes (default 5000, catches most UI icons). Use 0 to keep everything.",
    )
    args = parser.parse_args()

    if args.file:
        html, source_url, resources = read_local(args.file)
        outfile = args.outfile or default_outfile(str(args.file))
    else:
        html = fetch(args.url)
        source_url = args.url
        resources = {}
        outfile = args.outfile or default_outfile(args.url)

    n_images = 0
    if args.extract_images and resources:
        assets_dir = outfile.with_name(outfile.stem + "_assets")
        html, n_images = extract_images(html, resources, assets_dir, args.min_image_size)
    elif args.extract_images and not resources:
        print("warning: --extract-images requires an MHTML input with embedded images; skipping.", file=sys.stderr)

    md = to_markdown(html, source_url, with_images=args.extract_images)
    outfile.write_text(md, encoding="utf-8")
    msg = f"Wrote {len(md):,} chars to {outfile}"
    if n_images:
        msg += f" (+{n_images} images in {outfile.stem}_assets/)"
    print(msg)


if __name__ == "__main__":
    main()
