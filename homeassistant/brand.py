"""ABEDOME downstream distribution identity.

These constants describe the ABEDOME distribution. They intentionally do not
replace Home Assistant protocol identities, API names, or integration-facing
identifiers, which remain compatible with the upstream project.
"""

from typing import Final

DISTRIBUTION_NAME: Final = "ABEDOME OS"
DISTRIBUTION_DISPLAY_NAME: Final = "ABEDOME"
CORE_NAME: Final = "ABEDOME Core"
SUPERVISOR_NAME: Final = "ABEDOME Supervisor"
UPSTREAM_PROJECT_NAME: Final = "Home Assistant"
CLI_DESCRIPTION: Final = DISTRIBUTION_NAME
PRODUCT_ICON_URL: Final = "/static/icons/favicon-192x192.png"
DEVELOPMENT_BRANCH: Final = "abedome/develop"
CORE_REPOSITORY_URL: Final = "https://github.com/Mauro2020/abedome-core"
OS_REPOSITORY_URL: Final = "https://github.com/Mauro2020/abedome-os"
SUPERVISOR_REPOSITORY_URL: Final = "https://github.com/Mauro2020/abedome-supervisor"
FORK_NOTICE: Final = (
    "ABEDOME is independent software developed as a modified fork of Home Assistant. "
    "ABEDOME is not affiliated with, associated with, authorized by, or otherwise "
    "officially connected with Nabu Casa or Home Assistant."
)
UPSTREAM_NAME_USAGE_NOTICE: Final = (
    '"Home Assistant" is used solely to describe the origin of the software.'
)
