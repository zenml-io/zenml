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

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Never, Optional, Type, cast

from pydantic import BaseModel

from zenml import get_step_context
from zenml.alerter.base_alerter import BaseAlerter, BaseAlerterStepParameters
from zenml.integrations.smtp_email.flavors.smtp_email_alerter_flavor import (
    SMTPEmailAlerterConfig,
    SMTPEmailAlerterSettings,
)
from zenml.logger import get_logger

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
        param_class: Type = None,
    ) -> any:
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

        Raises:
            RuntimeError: if config is not of type `BaseAlerterStepParameters`.
            ValueError: if an email recipient was neither defined in the config
                nor in the alerter component.
        """
        return self._get_attribute_value(
            attribute_name="recipient_email",
            params=params,
            fail_if_missing=True,
            param_class=BaseAlerterStepParameters,
        )

    def _should_include_html(
        self, params: Optional[BaseAlerterStepParameters] = None
    ) -> bool:
        """Check if HTML content should be included.

        Args:
            params: Optional parameters.

        Returns:
            Boolean indicating if HTML should be included.
        """
        return self._get_attribute_value(
            attribute_name="include_html", params=params
        )

    def _get_subject_prefix(self) -> str:
        """Get the subject prefix to use.

        Returns:
            String prefix for email subjects.
        """
        return self._get_attribute_value(attribute_name="subject_prefix")

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

        # Properly format the message for HTML
        # - Replace newlines with <br> tags
        # - Add <pre> tags for code blocks
        # - Convert Markdown-style formatting to HTML (backticks, asterisks)
        formatted_message = message
        if message:
            # Helper function to process markdown-style formatting
            def process_markdown_line(line: str) -> str:
                # Handle backticks for code
                import re

                # Process inline code with backticks - replace `code` with <code>code</code>
                line = re.sub(
                    r"`([^`]+)`",
                    r'<code style="background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
                    line,
                )

                # Process bold with asterisks - replace *text* with <strong>text</strong>
                line = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", line)

                # Process italic with underscores - replace _text_ with <em>text</em>
                line = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", line)

                return line

            # Check if the message contains a traceback or code block
            if "Traceback" in message or "File " in message:
                # For tracebacks, use <pre> to preserve formatting
                formatted_parts: List[str] = []
                in_traceback = False
                for line in message.split("\n"):
                    if "Traceback" in line or in_traceback or "File " in line:
                        in_traceback = True
                        if not formatted_parts or not formatted_parts[
                            -1
                        ].startswith("<pre"):
                            formatted_parts.append(
                                "<pre style='font-family: monospace; white-space: pre-wrap; font-size: 12px; background-color: #f8f8f8; padding: 10px; border-radius: 3px;'>"
                            )
                        formatted_parts[-1] += line + "\n"
                    else:
                        if formatted_parts and formatted_parts[-1].startswith(
                            "<pre"
                        ):
                            formatted_parts[-1] += "</pre>"
                        # Process markdown formatting on non-traceback lines
                        formatted_line = process_markdown_line(line)
                        formatted_parts.append(formatted_line + "<br>")

                # Close the last pre tag if needed
                if formatted_parts and formatted_parts[-1].startswith("<pre"):
                    formatted_parts[-1] += "</pre>"

                formatted_message = "".join(formatted_parts)
            else:
                # For regular messages, process each line for markdown and replace newlines with <br> tags
                formatted_lines = []
                for line in message.split("\n"):
                    formatted_line = process_markdown_line(line)
                    formatted_lines.append(formatted_line)
                formatted_message = "<br>".join(formatted_lines)

        if (
            params
            and isinstance(params, SMTPEmailAlerterParameters)
            and params.payload is not None
        ):
            payload = params.payload
            html = f"""
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
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{payload.pipeline_name}</td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Step:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{payload.step_name}</td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Stack:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{payload.stack_name}</td>
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
            return html

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
        message: Optional[str] = None,
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Send an email alert.

        Args:
            message: Message content for the email.
            params: Optional parameters.

        Returns:
            True if operation succeeded, else False
        """
        if message is None:
            message = "ZenML Alert"

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
                subject = f"{self._get_subject_prefix()} {message[:50]}{'...' if len(message) > 50 else ''}"

            email_message["Subject"] = subject

            # Attach plain text version
            email_message.attach(MIMEText(message, "plain"))

            # Attach HTML version if enabled
            if include_html:
                html_body = self._create_html_body(message, params)
                email_message.attach(MIMEText(html_body, "html"))

            # Send email
            server = smtplib.SMTP(
                self.config.smtp_server, self.config.smtp_port
            )
            if self.config.use_tls:
                server.starttls()
            server.login(self.config.sender_email, self.config.password)
            server.send_message(email_message)
            server.quit()

            logger.info("Email alert sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
            return False

    def ask(
        self, question: str, params: Optional[BaseAlerterStepParameters] = None
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
