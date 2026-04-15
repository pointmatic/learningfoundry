# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""quizazz integration — QuizProvider backed by quizazz_builder."""

from pathlib import Path

from learningfoundry.exceptions import IntegrationError


class QuizazzProvider:
    """QuizProvider implementation backed by quizazz_builder.

    Delegates to ``quizazz_builder.compile_assessment()`` to produce a
    manifest dict from a single assessment YAML file.

    Requires the ``quizazz-builder`` package:
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
            IntegrationError: If quizazz_builder raises any error during
                validation or compilation.
            ImportError: If quizazz-builder is not installed.
        """
        try:
            from quizazz_builder import (
                compile_assessment,  # type: ignore[import-untyped]
            )
        except ImportError as exc:
            raise ImportError(
                "quizazz-builder is not installed. "
                "Install it with: pip install learningfoundry[quizazz]"
            ) from exc

        try:
            return compile_assessment(ref_path, base_dir)  # type: ignore[no-any-return]
        except Exception as exc:
            raise IntegrationError(
                f"quizazz failed to compile assessment `{ref_path}`: {exc}"
            ) from exc
