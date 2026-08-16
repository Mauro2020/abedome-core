"""Constants for the onboarding component."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DefaultArea:
    """Default area definition."""

    key: str
    fallback_name: str
    icon: str


DOMAIN = "onboarding"
STEP_USER = "user"
STEP_CORE_CONFIG = "core_config"
STEP_INTEGRATION = "integration"
STEP_ANALYTICS = "analytics"

STEPS = [STEP_USER, STEP_CORE_CONFIG, STEP_INTEGRATION]

DEFAULT_AREAS = (
    DefaultArea(key="living_room", fallback_name="Living Room", icon="mdi:sofa"),
    DefaultArea(key="kitchen", fallback_name="Kitchen", icon="mdi:stove"),
    DefaultArea(key="bedroom", fallback_name="Bedroom", icon="mdi:bed"),
)
