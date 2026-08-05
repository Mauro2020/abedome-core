"""Tests for the ABEDOME downstream distribution identity."""

from homeassistant.brand import (
    CLI_DESCRIPTION,
    DISTRIBUTION_DISPLAY_NAME,
    DISTRIBUTION_NAME,
    UPSTREAM_PROJECT_NAME,
)


def test_distribution_identity_preserves_upstream_attribution() -> None:
    """The downstream identity is explicit without hiding its upstream."""
    assert DISTRIBUTION_DISPLAY_NAME == "ABEDOME"
    assert DISTRIBUTION_NAME == "ABEDOME OS"
    assert UPSTREAM_PROJECT_NAME == "Home Assistant"
    assert CLI_DESCRIPTION == "ABEDOME OS, powered by Home Assistant."
