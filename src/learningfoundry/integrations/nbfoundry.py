# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""nbfoundry integration — ExerciseProvider backed by the nbfoundry package."""

from pathlib import Path

from learningfoundry.exceptions import IntegrationError


class NbfoundryProvider:
    """ExerciseProvider implementation backed by the nbfoundry package.

    Delegates to ``nbfoundry.compile_exercise()`` to produce a renderable
    exercise dict from a single exercise YAML file.

    Requires the ``nbfoundry`` package:
        pip install learningfoundry[nbfoundry]

    The ``status`` switch (stub vs. ready) is handled in the resolver, not
    here — ``compile_exercise`` is kept signature-identical to the
    ``ExerciseProvider`` protocol and to ``nbfoundry.compile_exercise`` so
    the protocol-match contract holds. Do not add a ``status`` parameter.
    """

    def compile_exercise(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        """Compile an exercise YAML file into a renderable exercise dict.

        Args:
            ref_path: Path to the exercise YAML file (relative to base_dir).
            base_dir: Root directory for resolving paths within the YAML.

        Returns:
            Compiled exercise dict (instructions, sections, expected outputs,
            hints, assets).

        Raises:
            IntegrationError: If nbfoundry raises any error during
                validation or compilation.
            ImportError: If nbfoundry is not installed.
        """
        try:
            from nbfoundry import compile_exercise
        except ImportError as exc:
            raise ImportError(
                "nbfoundry is not installed. "
                "Install it with: pip install learningfoundry[nbfoundry]"
            ) from exc

        try:
            return compile_exercise(ref_path, base_dir)  # type: ignore[no-any-return]
        except Exception as exc:
            raise IntegrationError(
                f"nbfoundry failed to compile exercise `{ref_path}`: {exc}"
            ) from exc
