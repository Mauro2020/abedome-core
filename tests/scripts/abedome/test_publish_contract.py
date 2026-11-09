"""Regression checks for the ABEDOME Core publication contract."""

from __future__ import annotations

import ast
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_VERSION = "2026.11.0"
EXPECTED_FRONTEND_VERSION = "20261028.4"
EXPECTED_FRONTEND_ASSET = "abedome_frontend-20261028.4-py3-none-any.whl"
EXPECTED_FRONTEND_SHA_VARIABLE = "ABEDOME_FRONTEND_20261028_4_SHA256"
EXPECTED_TRANSLATIONS_SHA256 = (
    "7ca5fbde9dea879ac7723949fc84347aac5182e6309c357b2e4973fd391b00f7"
)
EXPECTED_TRANSLATIONS_ASSET = "homeassistant-2026.11.0-py3-none-any.whl"


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


def test_project_core_and_image_metadata_use_stable_version() -> None:
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


def test_frontend_release_is_a_fail_closed_publication_gate() -> None:
    """Ensure both build paths require the real released Frontend digest."""
    for workflow_name in (
        "build-abedome-core.yml",
        "publish-abedome-core.yml",
    ):
        workflow = (ROOT / ".github/workflows" / workflow_name).read_text()
        assert EXPECTED_FRONTEND_VERSION in workflow
        assert EXPECTED_FRONTEND_ASSET in workflow
        assert EXPECTED_FRONTEND_SHA_VARIABLE in workflow
        assert '[[ ! "$FRONTEND_SHA256" =~ ^[0-9a-f]{64}$ ]]' in workflow
        assert (
            'echo "$FRONTEND_SHA256  $frontend_wheel" | sha256sum --check' in workflow
        )

    publish_workflow = (ROOT / ".github/workflows/publish-abedome-core.yml").read_text()
    build_workflow = (ROOT / ".github/workflows/build-abedome-core.yml").read_text()
    assert 'requirement.startswith("abedome-frontend @ ")' in publish_workflow
    assert "assert dependency == expected_frontend_dependency" in publish_workflow
    assert "Validate the pinned Frontend dependency" in build_workflow
    assert 'if requirement.startswith("abedome-frontend @ ")' in build_workflow
    assert "assert dependency == expected" in build_workflow


def test_publisher_verifies_candidate_before_creating_product_tags() -> None:
    """Ensure only a verified candidate can receive product tags."""
    workflow = (ROOT / ".github/workflows/publish-abedome-core.yml").read_text()

    candidate_build = workflow.index(
        "Build and publish the uniquely tagged candidate image"
    )
    candidate_check = workflow.index(
        "Verify candidate digest, metadata, translations, and Frontend"
    )
    alias_promotion = workflow.index(
        "Promote verified digest to immutable version and bootstrap alias"
    )
    alias_check = workflow.index("Confirm immutable version and landing-page alias")

    assert "group: publish-abedome-core\n" in workflow
    assert "if: github.ref == 'refs/heads/abedome/develop'" in workflow
    assert "BUILD_VERSION=${{ inputs.version }}" in workflow
    assert "BUILD_REVISION=${{ github.sha }}" in workflow
    assert "candidate-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" in workflow
    assert (
        "tags: ${{ steps.image.outputs.name }}:${{ steps.image.outputs.candidate_tag }}"
        in workflow
    )
    assert "Verify the signed upstream base image" in workflow
    assert "sigstore/cosign-installer@" in workflow
    assert (
        "certificate-identity-regexp https://github.com/home-assistant/docker/.*"
        in workflow
    )
    assert (
        "BASE_IMAGE: ghcr.io/home-assistant/amd64-homeassistant-base:2026.10.3"
        in workflow
    )
    assert 'echo "ref=$BASE_IMAGE@$digest" >> "$GITHUB_OUTPUT"' in workflow
    assert "BUILD_FROM=${{ steps.base.outputs.ref }}" in workflow
    assert '--tag "$IMAGE_NAME:$EXPECTED_VERSION"' in workflow
    assert "$IMAGE_NAME:landingpage" in workflow
    assert candidate_build < candidate_check < alias_promotion < alias_check
    assert '--tag "$IMAGE_NAME:$EXPECTED_VERSION"' not in workflow[:candidate_check]
    assert 'version("abedome-frontend") == expected' in workflow
    assert 'version("home-assistant-frontend")' in workflow
    assert 'manifest["requirements"] == [f"abedome-frontend=={expected}"]' in workflow
    assert 'index .Config.Labels "io.hass.version"' in workflow
    assert 'index .Config.Labels "org.opencontainers.image.version"' in workflow
    assert 'index .Config.Labels "org.opencontainers.image.revision"' in workflow


def test_build_workflow_covers_all_abedome_runtime_overlays() -> None:
    """Ensure changes to every downstream runtime overlay trigger validation."""
    workflow = (ROOT / ".github/workflows/build-abedome-core.yml").read_text()

    for path in (
        "homeassistant/components/analytics/**",
        "homeassistant/components/backup/**",
        "homeassistant/components/cloud/**",
        "homeassistant/components/hassio/**",
        "homeassistant/components/labs/**",
        "tests/components/analytics/**",
        "tests/components/backup/**",
        "tests/components/cloud/**",
        "tests/components/hassio/**",
        "tests/components/labs/**",
    ):
        assert f'      - "{path}"' in workflow
    assert "orjson==3.13.0" in workflow


def test_build_workflow_installs_the_local_core_test_runtime() -> None:
    """Ensure the focused tests run with the Core 2026.11 test package."""
    workflow = (ROOT / ".github/workflows/build-abedome-core.yml").read_text()

    assert "--editable ." in workflow
    assert "--editable packages/pytest-homeassistant" in workflow


def test_core_ci_keeps_frontend_url_direct_for_pytest_package_extras() -> None:
    """Ensure uv can resolve Core's pinned Frontend in the package test job."""
    workflow = (ROOT / ".github/workflows/ci.yaml").read_text()
    optional_helpers = workflow.split("- name: Test optional helpers and fixtures", 1)[
        1
    ]
    optional_helpers = optional_helpers.split("\n  prepare-pytest-full:", 1)[0]

    assert (
        '              . \\\n              "${wheel}[bluetooth,infrared,radio-frequency]"'
        in optional_helpers
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
        "Build and publish the uniquely tagged candidate image"
    )
    image_check = publish_workflow.index(
        "Verify candidate digest, metadata, translations, and Frontend"
    )

    for workflow in (publish_workflow, build_workflow):
        assert EXPECTED_TRANSLATIONS_SHA256 in workflow
        assert EXPECTED_TRANSLATIONS_ASSET in workflow
        assert "--require-language it" in workflow
    assert translation_import < image_build < image_check
    assert "python3 -m script.translations develop --all" in dockerfile
    assert "script/abedome/" in dockerfile
    assert "script/hassfest/translation_data.py" in dockerfile
    docker_generation = dockerfile.index("python3 -m script.translations develop --all")
    docker_verification = dockerfile.index("verify --language en --language it")
    docker_install = dockerfile.index("uv pip install", docker_generation)
    assert docker_generation < docker_verification < docker_install
    assert "python -m script.translations develop --all" in build_workflow
    assert "Verify Core distribution translations" in build_workflow
    assert "verify --language en --language it" in publish_workflow
    assert "verify --language en --language it" in build_workflow
    assert "extractall(" not in importer
