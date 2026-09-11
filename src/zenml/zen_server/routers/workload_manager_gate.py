# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Request-time availability gate for workload-manager routes."""

from fastapi import HTTPException, status

from zenml.zen_server.utils import server_config


def workload_manager_enabled() -> None:
    """Reject workload routes when no workload manager is configured.

    Raises:
        HTTPException: If workload management is disabled on this server.
    """
    if not server_config().workload_manager_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Workload management is not enabled on this server.",
        )
