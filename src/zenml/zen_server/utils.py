import os
from typing import Any, List

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from starlette import status

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType
from zenml.repository import Repository
from zenml.zen_stores.base_zen_store import BaseZenStore

# profile_name = os.environ.get(ENV_ZENML_PROFILE_NAME)
#
# # Check if profile name was passed as env variable:
# if profile_name:
#     profile = (
#         GlobalConfiguration().get_profile(profile_name)
#         or Repository().active_profile
#     )
# # Fallback to what Repository thinks is the active profile
# else:
#     profile = Repository().active_profile
#
# if profile.store_type == StoreType.REST:
#     raise ValueError(
#         "Server cannot be started with REST store type. Make sure you "
#         "specify a profile with a non-networked persistence backend "
#         "when trying to start the ZenServer. (use command line flag "
#         "`--profile=$PROFILE_NAME` or set the env variable "
#         f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
#         "other than the currently active one)"
#     )

security = HTTPBasic()


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Any


error_response = dict(model=ErrorModel)


def authorize(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Authorizes any request to the ZenServer.

    Right now this method only checks if the username provided as part of http
    basic auth credentials is registered in the ZenStore.

    Args:
        credentials: HTTP basic auth credentials passed to the request.

    Raises:
        HTTPException: If the username is not registered in the ZenStore.
    """
    try:
        zen_store.get_user(credentials.username)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username.",
        )


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.

    Returns:
        List of strings representing the error.
    """
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 404.
    """
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 409.
    """
    return HTTPException(status_code=409, detail=error_detail(error))


zen_store: BaseZenStore = Repository().zen_store

# # We initialize with track_analytics=False because we do not
# # want to track anything server side.
# zen_store: BaseZenStore = Repository.create_store(
#     skip_default_registrations=True,
#     track_analytics=False,
#     skip_migration=True,
# )
