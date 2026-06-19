# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Packaging-config tests (Story K.k).

The package version is single-sourced from ``src/learningfoundry/__init__.py``;
``pyproject.toml`` derives it dynamically via Hatchling. These guard against a
silent revert to a static ``[project].version``, which would re-introduce the
two-place version drift this story removed.
"""

import tomllib
from pathlib import Path
from typing import Any

import learningfoundry

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _pyproject() -> dict[str, Any]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_version_declared_dynamic() -> None:
    project = _pyproject()["project"]
    assert "version" in project.get("dynamic", [])


def test_no_static_version_key() -> None:
    # A static `[project].version` would shadow the dynamic source and drift.
    assert "version" not in _pyproject()["project"]


def test_hatch_version_source_is_dunder_init() -> None:
    hatch_version = _pyproject()["tool"]["hatch"]["version"]
    assert hatch_version["path"] == "src/learningfoundry/__init__.py"


def test_dunder_version_is_nonempty_str() -> None:
    assert isinstance(learningfoundry.__version__, str)
    assert learningfoundry.__version__
