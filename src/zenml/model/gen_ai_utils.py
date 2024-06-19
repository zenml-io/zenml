import os
import litellm
from litellm import image_generation

from zenml.model.gen_ai_helper import (
    construct_json_response_of_model_version_stats,
    construct_json_response_of_stack_and_components_from_pipeline_run,
    construct_json_response_of_steps_code_from_pipeline_run,
    get_model_version_latest_run,
    get_pipeline_info,
)
from zenml.models.v2.core.model_version import ModelReportType


def prompt_gemini(prompt: str) -> str:
    # Get credentials from the environment
    vertex_credentials = os.environ.get("VERTEX_CREDENTIALS")
    vertex_project = os.environ.get("VERTEX_PROJECT", "zenml-core")
    vertex_location = os.environ.get("VERTEX_LOCATION", "europe-west4")

    kwargs = {}
    if vertex_credentials:
        kwargs["credentials"] = vertex_credentials
    if vertex_project:
        kwargs["project"] = vertex_project
    if vertex_location:
        kwargs["location"] = vertex_location

    response = litellm.completion(
        model="gemini-1.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        **kwargs,
    )
    return response.choices[0].message.content


# # TODO: requires a east-US deployment of dall-e
# def generate_image(prompt: str) -> str:
#     response = image_generation(
#         model="azure/dall-e-3",
#         api_base="https://zentestgpt4.openai.azure.com/",
#         api_version="2024-05-01-preview",
#         prompt=prompt,
#         api_key="9e696febb07e40619101a9184a6ccec6",
#     )

#     print(response)


def generate_summary_section(
    pipeline_run_code: str, stack_config: str, pipeline_spec: str
) -> str:
    """Generate a summary section for a model."""
    prompt = f"Write a report (formatted as Markdown markup) that will function as a 'Model Card' for the following code and stack information. Reference the pipeline which can be fun. Context is: ## Pipeline Code (made up of step functions that are part of a pipeline)\n{pipeline_run_code}\n\n and here's the pipeline spec so you can see how all the steps work together {pipeline_spec}\n ## Stack Config\nThis code is run on the following stack: \n{stack_config}. \n Rules: Write a brief overview section (explaining a summary of what the pipeline and its steps are doing) followed by sections on the code (i.e. how it works) and the stack on which it's run. There's no need for a conclusion section."

    return prompt_gemini(prompt)


def generate_poem(summary_section: str) -> str:
    prompt = f"Write a short and delightful poem that is 5 lines long that is based on the following summary section: {summary_section}. Feel free to be creative! Please output the poem text as Markdown with newlines included in the markup."
    return prompt_gemini(prompt)


def generate_code_improvement_suggestions(
    pipeline_spec: str, pipeline_run_code: str, stack_config: str
) -> str:
    prompt = f"Based on the following pipeline spec, pipeline code and stack config, generate a list of suggestions for improvement. Context is: ## Pipeline Spec\n{pipeline_spec}\n\n## Pipeline Code\n{pipeline_run_code}\n\n## Stack Config\nThis code is run on the following stack: \n{stack_config}. \n Rules: Write a list of suggestions for improvement. Suggestions should be in the form of code changes that would make the pipeline more efficient, robust and maintainable. Focus on the big picture approaches that could be taken to improve the code, especially in the context of the stack the user is using. Output your suggestions in Markdown markup format."
    return prompt_gemini(prompt)


def generate_stack_improvement_suggestions(
    pipeline_spec: str, stack_config: str
) -> str:
    prompt = f"Based on the following pipeline spec and stack config, generate a list of suggestions for improvement. Context is: ## Pipeline Spec\n{pipeline_spec}\n\n## Stack Config\n {stack_config}. If a user isn't using an experiment tracker, for example, they might want to use CometML or Wandb. If they aren't using a model registry, they might want to use MLflow or Hugging Face, and if they're running on a local orchestrator then consider using a cloud orchestrator. Stick to recommendations for the infrastructure side of this stack. Output your suggestions in Markdown markup format."
    return prompt_gemini(prompt)


def generate_log_failure_pattern_suggestions(
    logs: str, pipeline_spec: str, stack_config: str
) -> str:
    prompt = f"Based on the following pipeline spec, stack config and logs, generate a list of suggestions for improvement. Context is: ## Pipeline Spec\n{pipeline_spec}\n\n## Stack Config\n {stack_config}. \n ## Logs:\n {logs}\n\n If there are common failures in logs, then make suggestions for how the user can avoid these failures. Output your suggestions in Markdown markup format."
    return prompt_gemini(prompt)


def generate_stats_summary(stats: str) -> str:
    prompt = f"Generate a summary of the following stats and metadata (provided as a JSON string here: {stats}). Generate the section using Markdown formatting and feel free to use tables if you feel they are appropriate."
    return prompt_gemini(prompt)


def generate_model_report(
    report_type: ModelReportType, model_version_id: str
) -> str:
    latest_run = get_model_version_latest_run(model_version_id)
    pipeline_spec = get_pipeline_info(latest_run)
    pipeline_run_code = (
        construct_json_response_of_steps_code_from_pipeline_run(latest_run)
    )
    stack_config = (
        construct_json_response_of_stack_and_components_from_pipeline_run(
            latest_run
        )
    )
    if report_type in [
        ModelReportType.SUMMARY,
        ModelReportType.POEM,
        ModelReportType.ALL,
    ]:
        summary_section = generate_summary_section(
            pipeline_run_code=pipeline_run_code,
            stack_config=stack_config,
            pipeline_spec=pipeline_spec,
        )

    if report_type in [ModelReportType.POEM, ModelReportType.ALL]:
        poem = generate_poem(summary_section)
    if report_type in [ModelReportType.CODE_IMPROVEMENT, ModelReportType.ALL]:
        code_improvement_suggestions = generate_code_improvement_suggestions(
            pipeline_spec, pipeline_run_code, stack_config
        )
    if report_type in [ModelReportType.STACK_IMPROVEMENT, ModelReportType.ALL]:
        stack_improvement_suggestions = generate_stack_improvement_suggestions(
            pipeline_spec, stack_config
        )
    if report_type in [ModelReportType.LOG_FAILURE, ModelReportType.ALL]:
        log_failure_pattern_suggestions = (
            generate_log_failure_pattern_suggestions(
                pipeline_spec, stack_config, pipeline_run_code
            )
        )

    if report_type in [ModelReportType.STATS_SUMMARY, ModelReportType.ALL]:
        model_version_stats = construct_json_response_of_model_version_stats(
            model_version_id
        )
        stats_summary = generate_stats_summary(model_version_stats)

    if report_type == ModelReportType.SUMMARY:
        return summary_section
    if report_type == ModelReportType.POEM:
        return poem
    if report_type == ModelReportType.CODE_IMPROVEMENT:
        return code_improvement_suggestions
    if report_type == ModelReportType.STACK_IMPROVEMENT:
        return stack_improvement_suggestions
    if report_type == ModelReportType.LOG_FAILURE:
        return log_failure_pattern_suggestions
    if report_type == ModelReportType.ALL:
        return "\n".join(
            [
                summary_section,
                "# Poem\n\n",
                poem,
                "# Code Improvement Suggestions:\n\n",
                code_improvement_suggestions,
                "# Stack Improvement Suggestions:\n\n",
                stack_improvement_suggestions,
                "# Log Failure Pattern Suggestions:\n\n",
                log_failure_pattern_suggestions,
                "# Model Version Stats:\n\n",
                stats_summary,
            ]
        )

    raise ValueError(f"Invalid report type: {report_type}")
