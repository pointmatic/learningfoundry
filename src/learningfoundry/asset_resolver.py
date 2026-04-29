# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Markdown image asset resolution.

Scans a lesson's markdown source for image references (``![alt](path)``,
``![alt](path "title")``, and the HTML ``<img src="path">`` form), copies
the referenced files into the generated SvelteKit project's ``static/``
directory under a content-keyed location (``content/<sha256[:12]>/<basename>``),
and rewrites the markdown URLs to absolute paths that resolve at any
SvelteKit route.

Absolute URLs (``http://``, ``https://``, protocol-relative ``//``, root-
absolute ``/...``) and ``data:`` URIs pass through unchanged so authors can
mix CDN-hosted images with co-located ones.

Fenced code blocks (``` ``` ``` ``` or ``~~~``) are skipped so literal
``![](...)`` strings inside code samples are not treated as image refs.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from learningfoundry.exceptions import ContentResolutionError

logger = logging.getLogger("learningfoundry.asset_resolver")

# Markdown image: `![alt](url)` or `![alt](url "title")`.
# - Group 1: alt text (kept verbatim in the rewrite)
# - Group 2: URL (the bit we resolve and possibly rewrite)
# - Group 3: optional title (kept verbatim, including its surrounding quotes)
# We deliberately do not try to handle escaped parens inside the URL —
# CommonMark's full grammar is out of scope for v0.37.0; the common case
# is a plain relative path or an absolute URL with no whitespace.
_MD_IMAGE_RE = re.compile(
    r"""
    !\[(?P<alt>[^\]]*)\]    # ![alt]
    \(                       # opening paren
    \s*
    (?P<url>[^\s)]+)         # url (no whitespace, no closing paren)
    (?:\s+(?P<title>"[^"]*"|'[^']*'))?  # optional "title" or 'title'
    \s*
    \)                       # closing paren
    """,
    re.VERBOSE,
)

# HTML <img src="..."> in either single- or double-quoted form.
# We reuse the same `url` group name so the substitution callback is uniform.
_HTML_IMG_RE = re.compile(
    r"""
    (?P<prefix><img\b[^>]*?\bsrc\s*=\s*)
    (?P<quote>["'])
    (?P<url>[^"']+)
    (?P=quote)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# A fenced code block opens with ≥3 backticks or ≥3 tildes at the start of a
# line (allowing up to 3 leading spaces per CommonMark) and closes with the
# same fence character at the same length-or-greater. We track the active
# fence character to avoid closing a backtick fence with a tilde line.
_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")

# URL schemes / leading characters that mean "leave this alone — it is not
# a relative on-disk reference". Order matters only for clarity.
_PASSTHROUGH_PREFIXES: tuple[str, ...] = (
    "http://",
    "https://",
    "//",       # protocol-relative
    "/",        # already root-absolute (already a SvelteKit static path)
    "data:",    # inline data URI
    "mailto:",
    "tel:",
)


@dataclass(frozen=True)
class Asset:
    """A single asset that must be copied into the generated project.

    Attributes:
        source: Absolute path to the source file on disk.
        dest_relative: Destination path relative to the generated project's
            ``static/`` directory (e.g. ``"content/abc123def456/diagram.png"``).
            Always uses forward slashes — this becomes a URL fragment too.
    """

    source: Path
    dest_relative: str

    @property
    def url_path(self) -> str:
        """Absolute URL path the rewritten markdown references."""
        return "/" + self.dest_relative


def resolve_markdown_assets(
    markdown: str,
    markdown_path: Path,
) -> tuple[str, list[Asset]]:
    """Find every relative image reference in ``markdown`` and resolve it.

    Args:
        markdown: Raw markdown source.
        markdown_path: Filesystem path of the markdown file. Relative image
            URLs are resolved against ``markdown_path.parent``.

    Returns:
        Tuple of ``(rewritten_markdown, assets)``. ``rewritten_markdown`` has
        every relative image URL replaced with an absolute
        ``/content/<hash>/<basename>`` path. ``assets`` is the deduped list of
        source files to copy into the generated project (keyed on the content
        hash, so two refs to the same bytes produce one ``Asset``).

    Raises:
        ContentResolutionError: A relative image reference points at a file
            that does not exist, including the markdown file path in the
            error message.
    """
    md_dir = markdown_path.parent
    assets_by_dest: dict[str, Asset] = {}

    def _make_asset(rel_url: str) -> Asset | None:
        """Resolve ``rel_url`` to an Asset, or None if it should pass through.

        Raises:
            ContentResolutionError: The path resolves but the file is missing.
        """
        if _is_passthrough(rel_url):
            return None
        # Strip any fragment / query — image URLs rarely have them, but a
        # `?cache=1` suffix should not become part of the on-disk lookup.
        clean = rel_url.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            return None
        source = (md_dir / clean).resolve()
        if not source.is_file():
            raise ContentResolutionError(
                f"image asset not found: `{clean}` "
                f"(resolved to `{source}`, referenced from `{markdown_path}`)"
            )
        try:
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
        except OSError as exc:
            raise ContentResolutionError(
                f"failed to read image asset `{source}` "
                f"(referenced from `{markdown_path}`): {exc}"
            ) from exc
        dest_relative = f"content/{digest}/{source.name}"
        asset = assets_by_dest.get(dest_relative)
        if asset is None:
            asset = Asset(source=source, dest_relative=dest_relative)
            assets_by_dest[dest_relative] = asset
        return asset

    rewritten_lines: list[str] = []
    in_fence = False
    fence_char: str | None = None

    for line in markdown.splitlines(keepends=True):
        match = _FENCE_RE.match(line)
        if match:
            fence = match.group("fence")
            if not in_fence:
                in_fence = True
                fence_char = fence[0]
            elif fence[0] == fence_char and len(fence) >= 3:
                in_fence = False
                fence_char = None
            rewritten_lines.append(line)
            continue

        if in_fence:
            rewritten_lines.append(line)
            continue

        rewritten_lines.append(_rewrite_line(line, _make_asset))

    rewritten = "".join(rewritten_lines)
    return rewritten, list(assets_by_dest.values())


def _is_passthrough(url: str) -> bool:
    """Return True if ``url`` should not be treated as an on-disk reference."""
    return any(url.startswith(p) for p in _PASSTHROUGH_PREFIXES)


def _rewrite_line(
    line: str,
    make_asset: Callable[[str], Asset | None],
) -> str:
    """Rewrite all image refs in a single non-fenced line."""

    def _md_sub(m: re.Match[str]) -> str:
        url = m.group("url")
        asset = make_asset(url)
        if asset is None:
            return m.group(0)
        title = m.group("title")
        title_part = f' {title}' if title else ''
        return f'![{m.group("alt")}]({asset.url_path}{title_part})'

    def _html_sub(m: re.Match[str]) -> str:
        url = m.group("url")
        asset = make_asset(url)
        if asset is None:
            return m.group(0)
        quote = m.group("quote")
        return f'{m.group("prefix")}{quote}{asset.url_path}{quote}'

    line = _MD_IMAGE_RE.sub(_md_sub, line)
    line = _HTML_IMG_RE.sub(_html_sub, line)
    return line
