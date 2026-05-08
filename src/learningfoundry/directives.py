# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tutorial-scaffold directive lint pass (Story J.d.2).

Story J.d.1 added a ``marked`` extension that wraps three named container
directives — ``::: worked-example``, ``::: faded-example``,
``::: independent-practice`` — in styled cards at *render* time. When a
known directive opens but never closes, the renderer silently fails to
match and the entire trailing markdown reads oddly. This module catches
those cases at *build* time so authors get a build-time error naming the
lesson and line, instead of debugging a render anomaly.

The lint is deliberately conservative:

- Only the three known directive names are tracked. Unknown names
  (``::: tip``) pass through untouched — same render-time semantics, no
  build-time noise. The vocabulary is owned by Story J.d.1.
- A bare ``:::`` close with no open on the known-directive stack is also
  passed through silently, because it almost always belongs to an
  unknown-directive block we are not tracking. Flagging it would create
  false positives whenever an author uses, e.g., ``::: tip … :::``.
- Lines inside fenced code blocks (``\\u0060\\u0060\\u0060`` or ``~~~``)
  are skipped so prose that *demonstrates* the directive syntax is not
  mistaken for an actual directive.
"""

import re

from learningfoundry.exceptions import ContentResolutionError

# Mirror of the TS-side ``KNOWN_DIRECTIVES`` list in
# ``sveltekit_template/src/lib/utils/markdown-directives.ts``. Keep these
# two in lockstep — adding a directive name here without registering it
# in the marked extension produces a build that lints clean but renders
# the new name as plain text.
KNOWN_DIRECTIVES: tuple[str, ...] = (
    "worked-example",
    "faded-example",
    "independent-practice",
)

_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_KNOWN_OPEN_RE = re.compile(
    r"^:::[ \t]+(" + "|".join(KNOWN_DIRECTIVES) + r")[ \t]*$"
)
_CLOSE_RE = re.compile(r"^:::[ \t]*$")


def lint_directives(markdown: str, location: str) -> None:
    """Raise ``ContentResolutionError`` on unbalanced known-directive blocks.

    Args:
        markdown: Raw markdown source to scan. Empty string returns cleanly.
        location: Lesson-location string (e.g.
            ``"module `mod-01` / lesson `lesson-01` / block[0]"``) used in
            the error message so authors can locate the offending file.

    Raises:
        ContentResolutionError: A known directive opens but never closes.
            The error names the directive, the opening line number (1-based),
            and the lesson location.
    """
    open_stack: list[tuple[str, int]] = []
    in_fence = False
    fence_marker: str | None = None

    for line_no, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.rstrip()

        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker == marker:
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue

        open_match = _KNOWN_OPEN_RE.match(stripped)
        if open_match:
            open_stack.append((open_match.group(1), line_no))
            continue
        if _CLOSE_RE.match(stripped) and open_stack:
            open_stack.pop()

    if open_stack:
        name, opened_at = open_stack[-1]
        raise ContentResolutionError(
            f"{location}: `::: {name}` opened on line {opened_at} has no "
            "closing `:::` on its own line"
        )
