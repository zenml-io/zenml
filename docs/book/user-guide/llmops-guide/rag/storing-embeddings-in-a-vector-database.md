---
description: Store embeddings in a vector database for efficient retrieval.
---

# Storing Embeddings in a Vector Database

Now that we have our index store, we can use it to create a chatbot that can
answer questions based on the documents in the index store. We can use the
`langchain` library to create a chatbot that uses the index store to retrieve
relevant documents and then generate a response based on those documents.

Here's an example of how you might do this using the `ConversationalChatAgent`.
The advantage of using a framework to handle this part is that it abstracts away
the complexity of managing the retriever and generator models, allowing you to
focus on building the chatbot and integrating it into your application.

```python
from typing import Dict
from typing_extensions import Annotated

from agent.agent_executor_materializer import AgentExecutorMaterializer
from agent.prompt import PREFIX, SUFFIX
from langchain.agents import ConversationalChatAgent
from langchain.chat_models import ChatOpenAI
from langchain.schema.vectorstore import VectorStore
from langchain.tools.vectorstore.tool import VectorStoreQATool
from langchain.agents import AgentExecutor
from pydantic import BaseModel
from zenml import step, ArtifactConfig, log_artifact_metadata


PIPELINE_NAME = "zenml_agent_creation_pipeline"
# Choose what character to use for your agent's answers
CHARACTER = "technical assistant"


class AgentParameters(BaseModel):
    """Parameters for the agent."""

    llm: Dict = {
        "temperature": 0,
        "max_tokens": 1000,
        "model_name": "gpt-3.5-turbo",
    }

    # allow extra fields
    class Config:
        extra = "ignore"


@step(output_materializers=AgentExecutorMaterializer)
def agent_creator(
    vector_store: VectorStore, config: AgentParameters = AgentParameters()
) -> Annotated[
    AgentExecutor, ArtifactConfig(name="agent", is_model_artifact=True)
]:
    """Create an agent from a vector store.

    Args:
        vector_store: Vector store to create agent from.

    Returns:
        An AgentExecutor.
    """
    tools = [
        VectorStoreQATool(
            name=f"zenml-qa-tool",
            vectorstore=vector_store,
            description="Use this tool to answer questions about ZenML. "
            "How to debug errors in ZenML, how to answer conceptual "
            "questions about ZenML like available features, existing abstractions, "
            "and other parts from the documentation.",
            llm=ChatOpenAI(**config.llm),
        ),
    ]

    system_prompt = PREFIX.format(character=CHARACTER)

    my_agent = ConversationalChatAgent.from_llm_and_tools(
        llm=ChatOpenAI(**config.llm),
        tools=tools,
        system_message=system_prompt,
        human_message=SUFFIX,
    )

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=my_agent,
        tools=tools,
        verbose=True,
    )

    log_artifact_metadata(
        artifact_name="agent",
        metadata={
            "Tools and their descriptions": {
                tool.name: tool.description for tool in tools
            },
            "Personality": {
                "character": CHARACTER,
                "temperature": config.llm["temperature"],
                "model_name": config.llm["model_name"],
            },
        },
    )

    return agent_executor
```

The other benefit of the step returning an agent is that you might choose to
enhance that agent with more tools or extra capabilities. For example, you could
add a search tool that allows the agent to search online for answers alongside
the documents we have in the index store, and you can tweak the personality
using parameters such as the temperature, model name, and character.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
