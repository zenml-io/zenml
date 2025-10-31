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
"""Implementation for SMTP Email flavor of alerter component."""

import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional, Type, Union, cast

from pydantic import BaseModel, field_validator
from typing_extensions import Never

from zenml import get_step_context
from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.smtp_email.flavors.smtp_email_alerter_flavor import (
    SMTPEmailAlerterConfig,
    SMTPEmailAlerterSettings,
)
from zenml.integrations.smtp_email.utils import validate_email
from zenml.logger import get_logger
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml.utils.markdown_utils import (
    EMAIL_MARKDOWN_OPTIONS,
    MarkdownOutputFormat,
    format_markdown,
)

logger = get_logger(__name__)


class SMTPEmailAlerterPayload(BaseModel):
    """SMTP Email alerter payload implementation."""

    pipeline_name: Optional[str] = None
    step_name: Optional[str] = None
    stack_name: Optional[str] = None


class SMTPEmailAlerterParameters(BaseAlerterStepParameters):
    """SMTP Email alerter parameters."""

    # The email address to send to
    recipient_email: Optional[str] = None

    # Email subject
    subject: Optional[str] = None

    # Custom HTML body
    html_body: Optional[str] = None

    # Whether to include HTML content
    include_html: Optional[bool] = None

    # Payload for email template
    payload: Optional[SMTPEmailAlerterPayload] = None

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


class SMTPEmailAlerter(BaseAlerter):
    """Send alerts via email using SMTP."""

    @property
    def config(self) -> SMTPEmailAlerterConfig:
        """Returns the `SMTPEmailAlerterConfig` config.

        Returns:
            The configuration.
        """
        return cast(SMTPEmailAlerterConfig, self._config)

    @property
    def settings_class(self) -> Type[SMTPEmailAlerterSettings]:
        """Settings class for the SMTP Email alerter.

        Returns:
            The settings class.
        """
        return SMTPEmailAlerterSettings

    def _get_attribute_value(
        self,
        attribute_name: str,
        params: Optional[BaseAlerterStepParameters] = None,
        fail_if_missing: bool = False,
        param_class: Optional[Type[BaseAlerterStepParameters]] = None,
    ) -> Any:
        """Generic method to get configuration attributes from different sources.

        Args:
            attribute_name: The name of the attribute to retrieve.
            params: Optional parameters.
            fail_if_missing: Whether to raise an error if the attribute is not found.
            param_class: The expected class type for params checking.

        Returns:
            The value of the requested attribute.

        Raises:
            RuntimeError: If params are not of the expected type.
            ValueError: If the attribute is not found and fail_if_missing is True.
        """
        # Check basic params validity
        if params and param_class and not isinstance(params, param_class):
            raise RuntimeError(
                f"The params object must be of type `{param_class.__name__}`."
            )

        # Check in params first
        if params:
            # For special case of SMTPEmailAlerterParameters attributes
            if isinstance(params, SMTPEmailAlerterParameters):
                if (
                    hasattr(params, attribute_name)
                    and getattr(params, attribute_name) is not None
                ):
                    return getattr(params, attribute_name)
            # For BaseAlerterStepParameters attributes
            elif (
                hasattr(params, attribute_name)
                and getattr(params, attribute_name) is not None
            ):
                return getattr(params, attribute_name)

        # Try to get from settings
        try:
            settings = cast(
                SMTPEmailAlerterSettings,
                self.get_settings(get_step_context().step_run),
            )
        except RuntimeError:
            settings = None

        if settings is not None and hasattr(settings, attribute_name):
            setting_value = getattr(settings, attribute_name)
            if setting_value is not None:
                return setting_value

        # Fall back to config value
        if hasattr(self.config, attribute_name):
            config_value = getattr(self.config, attribute_name)
            if config_value is not None or not fail_if_missing:
                return config_value

        # If we get here and fail_if_missing is True, raise an error
        if fail_if_missing:
            raise ValueError(
                f"The `{attribute_name}` is not set either in the runtime parameters, "
                f"settings, or the component configuration. Please specify at "
                f"least one."
            )

        return None

    def _get_recipient_email(
        self, params: Optional[BaseAlerterStepParameters] = None
    ) -> str:
        """Get the recipient email address to use.

        Args:
            params: Optional parameters.

        Returns:
            Email address of the recipient.
        """
        email = cast(
            str,
            self._get_attribute_value(
                attribute_name="recipient_email",
                params=params,
                fail_if_missing=True,
                param_class=BaseAlerterStepParameters,
            ),
        )
        # Validate the email format before returning
        return validate_email(email)

    def _should_include_html(
        self, params: Optional[BaseAlerterStepParameters] = None
    ) -> bool:
        """Check if HTML content should be included.

        Args:
            params: Optional parameters.

        Returns:
            Boolean indicating if HTML should be included.
        """
        return cast(
            bool,
            self._get_attribute_value(
                attribute_name="include_html", params=params
            ),
        )

    def _get_subject_prefix(self) -> str:
        """Get the subject prefix to use.

        Returns:
            String prefix for email subjects.
        """
        return cast(
            str, self._get_attribute_value(attribute_name="subject_prefix")
        )

    def _create_html_body(
        self, message: str, params: Optional[BaseAlerterStepParameters] = None
    ) -> str:
        """Create HTML content for the email.

        Args:
            message: The message to include.
            params: Optional parameters.

        Returns:
            HTML content for the email.
        """
        if (
            params
            and isinstance(params, SMTPEmailAlerterParameters)
            and params.html_body is not None
        ):
            return params.html_body

        # Use unified markdown utilities to format the message for HTML
        formatted_message = ""
        if message:
            formatted_message = format_markdown(
                message,
                output_format=MarkdownOutputFormat.HTML,
                options=EMAIL_MARKDOWN_OPTIONS,
            )

        if (
            params
            and isinstance(params, SMTPEmailAlerterParameters)
            and params.payload is not None
        ):
            payload = params.payload
            # Escape all payload fields to prevent XSS
            safe_pipeline_name = html.escape(payload.pipeline_name or "")
            safe_step_name = html.escape(payload.step_name or "")
            safe_stack_name = html.escape(payload.stack_name or "")

            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
                  <div style="text-align: center; margin-bottom: 20px;">
                    <img src="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png" alt="ZenML Logo" width="100" style="background-color: #361776; padding: 10px; border-radius: 10px;">
                  </div>
                  <h2 style="color: #361776; margin-bottom: 20px;">ZenML Pipeline Notification</h2>
                  <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd; width: 30%;"><strong>Pipeline:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{safe_pipeline_name}</td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Step:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{safe_step_name}</td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Stack:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{safe_stack_name}</td>
                    </tr>
                  </table>
                  <div style="background-color: #f3f3f3; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Message:</strong></p>
                    <div style="margin-top: 10px;">{formatted_message}</div>
                  </div>
                  <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 12px;">
                    <p>This is an automated message from ZenML. Please do not reply to this email.</p>
                  </div>
                </div>
              </body>
            </html>
            """
            return html_content

        # Simple HTML formatting if no payload
        return f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2>ZenML Notification</h2>
            <div>{formatted_message}</div>
            <p><em>This is an automated message from ZenML.</em></p>
          </body>
        </html>
        """

    def post(
        self,
        message: Union[str, AlerterMessage, None] = None,
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Send an email alert.

        This method now accepts a string or an AlerterMessage object.
        If AlerterMessage, we parse title/body/metadata for the email.

        Args:
            message: A string or AlerterMessage for email content.
            params: Optional parameters.

        Returns:
            True if operation succeeded, else False
        """
        # If we got an AlerterMessage, let's extract a fallback string from it.
        if isinstance(message, AlerterMessage):
            extracted_title = message.title or ""
            extracted_body = message.body or ""
            # We can store a combined string to pass as the fallback plain text.
            fallback_plain = (extracted_title + "\n" + extracted_body).strip()
            if not fallback_plain:
                fallback_plain = "ZenML Alert"
        else:
            # If it's None or a string, default the logic
            if message is None:
                fallback_plain = "ZenML Alert"
            else:
                fallback_plain = message

        try:
            recipient_email = self._get_recipient_email(params=params)
            include_html = self._should_include_html(params=params)

            # Create message
            email_message = MIMEMultipart("alternative")
            email_message["From"] = self.config.sender_email
            email_message["To"] = recipient_email

            # Determine subject
            if (
                params
                and isinstance(params, SMTPEmailAlerterParameters)
                and params.subject is not None
            ):
                subject = params.subject
            else:
                # Use default subject with prefix
                if isinstance(message, AlerterMessage):
                    # Use title or first part of body if available
                    msg_text = message.title or message.body or ""
                    truncated_text = msg_text[:50] if msg_text else ""
                    subject = f"{self._get_subject_prefix()} {truncated_text}{'...' if msg_text and len(msg_text) > 50 else ''}"
                else:
                    # At this point message is a string
                    msg_str = str(message)
                    subject = f"{self._get_subject_prefix()} {msg_str[:50]}{'...' if len(msg_str) > 50 else ''}"

            email_message["Subject"] = subject

            # Attach plain text version
            email_message.attach(MIMEText(fallback_plain, "plain"))

            # Attach HTML version if enabled
            if include_html:
                # If we had an AlerterMessage, create HTML from that, else from the fallback string
                if isinstance(message, AlerterMessage):
                    html_body = self._create_html_body(
                        message.body or "", params
                    )
                else:
                    html_body = self._create_html_body(fallback_plain, params)
                email_message.attach(MIMEText(html_body, "html"))

            # Send email with better error handling
            server = None
            try:
                # Connect to SMTP server
                server = smtplib.SMTP(
                    self.config.smtp_server, self.config.smtp_port
                )
                server.set_debuglevel(0)  # Set to 1 for SMTP debug output

                # Start TLS if configured
                if self.config.use_tls:
                    try:
                        server.starttls()
                    except smtplib.SMTPNotSupportedError:
                        logger.error(
                            f"TLS is not supported by the SMTP server {self.config.smtp_server}. "
                            "Please check your server configuration or disable TLS."
                        )
                        return False

                # Authenticate
                try:
                    server.login(
                        self.config.sender_email, self.config.password
                    )
                except smtplib.SMTPAuthenticationError as e:
                    logger.error(
                        f"SMTP authentication failed for {self.config.sender_email}. "
                        f"Please check your email credentials. Error: {str(e)}"
                    )
                    return False
                except smtplib.SMTPServerDisconnected:
                    logger.error(
                        "Server unexpectedly disconnected during authentication. "
                        "This might be due to incorrect server settings or network issues."
                    )
                    return False

                # Send the message
                try:
                    server.send_message(email_message)
                    logger.info(
                        f"Email alert sent successfully from {self.config.sender_email} "
                        f"to {recipient_email}"
                    )
                    return True
                except smtplib.SMTPRecipientsRefused as e:
                    logger.error(
                        f"Recipients refused by SMTP server: {e.recipients}. "
                        "Please check the recipient email addresses."
                    )
                    return False
                except smtplib.SMTPSenderRefused as e:
                    error_msg = (
                        e.smtp_error.decode("utf-8", errors="replace")
                        if isinstance(e.smtp_error, bytes)
                        else str(e.smtp_error)
                    )
                    logger.error(
                        f"Sender address {e.sender} refused by SMTP server: {error_msg}. "
                        "Please check your sender email configuration."
                    )
                    return False

            except smtplib.SMTPConnectError as e:
                logger.error(
                    f"Failed to connect to SMTP server {self.config.smtp_server}:{self.config.smtp_port}. "
                    f"Error: {str(e)}. Please check your server address and port."
                )
                return False
            except smtplib.SMTPServerDisconnected as e:
                logger.error(
                    f"Lost connection to SMTP server: {str(e)}. "
                    "This might be due to network issues or server timeout."
                )
                return False
            except smtplib.SMTPException as e:
                logger.error(
                    f"SMTP error occurred: {str(e)}. "
                    "Please check your SMTP configuration."
                )
                return False
            except ConnectionRefusedError:
                logger.error(
                    f"Connection refused by {self.config.smtp_server}:{self.config.smtp_port}. "
                    "Please ensure the SMTP server is running and accessible."
                )
                return False
            except TimeoutError:
                logger.error(
                    f"Connection to {self.config.smtp_server}:{self.config.smtp_port} timed out. "
                    "Please check your network connection and server availability."
                )
                return False
            except Exception as e:
                logger.error(
                    f"Unexpected error sending email alert: {type(e).__name__}: {str(e)}"
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

        except Exception as e:
            logger.error(f"Error preparing email message: {str(e)}")
            return False

    def ask(
        self,
        question: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> Never:
        """Method not supported for email alerters.

        Email doesn't support interactive approvals like chat services.
        This method raises a NotImplementedError as this functionality
        is not available for SMTP Email alerters.

        Args:
            question: Not used.
            params: Not used.

        Raises:
            NotImplementedError: Always raised as this functionality is not supported.
        """
        raise NotImplementedError(
            "The ask() method is not supported for SMTP Email alerters. "
            "Email doesn't support interactive approvals."
        )
