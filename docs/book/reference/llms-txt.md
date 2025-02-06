---
icon: robot
description: The llms.txt file(s) for ZenML
---

# The llms.txt file(s) for ZenML

The `llms.txt` file is a summary of the ZenML documentation that can be used to answer basic questions about ZenML. It is available at https://zenml.io/llms.txt. Read on to learn about additional files, where they are hosted and how to use them.

## Available llms.txt files

Owing to ZenML's vast documentation, we have created multiple `llms.txt` files that cover different parts of the documentation. You can find them on ZenML's llms.txt HuggingFace dataset: https://huggingface.co/datasets/zenml/llms.txt

1. llms.txt

**Tokens**: 120k

This file covers the User Guides and the Getting Started section of the ZenML documentation and can be used for answering basic questions about ZenML. This file can also be used alongside other domain-specific files in cases where you need better answers.

2. component-guide.txt

**Tokens**: 180k

This file covers all the stack components in ZenML and can be used when you want to find answers pertaining to all of our integrations, how to configure/use them and more.

3. how-to-guides.txt

**Tokens**: 75k

This file contains all the doc pages in the how-to section of our documentation; each page summarized to contain all useful information. For most cases, the how-to guides can answer all process questions.

4. llms-full.txt

**Tokens**: 600k

The whole ZenML documentation in its glory, un-summarized. Use this for the most accurate answers on ZenML.

## How to use the llms.txt file

Below are some tips and recommendations for using the `llms.txt` files.

- Choose the file that pertains to the part of ZenML you want answers for.
- In every file, the text comes prefixed with the filename which means you can ask your LLM to return file references when answering questions. This is particularly helpful when using the how-to guides which don't the full text, but rather a summary of it.
- You can mix two files, as your context window allows to get more accurate results.
- While prompting, make sure you tell the LLM to not return an answer that it can't infer from the given text file, to avoid getting hallucinated answers.


