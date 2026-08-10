"""Tests for the ABEDOME upstream analytics privacy policy."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from aiohasupervisor import SupervisorError
import pytest

from homeassistant import brand
from homeassistant.components.analytics import CONF_SNAPSHOTS_URL, DATA_COMPONENT
from homeassistant.components.analytics.analytics import Analytics
from homeassistant.components.analytics.const import (
    ATTR_BASE,
    ATTR_DIAGNOSTICS,
    ATTR_SNAPSHOTS,
    ATTR_STATISTICS,
    ATTR_USAGE,
    DOMAIN,
    STORAGE_KEY,
)
from homeassistant.components.hassio import HassioNotReadyError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import WebSocketGenerator

CUSTOM_SNAPSHOT_URL = "https://analytics-disabled.example.com"


def _enabled_storage() -> dict[str, Any]:
    """Return legacy analytics storage with every upstream feature enabled."""
    return {
        "version": 1,
        "data": {
            "onboarded": True,
            "preferences": {
                ATTR_BASE: True,
                ATTR_DIAGNOSTICS: True,
                ATTR_SNAPSHOTS: True,
                ATTR_STATISTICS: True,
                ATTR_USAGE: True,
            },
            "uuid": "legacy-installation-identifier",
            "submission_identifier": "legacy-submission-identifier",
            "snapshot_submission_time": 42.0,
        },
    }


async def test_legacy_storage_is_sanitized_and_never_submitted(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test enabled legacy state is cleared without any outbound submission."""
    assert not brand.UPSTREAM_ANALYTICS_ENABLED
    hass_storage[STORAGE_KEY] = _enabled_storage()
    analytics = Analytics(hass)
    basic_cancel = Mock()
    snapshot_cancel = Mock()
    analytics._basic_scheduled = basic_cancel
    analytics._snapshot_scheduled = snapshot_cancel

    with patch(
        "homeassistant.components.analytics.analytics.is_hassio", return_value=False
    ):
        await analytics.load()

    await analytics.send_analytics()
    await analytics.send_snapshot()

    assert analytics.onboarded
    assert analytics.uuid is None
    assert analytics.preferences == {
        ATTR_BASE: False,
        ATTR_DIAGNOSTICS: False,
        ATTR_USAGE: False,
        ATTR_STATISTICS: False,
        ATTR_SNAPSHOTS: False,
    }
    assert hass_storage[STORAGE_KEY]["data"] == {
        "onboarded": True,
        "preferences": {},
        "uuid": None,
        "submission_identifier": None,
        "snapshot_submission_time": None,
    }
    basic_cancel.assert_called_once_with()
    snapshot_cancel.assert_called_once_with()
    assert aioclient_mock.mock_calls == []


async def test_yaml_and_websocket_cannot_reenable_analytics(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    hass_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test YAML and WebSocket inputs remain compatible but cannot opt in."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {DOMAIN: {CONF_SNAPSHOTS_URL: CUSTOM_SNAPSHOT_URL}},
    )
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "analytics/preferences",
            "preferences": {
                ATTR_BASE: True,
                ATTR_DIAGNOSTICS: True,
                ATTR_SNAPSHOTS: True,
                ATTR_STATISTICS: True,
                ATTR_USAGE: True,
            },
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["preferences"] == {
        ATTR_BASE: False,
        ATTR_DIAGNOSTICS: False,
        ATTR_USAGE: False,
        ATTR_STATISTICS: False,
        ATTR_SNAPSHOTS: False,
    }
    assert hass.data[DATA_COMPONENT].uuid is None
    assert hass_storage[STORAGE_KEY]["data"]["preferences"] == {}

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(days=2))
    await hass.async_block_till_done()

    assert aioclient_mock.mock_calls == []


@pytest.mark.parametrize("supervisor_diagnostics", [True, False])
async def test_supervisor_diagnostics_is_forced_off(
    hass: HomeAssistant,
    supervisor_diagnostics: bool,
) -> None:
    """Test Supervisor diagnostics is explicitly disabled during each guard pass."""
    analytics = Analytics(hass)

    with (
        patch(
            "homeassistant.components.analytics.analytics.is_hassio",
            return_value=True,
        ),
        patch(
            "homeassistant.components.hassio.get_supervisor_info",
            return_value={ATTR_DIAGNOSTICS: supervisor_diagnostics},
        ),
        patch(
            "homeassistant.components.hassio.async_update_diagnostics",
            new=AsyncMock(),
        ) as update_diagnostics,
    ):
        await analytics.load()

    update_diagnostics.assert_awaited_once_with(hass, False)

    update_diagnostics.reset_mock()
    with (
        patch(
            "homeassistant.components.analytics.analytics.is_hassio",
            return_value=True,
        ),
        patch(
            "homeassistant.components.hassio.get_supervisor_info",
            return_value={ATTR_DIAGNOSTICS: supervisor_diagnostics},
        ),
        patch(
            "homeassistant.components.hassio.async_update_diagnostics",
            update_diagnostics,
        ),
    ):
        await analytics.async_schedule()

    update_diagnostics.assert_awaited_once_with(hass, False)


async def test_supervisor_not_ready_retries_policy_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test setup retries until Supervisor diagnostics can be inspected."""
    with (
        patch(
            "homeassistant.components.analytics.analytics.is_hassio",
            return_value=True,
        ),
        patch(
            "homeassistant.components.hassio.get_supervisor_info",
            side_effect=HassioNotReadyError,
        ),
    ):
        assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
        await hass.async_block_till_done()

    assert (
        hass.config_entries.async_entries(DOMAIN)[0].state
        is ConfigEntryState.SETUP_RETRY
    )


async def test_supervisor_update_failure_retries_policy_enforcement(
    hass: HomeAssistant,
) -> None:
    """Test setup retries when disabling Supervisor diagnostics fails."""
    with (
        patch(
            "homeassistant.components.analytics.analytics.is_hassio",
            return_value=True,
        ),
        patch(
            "homeassistant.components.hassio.get_supervisor_info",
            return_value={ATTR_DIAGNOSTICS: True},
        ),
        patch(
            "homeassistant.components.hassio.async_update_diagnostics",
            side_effect=SupervisorError("Supervisor unavailable"),
        ),
    ):
        assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
        await hass.async_block_till_done()

    assert (
        hass.config_entries.async_entries(DOMAIN)[0].state
        is ConfigEntryState.SETUP_RETRY
    )
