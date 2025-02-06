import os

from huggingface_hub import HfApi

HEADER_TEXT = """
Available llms.txt files for ZenML are listed below. You can find them on ZenML's llms.txt HuggingFace dataset: https://huggingface.co/datasets/zenml/llms.txt

1. llms.txt (this one)
Tokens: 120k

This file covers the User Guides and the Getting Started section of the ZenML documentation and can be used for answering basic questions about ZenML. This file can also be used alongside other domain-specific files in cases where you need better answers.

2. component-guide.txt
Tokens: 180k

This file covers all the stack components in ZenML and can be used when you want to find answers pertaining to all of our integrations, how to configure/use them and more.

3. how-to-guides.txt
Tokens: 75k

This file contains all the doc pages in the how-to section of our documentation; each page summarized to contain all useful information. For most cases, the how-to guides can answer all process questions.

4. llms-full.txt
Tokens: 600k

The whole ZenML documentation in its glory, un-summarized. Use this for the most accurate answers on ZenML.
"""


def upload_to_huggingface():
    api = HfApi(token=os.environ["HF_TOKEN"])

    # Upload OpenAI summary
    api.upload_file(
        path_or_fileobj="summarized_docs.txt",
        path_in_repo="how-to-guides.txt",
        repo_id="zenml/llms.txt",
        repo_type="dataset",
    )

    # Upload repomix outputs
    for filename in ["component-guide.txt", "llms.txt", "llms-full.txt"]:
        # add the header text to the llms.txt file
        if filename == "llms.txt":
            with open(f"repomix-outputs/{filename}", "r") as f:
                content = f.read()
            with open(f"repomix-outputs/{filename}", "w") as f:
                f.write(HEADER_TEXT + "\n\n" + content)

        api.upload_file(
            path_or_fileobj=f"repomix-outputs/{filename}",
            path_in_repo=filename,
            repo_id="zenml/llms.txt",
            repo_type="dataset",
        )


if __name__ == "__main__":
    upload_to_huggingface()
