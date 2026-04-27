# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for QuizazzProvider — verifies delegation and error wrapping."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from learningfoundry.exceptions import IntegrationError
from learningfoundry.integrations.quizazz import QuizazzProvider

_REF = Path("assessments/mod-01-pre.yml")
_BASE = Path("/curriculum")

_MOCK_MANIFEST = {
    "quizName": "mod-01-pre",
    "tree": [],
    "questions": [{"id": "q1", "text": "What is 2+2?", "answers": []}],
}


class TestQuizazzProviderDelegation:
    def test_delegates_to_compile_assessment(self) -> None:
        mock_compile = MagicMock(return_value=_MOCK_MANIFEST)
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            result = provider.compile_assessment(_REF, _BASE)

        mock_compile.assert_called_once_with(_REF, _BASE)
        assert result == _MOCK_MANIFEST

    def test_returns_manifest_dict(self) -> None:
        mock_compile = MagicMock(return_value=_MOCK_MANIFEST)
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            result = provider.compile_assessment(_REF, _BASE)

        assert isinstance(result, dict)
        assert "quizName" in result
        assert "questions" in result

    def test_passes_ref_and_base_dir(self) -> None:
        mock_compile = MagicMock(return_value={})
        custom_ref = Path("assessments/mod-02-post.yml")
        custom_base = Path("/other/curriculum")
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            QuizazzProvider().compile_assessment(custom_ref, custom_base)

        mock_compile.assert_called_once_with(custom_ref, custom_base)


class TestQuizazzProviderErrorWrapping:
    def test_quizazz_error_wrapped_in_integration_error(self) -> None:
        mock_compile = MagicMock(side_effect=ValueError("missing required field"))
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            with pytest.raises(IntegrationError, match="quizazz failed"):
                provider.compile_assessment(_REF, _BASE)

    def test_error_message_includes_ref_path(self) -> None:
        mock_compile = MagicMock(side_effect=RuntimeError("bad YAML"))
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            with pytest.raises(IntegrationError, match=str(_REF)):
                provider.compile_assessment(_REF, _BASE)

    def test_original_error_is_chained(self) -> None:
        cause = ValueError("underlying cause")
        mock_compile = MagicMock(side_effect=cause)
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            with pytest.raises(IntegrationError) as exc_info:
                provider.compile_assessment(_REF, _BASE)

        assert exc_info.value.__cause__ is cause

    def test_integration_error_inherits_base(self) -> None:
        from learningfoundry.exceptions import LearningFoundryError

        mock_compile = MagicMock(side_effect=Exception("boom"))
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            with pytest.raises(LearningFoundryError):
                provider.compile_assessment(_REF, _BASE)


class TestQuizazzProviderMissingPackage:
    def test_missing_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"quizazz": None}):  # type: ignore[dict-item]
            provider = QuizazzProvider()
            with pytest.raises(ImportError, match="quizazz is not installed"):
                provider.compile_assessment(_REF, _BASE)
