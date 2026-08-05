"""ABEDOME downstream distribution identity.

These constants describe the ABEDOME distribution. They intentionally do not
replace Home Assistant protocol identities, API names, or integration-facing
identifiers, which remain compatible with the upstream project.
"""

from typing import Final

DISTRIBUTION_NAME: Final = "ABEDOME OS"
DISTRIBUTION_DISPLAY_NAME: Final = "ABEDOME"
UPSTREAM_PROJECT_NAME: Final = "Home Assistant"
CLI_DESCRIPTION: Final = f"{DISTRIBUTION_NAME}, powered by {UPSTREAM_PROJECT_NAME}."
