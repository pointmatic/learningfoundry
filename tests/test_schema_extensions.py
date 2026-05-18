# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for project-specific schema extensions (Story J.h)."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from learningfoundry.exceptions import SchemaExtensionError
from learningfoundry.schema_extensions import (
    SchemaExtensions,
    build_extended_meta_models,
    load_schema_extensions,
)
from learningfoundry.schema_v1 import CurriculumMeta, LessonMeta, ModuleMeta


def _ext(**sections: object) -> SchemaExtensions:
    """Helper: build a SchemaExtensions from kwargs (`version: "1"` baked in)."""
    return SchemaExtensions.model_validate({"version": "1", **sections})


class TestBaseBehaviourWithoutExtensions:
    """Sanity guard: an empty extensions doc must leave every meta model
    on its base class. Today's ``extra="allow"`` behaviour is the
    contract being preserved for backward compatibility."""

    def test_no_sections_returns_base_models(self) -> None:
        cur_cls, mod_cls, les_cls = build_extended_meta_models(_ext())
        assert cur_cls is CurriculumMeta
        assert mod_cls is ModuleMeta
        assert les_cls is LessonMeta

    def test_base_lesson_meta_still_allows_extras(self) -> None:
        # Regression guard: a typo'd field passes silently because the
        # caller chose not to opt into extensions.
        _, _, les_cls = build_extended_meta_models(_ext())
        m = les_cls.model_validate({"covres": ["typo-survives"]})
        assert m.model_dump()["covres"] == ["typo-survives"]


class TestStrictWhitelistRejection:
    """The whole point of J.h: a project that declares ``covers`` in its
    extensions file gets a build-time error when the LLM writes
    ``covres`` instead."""

    def _lesson_meta_with_covers(self) -> type[BaseModel]:
        ext = _ext(lesson_meta={
            "fields": {"covers": {"type": "list[str]", "default": []}},
        })
        _, _, les_cls = build_extended_meta_models(ext)
        return les_cls

    def test_declared_field_accepted(self) -> None:
        les_cls = self._lesson_meta_with_covers()
        m = les_cls.model_validate({"covers": ["a:topic-one", "b:topic-two"]})
        assert m.covers == ["a:topic-one", "b:topic-two"]  # type: ignore[attr-defined]

    def test_typo_rejected_with_field_name_in_error(self) -> None:
        les_cls = self._lesson_meta_with_covers()
        with pytest.raises(ValidationError) as exc:
            les_cls.model_validate({"covres": ["typo-name"]})
        assert "covres" in str(exc.value)

    def test_base_declared_fields_still_validated(self) -> None:
        # Strict mode doesn't lose the base model's own field checks.
        les_cls = self._lesson_meta_with_covers()
        m = les_cls.model_validate({"role": "opener", "covers": []})
        assert m.role == "opener"  # type: ignore[attr-defined]
        with pytest.raises(ValidationError):
            les_cls.model_validate({"duration_minutes": "fifteen"})


class TestFieldTypes:
    """Each supported `type:` value resolves to the right Python type
    and enforces the expected validation."""

    def test_str_type(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "author": {"type": "str", "required": False},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({"author": "Ada"})
        assert m.author == "Ada"  # type: ignore[attr-defined]
        with pytest.raises(ValidationError):
            les_cls.model_validate({"author": 42})

    def test_int_type(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "n_examples": {"type": "int", "required": False},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({"n_examples": 5})
        assert m.n_examples == 5  # type: ignore[attr-defined]
        with pytest.raises(ValidationError):
            les_cls.model_validate({"n_examples": "five"})

    def test_bool_type(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "hands_on": {"type": "bool", "required": False},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        assert les_cls.model_validate({"hands_on": True}).hands_on is True  # type: ignore[attr-defined]

    def test_list_str_type(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "prerequisites": {"type": "list[str]", "default": []},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({"prerequisites": ["intro", "loops"]})
        assert m.prerequisites == ["intro", "loops"]  # type: ignore[attr-defined]
        with pytest.raises(ValidationError):
            les_cls.model_validate({"prerequisites": "intro"})

    def test_enum_accepts_declared_values(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "difficulty": {
                "type": "enum",
                "values": ["intro", "intermediate", "advanced"],
                "required": False,
            },
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({"difficulty": "intermediate"})
        assert m.difficulty == "intermediate"  # type: ignore[attr-defined]

    def test_enum_rejects_out_of_vocab_value(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "difficulty": {
                "type": "enum",
                "values": ["intro", "intermediate", "advanced"],
                "required": False,
            },
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        with pytest.raises(ValidationError) as exc:
            les_cls.model_validate({"difficulty": "godlike"})
        # Pydantic's Literal error names the field and the allowed values.
        msg = str(exc.value)
        assert "difficulty" in msg
        assert "intermediate" in msg


class TestRequiredVsDefault:
    def test_required_no_default_rejects_omission(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "must_have": {"type": "str", "required": True},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        with pytest.raises(ValidationError) as exc:
            les_cls.model_validate({})
        assert "must_have" in str(exc.value)

    def test_optional_no_default_defaults_to_none(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "maybe": {"type": "str", "required": False},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({})
        assert m.maybe is None  # type: ignore[attr-defined]

    def test_explicit_default_applied(self) -> None:
        ext = _ext(lesson_meta={"fields": {
            "size": {"type": "int", "default": 10},
        }})
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({})
        assert m.size == 10  # type: ignore[attr-defined]


class TestPerModelExtraOverride:
    """``extra: allow`` per model restores today's behaviour for that
    model only, without affecting the strictness of other meta layers."""

    def test_lesson_meta_extra_allow_with_declared_fields(self) -> None:
        ext = _ext(lesson_meta={
            "extra": "allow",
            "fields": {"covers": {"type": "list[str]", "default": []}},
        })
        _, _, les_cls = build_extended_meta_models(ext)
        # Declared field is still type-checked.
        with pytest.raises(ValidationError):
            les_cls.model_validate({"covers": "not-a-list"})
        # Undeclared extras pass through.
        m = les_cls.model_validate({"covers": [], "experimental": 1})
        assert m.model_dump()["experimental"] == 1

    def test_independent_strictness_per_layer(self) -> None:
        ext = _ext(
            curriculum_meta={"fields": {
                "approach": {"type": "str", "required": False},
            }},
            lesson_meta={"extra": "allow", "fields": {}},
        )
        cur_cls, mod_cls, les_cls = build_extended_meta_models(ext)
        # curriculum_meta is strict — typo rejected.
        with pytest.raises(ValidationError):
            cur_cls.model_validate({"aproach": "spiral"})
        # lesson_meta opted back into allow — typo passes.
        m = les_cls.model_validate({"covres": ["typo-ok-here"]})
        assert m.model_dump()["covres"] == ["typo-ok-here"]
        # module_meta untouched — base extra="allow".
        assert mod_cls is ModuleMeta


class TestCurriculumMetaExtensions:
    def test_curriculum_meta_extended_with_new_field(self) -> None:
        ext = _ext(curriculum_meta={"fields": {
            "pedagogical_approach": {"type": "str", "required": False},
        }})
        cur_cls, _, _ = build_extended_meta_models(ext)
        m = cur_cls.model_validate({
            "target_audience": "engineers",
            "pedagogical_approach": "spiral",
        })
        assert m.target_audience == "engineers"  # type: ignore[attr-defined]
        assert m.pedagogical_approach == "spiral"  # type: ignore[attr-defined]

    def test_curriculum_meta_typo_rejected(self) -> None:
        ext = _ext(curriculum_meta={"fields": {
            "pedagogical_approach": {"type": "str", "required": False},
        }})
        cur_cls, _, _ = build_extended_meta_models(ext)
        with pytest.raises(ValidationError) as exc:
            cur_cls.model_validate({"pedagogcal_approach": "spiral"})
        assert "pedagogcal_approach" in str(exc.value)


class TestSchemaExtensionFileItselfIsStrict:
    """The extensions file must itself fail loudly on typos — otherwise
    a misspelled ``defalt:`` silently degrades the validation contract
    the file is supposed to tighten."""

    def test_unknown_top_level_section_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SchemaExtensions.model_validate({
                "version": "1",
                "lesso_meta": {"fields": {}},  # typo: lesso_meta
            })

    def test_unknown_field_attr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SchemaExtensions.model_validate({
                "version": "1",
                "lesson_meta": {"fields": {
                    "covers": {
                        "type": "list[str]",
                        "defalt": [],  # typo: defalt
                    },
                }},
            })

    def test_unsupported_field_type_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            SchemaExtensions.model_validate({
                "version": "1",
                "lesson_meta": {"fields": {
                    "foo": {"type": "uuid"},
                }},
            })
        # Pydantic's discriminator error names the field and the
        # accepted values; "uuid" is the unsupported type.
        assert "uuid" in str(exc.value) or "discriminator" in str(exc.value).lower()

    def test_enum_default_must_be_in_values(self) -> None:
        with pytest.raises(ValidationError) as exc:
            SchemaExtensions.model_validate({
                "version": "1",
                "lesson_meta": {"fields": {
                    "difficulty": {
                        "type": "enum",
                        "values": ["intro", "advanced"],
                        "default": "extreme",
                    },
                }},
            })
        assert "extreme" in str(exc.value)

    def test_enum_values_must_be_nonempty(self) -> None:
        with pytest.raises(ValidationError):
            SchemaExtensions.model_validate({
                "version": "1",
                "lesson_meta": {"fields": {
                    "x": {"type": "enum", "values": []},
                }},
            })

    def test_unsupported_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SchemaExtensions.model_validate({"version": "2"})


class TestBuildExtendedCurriculumV1:
    """Verify the full chained-rebuild (Lesson → Module → CurriculumDef →
    CurriculumV1) wires the extended meta types in at every layer."""

    def _minimal_doc(self, lesson_meta: dict | None = None) -> dict:  # type: ignore[type-arg]
        meta_block = {"meta": lesson_meta} if lesson_meta is not None else {}
        return {
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{
                        "id": "lesson-01", "title": "L",
                        **meta_block,
                        "content_blocks": [],
                    }],
                }],
            },
        }

    def test_no_extensions_returns_base_class(self) -> None:
        from learningfoundry.schema_extensions import build_extended_curriculum_v1
        from learningfoundry.schema_v1 import CurriculumV1

        cls = build_extended_curriculum_v1(_ext())
        assert cls is CurriculumV1

    def test_extension_propagates_to_lesson_meta_validation(self) -> None:
        from learningfoundry.schema_extensions import build_extended_curriculum_v1

        ext = _ext(lesson_meta={"fields": {
            "covers": {"type": "list[str]", "default": []},
        }})
        cls = build_extended_curriculum_v1(ext)

        # Good doc: declared `covers` is accepted.
        ok = cls.model_validate(self._minimal_doc({"covers": ["a:one"]}))
        assert ok.curriculum.modules[0].lessons[0].meta.covers == ["a:one"]

        # Bad doc: typo at lesson.meta level is rejected.
        with pytest.raises(ValidationError) as exc:
            cls.model_validate(self._minimal_doc({"covres": ["typo"]}))
        assert "covres" in str(exc.value)

    def test_curriculum_meta_extension_propagates(self) -> None:
        from learningfoundry.schema_extensions import build_extended_curriculum_v1

        ext = _ext(curriculum_meta={"fields": {
            "pedagogical_approach": {"type": "str", "required": False},
        }})
        cls = build_extended_curriculum_v1(ext)

        doc = self._minimal_doc()
        doc["curriculum"]["meta"] = {"pedagogcal_approach": "spiral"}  # typo
        with pytest.raises(ValidationError) as exc:
            cls.model_validate(doc)
        assert "pedagogcal_approach" in str(exc.value)


class TestParseCurriculumWithExtendedModel:
    """`parse_curriculum(model_cls=...)` honours the override and still
    runs the version-dispatch sanity check on the YAML file."""

    def _write_curriculum(
        self, tmp_path: Path, lesson_meta: dict | None = None
    ) -> Path:
        import yaml as _yaml
        meta_block = {"meta": lesson_meta} if lesson_meta is not None else {}
        doc = {
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{
                        "id": "lesson-01", "title": "L",
                        **meta_block,
                        "content_blocks": [],
                    }],
                }],
            },
        }
        path = tmp_path / "curriculum.yml"
        path.write_text(_yaml.safe_dump(doc))
        return path

    def test_override_used_when_supplied(self, tmp_path: Path) -> None:
        from learningfoundry.exceptions import CurriculumValidationError
        from learningfoundry.parser import parse_curriculum
        from learningfoundry.schema_extensions import build_extended_curriculum_v1

        ext = _ext(lesson_meta={"fields": {
            "covers": {"type": "list[str]", "default": []},
        }})
        extended_cls = build_extended_curriculum_v1(ext)

        # Without the override, the typo is silently accepted (base
        # extra="allow"). With the override, it must be rejected.
        bad_path = self._write_curriculum(tmp_path, {"covres": ["typo"]})
        parse_curriculum(bad_path)  # no override → passes
        with pytest.raises(CurriculumValidationError) as exc:
            parse_curriculum(bad_path, model_cls=extended_cls)
        assert "covres" in str(exc.value)

    def test_unsupported_version_still_rejected_with_override(
        self, tmp_path: Path
    ) -> None:
        # The override must not bypass version-dispatch validation —
        # otherwise a v99 YAML would silently parse as v1.
        import yaml as _yaml

        from learningfoundry.exceptions import CurriculumVersionError
        from learningfoundry.parser import parse_curriculum
        from learningfoundry.schema_extensions import build_extended_curriculum_v1

        path = tmp_path / "curriculum.yml"
        path.write_text(_yaml.safe_dump({"version": "99.0.0", "curriculum": {}}))
        extended_cls = build_extended_curriculum_v1(_ext())
        with pytest.raises(CurriculumVersionError):
            parse_curriculum(path, model_cls=extended_cls)


class TestResolveSchemaExtensionsPath:
    """File-path precedence: CLI > pyproject.toml > auto-discovery > none."""

    def test_returns_none_when_no_source(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        assert resolve_schema_extensions_path(None, curriculum) is None

    def test_cli_path_wins(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        # Also create an auto-discovery candidate to confirm CLI wins.
        auto = tmp_path / "learningfoundry-schema-extensions.yml"
        auto.write_text("version: '1'\n")
        cli = tmp_path / "elsewhere.yml"
        cli.write_text("version: '1'\n")

        result = resolve_schema_extensions_path(cli, curriculum)
        assert result == cli

    def test_pyproject_setting_used(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        custom = tmp_path / "custom-ext.yml"
        custom.write_text("version: '1'\n")
        (tmp_path / "pyproject.toml").write_text(
            "[tool.learningfoundry]\n"
            'schema_extensions = "custom-ext.yml"\n'
        )

        result = resolve_schema_extensions_path(None, curriculum)
        assert result == custom.resolve()

    def test_pyproject_beats_auto_discovery(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        custom = tmp_path / "custom-ext.yml"
        custom.write_text("version: '1'\n")
        (tmp_path / "learningfoundry-schema-extensions.yml").write_text(
            "version: '1'\n"
        )
        (tmp_path / "pyproject.toml").write_text(
            "[tool.learningfoundry]\n"
            'schema_extensions = "custom-ext.yml"\n'
        )

        result = resolve_schema_extensions_path(None, curriculum)
        assert result == custom.resolve()

    def test_auto_discovery_when_no_other_source(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        auto = tmp_path / "learningfoundry-schema-extensions.yml"
        auto.write_text("version: '1'\n")

        result = resolve_schema_extensions_path(None, curriculum)
        assert result == auto

    def test_malformed_pyproject_falls_through_to_auto(
        self, tmp_path: Path
    ) -> None:
        from learningfoundry.pipeline import resolve_schema_extensions_path

        curriculum = tmp_path / "curriculum.yml"
        curriculum.write_text("version: '1.0.0'\n")
        (tmp_path / "pyproject.toml").write_text("this is not valid toml ===\n")
        auto = tmp_path / "learningfoundry-schema-extensions.yml"
        auto.write_text("version: '1'\n")

        result = resolve_schema_extensions_path(None, curriculum)
        assert result == auto


class TestRunValidateWithExtensions:
    """End-to-end: `run_validate` picks up extensions and rejects typos."""

    def _write_curriculum(
        self, tmp_path: Path, lesson_meta: dict | None = None
    ) -> Path:
        import yaml as _yaml
        meta_block = {"meta": lesson_meta} if lesson_meta is not None else {}
        doc = {
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{
                        "id": "lesson-01", "title": "L",
                        **meta_block,
                        "content_blocks": [],
                    }],
                }],
            },
        }
        path = tmp_path / "curriculum.yml"
        path.write_text(_yaml.safe_dump(doc))
        return path

    def test_no_extensions_accepts_typo(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import run_validate

        path = self._write_curriculum(tmp_path, {"covres": ["typo"]})
        ok, errors = run_validate(path)
        assert ok, errors

    def test_extensions_file_auto_discovered_rejects_typo(
        self, tmp_path: Path
    ) -> None:
        from learningfoundry.pipeline import run_validate

        path = self._write_curriculum(tmp_path, {"covres": ["typo"]})
        (tmp_path / "learningfoundry-schema-extensions.yml").write_text(
            "version: '1'\n"
            "lesson_meta:\n"
            "  fields:\n"
            "    covers: { type: 'list[str]', default: [] }\n"
        )
        ok, errors = run_validate(path)
        assert not ok
        assert any("covres" in e for e in errors)

    def test_cli_path_override_used(self, tmp_path: Path) -> None:
        from learningfoundry.pipeline import run_validate

        path = self._write_curriculum(tmp_path, {"covres": ["typo"]})
        ext = tmp_path / "custom-ext.yml"
        ext.write_text(
            "version: '1'\n"
            "lesson_meta:\n"
            "  fields:\n"
            "    covers: { type: 'list[str]', default: [] }\n"
        )
        ok, errors = run_validate(path, schema_extensions_path=ext)
        assert not ok
        assert any("covres" in e for e in errors)


class TestCliSchemaExtensionsFlag:
    """`--schema-extensions` flag on the CLI exits non-zero when the
    project schema declares a field the curriculum then typo's."""

    def _write_curriculum(self, tmp_path: Path) -> Path:
        import yaml as _yaml
        doc = {
            "version": "1.0.0",
            "curriculum": {
                "title": "T",
                "modules": [{
                    "id": "mod-01", "title": "M",
                    "lessons": [{
                        "id": "lesson-01", "title": "L",
                        "meta": {"covres": ["typo"]},
                        "content_blocks": [],
                    }],
                }],
            },
        }
        path = tmp_path / "curriculum.yml"
        path.write_text(_yaml.safe_dump(doc))
        return path

    def test_validate_with_extensions_exits_nonzero(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from learningfoundry.cli import main

        curriculum = self._write_curriculum(tmp_path)
        ext = tmp_path / "custom-ext.yml"
        ext.write_text(
            "version: '1'\n"
            "lesson_meta:\n"
            "  fields:\n"
            "    covers: { type: 'list[str]', default: [] }\n"
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "-c", str(curriculum),
             "--schema-extensions", str(ext)],
        )
        assert result.exit_code != 0
        assert "covres" in result.output + (result.stderr or "")

    def test_validate_without_extensions_passes(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from learningfoundry.cli import main

        curriculum = self._write_curriculum(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "-c", str(curriculum)])
        assert result.exit_code == 0
        assert "OK" in result.output


class TestLoadSchemaExtensions:
    """File loading: missing file, malformed YAML, valid-shape end-to-end."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SchemaExtensionError) as exc:
            load_schema_extensions(tmp_path / "nope.yml")
        assert "not found" in str(exc.value).lower()

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "ext.yml"
        bad.write_text("version: '1'\nlesson_meta: [unbalanced\n")
        with pytest.raises(SchemaExtensionError):
            load_schema_extensions(bad)

    def test_non_mapping_top_level_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "ext.yml"
        bad.write_text("- just-a-list\n")
        with pytest.raises(SchemaExtensionError) as exc:
            load_schema_extensions(bad)
        assert "mapping" in str(exc.value).lower()

    def test_valid_file_loads_and_extends(self, tmp_path: Path) -> None:
        f = tmp_path / "ext.yml"
        f.write_text(
            "version: '1'\n"
            "lesson_meta:\n"
            "  fields:\n"
            "    covers:\n"
            "      type: list[str]\n"
            "      default: []\n"
        )
        ext = load_schema_extensions(f)
        _, _, les_cls = build_extended_meta_models(ext)
        m = les_cls.model_validate({"covers": ["a:one"]})
        assert m.covers == ["a:one"]  # type: ignore[attr-defined]

    def test_validation_error_wraps_with_path(self, tmp_path: Path) -> None:
        f = tmp_path / "ext.yml"
        f.write_text(
            "version: '1'\n"
            "lesson_meta:\n"
            "  fields:\n"
            "    covers: { type: nope }\n"
        )
        with pytest.raises(SchemaExtensionError) as exc:
            load_schema_extensions(f)
        assert str(f) in str(exc.value)
