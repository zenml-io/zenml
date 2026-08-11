#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""AWS RDS IAM authentication for MySQL database connections."""

import ssl
import time
from typing import Any, Dict, List, Tuple, Type

import pymysql
from pymysql.constants import CLIENT
from sqlalchemy import Engine, event

from zenml.utils.time_utils import exponential_backoff_delays

TOKEN_ATTEMPTS = 3
TOKEN_INITIAL_DELAY = 0.1
TOKEN_MAX_DELAY = 0.2

TRANSIENT_ERROR_CODES = {
    "InternalFailure",
    "RequestTimeout",
    "ServiceUnavailable",
    "Throttling",
    "ThrottlingException",
}


class TLSRequiredMySQLConnection(pymysql.Connection):
    """PyMySQL connection that refuses to authenticate over plaintext.

    PyMySQL negotiates TLS opportunistically: when the server does not
    advertise the `CLIENT.SSL` capability it silently continues in plaintext
    and sends the handshake response - which carries the password - in the
    clear. Under RDS IAM that password is a live authentication token, so a
    downgraded connection hands a usable credential to whoever is on the other
    end, before any post-connect check gets a chance to run.

    The credential is only written by `_request_authentication`, so gating that
    call is what keeps the token off a plaintext socket. Overriding a PyMySQL
    private method is deliberate: there is no public hook between reading the
    server capabilities and sending the credential. The dependency is pinned to
    a single minor version (`pymysql ~=1.1.0`), and the override fails closed -
    an unexpected internal change surfaces as a failed connection, never as a
    silent plaintext one.
    """

    def _request_authentication(self) -> Any:
        """Send the authentication handshake once TLS is guaranteed.

        Returns:
            Whatever the PyMySQL implementation returns.

        Raises:
            RuntimeError: If the server did not negotiate TLS.
        """
        # `server_capabilities` and `_request_authentication` are real PyMySQL
        # members that the `types-PyMySQL` stubs do not declare.
        capabilities: int = self.server_capabilities  # type: ignore[attr-defined]
        if not (self.ssl and capabilities & CLIENT.SSL):
            raise RuntimeError(
                "AWS RDS IAM authentication requires TLS, but the database "
                "server did not offer an encrypted connection. Refusing to "
                "send the authentication token over an unencrypted socket."
            )
        return super()._request_authentication()  # type: ignore[misc]


class RDSIAMAuthenticator:
    """Mints short-lived RDS IAM tokens for SQLAlchemy engine connections.

    RDS IAM tokens expire after 15 minutes, so they are minted per connection
    attempt rather than baked into the engine URL. One authenticator is shared
    by every engine built from the same store configuration: constructing a
    boto3 client loads botocore's service and endpoint models from disk, which
    is too expensive to repeat for each of the engines a server start creates.
    """

    def __init__(self, aws_region: str) -> None:
        """Initialize the authenticator and its AWS client.

        Args:
            aws_region: The AWS region of the RDS instance.

        Raises:
            ImportError: If the optional AWS SDK dependency is not installed.
        """
        try:
            import boto3
            from botocore.exceptions import (
                ClientError,
                ConnectionClosedError,
                ConnectTimeoutError,
                EndpointConnectionError,
                ReadTimeoutError,
            )
        except ImportError as error:
            raise ImportError(
                "AWS RDS IAM database authentication requires the optional "
                "AWS SDK dependency. Install it with "
                "`pip install 'zenml[aws-rds-iam]'`."
            ) from error

        self.aws_region = aws_region
        self.client = boto3.client("rds", region_name=aws_region)
        self._client_error: Type[Exception] = ClientError
        self._transient_errors: Tuple[Type[Exception], ...] = (
            ConnectionClosedError,
            ConnectTimeoutError,
            EndpointConnectionError,
            ReadTimeoutError,
        )

    def _is_transient(self, error: Exception) -> bool:
        """Check whether a failed token request may succeed on a retry.

        Args:
            error: The error raised while requesting a token.

        Returns:
            Whether the error is transient.
        """
        if isinstance(error, self._transient_errors):
            return True
        if isinstance(error, self._client_error):
            code = error.response.get("Error", {}).get("Code")  # type: ignore[attr-defined]
            return code in TRANSIENT_ERROR_CODES
        return False

    def generate_token(self, host: str, port: int, username: str) -> str:
        """Generate an RDS IAM authentication token.

        Transient transport and throttling errors are retried; every other
        error - notably authorization failures - is raised immediately, because
        retrying them only delays an actionable message.

        Args:
            host: The hostname the connection is being made to.
            port: The port the connection is being made to.
            username: The database user to authenticate as.

        Returns:
            The generated authentication token.

        Raises:
            Exception: Whatever the AWS SDK raised, once retries are exhausted
                or the error is not retryable.
        """
        delays = iter(
            exponential_backoff_delays(
                attempts=TOKEN_ATTEMPTS - 1,
                initial_delay=TOKEN_INITIAL_DELAY,
                max_delay=TOKEN_MAX_DELAY,
                factor=2.0,
                jitter="none",
            )
        )
        for _ in range(TOKEN_ATTEMPTS - 1):
            try:
                return self._request_token(host, port, username)
            except Exception as error:
                if not self._is_transient(error):
                    raise
                time.sleep(next(delays))

        return self._request_token(host, port, username)

    def _request_token(self, host: str, port: int, username: str) -> str:
        """Request a single RDS IAM authentication token.

        Args:
            host: The hostname the connection is being made to.
            port: The port the connection is being made to.
            username: The database user to authenticate as.

        Returns:
            The generated authentication token.
        """
        token: str = self.client.generate_db_auth_token(
            DBHostname=host,
            Port=port,
            DBUsername=username,
        )
        return token

    def register(self, engine: Engine) -> None:
        """Wire IAM authentication into an engine's connection lifecycle.

        Args:
            engine: The engine whose connections should authenticate via IAM.
        """

        @event.listens_for(engine.dialect, "do_connect")
        def _connect_with_iam_token(
            dialect: Any,
            connection_record: Any,
            cargs: List[Any],
            cparams: Dict[str, Any],
        ) -> Any:
            del dialect, connection_record, cargs
            cparams["password"] = self.generate_token(
                host=cparams["host"],
                port=int(cparams.get("port") or 3306),
                username=cparams["user"],
            )
            return TLSRequiredMySQLConnection(**cparams)

        @event.listens_for(engine, "connect")
        def _assert_verified_tls(
            dbapi_connection: Any, connection_record: Any
        ) -> None:
            del connection_record
            assert_verified_tls(dbapi_connection)


def assert_verified_tls(dbapi_connection: Any) -> None:
    """Check that a connection runs over TLS with a verified peer certificate.

    This runs after authentication and complements the pre-authentication gate
    in `TLSRequiredMySQLConnection`: it confirms that the negotiated session
    actually validated the server certificate and hostname, rather than only
    that TLS was used at all.

    Args:
        dbapi_connection: The DBAPI connection to check.

    Raises:
        RuntimeError: If the connection is not running over verified TLS.
    """
    tls_socket = getattr(dbapi_connection, "_sock", None)
    if not isinstance(tls_socket, ssl.SSLSocket):
        raise RuntimeError(
            "AWS RDS IAM authentication requires a live TLS connection."
        )

    tls_context = tls_socket.context
    if (
        tls_context.verify_mode != ssl.CERT_REQUIRED
        or not tls_context.check_hostname
        or not tls_socket.server_hostname
        or not tls_socket.getpeercert()
    ):
        raise RuntimeError(
            "AWS RDS IAM authentication requires verified TLS with "
            "hostname validation."
        )
