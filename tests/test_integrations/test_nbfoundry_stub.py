# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for NbfoundryStub — verifies return structure matches ExerciseContent."""

from pathlib import Path

from learningfoundry.integrations.nbfoundry_stub import NbfoundryStub, stub_exercise

# Keys required by the ExerciseContent TypeScript interface in lib/types/index.ts
# (Story K.j.1 banner shape — `instructions`→`description`; the static
# `sections`/`expected_outputs`/`assets` fields are retired with Option C).
_EXERCISE_CONTENT_KEYS = {
    "type",
    "source",
    "ref",
    "status",
    "title",
    "description",
    "hints",
    "environment",
}

# Retired Option-B fields the banner shape must no longer emit.
_RETIRED_KEYS = {"instructions", "sections", "expected_outputs", "assets"}


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

    def test_description_is_str(self) -> None:
        assert isinstance(self.result["description"], str)

    def test_drops_retired_static_fields(self) -> None:
        assert _RETIRED_KEYS.isdisjoint(self.result.keys())

    def test_hints_is_list(self) -> None:
        assert isinstance(self.result["hints"], list)

    def test_environment_is_none(self) -> None:
        assert self.result["environment"] is None

    def test_different_refs_produce_different_titles(self) -> None:
        other = self.stub.compile_exercise(
            Path("exercises/mod-02-exercise-02.yml"), self.base
        )
        assert other["title"] != self.result["title"]


class TestStubExerciseHelper:
    """The placeholder dict is produced by a single module-level factory
    (Story K.d) so both the resolver's `status: stub` path and the
    retained `NbfoundryStub` share one source of truth — and the resolver
    never has to import or call nbfoundry for a stub block."""

    ref = Path("exercises/mod-01-exercise-01.yml")

    def test_returns_dict_with_all_exercise_content_keys(self) -> None:
        result = stub_exercise(self.ref)
        assert isinstance(result, dict)
        assert _EXERCISE_CONTENT_KEYS.issubset(result.keys())

    def test_status_is_stub(self) -> None:
        assert stub_exercise(self.ref)["status"] == "stub"

    def test_title_and_ref_carry_the_path(self) -> None:
        result = stub_exercise(self.ref)
        assert "mod-01-exercise-01" in result["title"]
        assert "mod-01-exercise-01" in result["ref"]

    def test_stub_provider_delegates_to_helper(self) -> None:
        # NbfoundryStub.compile_exercise is now a thin wrapper over the
        # shared factory — both produce an identical placeholder.
        assert NbfoundryStub().compile_exercise(self.ref, Path("/curriculum")) == (
            stub_exercise(self.ref)
        )
