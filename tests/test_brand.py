"""Tests for the ABEDOME downstream distribution identity."""

from homeassistant.brand import (
    CLI_DESCRIPTION,
    DISTRIBUTION_DISPLAY_NAME,
    DISTRIBUTION_NAME,
    FORK_NOTICE,
    UPSTREAM_NAME_USAGE_NOTICE,
    UPSTREAM_PROJECT_NAME,
)


def test_distribution_identity_preserves_upstream_attribution() -> None:
    """The downstream identity is explicit without hiding its upstream."""
    assert DISTRIBUTION_DISPLAY_NAME == "ABEDOME"
    assert DISTRIBUTION_NAME == "ABEDOME OS"
    assert UPSTREAM_PROJECT_NAME == "Home Assistant"
    assert CLI_DESCRIPTION == "ABEDOME OS"
    assert FORK_NOTICE == (
        "ABEDOME is independent software developed as a modified fork of Home Assistant. "
        "ABEDOME is not affiliated with, associated with, authorized by, or otherwise "
        "officially connected with Nabu Casa or Home Assistant."
    )
    assert UPSTREAM_NAME_USAGE_NOTICE == (
        '"Home Assistant" is used solely to describe the origin of the software.'
    )
