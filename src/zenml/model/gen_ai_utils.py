import litellm
from litellm import image_generation

litellm.vertex_project = "zenml-core"  # Your Project ID
litellm.vertex_location = "europe-west4"  # proj location


def prompt_gemini(prompt: str) -> str:
    response = litellm.completion(
        model="gemini-1.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return response.choices[0].message.content


# TODO: requires a east-US deployment of dall-e
def generate_image(prompt: str) -> str:
    response = image_generation(
        model="azure/dall-e-3",
        api_base="https://zentestgpt4.openai.azure.com/",
        api_version="2024-05-01-preview",
        prompt=prompt,
        api_key="9e696febb07e40619101a9184a6ccec6",
    )

    print(response)


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


def generate_stats_summary(
    stats: str
) -> str:
    prompt = f"Generate a summary of the following stats and metadata (provided as a JSON string here: {stats}). Generate the section using Markdown formatting and feel free to use tables if you feel they are appropriate."
    return prompt_gemini(prompt)
