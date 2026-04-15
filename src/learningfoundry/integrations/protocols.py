# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Provider protocols defining integration contracts for learningfoundry."""

from pathlib import Path
from typing import Protocol


class QuizProvider(Protocol):
    def compile_assessment(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        """Compile an assessment YAML file into a renderable manifest dict.

        Returns the quizazz manifest structure (questions, nav tree).
        Raises IntegrationError on parse/validation failure.
        """
        ...


class ExerciseProvider(Protocol):
    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        """Compile an exercise YAML file into a renderable exercise dict.

        Returns exercise content (instructions, code scaffolding, expected outputs).
        Raises IntegrationError on parse/validation failure.
        """
        ...


class VisualizationProvider(Protocol):
    def compile_visualization(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        """Compile a visualization definition into a renderable artifact dict.

        Returns visualization content (image data, HTML, or component config).
        Raises IntegrationError on parse/validation failure.
        """
        ...
