# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0
"""
End-to-end stack spike: YAML parse → content resolve → SvelteKit skeleton output.

This is a throwaway script that wires the full critical path together before
production modules are built. It is NOT part of the learningfoundry package.

Usage:
    pyve run python scripts/spike_e2e.py
"""

import json
import shutil
import tempfile
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).parent
FIXTURES_DIR = SCRIPTS_DIR / "fixtures"
CURRICULUM_YML = FIXTURES_DIR / "spike-curriculum.yml"


def load_curriculum(path: Path) -> dict:  # type: ignore[type-arg]
    with path.open() as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def resolve_content(curriculum: dict, base_dir: Path) -> dict:  # type: ignore[type-arg]
    """Walk content blocks and replace text refs with file contents."""
    resolved = dict(curriculum)
    resolved_modules = []
    for module in curriculum["curriculum"]["modules"]:
        resolved_lessons = []
        for lesson in module["lessons"]:
            resolved_blocks = []
            for block in lesson["content_blocks"]:
                if block["type"] == "text":
                    content_path = base_dir / block["ref"]
                    html = f"<p>{content_path.read_text().strip()}</p>"
                    resolved_blocks.append({"type": "text", "content": html})
                else:
                    resolved_blocks.append(block)
            resolved_lessons.append({**lesson, "content_blocks": resolved_blocks})
        resolved_modules.append({**module, "lessons": resolved_lessons})

    resolved["curriculum"] = {**curriculum["curriculum"], "modules": resolved_modules}
    return resolved


def generate_skeleton(resolved: dict, output_dir: Path) -> None:
    """Write a minimal SvelteKit skeleton with curriculum.json to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Minimal package.json placeholder
    pkg = {
        "name": "learningfoundry-spike",
        "version": "0.0.1",
        "private": True,
        "scripts": {"dev": "vite dev", "build": "vite build"},
    }
    (output_dir / "package.json").write_text(json.dumps(pkg, indent=2) + "\n")

    # curriculum.json consumed by the SvelteKit frontend
    curriculum_json = {
        "version": resolved["version"],
        "title": resolved["curriculum"]["title"],
        "description": resolved["curriculum"].get("description", ""),
        "modules": resolved["curriculum"]["modules"],
    }
    static_dir = output_dir / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "curriculum.json").write_text(
        json.dumps(curriculum_json, indent=2) + "\n"
    )


def main() -> None:
    print("=== learningfoundry end-to-end spike ===")
    print(f"Loading curriculum: {CURRICULUM_YML}")
    curriculum = load_curriculum(CURRICULUM_YML)

    print("Resolving content references...")
    resolved = resolve_content(curriculum, base_dir=FIXTURES_DIR)

    with tempfile.TemporaryDirectory(prefix="lf_spike_", delete=False) as tmp:
        output_dir = Path(tmp)

    print(f"Generating SvelteKit skeleton at: {output_dir}")
    generate_skeleton(resolved, output_dir)

    curriculum_json_path = output_dir / "static" / "curriculum.json"
    print(f"\nGenerated SvelteKit project at {output_dir}")
    print(f"  curriculum.json: {curriculum_json_path}")
    print(f"  curriculum.json exists: {curriculum_json_path.exists()}")

    data = json.loads(curriculum_json_path.read_text())
    module_count = len(data["modules"])
    lesson_count = sum(len(m["lessons"]) for m in data["modules"])
    print(f"  modules: {module_count}, lessons: {lesson_count}")
    print("\nSpike complete.")


if __name__ == "__main__":
    main()
