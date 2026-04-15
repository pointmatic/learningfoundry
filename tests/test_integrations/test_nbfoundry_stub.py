# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for NbfoundryStub — verifies return structure matches ExerciseContent."""

from pathlib import Path

from learningfoundry.integrations.nbfoundry_stub import NbfoundryStub

# Keys required by the ExerciseContent TypeScript interface in lib/types/index.ts
_EXERCISE_CONTENT_KEYS = {
    "type",
    "source",
    "ref",
    "status",
    "title",
    "instructions",
    "sections",
    "expected_outputs",
    "hints",
    "environment",
}


class TestNbfoundryStub:
    def setup_method(self) -> None:
        self.stub = NbfoundryStub()
        self.ref = Path("exercises/mod-01-exercise-01.yml")
        self.base = Path("/curriculum")
        self.result = self.stub.compile_exercise(self.ref, self.base)

    def test_returns_dict(self) -> None:
        assert isinstance(self.result, dict)

    def test_has_all_exercise_content_keys(self) -> None:
        assert _EXERCISE_CONTENT_KEYS.issubset(self.result.keys())

    def test_type_is_exercise(self) -> None:
        assert self.result["type"] == "exercise"

    def test_source_is_nbfoundry(self) -> None:
        assert self.result["source"] == "nbfoundry"

    def test_status_is_stub(self) -> None:
        assert self.result["status"] == "stub"

    def test_ref_contains_path(self) -> None:
        assert "mod-01-exercise-01" in self.result["ref"]

    def test_title_contains_stem(self) -> None:
        assert "mod-01-exercise-01" in self.result["title"]

    def test_sections_is_list(self) -> None:
        assert isinstance(self.result["sections"], list)

    def test_expected_outputs_is_list(self) -> None:
        assert isinstance(self.result["expected_outputs"], list)

    def test_hints_is_list(self) -> None:
        assert isinstance(self.result["hints"], list)

    def test_environment_is_none(self) -> None:
        assert self.result["environment"] is None

    def test_different_refs_produce_different_titles(self) -> None:
        other = self.stub.compile_exercise(
            Path("exercises/mod-02-exercise-02.yml"), self.base
        )
        assert other["title"] != self.result["title"]
