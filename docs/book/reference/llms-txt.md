---
icon: robot
description: Access ZenML documentation via MCP server or llms.txt
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

## Use llms-full.txt for complete documentation context

The llms-full.txt file contains the entire ZenML documentation in a single, concatenated markdown file optimized for LLMs. Use it when you want to load all docs as context at once (for example, a one-shot grounding pass) rather than querying individual pages. Access it here: https://docs.zenml.io/llms-full.txt. For interactive, selective queries from your IDE, the built-in MCP server is still the recommended option.

## Use the built-in GitBook MCP server (recommended)

ZenML docs are also exposed through a native GitBook MCP server that IDE agents can query in real time.

- Endpoint: https://docs.zenml.io/~gitbook/mcp

### Quick setup

#### Claude Code (VS Code)
Run the following command in your terminal to add the server:
```bash
claude mcp add zenmldocs --transport http https://docs.zenml.io/~gitbook/mcp
```

#### Cursor
Add the server via Cursor's JSON settings (Settings → search "MCP" → Configure via JSON):
```json
{
  "mcpServers": {
    "zenmldocs": {
      "transport": {
        "type": "http",
        "url": "https://docs.zenml.io/~gitbook/mcp"
      }
    }
  }
}
```

### Why use it
- Live doc queries directly from your IDE agent
- Syntax-aware, source-of-truth answers with fewer hallucinations
- Faster feature discovery across guides, APIs, and examples

The MCP server indexes the latest released documentation, not the develop branch.

{% hint style="info" %}
**Looking to chat with your ZenML server data?** ZenML also provides its own MCP server that connects directly to your ZenML server, allowing you to query pipelines, analyze runs, and trigger executions through natural language. See the [MCP Chat with Server guide](https://docs.zenml.io/user-guides/best-practices/mcp-chat-with-server) for setup instructions.
{% endhint %}

Prefer the native GitBook MCP server above for the best experience; if you prefer working directly with llms.txt or need alternative workflows, the following tools are helpful:

To use the llms.txt file in partnership with an MCP client, you can use the
following tools:

- [GitMCP](https://gitmcp.io/) - A way to quickly create an MCP server for a github repository (e.g. for `zenml-io/zenml`)
- [mcp-llms](https://github.com/parlance-labs/mcp-llms.txt/) - This shows how to use an MCP server to iteratively explore the llms.txt file with your MCP client
- [mcp-llms-txt-explorer](https://github.com/thedaviddias/mcp-llms-txt-explorer) -  A tool to help you explore and discover websites that have llms.txt files
