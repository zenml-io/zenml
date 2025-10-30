from zenml import pipeline, step, get_step_context
from zenml.client import Client
from zenml.integrations.slack.alerters.slack_alerter import (
    SlackAlerterParameters, SlackAlerterPayload
)


# Displaying pipeline info
@step
def post_statement() -> None:
    params = SlackAlerterParameters(
        payload=SlackAlerterPayload(
            pipeline_name=get_step_context().pipeline.name,
            step_name=get_step_context().step_run.name,
            stack_name=Client().active_stack.name,

        ),

    )
    Client().active_stack.alerter.post(
        message="This is a message with additional information about your pipeline.",
        params=params
    )


# Formatting with blocks and custom approval options
@step
def ask_question() -> bool:
    message = ":tada: Should I continue? (Y/N)"
    my_custom_block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": message,
                "emoji": True
            }
        }
    ]
    params = SlackAlerterParameters(
        blocks=my_custom_block,
        approve_msg_options=["Y"],
        disapprove_msg_options=["N"],

    )
    return Client().active_stack.alerter.ask(question=message, params=params)

@step  
def process_approval_response(approved: bool) -> None:
    if approved:
        print("User approved! Continuing with operation...")
        # Your logic here
    else:
        print("User declined. Stopping operation.")


@pipeline(enable_cache=False)
def my_pipeline():
    post_statement()
    approved = ask_question()
    process_approval_response(approved)


if __name__ == "__main__":
    my_pipeline()