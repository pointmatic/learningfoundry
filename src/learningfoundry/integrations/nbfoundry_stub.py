# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Placeholder exercise factory + test-double ExerciseProvider.

The placeholder dict is produced by the module-level :func:`stub_exercise`
factory so the resolver's ``status: stub`` path and the retained
:class:`NbfoundryStub` share one source of truth (Story K.d). The resolver
calls :func:`stub_exercise` directly for stub blocks, so an all-``stub``
curriculum never imports nbfoundry. ``NbfoundryStub`` is no longer the
default exercise provider — it survives only as a test double / explicit
"no-notebooks" injectable.
"""

from pathlib import Path


def stub_exercise(ref_path: Path) -> dict:  # type: ignore[type-arg]
    """Build the placeholder exercise dict for an un-built (``stub``) block.

    Returns a dict matching the ``ExerciseContent`` TS interface with
    ``status: "stub"`` so ``ExerciseBlock.svelte`` renders its placeholder
    card. No nbfoundry import, no file I/O — purely derived from ``ref_path``.
    """
    return {
        "type": "exercise",
        "source": "nbfoundry",
        "ref": str(ref_path),
        "status": "stub",
        "title": f"Exercise: {ref_path.stem}",
        "description": (
            f"<p>Exercise placeholder for <code>{ref_path}</code>. "
            "nbfoundry integration pending.</p>"
        ),
        "hints": [],
        "environment": None,
    }


class NbfoundryStub:
    """Test-double / "no-notebooks" ExerciseProvider.

    Delegates to :func:`stub_exercise`. Retained as an explicit injectable
    (e.g. a global stub override in tests or a notebooks-disabled build) —
    it is no longer the resolver's default provider and is never selected by
    the ``status`` switch, which calls :func:`stub_exercise` directly.
    """

    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        return stub_exercise(ref_path)
