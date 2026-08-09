"""Tests for the ABEDOME downstream distribution identity."""

from homeassistant.brand import (
    CLI_DESCRIPTION,
    CORE_NAME,
    CORE_REPOSITORY_URL,
    DEVELOPMENT_BRANCH,
    DISTRIBUTION_DISPLAY_NAME,
    DISTRIBUTION_NAME,
    FORK_NOTICE,
    OS_REPOSITORY_URL,
    PRODUCT_ICON_URL,
    SUPERVISOR_NAME,
    SUPERVISOR_REPOSITORY_URL,
    UPSTREAM_NAME_USAGE_NOTICE,
    UPSTREAM_PROJECT_NAME,
)


def test_distribution_identity_preserves_upstream_attribution() -> None:
    """The downstream identity is explicit without hiding its upstream."""
    assert DISTRIBUTION_DISPLAY_NAME == "ABEDOME"
    assert DISTRIBUTION_NAME == "ABEDOME OS"
    assert CORE_NAME == "ABEDOME Core"
    assert SUPERVISOR_NAME == "ABEDOME Supervisor"
    assert UPSTREAM_PROJECT_NAME == "Home Assistant"
    assert CLI_DESCRIPTION == "ABEDOME OS"
    assert PRODUCT_ICON_URL == "/static/icons/favicon-192x192.png"
    assert DEVELOPMENT_BRANCH == "abedome/develop"
    assert CORE_REPOSITORY_URL == "https://github.com/Mauro2020/abedome-core"
    assert OS_REPOSITORY_URL == "https://github.com/Mauro2020/abedome-os"
    assert (
        SUPERVISOR_REPOSITORY_URL == "https://github.com/Mauro2020/abedome-supervisor"
    )
    assert FORK_NOTICE == (
        "ABEDOME is independent software developed as a modified fork of Home Assistant. "
        "ABEDOME is not affiliated with, associated with, authorized by, or otherwise "
        "officially connected with Nabu Casa or Home Assistant."
    )
    assert UPSTREAM_NAME_USAGE_NOTICE == (
        '"Home Assistant" is used solely to describe the origin of the software.'
    )
