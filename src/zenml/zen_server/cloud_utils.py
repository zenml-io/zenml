"""Utils concerning anything concerning the cloud control plane backend."""

import os
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, validator
from requests.adapters import HTTPAdapter, Retry

from zenml.exceptions import SubscriptionUpgradeRequiredError

ZENML_CLOUD_RBAC_ENV_PREFIX = "ZENML_CLOUD_"


class ZenMLCloudConfiguration(BaseModel):
    """ZenML Cloud RBAC configuration."""

    api_url: str

    oauth2_client_id: str
    oauth2_client_secret: str
    oauth2_audience: str
    auth0_domain: str

    @validator("api_url")
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

    class Config:
        """Pydantic configuration class."""

        # Allow extra attributes from configs of previous ZenML versions to
        # permit downgrading
        extra = "allow"


class ZenMLCloudSession:
    """Class to use for communication between server and control plane."""

    def __init__(self) -> None:
        """Initialize the RBAC component."""
        self._config = ZenMLCloudConfiguration.from_environment()
        self._session: Optional[requests.Session] = None

    def _get(
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
            # Refresh the auth token and try again
            self._clear_session()
            response = self.session.get(url=url, params=params, timeout=7)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            if response.status_code == 402:
                raise SubscriptionUpgradeRequiredError(response.json())
            else:
                raise RuntimeError(
                    f"Failed with the following error {response.json()}"
                )

        return response

    def _post(
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
                f"Failed while trying to contact the central zenml cloud "
                f"service: {e}"
            )

        return response

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML Cloud API.

        Returns:
            A requests session with the authentication token.
        """
        if self._session is None:
            self._session = requests.Session()
            token = self._fetch_auth_token()
            self._session.headers.update({"Authorization": "Bearer " + token})

            retries = Retry(total=5, backoff_factor=0.1)
            self._session.mount("https://", HTTPAdapter(max_retries=retries))

        return self._session

    def _clear_session(self) -> None:
        """Clear the authentication session."""
        self._session = None

    def _fetch_auth_token(self) -> str:
        """Fetch an auth token for the Cloud API from auth0.

        Raises:
            RuntimeError: If the auth token can't be fetched.

        Returns:
            Auth token.
        """
        # Get an auth token from auth0
        auth0_url = f"https://{self._config.auth0_domain}/oauth/token"
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {
            "client_id": self._config.oauth2_client_id,
            "client_secret": self._config.oauth2_client_secret,
            "audience": self._config.oauth2_audience,
            "grant_type": "client_credentials",
        }
        try:
            response = requests.post(
                auth0_url, headers=headers, data=payload, timeout=7
            )
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Error fetching auth token from auth0: {e}")

        access_token = response.json().get("access_token", "")

        if not access_token or not isinstance(access_token, str):
            raise RuntimeError("Could not fetch auth token from auth0.")

        return str(access_token)
