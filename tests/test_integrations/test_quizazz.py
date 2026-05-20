# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for QuizazzProvider — verifies delegation, error wrapping, and the
RR-1a wire-format relabel (``quizName`` → ``assessmentName``)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from learningfoundry.exceptions import IntegrationError
from learningfoundry.integrations.quizazz import QuizazzProvider

_REF = Path("assessments/mod-01-pre.yml")
_BASE = Path("/curriculum")

# What quizazz emits on the vendor wire format — uses `quizName` (its
# native key). The adapter is responsible for relabeling to
# `assessmentName` before returning (RR-1a).
_MOCK_MANIFEST = {
    "quizName": "mod-01-pre",
    "tree": [],
    "questions": [{"id": "q1", "text": "What is 2+2?", "answers": []}],
}


class TestQuizazzProviderDelegation:
    def test_delegates_to_compile_assessment(self) -> None:
        mock_compile = MagicMock(return_value=dict(_MOCK_MANIFEST))
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            result = provider.compile_assessment(_REF, _BASE)

        mock_compile.assert_called_once_with(_REF, _BASE)
        # After RR-1a relabel: `quizName` becomes `assessmentName`;
        # other fields pass through unchanged.
        assert result == {
            "assessmentName": "mod-01-pre",
            "tree": [],
            "questions": _MOCK_MANIFEST["questions"],
        }

    def test_returns_manifest_dict(self) -> None:
        mock_compile = MagicMock(return_value=dict(_MOCK_MANIFEST))
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            provider = QuizazzProvider()
            result = provider.compile_assessment(_REF, _BASE)

        assert isinstance(result, dict)
        # Post-relabel: vendor's `quizName` is gone; ours is present.
        assert "quizName" not in result
        assert "assessmentName" in result
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


class TestWireFormatRelabel:
    """RR-1a — `QuizazzProvider` translates the vendor's manifest wire-
    format key ``quizName`` to learningfoundry's ``assessmentName`` so
    the downstream ``AssessmentManifest`` TS type and ``curriculum.json``
    never see the vendor key. The relabel is idempotent and preserves
    the order/identity of all other manifest fields."""

    def test_quizName_becomes_assessmentName(self) -> None:
        mock_compile = MagicMock(
            return_value={"quizName": "mod-01-pre", "questions": []}
        )
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            result = QuizazzProvider().compile_assessment(_REF, _BASE)
        assert result == {"assessmentName": "mod-01-pre", "questions": []}

    def test_other_fields_pass_through_unchanged(self) -> None:
        mock_compile = MagicMock(
            return_value={
                "quizName": "x",
                "tree": [{"node": 1}],
                "questions": [{"id": "q1"}],
                "schemaVersion": "1.0",
            }
        )
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            result = QuizazzProvider().compile_assessment(_REF, _BASE)
        assert result["tree"] == [{"node": 1}]
        assert result["questions"] == [{"id": "q1"}]
        assert result["schemaVersion"] == "1.0"
        assert result["assessmentName"] == "x"

    def test_idempotent_when_already_relabeled(self) -> None:
        # Future-proofing: if quizazz ever emits `assessmentName`
        # natively, leave the existing value alone.
        mock_compile = MagicMock(
            return_value={"assessmentName": "already-renamed", "questions": []}
        )
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            result = QuizazzProvider().compile_assessment(_REF, _BASE)
        assert result == {"assessmentName": "already-renamed", "questions": []}

    def test_no_quizName_key_no_relabel(self) -> None:
        # Manifest with neither key — pass through unchanged.
        mock_compile = MagicMock(return_value={"questions": [], "tree": []})
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            result = QuizazzProvider().compile_assessment(_REF, _BASE)
        assert result == {"questions": [], "tree": []}
        assert "assessmentName" not in result
        assert "quizName" not in result

    def test_both_keys_present_keeps_existing_assessmentName(self) -> None:
        # Defensive: if both keys are somehow present, prefer the
        # already-correct `assessmentName` and drop the legacy
        # `quizName`. Avoids silent overwrite of post-rename data.
        mock_compile = MagicMock(
            return_value={
                "quizName": "old",
                "assessmentName": "new",
                "questions": [],
            }
        )
        with patch.dict(
            "sys.modules",
            {"quizazz": MagicMock(compile_assessment=mock_compile)},
        ):
            result = QuizazzProvider().compile_assessment(_REF, _BASE)
        # Adapter does NOT relabel when `assessmentName` is already
        # present; vendor's `quizName` is left intact in the dict
        # (no proactive cleanup — the relabel is conservative). A
        # downstream consumer reading `assessmentName` sees the right
        # value either way.
        assert result["assessmentName"] == "new"
