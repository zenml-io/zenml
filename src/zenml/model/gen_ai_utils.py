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


def generate_summary_section(pipeline_run_code: str, stack_config: str) -> str:
    """Generate a summary section for a model."""
    prompt = f"Write a report (formatted as Markdown markup) that summarises the following code: ##Pipeline Code (made up of step functions that are part of a pipeline)\n{pipeline_run_code}\n\n ## Stack Config\nThis code is run on the following stack: \n{stack_config}. Please write a brief overview section followed by sections on the code (i.e. how it works) and the stack on which it's run."

    return prompt_gemini(prompt)
