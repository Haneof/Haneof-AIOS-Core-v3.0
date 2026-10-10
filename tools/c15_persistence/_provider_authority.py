"""Private cryptographic authority placeholder.

ISOLATION ENFORCEMENT:
----------------------
In accordance with PM49-BLK-002R, in-process signing authority has been eliminated.
Private signing authority lives exclusively within `provider_process.py` which
executes only as an isolated subprocess (`PROVIDER_PID != OPERATOR_PID`).

Any attempt to import this module into the operator or recovery process is strictly
prohibited and will raise an ImportError.
"""

raise ImportError(
    "_provider_authority module is permanently removed; provider signing authority "
    "is isolated in provider_process subprocess boundary"
)
