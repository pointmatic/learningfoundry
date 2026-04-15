# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""Stub VisualizationProvider for v1 (d3foundry not yet published)."""

from pathlib import Path


class D3foundryStub:
    """Stub VisualizationProvider for v1.

    Returns a placeholder visualization dict. The real d3foundry
    integration will generate Matplotlib images, D3.js interactive
    visualizations, or brokered artifacts (CNN Explainer, etc.).
    """

    def compile_visualization(self, ref_path: Path, base_dir: Path) -> dict:  # type: ignore[type-arg]
        return {
            "type": "visualization",
            "source": "d3foundry",
            "ref": str(ref_path),
            "status": "stub",
            "title": f"Visualization: {ref_path.stem}",
            "caption": "",
            "render_type": "image",
            "content": "",
            "content_type": "image/svg+xml",
            "alt_text": f"Placeholder for {ref_path}",
        }
