# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for D3foundryStub — verifies return structure matches VisualizationContent."""

from pathlib import Path

from learningfoundry.integrations.d3foundry_stub import D3foundryStub

# Keys required by the VisualizationContent TypeScript interface in lib/types/index.ts
_VISUALIZATION_CONTENT_KEYS = {
    "type",
    "source",
    "ref",
    "status",
    "title",
    "caption",
    "render_type",
    "content",
    "content_type",
    "alt_text",
}


class TestD3foundryStub:
    def setup_method(self) -> None:
        self.stub = D3foundryStub()
        self.ref = Path("visualizations/mod-01-vis-01.yml")
        self.base = Path("/curriculum")
        self.result = self.stub.compile_visualization(self.ref, self.base)

    def test_returns_dict(self) -> None:
        assert isinstance(self.result, dict)

    def test_has_all_visualization_content_keys(self) -> None:
        assert _VISUALIZATION_CONTENT_KEYS.issubset(self.result.keys())

    def test_type_is_visualization(self) -> None:
        assert self.result["type"] == "visualization"

    def test_source_is_d3foundry(self) -> None:
        assert self.result["source"] == "d3foundry"

    def test_status_is_stub(self) -> None:
        assert self.result["status"] == "stub"

    def test_ref_contains_path(self) -> None:
        assert "mod-01-vis-01" in self.result["ref"]

    def test_title_contains_stem(self) -> None:
        assert "mod-01-vis-01" in self.result["title"]

    def test_render_type_is_image(self) -> None:
        assert self.result["render_type"] == "image"

    def test_content_type_is_svg(self) -> None:
        assert self.result["content_type"] == "image/svg+xml"

    def test_content_is_empty_string(self) -> None:
        assert self.result["content"] == ""

    def test_caption_is_empty_string(self) -> None:
        assert self.result["caption"] == ""

    def test_alt_text_mentions_path(self) -> None:
        assert "mod-01-vis-01" in self.result["alt_text"]

    def test_different_refs_produce_different_titles(self) -> None:
        other = self.stub.compile_visualization(
            Path("visualizations/mod-02-vis-02.yml"), self.base
        )
        assert other["title"] != self.result["title"]
