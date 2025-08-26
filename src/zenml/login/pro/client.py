#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""ZenML Pro client."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter, Retry

from zenml.analytics import source_context
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.login.credentials import APIToken
from zenml.login.credentials_store import get_credentials_store
from zenml.login.pro.models import BaseRestAPIModel
from zenml.models.v2.misc.auth_models import OAuthTokenResponse
from zenml.utils.singleton import SingletonMetaClass
from zenml.zen_server.exceptions import exception_from_response

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.login.pro.organization.client import OrganizationClient
    from zenml.login.pro.workspace.client import WorkspaceClient

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


AnyResponse = TypeVar("AnyResponse", bound=BaseRestAPIModel)


class ZenMLProClient(metaclass=SingletonMetaClass):
    """ZenML Pro client."""

    _url: str
    _api_token: Optional[APIToken] = None
    _session: Optional[requests.Session] = None
    _workspace: Optional["WorkspaceClient"] = None
    _organization: Optional["OrganizationClient"] = None

    def __init__(self, url: str) -> None:
        """Initialize the ZenML Pro client.

        Args:
            url: The URL of the ZenML Pro API server.
        """
        self._url = url

    def authenticate(self) -> APIToken:
        """Authenticate to ZenML Pro and return the API token.

        Returns:
            The API token.

        Raises:
            AuthorizationException: If the login fails.
        """
        credentials_store = get_credentials_store()
        pro_credentials = credentials_store.get_pro_credentials(self._url)
        if pro_credentials is None:
            raise AuthorizationException(
                "No ZenML Pro credentials found. Please run 'zenml login' to "
                "login to ZenML Pro."
            )
        if pro_credentials.has_valid_token:
            assert pro_credentials.api_token is not None
            return pro_credentials.api_token

        if pro_credentials.can_refresh_token:
            assert pro_credentials.api_key is not None
            api_token = self.fetch_api_token(
                self._url, pro_credentials.api_key
            )
            return credentials_store.set_token(
                self._url,
                api_token,
                is_zenml_pro=True,
            )
        else:
            raise AuthorizationException(
                "Your ZenML Pro authentication has expired. Please run "
                "'zenml login' to login again."
            )

    @property
    def workspace(self) -> "WorkspaceClient":
        """Get the workspace client.

        Returns:
            The workspace client.
        """
        if self._workspace is None:
            from zenml.login.pro.workspace.client import WorkspaceClient

            self._workspace = WorkspaceClient(client=self)
        return self._workspace

    @property
    def organization(self) -> "OrganizationClient":
        """Get the organization client.

        Returns:
            The organization client.
        """
        if self._organization is None:
            from zenml.login.pro.organization.client import OrganizationClient

            self._organization = OrganizationClient(client=self)
        return self._organization

    @property
    def api_token(self) -> str:
        """Get the API token.

        Returns:
            The API token.
        """
        if self._api_token is None or self._api_token.expired:
            self._api_token = self.authenticate()
        return self._api_token.access_token

    @property
    def session(self) -> requests.Session:
        """Authenticate to the ZenML Pro API server.

        Returns:
            A requests session with the authentication token.
        """
        if self._session is None:
            self._session = requests.Session()
            retries = Retry(backoff_factor=0.1, connect=5)
            self._session.mount("https://", HTTPAdapter(max_retries=retries))
            self._session.mount("http://", HTTPAdapter(max_retries=retries))
            self._session.headers.update(
                {"Authorization": "Bearer " + self.api_token}
            )
            logger.debug("Authenticated to ZenML Pro server.")
        return self._session

    @classmethod
    def fetch_api_token(cls, url: str, api_key: str) -> OAuthTokenResponse:
        """Fetch the API token for a given ZenML Pro server URL.

        Args:
            url: ZenML Pro server URL
            api_key: API key

        Returns:
            The API token.

        Raises:
            ValueError: if the response is not in the right format.
        """
        headers = {"Authorization": "Bearer " + api_key}
        response = requests.post(
            url + "/auth/login",
            data={"password": api_key},
            headers=headers,
            timeout=10,
        )
        json_response = cls._handle_response(response)
        if not isinstance(json_response, dict):
            raise ValueError(
                f"Bad response from API. Expected dict, got\n{json_response}"
            )

        return OAuthTokenResponse.model_validate(json_response)

    @staticmethod
    def _handle_response(response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception.

        Args:
            response: The response to handle.

        Returns:
            The parsed response.

        Raises:
            ValueError: if the response is not in the right format.
            RuntimeError: if an error response is received from the server
                and a more specific exception cannot be determined.
            exc: the exception converted from an error response, if one
                is returned from the server.
        """
        if 200 <= response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                raise ValueError(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code >= 400:
            exc = exception_from_response(response)
            if exc is not None:
                raise exc
            else:
                raise RuntimeError(
                    f"{response.status_code} HTTP Error received from server: "
                    f"{response.text}"
                )
        else:
            raise RuntimeError(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a request to the REST API.

        Args:
            method: The HTTP method to use.
            url: The URL to request.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The parsed response.
        """
        params = {k: str(v) for k, v in params.items()} if params else {}

        self.session.headers.update(
            {source_context.name: source_context.get().value}
        )

        return self._handle_response(
            self.session.request(
                method,
                url,
                params=params,
                **kwargs,
            )
        )

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a GET request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending GET request to {path}...")
        return self._request(
            "GET",
            self._url + path,
            params=params,
            **kwargs,
        )

    def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a DELETE request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending DELETE request to {path}...")
        return self._request(
            "DELETE",
            self._url + path,
            params=params,
            **kwargs,
        )

    def post(
        self,
        path: str,
        body: BaseRestAPIModel,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a POST request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending POST request to {path}...")
        return self._request(
            "POST",
            self._url + path,
            json=body.model_dump(mode="json"),
            params=params,
            **kwargs,
        )

    def put(
        self,
        path: str,
        body: Optional[BaseRestAPIModel] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a PUT request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending PUT request to {path}...")
        json = (
            body.model_dump(mode="json", exclude_unset=True) if body else None
        )
        return self._request(
            "PUT",
            self._url + path,
            json=json,
            params=params,
            **kwargs,
        )

    def patch(
        self,
        path: str,
        body: Optional[BaseRestAPIModel] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Json:
        """Make a PATCH request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.
            params: The query parameters to pass to the endpoint.
            kwargs: Additional keyword arguments to pass to the request.

        Returns:
            The response body.
        """
        logger.debug(f"Sending PATCH request to {path}...")
        json = (
            body.model_dump(mode="json", exclude_unset=True) if body else None
        )
        return self._request(
            "PATCH",
            self._url + path,
            json=json,
            params=params,
            **kwargs,
        )

    def _create_resource(
        self,
        resource: BaseRestAPIModel,
        response_model: Type[AnyResponse],
        route: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnyResponse:
        """Create a new resource.

        Args:
            resource: The resource to create.
            route: The resource REST API route to use.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The created resource.
        """
        response_body = self.post(f"{route}", body=resource, params=params)

        return response_model.model_validate(response_body)

    def _get_resource(
        self,
        resource_id: Union[str, int, UUID],
        route: str,
        response_model: Type[AnyResponse],
        **params: Any,
    ) -> AnyResponse:
        """Retrieve a single resource.

        Args:
            resource_id: The ID of the resource to retrieve.
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The retrieved resource.
        """
        # leave out filter params that are not supplied
        params = dict(filter(lambda x: x[1] is not None, params.items()))
        body = self.get(f"{route}/{str(resource_id)}", params=params)
        return response_model.model_validate(body)

    def _list_resources(
        self,
        route: str,
        response_model: Type[AnyResponse],
        **params: Any,
    ) -> List[AnyResponse]:
        """Retrieve a list of resources filtered by some criteria.

        Args:
            route: The resource REST API route to use.
            response_model: Model to use to serialize the response body.
            params: Filter parameters to use in the query.

        Returns:
            List of retrieved resources matching the filter criteria.

        Raises:
            ValueError: If the value returned by the server is not a list.
        """
        # leave out filter params that are not supplied
        params = dict(filter(lambda x: x[1] is not None, params.items()))
        body = self.get(f"{route}", params=params)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [response_model.model_validate(entry) for entry in body]

    def _update_resource(
        self,
        resource_id: Union[str, int, UUID],
        resource_update: BaseRestAPIModel,
        response_model: Type[AnyResponse],
        route: str,
        **params: Any,
    ) -> AnyResponse:
        """Update an existing resource.

        Args:
            resource_id: The id of the resource to update.
            resource_update: The resource update.
            response_model: Optional model to use to deserialize the response
                body. If not provided, the resource class itself will be used.
            route: The resource REST API route to use.
            params: Optional query parameters to pass to the endpoint.

        Returns:
            The updated resource.
        """
        # leave out filter params that are not supplied
        params = dict(filter(lambda x: x[1] is not None, params.items()))
        response_body = self.put(
            f"{route}/{str(resource_id)}", body=resource_update, params=params
        )

        return response_model.model_validate(response_body)

    def _delete_resource(
        self, resource_id: Union[str, UUID], route: str
    ) -> None:
        """Delete a resource.

        Args:
            resource_id: The ID of the resource to delete.
            route: The resource REST API route to use.
        """
        self.delete(f"{route}/{str(resource_id)}")
