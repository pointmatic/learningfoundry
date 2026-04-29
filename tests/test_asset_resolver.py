# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Tests for the markdown image asset resolver."""

import hashlib
from pathlib import Path

import pytest

from learningfoundry.asset_resolver import Asset, resolve_markdown_assets
from learningfoundry.exceptions import ContentResolutionError

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes-for-tests"


def _write_image(path: Path, content: bytes = PNG_BYTES) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _expected_dest(content: bytes, basename: str) -> str:
    digest = hashlib.sha256(content).hexdigest()[:12]
    return f"content/{digest}/{basename}"


class TestRelativeImageReference:
    def test_simple_co_located_image(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "diagram.png")
        md_path.write_text("See ![Diagram](diagram.png) below.")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        expected_url = "/" + _expected_dest(PNG_BYTES, "diagram.png")
        assert f"![Diagram]({expected_url})" in rewritten
        assert assets[0].source == (tmp_path / "diagram.png").resolve()
        assert assets[0].dest_relative == _expected_dest(PNG_BYTES, "diagram.png")

    def test_subdirectory_image(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "figures" / "arch.png")
        md_path.write_text("![](figures/arch.png)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        assert assets[0].source == (tmp_path / "figures" / "arch.png").resolve()
        assert _expected_dest(PNG_BYTES, "arch.png") in rewritten

    def test_image_with_title_attribute(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "diagram.png")
        md_path.write_text('![Alt](diagram.png "Hover title")')

        rewritten, _ = resolve_markdown_assets(md_path.read_text(), md_path)

        # Title preserved verbatim, including its quoting.
        assert '"Hover title"' in rewritten
        assert "![Alt](" in rewritten


class TestAbsoluteUrlPassthrough:
    def test_https_url_unchanged(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text("![CDN](https://cdn.example.com/foo.png)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "https://cdn.example.com/foo.png" in rewritten

    def test_http_url_unchanged(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text("![Plain HTTP](http://example.com/p.jpg)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "http://example.com/p.jpg" in rewritten

    def test_protocol_relative_unchanged(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text("![PR](//cdn.example.com/p.png)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "//cdn.example.com/p.png" in rewritten

    def test_root_absolute_unchanged(self, tmp_path: Path) -> None:
        # Already a SvelteKit static URL — must not be touched, even if the
        # path doesn't exist on the filesystem.
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text("![Local](/static/figs/foo.png)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "/static/figs/foo.png" in rewritten

    def test_data_uri_unchanged(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text(
            "![Inline](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA)"
        )

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "data:image/png;base64," in rewritten


class TestMissingAsset:
    def test_missing_image_raises_with_path_in_message(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text("![](does-not-exist.png)")

        with pytest.raises(ContentResolutionError) as exc_info:
            resolve_markdown_assets(md_path.read_text(), md_path)

        msg = str(exc_info.value)
        assert "does-not-exist.png" in msg
        assert str(md_path) in msg


class TestDeduplication:
    def test_same_image_referenced_twice_produces_one_asset(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "shared.png")
        md_path.write_text(
            "![first](shared.png)\n\nlater:\n\n![second](shared.png)\n"
        )

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        # Both references should rewrite to the same /content/<hash>/... URL.
        expected_url = "/" + _expected_dest(PNG_BYTES, "shared.png")
        assert rewritten.count(expected_url) == 2

    def test_different_files_same_basename_get_different_dests(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "a" / "diagram.png", content=b"version-A")
        _write_image(tmp_path / "b" / "diagram.png", content=b"version-B")
        md_path.write_text("![](a/diagram.png)\n![](b/diagram.png)\n")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 2
        # Hash differs → dest_relative differs → no collision.
        assert assets[0].dest_relative != assets[1].dest_relative
        assert assets[0].dest_relative.endswith("/diagram.png")
        assert assets[1].dest_relative.endswith("/diagram.png")


class TestHtmlImg:
    def test_html_img_double_quoted(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "diagram.png")
        md_path.write_text('<img src="diagram.png" alt="x">')

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        expected_url = "/" + _expected_dest(PNG_BYTES, "diagram.png")
        assert f'src="{expected_url}"' in rewritten

    def test_html_img_single_quoted(self, tmp_path: Path) -> None:
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "diagram.png")
        md_path.write_text("<img src='diagram.png' />")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        expected_url = "/" + _expected_dest(PNG_BYTES, "diagram.png")
        assert f"src='{expected_url}'" in rewritten

    def test_html_img_with_absolute_url_passthrough(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text('<img src="https://cdn.example.com/p.png">')

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "https://cdn.example.com/p.png" in rewritten


class TestFencedCodeBlocks:
    def test_image_inside_backtick_fence_is_not_rewritten(
        self, tmp_path: Path
    ) -> None:
        # An author showing how to write a markdown image in a code sample
        # must not have that sample silently rewritten.
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "real.png")
        md_path.write_text(
            "Real image:\n\n"
            "![Real](real.png)\n\n"
            "Code sample:\n\n"
            "```markdown\n"
            "![NotReal](nonexistent.png)\n"
            "```\n"
        )

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        # Only the real image was registered; the code-fenced one was not
        # resolved (so it didn't even raise on the missing file).
        assert len(assets) == 1
        assert "![NotReal](nonexistent.png)" in rewritten

    def test_image_inside_tilde_fence_is_not_rewritten(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        md_path.write_text(
            "~~~\n"
            "![NotReal](nonexistent.png)\n"
            "~~~\n"
        )

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert "nonexistent.png" in rewritten


class TestUrlNormalisation:
    def test_query_and_fragment_are_stripped_for_disk_lookup(
        self, tmp_path: Path
    ) -> None:
        # `?cache=1` is a runtime hint, not part of the on-disk filename.
        md_path = tmp_path / "lesson-01.md"
        _write_image(tmp_path / "diagram.png")
        md_path.write_text("![](diagram.png?cache=1#anchor)")

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert len(assets) == 1
        # The rewritten URL is the canonical hashed path; the query/fragment
        # are dropped (a future story can add cache-busting properly if
        # anyone actually wants it).
        expected_url = "/" + _expected_dest(PNG_BYTES, "diagram.png")
        assert expected_url in rewritten


class TestNoImagesNoOp:
    def test_markdown_with_no_images_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        md_path = tmp_path / "lesson-01.md"
        original = "# Heading\n\nJust text. No images. `inline code`.\n"
        md_path.write_text(original)

        rewritten, assets = resolve_markdown_assets(md_path.read_text(), md_path)

        assert assets == []
        assert rewritten == original


class TestAssetDataclass:
    def test_url_path_property(self) -> None:
        asset = Asset(
            source=Path("/abs/diagram.png"),
            dest_relative="content/abc123def456/diagram.png",
        )
        assert asset.url_path == "/content/abc123def456/diagram.png"
