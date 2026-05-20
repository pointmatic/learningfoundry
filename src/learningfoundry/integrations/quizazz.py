# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""quizazz integration — AssessmentProvider backed by the quizazz package."""

from pathlib import Path

from learningfoundry.exceptions import IntegrationError


class QuizazzProvider:
    """AssessmentProvider implementation backed by the quizazz package.

    Delegates to ``quizazz.compile_assessment()`` to produce a
    manifest dict from a single assessment YAML file.

    Requires the ``quizazz`` package:
        pip install learningfoundry[quizazz]
    """

    def compile_assessment(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        """Compile an assessment YAML file into a renderable manifest dict.

        Args:
            ref_path: Path to the assessment YAML file (relative to base_dir).
            base_dir: Root directory for resolving paths within the YAML.

        Returns:
            Compiled quiz manifest dict (questions, nav tree).

        Raises:
            IntegrationError: If quizazz raises any error during
                validation or compilation.
            ImportError: If quizazz is not installed.
        """
        try:
            from quizazz import (
                compile_assessment,
            )
        except ImportError as exc:
            raise ImportError(
                "quizazz is not installed. "
                "Install it with: pip install learningfoundry[quizazz]"
            ) from exc

        try:
            manifest = compile_assessment(ref_path, base_dir)
        except Exception as exc:
            raise IntegrationError(
                f"quizazz failed to compile assessment `{ref_path}`: {exc}"
            ) from exc

        # Wire-format relabel (RR-1a in dependency-spec.md; project-essentials
        # "Hidden Coupling"): quizazz emits `quizName` on the vendor wire
        # format; learningfoundry's downstream AssessmentManifest TS type
        # uses `assessmentName`. Translate at the adapter boundary so the
        # vendor key never appears in `curriculum.json`. Idempotent: if the
        # dict already has `assessmentName` (future-proofing), leave it
        # alone.
        if "quizName" in manifest and "assessmentName" not in manifest:
            manifest["assessmentName"] = manifest.pop("quizName")
        return manifest  # type: ignore[no-any-return]
