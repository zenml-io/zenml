import os
import re
import json
from openai import OpenAI
from pathlib import Path
from typing import List, Dict
import time

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_content_blocks(md_content: str) -> str:
    """Extracts content blocks while preserving order and marking code blocks."""
    parts = re.split(r'(```[\s\S]*?```)', md_content)
    
    processed_content = ""
    for part in parts:
        if part.startswith('```'):
            processed_content += "\n[CODE_BLOCK_START]\n" + part + "\n[CODE_BLOCK_END]\n"
        else:
            cleaned_text = re.sub(r'\s+', ' ', part).strip()
            if cleaned_text:
                processed_content += "\n" + cleaned_text + "\n"
    
    return processed_content

def prepare_batch_requests(md_files: List[Path]) -> List[Dict]:
    """Prepares batch requests for each markdown file."""
    batch_requests = []

    for i, file_path in enumerate(md_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            processed_content = extract_content_blocks(content)

            file_path_str_with_no_slashes = str(file_path).replace("/", "_")
            
            # Prepare the request for this file
            request = {
                "custom_id": f"file-{i}-{file_path_str_with_no_slashes}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a technical documentation summarizer."
                        },
                        {
                            "role": "user",
                            "content": f"""Please summarize the following documentation text for another LLM to be able to answer questions about it with enough detail. 
                            Keep all important technical information and key points while removing redundancy and verbose explanations. 
                            Make it concise but ensure NO critical information is lost and some details that you think are important are kept.
                            Make the code shorter where possible keeping only the most important parts while preserving syntax and accuracy:

                            {processed_content}"""
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            }
            batch_requests.append(request)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return batch_requests

def submit_batch_job(batch_requests: List[Dict]) -> str:
    """Submits batch job to OpenAI and returns batch ID."""
    # Create batch input file
    batch_file_path = "batch_input.jsonl"
    with open(batch_file_path, "w") as f:
        for request in batch_requests:
            f.write(json.dumps(request) + "\n")
    
    # Upload the file
    with open(batch_file_path, "rb") as f:
        batch_input_file = client.files.create(
            file=f,
            purpose="batch"
        )
    
    # Create the batch
    batch = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "ZenML docs summarization"
        }
    )

    # Store batch ID for later use
    with open("batch_id.txt", "w") as f:
        f.write(batch.id)
    
    print(f"Batch job submitted with ID: {batch.id}")
    return batch.id

def main():
    docs_dir = "docs/book"
    
    # Get markdown files
    exclude_files = ["toc.md"]
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [file for file in md_files if file.name not in exclude_files]

    # Prepare and submit batch job
    batch_requests = prepare_batch_requests(md_files)
    batch_id = submit_batch_job(batch_requests)

if __name__ == "__main__":
    main() 