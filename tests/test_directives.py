# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the tutorial-scaffold directive lint pass (Story J.d.2)."""

import pytest

from learningfoundry.directives import KNOWN_DIRECTIVES, lint_directives
from learningfoundry.exceptions import ContentResolutionError

LOCATION = "module `mod-01` / lesson `lesson-01` / block[0]"


class TestBalanced:
    """Balanced known-directive blocks lint cleanly."""

    def test_empty_markdown(self) -> None:
        lint_directives("", LOCATION)

    def test_no_directives(self) -> None:
        lint_directives("# Heading\n\nSome prose.\n", LOCATION)

    def test_single_balanced_directive(self) -> None:
        md = "::: worked-example\nA worked example body.\n:::\n"
        lint_directives(md, LOCATION)

    @pytest.mark.parametrize("name", KNOWN_DIRECTIVES)
    def test_each_known_directive_balances(self, name: str) -> None:
        md = f"::: {name}\nBody.\n:::\n"
        lint_directives(md, LOCATION)

    def test_three_back_to_back_balanced(self) -> None:
        md = (
            "::: worked-example\nA\n:::\n\n"
            "::: faded-example\nB\n:::\n\n"
            "::: independent-practice\nC\n:::\n"
        )
        lint_directives(md, LOCATION)

    def test_directive_with_blank_lines_inside(self) -> None:
        md = "::: worked-example\n\nFirst paragraph.\n\nSecond paragraph.\n\n:::\n"
        lint_directives(md, LOCATION)


class TestUnbalanced:
    """Known directive opens with no matching close raise."""

    def test_unclosed_known_directive_raises_with_lesson_location(self) -> None:
        md = "::: worked-example\nBody with no close.\n"
        with pytest.raises(ContentResolutionError) as exc:
            lint_directives(md, LOCATION)
        msg = str(exc.value)
        assert LOCATION in msg
        assert "worked-example" in msg
        # 1-based line number of the open.
        assert "line 1" in msg

    def test_two_unclosed_reports_most_recent_open(self) -> None:
        md = (
            "::: worked-example\nA\n"
            "::: faded-example\nB\n"
        )
        with pytest.raises(ContentResolutionError) as exc:
            lint_directives(md, LOCATION)
        # The "most recent" open is the one the author was probably
        # working on when they forgot the close.
        assert "faded-example" in str(exc.value)
        assert "line 3" in str(exc.value)

    def test_unclosed_after_balanced_block_still_raises(self) -> None:
        md = (
            "::: worked-example\nA\n:::\n\n"
            "::: independent-practice\nB with no close.\n"
        )
        with pytest.raises(ContentResolutionError) as exc:
            lint_directives(md, LOCATION)
        assert "independent-practice" in str(exc.value)

    def test_close_with_no_open_passes_through_silently(self) -> None:
        # Conservative: an orphan `:::` close almost always belongs to
        # an unknown-name directive we are not tracking. Flagging would
        # create false positives whenever an author uses `::: tip … :::`.
        lint_directives("Some text.\n:::\nMore text.\n", LOCATION)


class TestUnknownDirectivesPassThrough:
    """Unknown directive names are not tracked — they render as plain
    text via the markdown plugin's default block lexer."""

    def test_unknown_directive_open_does_not_raise(self) -> None:
        md = "::: tip\nA helpful note.\n:::\n"
        lint_directives(md, LOCATION)

    def test_unknown_open_without_close_does_not_raise(self) -> None:
        md = "::: tip\nA dangling unknown directive.\n"
        lint_directives(md, LOCATION)

    def test_unknown_open_inside_known_block_does_not_corrupt_balance(
        self,
    ) -> None:
        md = (
            "::: worked-example\n"
            "::: tip\n"
            "Inner text.\n"
            ":::\n"  # closes worked-example
        )
        lint_directives(md, LOCATION)


class TestFencedCodeBlocks:
    """Lines inside fenced code blocks are not scanned — the prose may
    be teaching directive syntax."""

    def test_directive_inside_backtick_fence_is_ignored(self) -> None:
        md = (
            "Here is how to write a worked example:\n\n"
            "```markdown\n"
            "::: worked-example\n"
            "Sample body.\n"
            ":::\n"
            "```\n"
        )
        lint_directives(md, LOCATION)

    def test_directive_inside_tilde_fence_is_ignored(self) -> None:
        md = (
            "~~~markdown\n"
            "::: faded-example\n"
            "Body.\n"
            ":::\n"
            "~~~\n"
        )
        lint_directives(md, LOCATION)

    def test_unclosed_directive_outside_fence_still_raises(self) -> None:
        # The fenced block does not "swallow" the unclosed real directive.
        md = (
            "```markdown\n"
            "::: worked-example\n"
            "fake (inside fence)\n"
            ":::\n"
            "```\n\n"
            "::: worked-example\n"
            "real (outside fence) — no close.\n"
        )
        with pytest.raises(ContentResolutionError) as exc:
            lint_directives(md, LOCATION)
        assert "worked-example" in str(exc.value)
