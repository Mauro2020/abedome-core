"""Common fixtures for the analytics tests."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from homeassistant.generated.labs import LABS_PREVIEW_FEATURES

MOCK_SNAPSHOT_PAYLOAD = {"mock_integration": {"devices": [], "entities": []}}

_ANALYTICS_LABS_FEATURE = {
    "snapshots": {
        "feedback_url": "https://example.com/feedback",
        "learn_more_url": "https://example.com/learn-more",
        "report_issue_url": "https://example.com/report-issue",
    }
}


@pytest.fixture(autouse=True)
def enable_upstream_analytics_for_compatibility_tests() -> Generator[None]:
    """Keep upstream analytics behavior covered independently of ABEDOME policy."""
    with (
        patch("homeassistant.brand.UPSTREAM_ANALYTICS_ENABLED", True),
        patch.dict(
            LABS_PREVIEW_FEATURES,
            {"analytics": _ANALYTICS_LABS_FEATURE},
        ),
    ):
        yield


@pytest.fixture
def mock_snapshot_payload() -> Generator[None]:
    """Mock _async_snapshot_payload to return non-empty data."""
    with patch(
        "homeassistant.components.analytics.analytics._async_snapshot_payload",
        return_value=MOCK_SNAPSHOT_PAYLOAD,
    ):
        yield
