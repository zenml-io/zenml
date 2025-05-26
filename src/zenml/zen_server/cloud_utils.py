"""Utils concerning anything concerning the cloud control plane backend."""

import logging
import threading
import time
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from zenml.config.server_config import ServerProConfiguration
from zenml.exceptions import (
    IllegalOperationError,
    SubscriptionUpgradeRequiredError,
)
from zenml.logger import get_logger
from zenml.utils.time_utils import utc_now
from zenml.zen_server.utils import get_zenml_headers, server_config

logger = get_logger(__name__)

_cloud_connection: Optional["ZenMLCloudConnection"] = None


class ZenMLCloudConnection:
    """Class to use for communication between server and control plane."""

    def __init__(self) -> None:
        """Initialize the RBAC component."""
        self._config = ServerProConfiguration.get_server_config()
        self._session: Optional[requests.Session] = None
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._lock = RLock()

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> requests.Response:
        """Send a request using the active session.

        Args:
            method: The HTTP method to use.
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.
            data: Data to include in the request.

        Raises:
            SubscriptionUpgradeRequiredError: If the current subscription tier
                is insufficient for the attempted operation.
            IllegalOperationError: If the request failed with a 403 status code.
            RuntimeError: If the request failed.

        Returns:
            The response.
        """
        url = self._config.api_url + endpoint

        if logger.isEnabledFor(logging.DEBUG):
            # Get the request ID from the current thread object
            request_id = threading.current_thread().name
            logger.debug(
                f"[{request_id}] RBAC STATS - {method} {endpoint} started"
            )
            start_time = time.time()

        status_code: Optional[int] = None
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self._config.http_timeout,
            )
            if response.status_code == 401:
                # Refresh the auth token and try again
                self._reset_login()
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self._config.http_timeout,
                )

            status_code = response.status_code
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 402:
                    raise SubscriptionUpgradeRequiredError(response.json())
                elif response.status_code == 403:
                    raise IllegalOperationError(response.json())
                else:
                    raise RuntimeError(
                        f"Failed while trying to contact the central zenml pro "
                        f"service: {e}"
                    )
        finally:
            if logger.isEnabledFor(logging.DEBUG):
                duration = (time.time() - start_time) * 1000
                logger.debug(
                    f"[{request_id}] RBAC STATS - {status_code} {method} "
                    f"{endpoint} completed in {duration:.2f}ms"
                )

        return response

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]]
    ) -> requests.Response:
        """Send a GET request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.

        Returns:
            The response.
        """
        return self.request(method="GET", endpoint=endpoint, params=params)

    def post(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> requests.Response:
        """Send a POST request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.
            data: Data to include in the request.

        Returns:
            The response.
        """
        return self.request(
            method="POST", endpoint=endpoint, params=params, data=data
        )

    def patch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Send a PATCH request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.
            data: Data to include in the request.

        Returns:
            The response.
        """
        return self.request(
            method="PATCH", endpoint=endpoint, params=params, data=data
        )

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Send a DELETE request using the active session.

        Args:
            endpoint: The endpoint to send the request to. This will be appended
                to the base URL.
            params: Parameters to include in the request.
            data: Data to include in the request.

        Returns:
            The response.
        """
        return self.request(
            method="DELETE", endpoint=endpoint, params=params, data=data
        )

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML Pro Management Plane.

        Returns:
            A requests session with the authentication token.
        """
        with self._lock:
            if self._session is None:
                # Set up the session's connection pool size to match the server's
                # thread pool size. This allows the server to cache one connection
                # per thread, which means we can keep connections open for longer
                # and avoid the overhead of setting up a new connection for each
                # request.
                conn_pool_size = server_config().thread_pool_size

                self._session = requests.Session()
                # Add the ZenML specific headers
                self._session.headers.update(get_zenml_headers())

                retries = Retry(
                    connect=5,
                    read=8,
                    redirect=3,
                    status=10,
                    allowed_methods=[
                        "HEAD",
                        "GET",
                        "PUT",
                        "PATCH",
                        "POST",
                        "DELETE",
                        "OPTIONS",
                    ],
                    status_forcelist=[
                        408,  # Request Timeout
                        429,  # Too Many Requests
                        502,  # Bad Gateway
                        503,  # Service Unavailable
                        504,  # Gateway Timeout
                    ],
                    other=3,
                    backoff_factor=0.5,
                )

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

            # Login to the ZenML Pro Management Plane. Calling this will fetch
            # the active session token. It will also refresh the token if it is
            # going to expire soon or if it is already expired.
            access_token = self._fetch_auth_token(session=self._session)
            self._session.headers.update(
                {"Authorization": "Bearer " + access_token}
            )

            return self._session

    def _reset_login(self) -> None:
        """Force a new login to the ZenML Pro Management Plane."""
        with self._lock:
            self._token = None
            self._token_expires_at = None

    def _fetch_auth_token(self, session: requests.Session) -> str:
        """Fetch an auth token from the Cloud API.

        Args:
            session: The session to use to fetch the auth token.

        Returns:
            The auth token.

        Raises:
            RuntimeError: If the auth token can't be fetched.
        """
        if (
            self._token is not None
            and self._token_expires_at is not None
            and utc_now() + timedelta(minutes=5) < self._token_expires_at
        ):
            # Already logged in and token is still valid
            return self._token

        # Get an auth token from the Cloud API
        login_url = f"{self._config.api_url}/auth/login"
        headers = {"content-type": "application/x-www-form-urlencoded"}
        # Add zenml specific headers to the request
        headers.update(get_zenml_headers())
        payload = {
            # The client ID is the external server ID
            "client_id": str(server_config().get_external_server_id()),
            "client_secret": self._config.oauth2_client_secret,
            "audience": self._config.oauth2_audience,
            "grant_type": "client_credentials",
        }

        try:
            response = session.post(
                login_url,
                headers=headers,
                data=payload,
                timeout=self._config.http_timeout,
            )
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                f"Error fetching auth token from the Cloud API: {e}"
            )

        json_response = response.json()
        access_token = json_response.get("access_token", "")
        expires_in = json_response.get("expires_in", 0)

        if (
            not access_token
            or not isinstance(access_token, str)
            or not expires_in
            or not isinstance(expires_in, int)
        ):
            raise RuntimeError(
                "Could not fetch auth token from the Cloud API."
            )

        self._token_expires_at = utc_now() + timedelta(seconds=expires_in)
        self._token = access_token

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


def send_pro_workspace_status_update() -> None:
    """Send a workspace status update to the Cloud API."""
    cloud_connection().patch("/workspace_status")
