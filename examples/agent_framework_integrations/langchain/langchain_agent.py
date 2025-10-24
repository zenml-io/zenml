"""LangChain agent example for PanAgent."""

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI


def load_docs(input_dict: dict) -> str:
    """Load docs from a URL provided in the input and return the text content."""
    url = input_dict.get("url")
    if not url:
        return "No URL provided."

    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        return "\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Error loading URL: {str(e)}"


# Define the model and prompt
llm = ChatOpenAI(model="gpt-5-nano")
prompt = ChatPromptTemplate.from_template(
    "Write a concise summary of the following text:\n\n{text}"
)

# Create the runnable chain that PanAgent will discover
# The adapter will pass the full JSON body as the input dictionary
chain: Runnable = (
    RunnableLambda(load_docs)
    | RunnableLambda(lambda text: {"text": text})
    | prompt
    | llm
    | StrOutputParser()
)
