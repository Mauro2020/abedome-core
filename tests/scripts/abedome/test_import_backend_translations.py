"""Tests for importing pinned backend translations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import zipfile

import pytest

from script.abedome.import_backend_translations import (
    import_translations,
    verify_onboarding_translations,
)

ONBOARDING_STRINGS = {
    "area": {
        "bedroom": "Bedroom",
        "kitchen": "Kitchen",
        "living_room": "Living Room",
    }
}


def _write_component(components_root: Path, domain: str, strings: dict) -> None:
    component_root = components_root / domain
    component_root.mkdir(parents=True)
    (component_root / "strings.json").write_text(json.dumps(strings), encoding="utf-8")


def _write_wheel(
    wheel: Path, members: list[tuple[str | zipfile.ZipInfo, object]]
) -> str:
    with zipfile.ZipFile(wheel, "w") as archive:
        for member, value in members:
            data = value if isinstance(value, bytes) else json.dumps(value).encode()
            archive.writestr(member, data)
    return hashlib.sha256(wheel.read_bytes()).hexdigest()


def test_imports_only_compatible_non_english_translations(tmp_path: Path) -> None:
    """Test import filtering and current-source English ownership."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    translations_root = components_root / "onboarding" / "translations"
    translations_root.mkdir()
    current_english = {"area": {"living_room": "Current English"}}
    (translations_root / "en.json").write_text(
        json.dumps(current_english), encoding="utf-8"
    )
    wheel = tmp_path / "homeassistant.whl"
    digest = _write_wheel(
        wheel,
        [
            (
                "homeassistant/components/onboarding/translations/en.json",
                {"area": {"living_room": "Stale English"}},
            ),
            (
                "homeassistant/components/onboarding/translations/it.json",
                {
                    "area": {
                        "bedroom": "Camera da letto",
                        "kitchen": "Cucina",
                        "living_room": "Soggiorno",
                        "removed": "Rimossa",
                    },
                    "removed_category": {"value": "Rimossa"},
                },
            ),
            (
                "homeassistant/components/removed/translations/it.json",
                {"area": {"living_room": "Ignorata"}},
            ),
        ],
    )

    summary = import_translations(wheel, digest, components_root)

    assert summary.files == 1
    assert summary.components == 1
    assert summary.languages == frozenset({"it"})
    assert json.loads((translations_root / "en.json").read_text()) == current_english
    imported = json.loads(
        (components_root / "onboarding" / "translations" / "it.json").read_text()
    )
    assert imported == {
        "area": {
            "bedroom": "Camera da letto",
            "kitchen": "Cucina",
            "living_room": "Soggiorno",
        }
    }
    verify_onboarding_translations(components_root, ["it"])


def test_rejects_wheel_digest_mismatch(tmp_path: Path) -> None:
    """Test the wheel is authenticated before any import."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    wheel = tmp_path / "homeassistant.whl"
    _write_wheel(wheel, [])

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        import_translations(wheel, "0" * 64, components_root)


@pytest.mark.parametrize(
    ("member", "error"),
    [
        pytest.param("../translations/it.json", "Unsafe wheel path", id="traversal"),
        pytest.param(
            "/homeassistant/components/onboarding/translations/it.json",
            "Unsafe wheel path",
            id="absolute",
        ),
    ],
)
def test_rejects_unsafe_wheel_paths(tmp_path: Path, member: str, error: str) -> None:
    """Test wheel paths cannot escape the controlled component tree."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    wheel = tmp_path / "homeassistant.whl"
    digest = _write_wheel(wheel, [(member, ONBOARDING_STRINGS)])

    with pytest.raises(ValueError, match=error):
        import_translations(wheel, digest, components_root)


def test_rejects_wheel_symlink(tmp_path: Path) -> None:
    """Test translation members cannot be symbolic links."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    wheel = tmp_path / "homeassistant.whl"
    member = zipfile.ZipInfo("homeassistant/components/onboarding/translations/it.json")
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    digest = _write_wheel(wheel, [(member, ONBOARDING_STRINGS)])

    with pytest.raises(ValueError, match="symlink"):
        import_translations(wheel, digest, components_root)


def test_rejects_duplicate_translation_member(tmp_path: Path) -> None:
    """Test duplicate archive members cannot override verified data."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    wheel = tmp_path / "homeassistant.whl"
    member = "homeassistant/components/onboarding/translations/it.json"
    with pytest.warns(UserWarning, match="Duplicate name"):
        digest = _write_wheel(
            wheel,
            [(member, ONBOARDING_STRINGS), (member, ONBOARDING_STRINGS)],
        )

    with pytest.raises(ValueError, match="Duplicate wheel member"):
        import_translations(wheel, digest, components_root)


def test_rejects_non_object_translation_json(tmp_path: Path) -> None:
    """Test translation files must contain JSON objects."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    wheel = tmp_path / "homeassistant.whl"
    digest = _write_wheel(
        wheel,
        [("homeassistant/components/onboarding/translations/it.json", [])],
    )

    with pytest.raises(TypeError, match="Expected a JSON object"):
        import_translations(wheel, digest, components_root)


def test_late_archive_error_preserves_existing_translations(tmp_path: Path) -> None:
    """Test validation completes before existing translations are replaced."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    translations_root = components_root / "onboarding" / "translations"
    translations_root.mkdir()
    existing_italian = {"area": {"living_room": "Vecchio soggiorno"}}
    (translations_root / "it.json").write_text(
        json.dumps(existing_italian), encoding="utf-8"
    )
    wheel = tmp_path / "homeassistant.whl"
    digest = _write_wheel(
        wheel,
        [
            (
                "homeassistant/components/onboarding/translations/fr.json",
                ONBOARDING_STRINGS,
            ),
            (
                "homeassistant/components/onboarding/translations/de.json",
                b"{invalid-json",
            ),
        ],
    )

    with pytest.raises(ValueError, match="Invalid JSON"):
        import_translations(wheel, digest, components_root)

    assert json.loads((translations_root / "it.json").read_text()) == existing_italian
    assert not (translations_root / "fr.json").exists()


def test_verify_rejects_missing_language(tmp_path: Path) -> None:
    """Test verification fails when a requested language is not packaged."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)

    with pytest.raises(ValueError, match="Missing onboarding translation file for it"):
        verify_onboarding_translations(components_root, ["it"])


def test_verify_rejects_missing_required_keys(tmp_path: Path) -> None:
    """Test verification fails when onboarding area keys are incomplete."""
    components_root = tmp_path / "homeassistant" / "components"
    _write_component(components_root, "onboarding", ONBOARDING_STRINGS)
    translations_root = components_root / "onboarding" / "translations"
    translations_root.mkdir()
    (translations_root / "it.json").write_text(
        json.dumps({"area": {"living_room": "Soggiorno"}}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="bedroom, kitchen"):
        verify_onboarding_translations(components_root, ["it"])
