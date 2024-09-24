"""Utils concerning anything concerning the cloud control plane backend."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, ConfigDict, field_validator
from requests.adapters import HTTPAdapter, Retry

from zenml.exceptions import SubscriptionUpgradeRequiredError
from zenml.zen_server.utils import server_config

ZENML_CLOUD_RBAC_ENV_PREFIX = "ZENML_CLOUD_"

_cloud_connection: Optional["ZenMLCloudConnection"] = None


class ZenMLCloudConfiguration(BaseModel):
    """ZenML Pro RBAC configuration."""

    api_url: str
    oauth2_client_id: str
    oauth2_client_secret: str

    @field_validator("api_url")
    @classmethod
    def _strip_trailing_slashes_url(cls, url: str) -> str:
        """Strip any trailing slashes on the API URL.

        Args:
            url: The API URL.

        Returns:
            The API URL with potential trailing slashes removed.
        """
        return url.rstrip("/")

    @classmethod
    def from_environment(cls) -> "ZenMLCloudConfiguration":
        """Get the RBAC configuration from environment variables.

        Returns:
            The RBAC configuration.
        """
        env_config: Dict[str, Any] = {}
        for k, v in os.environ.items():
            if v == "":
                continue
            if k.startswith(ZENML_CLOUD_RBAC_ENV_PREFIX):
                env_config[k[len(ZENML_CLOUD_RBAC_ENV_PREFIX) :].lower()] = v

        return ZenMLCloudConfiguration(**env_config)

    model_config = ConfigDict(
        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra="allow"
    )


class ZenMLCloudConnection:
    """Class to use for communication between server and control plane."""

    def __init__(self) -> None:
        """Initialize the RBAC component."""
        self._config = ZenMLCloudConfiguration.from_environment()
        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]]
    ) -> requests.Response:
        """Send a GET request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.

        Raises:
            RuntimeError: If the request failed.
            SubscriptionUpgradeRequiredError: In case the current subscription
                tier is insufficient for the attempted operation.

        Returns:
            The response.
        """
        url = self._config.api_url + endpoint

        response = self.session.get(url=url, params=params, timeout=7)
        if response.status_code == 401:
            # If we get an Unauthorized error from the API serer, we refresh the
            # auth token and try again
            self._clear_session()
            response = self.session.get(url=url, params=params, timeout=7)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            if response.status_code == 402:
                raise SubscriptionUpgradeRequiredError(response.json())
            else:
                raise RuntimeError(
                    f"Failed with the following error {response} {response.text}"
                )

        return response

    def post(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Send a POST request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.
            data: Data to include in the request.

        Raises:
            RuntimeError: If the request failed.

        Returns:
            The response.
        """
        url = self._config.api_url + endpoint

        response = self.session.post(
            url=url, params=params, json=data, timeout=7
        )
        if response.status_code == 401:
            # Refresh the auth token and try again
            self._clear_session()
            response = self.session.post(
                url=url, params=params, json=data, timeout=7
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(
                f"Failed while trying to contact the central zenml pro "
                f"service: {e}"
            )

        return response

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML Pro Management Plane.

        Returns:
            A requests session with the authentication token.
        """
        if self._session is None:
            # Set up the session's connection pool size to match the server's
            # thread pool size. This allows the server to cache one connection
            # per thread, which means we can keep connections open for longer
            # and avoid the overhead of setting up a new connection for each
            # request.
            conn_pool_size = server_config().thread_pool_size

            self._session = requests.Session()
            token = self._fetch_auth_token()
            self._session.headers.update({"Authorization": "Bearer " + token})

            retries = Retry(total=5, backoff_factor=0.1)
            self._session.mount(
                "https://",
                HTTPAdapter(
                    max_retries=retries,
                    # We only use one connection pool to be cached because we
                    # only communicate with one remote server (the control
                    # plane)
                    pool_connections=1,
                    pool_maxsize=conn_pool_size,
                ),
            )

        return self._session

    def _clear_session(self) -> None:
        """Clear the authentication session."""
        self._session = None
        self._token = None
        self._token_expires_at = None

    def _fetch_auth_token(self) -> str:
        """Fetch an auth token for the Cloud API from auth0.

        Raises:
            RuntimeError: If the auth token can't be fetched.

        Returns:
            Auth token.
        """
        if (
            self._token is not None
            and self._token_expires_at is not None
            and datetime.now(timezone.utc) + timedelta(minutes=5)
            < self._token_expires_at
        ):
            return self._token

        # Get an auth token from auth0
        login_url = f"{self._config.api_url}/auth/login"
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {
            "client_id": self._config.oauth2_client_id,
            "client_secret": self._config.oauth2_client_secret,
            "grant_type": "client_credentials",
        }
        try:
            response = requests.post(
                login_url, headers=headers, data=payload, timeout=7
            )
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Error fetching auth token from auth0: {e}")

        json_response = response.json()
        access_token = json_response.get("access_token", "")
        expires_in = json_response.get("expires_in", 0)

        if (
            not access_token
            or not isinstance(access_token, str)
            or not expires_in
            or not isinstance(expires_in, int)
        ):
            raise RuntimeError("Could not fetch auth token from auth0.")

        self._token = access_token
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )

        assert self._token is not None
        return self._token


def cloud_connection() -> ZenMLCloudConnection:
    """Return the initialized cloud connection.

    Returns:
        The cloud connection.
    """
    global _cloud_connection
    if _cloud_connection is None:
        _cloud_connection = ZenMLCloudConnection()

    return _cloud_connection
