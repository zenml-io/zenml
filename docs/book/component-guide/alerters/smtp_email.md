---
description: Sending automated alerts via email using SMTP.
---

# SMTP Email Alerter

The `SMTPEmailAlerter` enables you to send email notifications directly from within your ZenML pipelines and steps. It supports both plain text and HTML-formatted emails, making it ideal for sending rich, visually appealing notifications.

## How to Create

### Generating an App Password (for Gmail)

If you plan to use Gmail as your SMTP server, you'll need to generate an App Password rather than using your regular account password:

1. Go to your [Google Account Security settings](https://myaccount.google.com/security)
2. Ensure 2-Step Verification is enabled
3. Under "Signing in to Google," select "App passwords"
4. Generate a new app password for "Mail" and "Other (Custom name)" - you can name it "ZenML"
5. Save the generated 16-character password for use in your alerter configuration

### Registering an SMTP Email Alerter in ZenML

To create an `SMTPEmailAlerter`, no additional integrations need to be installed as it uses the standard library's `smtplib` module.

You can use the ZenML CLI to create a secret and register an alerter:

```shell
# Create a secret for your email password/app password
zenml secret create email_credentials \
    --smtp_password=<YOUR_APP_PASSWORD>

# Register the alerter
zenml alerter register email_alerter \
    --flavor=smtp_email \
    --smtp_server=smtp.gmail.com \
    --smtp_port=587 \
    --sender_email=<YOUR_EMAIL_ADDRESS> \
    --password="{{email_credentials.smtp_password}}" \
    --recipient_email=<RECIPIENT_EMAIL_ADDRESS>
```

Here's what the parameters mean:

* `smtp_server`: Your email provider's SMTP server (e.g., `smtp.gmail.com` for Gmail)
* `smtp_port`: The port for your SMTP server (typically 587 for TLS)
* `sender_email`: The email address sending the notifications
* `password`: The password or app password for the sender email account
* `recipient_email`: (Optional) Default recipient email address for alerts

After you have registered the `email_alerter`, you can add it to your stack:

```shell
zenml stack register ... -al email_alerter --set
```

## How to Use

In ZenML, you can use the email alerter in various ways.

### Use the `post()` Method Directly

You can use the client to fetch the active alerter and use the `post` method directly:

```python
from zenml import pipeline, step
from zenml.client import Client

@step
def send_email_alert() -> None:
    Client().active_stack.alerter.post("Pipeline step completed successfully!")

@pipeline(enable_cache=False)
def my_pipeline():
    send_email_alert()

if __name__ == "__main__":
    my_pipeline()
```

### Use with Custom Settings

The SMTP Email alerter comes with several configurable settings:

```python
from zenml import pipeline, step
from zenml.client import Client

# Use different recipient and subject prefix for this step
@step(settings={"alerter": {
    "recipient_email": "team@example.com",
    "subject_prefix": "[URGENT]",
    "include_html": True
}})
def send_urgent_alert() -> None:
    Client().active_stack.alerter.post("Critical alert: Database backup required!")

@pipeline(enable_cache=False)
def my_pipeline():
    send_urgent_alert()

if __name__ == "__main__":
    my_pipeline()
```

### Use with SMTPEmailAlerterParameters and SMTPEmailAlerterPayload

You can customize email content and appearance using parameter and payload classes:

```python
from zenml import pipeline, step, get_step_context
from zenml.client import Client
from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerterParameters, SMTPEmailAlerterPayload
)

@step
def send_pipeline_status() -> None:
    # Create a payload with pipeline information
    payload = SMTPEmailAlerterPayload(
        pipeline_name=get_step_context().pipeline.name,
        step_name=get_step_context().step_run.name,
        stack_name=Client().active_stack.name,
    )
    
    # Set up parameters for this specific email
    params = SMTPEmailAlerterParameters(
        recipient_email="team@example.com",
        subject="Pipeline Execution Update",
        payload=payload
    )
    
    # Send the email with custom parameters
    Client().active_stack.alerter.post(
        message="The pipeline has completed successfully with all validation tests passing.",
        params=params
    )

@pipeline(enable_cache=False)
def my_pipeline():
    send_pipeline_status()

if __name__ == "__main__":
    my_pipeline()
```

You can also provide custom HTML content for complete control over email appearance:

```python
@step
def send_custom_html_email() -> None:
    # Create custom HTML
    custom_html = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f7f7f7; border-radius: 10px;">
          <h1 style="color: #4A6CFA;">Model Training Complete</h1>
          <p>Your machine learning model has completed training with the following metrics:</p>
          <ul>
            <li><strong>Accuracy:</strong> 92.5%</li>
            <li><strong>Precision:</strong> 90.2%</li>
            <li><strong>Recall:</strong> 88.7%</li>
          </ul>
          <p>View the <a href="https://cloud.zenml.io" style="color: #4A6CFA;">complete results in the dashboard</a>.</p>
        </div>
      </body>
    </html>
    """
    
    params = SMTPEmailAlerterParameters(
        subject="Model Training Results",
        html_body=custom_html
    )
    
    Client().active_stack.alerter.post(
        message="Model training complete. Accuracy: 92.5%, Precision: 90.2%, Recall: 88.7%",
        params=params
    )
```

### Using with Failure and Success Hooks

Email alerts are particularly useful when combined with step hooks for success and failure notifications.

#### Standard Alerter Hooks (Recommended)

The standard alerter hooks now use the new `AlerterMessage` format internally, which provides excellent email formatting:

```python
from zenml import pipeline, step
from zenml.hooks import alerter_failure_hook, alerter_success_hook

@step(on_failure=alerter_failure_hook, on_success=alerter_success_hook)
def risky_step() -> None:
    # This step will trigger alerts on either success or failure
    import random
    if random.random() < 0.5:
        raise RuntimeError("Step failed with a simulated error")
    return "Step completed successfully"

@pipeline(enable_cache=False)
def my_pipeline():
    risky_step()

if __name__ == "__main__":
    my_pipeline()
```

The alerter hooks use `AlerterMessage` format which provides:
- **Title**: "Pipeline Success Notification" or "Pipeline Failure Alert"
- **Body**: Detailed information about the pipeline, step, and context
- **Metadata**: Additional context like pipeline name, run ID, and stack name

The SMTP Email alerter automatically formats these messages into well-structured HTML emails.

#### Email-Specific Hooks (Enhanced Formatting)

The SMTP Email integration also provides specialized hooks that offer enhanced email-specific formatting:

```python
from zenml import pipeline, step
from zenml.integrations.smtp_email.hooks import (
    smtp_email_alerter_failure_hook,
    smtp_email_alerter_success_hook
)

@step(on_failure=smtp_email_alerter_failure_hook, on_success=smtp_email_alerter_success_hook)
def risky_step() -> None:
    # This step will trigger email-optimized alerts
    import random
    if random.random() < 0.5:
        raise RuntimeError("Step failed with a simulated error")
    return "Step completed successfully"

@pipeline(enable_cache=False)
def my_pipeline():
    risky_step()

if __name__ == "__main__":
    my_pipeline()
```

These specialized hooks provide additional email-specific features:
- Custom HTML templates with professional styling
- Email-optimized error formatting
- Structured payloads for better email organization
- Automatic subject line generation

Both approaches work well - use the standard hooks for consistency across alerter types, or use the email-specific hooks if you need the enhanced email formatting features.

### Using the Generic Alerter Step

ZenML provides a generic alerter step that works with any alerter flavor, including the SMTP Email alerter:

```python
from zenml import pipeline
from zenml.alerter.steps.alerter_post_step import alerter_post_step
from zenml.models.v2.misc.alerter_models import AlerterMessage

@pipeline(enable_cache=False)
def notification_pipeline():
    # Create an AlerterMessage object with title and body
    message = AlerterMessage(
        title="Pipeline Notification",
        body="Pipeline execution started!",
        metadata={
            "recipient_email": "team@example.com",
            "include_pipeline_info": True
        }
    )
    
    # Send the email notification
    alerter_post_step(message)
    
    # Perform other pipeline steps...

if __name__ == "__main__":
    notification_pipeline()
```

This provides a unified interface for sending email alerts that works consistently across all alerter flavors.

## Notes

* The `ask()` method is not supported in the SMTP Email alerter, as email doesn't support interactive approvals like chat systems.
* For security best practices, always store your email credentials as secrets rather than hardcoding them.
* You can use this alerter with any SMTP-compliant email service, including Gmail, Outlook, AWS SES, SendGrid, and others.

For more information and a full list of configurable attributes of the SMTP Email alerter, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-smtp_email/#zenml.integrations.smtp_email.alerters.smtp_email_alerter.SMTPEmailAlerter).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
