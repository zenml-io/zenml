import os
from pathlib import Path
from typing import List
from google import genai
from google.genai import types

from summarize_docs import extract_content_blocks

def initialize_gemini_client():
    """Initialize Gemini client with project settings."""
    return genai.Client(
        vertexai=True,
        project="zenml-core",
        location="us-central1"
    )

def get_gemini_config():
    """Returns the configuration for Gemini API calls."""
    return types.GenerateContentConfig(
        temperature=0.3,  # Lower temperature for more focused summaries
        max_output_tokens=2000,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ]
    )

def summarize_document(client, content: str, config) -> str:
    """Summarize a single document using Gemini."""
    prompt = f"""Please summarize the following documentation text for another LLM to be able to answer questions about it with enough detail. 
    Keep all important technical information and key points while removing redundancy and verbose explanations. 
    Make it concise but ensure NO critical information is lost and some details that you think are important are kept.
    Make the code shorter where possible keeping only the most important parts while preserving syntax and accuracy:

    {content}"""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=config
    )
    
    return response.text

def main():
    docs_dir = "docs/book/how-to"
    output_file = "summaries_gemini.md"
    
    # Initialize client and config
    client = initialize_gemini_client()
    config = get_gemini_config()
    
    # Get markdown files
    exclude_files = ["toc.md"]
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [file for file in md_files if file.name not in exclude_files]

    # delete files before docs/book/how-to/infrastructure-deployment/stack-deployment/README.md in the list
    for i, file in enumerate(md_files):
        if file == Path("docs/book/how-to/infrastructure-deployment/stack-deployment/README.md"):
            md_files = md_files[i:]
            break

    breakpoint()
    
    # Process each file
    with open(output_file, 'a', encoding='utf-8') as out_f:
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                processed_content = extract_content_blocks(content)  # Reuse from original
                summary = summarize_document(client, processed_content, config)
                
                out_f.write(f"# {file_path}\n\n")
                out_f.write(summary)
                out_f.write("\n\n" + "="*80 + "\n\n")
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    main()
