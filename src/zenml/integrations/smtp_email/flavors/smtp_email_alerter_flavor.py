#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""SMTP Email alerter flavor."""

import smtplib
from typing import TYPE_CHECKING, Optional, Type

from pydantic import field_validator

from zenml.alerter.base_alerter import BaseAlerterConfig, BaseAlerterFlavor
from zenml.config.base_settings import BaseSettings
from zenml.integrations.smtp_email import SMTP_EMAIL_ALERTER_FLAVOR
from zenml.integrations.smtp_email.utils import validate_email
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.integrations.smtp_email.alerters import SMTPEmailAlerter


class SMTPEmailAlerterSettings(BaseSettings):
    """Settings for the SMTP Email alerter.

    Attributes:
        recipient_email: The email address of the recipient.
        subject_prefix: Prefix to prepend to all email subjects.
        include_html: Whether to include HTML formatted emails.
    """

    recipient_email: Optional[str] = None
    subject_prefix: str = "[ZenML]"
    include_html: bool = True

    @field_validator("recipient_email")
    @classmethod
    def validate_recipient_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate recipient email format.

        Args:
            v: The recipient email to validate.

        Returns:
            The validated email or None.
        """
        if v is not None:
            return validate_email(v)
        return v


class SMTPEmailAlerterConfig(BaseAlerterConfig, SMTPEmailAlerterSettings):
    """SMTP Email alerter config.

    Attributes:
        smtp_server: The SMTP server address (e.g., smtp.gmail.com).
        smtp_port: The SMTP server port (e.g., 587 for TLS).
        sender_email: The email address to send from.
        password: The password or app password for the sender's email account.
        use_tls: Whether to use TLS encryption for the SMTP connection.
    """

    smtp_server: str
    smtp_port: int = 587
    sender_email: str
    password: str = SecretField()
    use_tls: bool = True

    @field_validator("sender_email")
    @classmethod
    def validate_sender_email(cls, v: str) -> str:
        """Validate sender email format.

        Args:
            v: The sender email to validate.

        Returns:
            The validated email.
        """
        return validate_email(v)

    @property
    def is_valid(self) -> bool:
        """Check if the stack component is valid.

        Returns:
            True if the stack component is valid, False otherwise.
        """
        server = None
        try:
            # Test the SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(0)

            if self.use_tls:
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    logger.error(
                        f"TLS is not supported by the SMTP server {self.smtp_server}. "
                        "Please check your server configuration or disable TLS."
                    )
                    return False

            try:
                server.login(self.sender_email, self.password)
            except smtplib.SMTPAuthenticationError as e:
                logger.error(
                    f"SMTP authentication failed for {self.sender_email}. "
                    f"Please check your email credentials. Error: {str(e)}"
                )
                return False

            logger.debug(
                f"SMTP configuration validated successfully for {self.smtp_server}"
            )
            return True

        except smtplib.SMTPConnectError as e:
            logger.error(
                f"Failed to connect to SMTP server {self.smtp_server}:{self.smtp_port}. "
                f"Error: {str(e)}. Please check your server address and port."
            )
            return False
        except ConnectionRefusedError:
            logger.error(
                f"Connection refused by {self.smtp_server}:{self.smtp_port}. "
                "Please ensure the SMTP server is running and accessible."
            )
            return False
        except TimeoutError:
            logger.error(
                f"Connection to {self.smtp_server}:{self.smtp_port} timed out. "
                "Please check your network connection and server availability."
            )
            return False
        except Exception as e:
            logger.error(
                f"SMTP Email Alerter configuration error: {type(e).__name__}: {str(e)}"
            )
            return False
        finally:
            # Always close the connection if it was established
            if server:
                try:
                    server.quit()
                except Exception:
                    # Ignore errors when closing
                    pass


class SMTPEmailAlerterFlavor(BaseAlerterFlavor):
    """SMTP Email alerter flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SMTP_EMAIL_ALERTER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/alerter/email.png"

    @property
    def config_class(self) -> Type[SMTPEmailAlerterConfig]:
        """Returns `SMTPEmailAlerterConfig` config class.

        Returns:
                The config class.
        """
        return SMTPEmailAlerterConfig

    @property
    def implementation_class(self) -> Type["SMTPEmailAlerter"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.smtp_email.alerters import SMTPEmailAlerter

        return SMTPEmailAlerter
