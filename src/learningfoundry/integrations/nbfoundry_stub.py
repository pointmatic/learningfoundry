# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Stub ExerciseProvider for v1 (nbfoundry not yet published)."""

from pathlib import Path


class NbfoundryStub:
    """Stub ExerciseProvider for v1.

    Returns a placeholder exercise dict with the ref path and a
    "coming soon" message. The real nbfoundry integration will
    generate Marimo applications for interactive model-training exercises.
    """

    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        return {
            "type": "exercise",
            "source": "nbfoundry",
            "ref": str(ref_path),
            "status": "stub",
            "title": f"Exercise: {ref_path.stem}",
            "instructions": (
                f"<p>Exercise placeholder for <code>{ref_path}</code>. "
                "nbfoundry integration pending.</p>"
            ),
            "sections": [],
            "expected_outputs": [],
            "hints": [],
            "environment": None,
        }
