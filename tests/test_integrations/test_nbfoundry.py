# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for NbfoundryProvider — the real ExerciseProvider backed by the
nbfoundry package (Story K.d). Mirrors test_quizazz.py: nbfoundry is mocked
via sys.modules so the suite needs no nbfoundry install."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from learningfoundry.exceptions import IntegrationError, LearningFoundryError
from learningfoundry.integrations.nbfoundry import NbfoundryProvider
from learningfoundry.integrations.protocols import ExerciseProvider

_REF = Path("exercises/mod-01-exercise-01.yml")
_BASE = Path("/curriculum")

# A representative compiled-exercise dict nbfoundry's compile_exercise emits
# (Story K.g): banner metadata + the marimo notebook source as a string. No
# sections/expected_outputs/submission — the notebook carries the cells/outputs.
# No `mode` — that is the curriculum author's ExerciseBlock field, not nbfoundry's.
_MOCK_EXERCISE = {
    "type": "exercise",
    "source": "nbfoundry",
    "ref": str(_REF),
    "title": "Train a tiny classifier",
    "description": "<p>Build and train …</p>",
    "hints": ["Start with nn.Conv2d."],
    "environment": {
        "python_version": "3.12",
        "dependencies": ["marimo", "torch"],
        "setup_instructions": "pip install -r requirements.txt",
    },
    "notebook_source": "import marimo\napp = marimo.App()\n# ... cells ...",
}


class TestNbfoundryProviderDelegation:
    def test_delegates_to_compile_exercise(self) -> None:
        mock_compile = MagicMock(return_value=dict(_MOCK_EXERCISE))
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            result = NbfoundryProvider().compile_exercise(_REF, _BASE)

        mock_compile.assert_called_once_with(_REF, _BASE)
        assert result == _MOCK_EXERCISE

    def test_returns_compiled_dict_unchanged(self) -> None:
        # Unlike QuizazzProvider, there is no wire-format relabel — the
        # nbfoundry dict passes through verbatim, including the
        # `notebook_source` string the build side (K.h) stages.
        mock_compile = MagicMock(return_value=dict(_MOCK_EXERCISE))
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            result = NbfoundryProvider().compile_exercise(_REF, _BASE)

        assert isinstance(result, dict)
        assert result["title"] == "Train a tiny classifier"
        assert result["notebook_source"] == _MOCK_EXERCISE["notebook_source"]
        # Static-render fields and `mode` are not in nbfoundry's contract.
        assert "sections" not in result
        assert "expected_outputs" not in result
        assert "mode" not in result

    def test_passes_ref_and_base_dir(self) -> None:
        mock_compile = MagicMock(return_value={})
        custom_ref = Path("exercises/mod-02-exercise-02.yml")
        custom_base = Path("/other/curriculum")
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            NbfoundryProvider().compile_exercise(custom_ref, custom_base)

        mock_compile.assert_called_once_with(custom_ref, custom_base)


class TestNbfoundryProviderErrorWrapping:
    def test_nbfoundry_error_wrapped_in_integration_error(self) -> None:
        mock_compile = MagicMock(side_effect=ValueError("missing required field"))
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            with pytest.raises(IntegrationError, match="nbfoundry failed"):
                NbfoundryProvider().compile_exercise(_REF, _BASE)

    def test_error_message_includes_ref_path(self) -> None:
        mock_compile = MagicMock(side_effect=RuntimeError("bad notebook"))
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            with pytest.raises(IntegrationError, match=str(_REF)):
                NbfoundryProvider().compile_exercise(_REF, _BASE)

    def test_original_error_is_chained(self) -> None:
        cause = ValueError("underlying cause")
        mock_compile = MagicMock(side_effect=cause)
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            with pytest.raises(IntegrationError) as exc_info:
                NbfoundryProvider().compile_exercise(_REF, _BASE)

        assert exc_info.value.__cause__ is cause

    def test_integration_error_inherits_base(self) -> None:
        mock_compile = MagicMock(side_effect=Exception("boom"))
        with patch.dict(
            "sys.modules",
            {"nbfoundry": MagicMock(compile_exercise=mock_compile)},
        ):
            with pytest.raises(LearningFoundryError):
                NbfoundryProvider().compile_exercise(_REF, _BASE)


class TestNbfoundryProviderMissingPackage:
    def test_missing_package_raises_import_error_with_extra_hint(self) -> None:
        with patch.dict("sys.modules", {"nbfoundry": None}):  # type: ignore[dict-item]
            with pytest.raises(ImportError, match="nbfoundry is not installed"):
                NbfoundryProvider().compile_exercise(_REF, _BASE)

    def test_import_error_names_the_extra(self) -> None:
        with patch.dict("sys.modules", {"nbfoundry": None}):  # type: ignore[dict-item]
            with pytest.raises(
                ImportError, match=r"learningfoundry\[nbfoundry\]"
            ):
                NbfoundryProvider().compile_exercise(_REF, _BASE)


class TestNbfoundryProviderProtocolContract:
    """Consumer-dependency-spec testing matrix: NbfoundryProvider must
    structurally satisfy the ExerciseProvider protocol (signature-identical
    compile_exercise — no `status` param)."""

    def test_satisfies_exercise_provider_protocol(self) -> None:
        provider: ExerciseProvider = NbfoundryProvider()
        assert isinstance(provider, ExerciseProvider)
