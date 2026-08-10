"""Regression checks for the ABEDOME Core publication contract."""

from __future__ import annotations

import ast
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_VERSION = "2026.9.1.dev5"
EXPECTED_FRONTEND_VERSION = "2026.8.5.dev5"
EXPECTED_FRONTEND_SHA256 = (
    "ca552d9b04d4c517226844c0c4b32df19cec6fb1a306110e95a12c0c9886fe02"
)


def _core_version() -> str:
    tree = ast.parse((ROOT / "homeassistant/const.py").read_text())
    values: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            values[node.target.id] = node.value.value
    return (
        f"{values['MAJOR_VERSION']}.{values['MINOR_VERSION']}.{values['PATCH_VERSION']}"
    )


def test_project_core_and_image_metadata_use_next_version() -> None:
    """Ensure Core and container metadata share the immutable version."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert project["project"]["version"] == EXPECTED_VERSION
    assert _core_version() == EXPECTED_VERSION
    assert "ARG BUILD_VERSION" in dockerfile
    assert "ARG BUILD_REVISION" in dockerfile
    assert 'io.hass.version="${BUILD_VERSION}"' in dockerfile
    assert 'org.opencontainers.image.version="${BUILD_VERSION}"' in dockerfile
    assert 'org.opencontainers.image.revision="${BUILD_REVISION}"' in dockerfile


def test_frontend_pin_is_consistent_across_core_and_workflows() -> None:
    """Ensure every Core build path verifies the same Frontend artifact."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependency = next(
        requirement
        for requirement in project["project"]["dependencies"]
        if requirement.startswith("abedome-frontend @ ")
    )
    expected_asset = f"abedome_frontend-{EXPECTED_FRONTEND_VERSION}-py3-none-any.whl"

    assert EXPECTED_FRONTEND_VERSION in dependency
    assert dependency.endswith(f"#sha256={EXPECTED_FRONTEND_SHA256}")

    for workflow_name in (
        "build-abedome-core.yml",
        "publish-abedome-core.yml",
    ):
        workflow = (ROOT / ".github/workflows" / workflow_name).read_text()
        assert EXPECTED_FRONTEND_VERSION in workflow
        assert EXPECTED_FRONTEND_SHA256 in workflow
        assert expected_asset in workflow


def test_publisher_verifies_before_promoting_bootstrap_alias() -> None:
    """Ensure publication verifies the image before moving the alias."""
    workflow = (ROOT / ".github/workflows/publish-abedome-core.yml").read_text()

    immutable_check = workflow.index("Confirm immutable image digest and metadata")
    alias_promotion = workflow.index(
        "Promote verified image to landing-page bootstrap alias"
    )
    alias_check = workflow.index("Confirm landing-page alias digest and metadata")

    assert "group: publish-abedome-core\n" in workflow
    assert "BUILD_VERSION=${{ inputs.version }}" in workflow
    assert "BUILD_REVISION=${{ github.sha }}" in workflow
    assert "$IMAGE_NAME:landingpage" in workflow
    assert immutable_check < alias_promotion < alias_check
    assert workflow.count('index .Config.Labels "io.hass.version"') >= 2
    assert (
        workflow.count('index .Config.Labels "org.opencontainers.image.version"') >= 2
    )
    assert (
        workflow.count('index .Config.Labels "org.opencontainers.image.revision"') >= 2
    )
