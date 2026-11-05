# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
"""AWS RDS IAM authentication for MySQL database connections."""

import os
import ssl
import time
from typing import Any

import pymysql
from pymysql.constants import CLIENT, ER
from sqlalchemy import Engine, event

from zenml.logger import get_logger

logger = get_logger(__name__)


class TLSRequiredMySQLConnection(pymysql.Connection):
    """PyMySQL connection that never sends credentials without TLS."""

    def _request_authentication(self) -> Any:
        """Send the authentication handshake after TLS was negotiated.

        Returns:
            The result of the PyMySQL authentication handshake.

        Raises:
            RuntimeError: If the server did not negotiate TLS.
        """
        capabilities: int = self.server_capabilities  # type: ignore[attr-defined]
        if not (self.ssl and capabilities & CLIENT.SSL):
            raise RuntimeError(
                "AWS RDS IAM authentication requires TLS. Refusing to send "
                "the authentication token over an unencrypted connection."
            )
        return super()._request_authentication()  # type: ignore[misc]


def create_verified_ssl_context() -> ssl.SSLContext:
    """Create the verified TLS context used for RDS IAM authentication.

    Returns:
        A TLS context that verifies the certificate and hostname.

    Raises:
        ValueError: If the TLS context cannot be initialized.
    """
    try:
        return ssl.create_default_context()
    except OSError as error:
        raise ValueError(
            f"Failed to initialize TLS for AWS RDS IAM authentication: {error}"
        ) from error


def _create_rds_client(region: str, role_arn: str | None) -> Any:
    """Create an RDS client with automatically refreshed credentials.

    Args:
        region: AWS region of the database.
        role_arn: Optional role assumed directly with the pod's web identity.

    Returns:
        A boto3 RDS client.

    Raises:
        ImportError: If the optional AWS SDK dependency is not installed.
        ValueError: If a role is configured without a projected identity token.
    """
    try:
        import boto3
    except ImportError as error:
        raise ImportError(
            "AWS RDS IAM database authentication requires the optional AWS "
            "SDK dependency. Install it with "
            "`pip install 'zenml[aws-rds-iam]'`."
        ) from error

    if not role_arn:
        return boto3.client("rds", region_name=region)

    token_file = os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
    if not token_file:
        raise ValueError(
            "AWS RDS IAM role authentication requires the projected web "
            "identity token path in `AWS_WEB_IDENTITY_TOKEN_FILE`."
        )

    from botocore.credentials import (
        AssumeRoleWithWebIdentityProvider,
        CredentialResolver,
    )
    from botocore.session import Session as BotocoreSession

    profile_name = "zenml-rds-iam"
    botocore_session = BotocoreSession()
    provider = AssumeRoleWithWebIdentityProvider(
        load_config=lambda: {
            "profiles": {
                profile_name: {
                    "role_arn": role_arn,
                    "role_session_name": "zenml-rds-iam",
                    "web_identity_token_file": token_file,
                }
            }
        },
        client_creator=botocore_session.create_client,
        profile_name=profile_name,
        disable_env_vars=True,
    )
    botocore_session.register_component(
        "credential_provider", CredentialResolver([provider])
    )
    return boto3.Session(
        botocore_session=botocore_session,
        region_name=region,
    ).client("rds")


def generate_rds_iam_token(
    *,
    region: str,
    role_arn: str | None,
    host: str,
    port: int,
    username: str,
) -> str:
    """Generate an RDS IAM token for a non-SQLAlchemy database client.

    Args:
        region: AWS region of the database.
        role_arn: Optional role assumed directly with the pod's web identity.
        host: Database or proxy hostname.
        port: Database port.
        username: Database username.

    Returns:
        A short-lived RDS IAM authentication token.
    """
    client = _create_rds_client(region, role_arn)
    token: str = client.generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=username,
    )
    return token


def _is_iam_propagation_error(error: Exception) -> bool:
    """Check whether an error can be explained by pending IAM propagation.

    Args:
        error: The error raised while generating a token or connecting.

    Returns:
        True for STS or database access-denied errors.
    """
    if isinstance(error, pymysql.err.OperationalError):
        return bool(error.args[0] == ER.ACCESS_DENIED_ERROR)

    # The AWS SDK is optional, so its errors are matched by shape.
    response: dict[str, Any] = getattr(error, "response", {})
    return response.get("Error", {}).get("Code") in (
        "AccessDenied",
        "InvalidIdentityToken",
    )


def configure_rds_iam_authentication(
    engine: Engine,
    region: str,
    role_arn: str | None = None,
    max_wait_seconds: float = 30.0,
) -> None:
    """Generate a fresh IAM token for every physical engine connection.

    IAM is eventually consistent, so a newly created role or `rds-db:connect`
    policy may be rejected at first. Such connections are retried for a
    bounded time, because a misconfigured role fails the same way.

    Args:
        engine: SQLAlchemy engine to configure.
        region: AWS region of the database.
        role_arn: Optional role assumed directly with the pod's web identity.
        max_wait_seconds: Maximum total time a connection attempt waits for
            IAM changes to propagate.
    """
    client = _create_rds_client(region, role_arn)

    @event.listens_for(engine.dialect, "do_connect")
    def _connect_with_iam_token(
        _dialect: Any,
        _connection_record: Any,
        _cargs: list[Any],
        cparams: dict[str, Any],
    ) -> Any:
        waited, delay = 0.0, 1.0
        while True:
            try:
                cparams["password"] = client.generate_db_auth_token(
                    DBHostname=cparams["host"],
                    Port=int(cparams.get("port") or 3306),
                    DBUsername=cparams["user"],
                )
                return TLSRequiredMySQLConnection(**cparams)
            except Exception as error:
                delay = min(delay, max_wait_seconds - waited)
                if delay <= 0 or not _is_iam_propagation_error(error):
                    raise
                logger.warning(
                    "AWS RDS IAM authentication is not available yet (%s); "
                    "retrying in %.1f seconds.",
                    error,
                    delay,
                )
                time.sleep(delay)
                waited += delay
                delay *= 2
