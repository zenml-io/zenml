"""Steps for creating and using prompts."""

from typing import List

from zenml import step
from zenml.prompts import Prompt


@step
def create_summarization_prompt_v1() -> Prompt:
    """Create version 1 prompt for text summarization (ZenML will auto-version this).

    Returns:
        Version 1 summarization prompt
    """
    template = """
    Please summarize the following text in 2-3 sentences, focusing on the main points:

    Text: {article}

    Summary:
    """.strip()

    return Prompt(template=template, variables={"article": ""})


@step
def create_summarization_prompt_v2() -> Prompt:
    """Create version 2 prompt for text summarization (ZenML will auto-version this).

    Returns:
        Version 2 summarization prompt - more detailed instructions
    """
    template = """
    You are an expert summarizer. Please provide a concise summary of the following text, 
    highlighting the key concepts and main ideas in exactly 2 sentences:

    Article: {article}

    Key Summary:
    """.strip()

    return Prompt(template=template, variables={"article": ""})


@step
def apply_prompt_to_text(prompt: Prompt, texts: List[str]) -> List[str]:
    """Apply a prompt template to multiple texts to generate formatted prompts.

    Args:
        prompt: The prompt template to use
        texts: List of texts to process

    Returns:
        List of formatted prompts ready for LLM processing
    """
    formatted_prompts = []

    for text in texts:
        # Format the prompt with the article text
        formatted = prompt.format(article=text)
        formatted_prompts.append(formatted)

    return formatted_prompts
