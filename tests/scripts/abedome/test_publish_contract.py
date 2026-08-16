"""Regression checks for the ABEDOME Core publication contract."""

from __future__ import annotations

import ast
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_VERSION = "2026.9.1.dev7"
EXPECTED_FRONTEND_VERSION = "2026.8.5.dev7"
EXPECTED_FRONTEND_SHA256 = (
    "886fabc0e7d924ce8a7f46a1dd3d624b707a9a17cd21934dc10736945cebd547"
)
EXPECTED_TRANSLATIONS_SHA256 = (
    "35005ce5491f64e48dfa0ca8436751474b8d8ec346a2406c2e2ba0f40427afcd"
)
EXPECTED_TRANSLATIONS_ASSET = "homeassistant-2026.8.1-py3-none-any.whl"


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


def test_publisher_packages_verified_backend_translations() -> None:
    """Ensure the image imports pinned locales and generates current English."""
    publish_workflow = (ROOT / ".github/workflows/publish-abedome-core.yml").read_text()
    build_workflow = (ROOT / ".github/workflows/build-abedome-core.yml").read_text()
    dockerfile = (ROOT / "Dockerfile").read_text()
    importer = (ROOT / "script/abedome/import_backend_translations.py").read_text()

    translation_import = publish_workflow.index(
        "Import pinned upstream backend translations"
    )
    image_build = publish_workflow.index(
        "Build and publish the immutable ABEDOME Core image"
    )
    image_check = publish_workflow.index("Confirm immutable image digest and metadata")

    for workflow in (publish_workflow, build_workflow):
        assert EXPECTED_TRANSLATIONS_SHA256 in workflow
        assert EXPECTED_TRANSLATIONS_ASSET in workflow
        assert "--require-language it" in workflow
    assert translation_import < image_build < image_check
    assert "python3 -m script.translations develop --all" in dockerfile
    assert "script/abedome/" in dockerfile
    docker_generation = dockerfile.index("python3 -m script.translations develop --all")
    docker_verification = dockerfile.index("verify --language en --language it")
    docker_install = dockerfile.index("uv pip install", docker_generation)
    assert docker_generation < docker_verification < docker_install
    assert "python -m script.translations develop --all" in build_workflow
    assert "Verify Core distribution translations" in build_workflow
    assert "verify --language en --language it" in publish_workflow
    assert "verify --language en --language it" in build_workflow
    assert "extractall(" not in importer
