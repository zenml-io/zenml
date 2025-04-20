---
icon: robot
description: The llms.txt file(s) for ZenML
---

## About llms.txt
The llms.txt file format was proposed by [llmstxt.org](https://llmstxt.org/) as a standard way to provide information to help LLMs answer questions about a product/website. From their website:

> We propose adding a /llms.txt markdown file to websites to provide LLM-friendly content. This file offers brief background information, guidance, and links to detailed markdown files. llms.txt markdown is human and LLM readable, but is also in a precise format allowing fixed processing methods (i.e. classical programming techniques such as parsers and regex).

## ZenML's llms.txt

ZenML's documentation is now made available to LLMs at the following link:

```
https://docs.zenml.io/llms.txt
```

This file contains a comprehensive summary of the ZenML documentation
(containing links and descriptions) that LLMs can use to answer questions about
ZenML's features, functionality, and usage.

## How to use the llms.txt file

When working with LLMs (like ChatGPT, Claude, or others), you can use this file to help the model provide more accurate answers about ZenML:

- Point the LLM to the `docs.zenml.io/llms.txt` URL when asking questions about ZenML
- While prompting, instruct the LLM to only provide answers based on information contained in the file to avoid hallucinations
- For best results, use models with sufficient context window to process the entire file

To use the llms.txt file in partnership with an MCP client, you can use the
following tools:

- [GitMCP](https://gitmcp.io/) - A way to quickly create an MCP server for a
  github repository (e.g. for `zenml-io/zenml`)
- [mcp-llms](https://github.com/parlance-labs/mcp-llms.txt/) - This shows how to
  use an MCP server to iteratively explore the llms.txt file with your MCP
  client
- [mcp-llms-txt-explorer](https://github.com/thedaviddias/mcp-llms-txt-explorer) -
  A tool to help you explore and discover websites that have llms.txt files
