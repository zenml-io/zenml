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
            
            # Prepare the request for this file
            request = {
                "custom_id": f"file-{i}-{file_path.name}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a technical documentation summarizer optimizing content for LLM comprehension."
                        },
                        {
                            "role": "user",
                            "content": f"""Please summarize the following documentation text. 
                            Keep all important technical information and key points while removing redundancy and verbose explanations.
                            Make it concise but ensure no critical information is lost
                            Make the code shorter where possible too keeping only the most important parts while preserving syntax and accuracy:

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

    print(batch)
    
    return batch.id

def process_batch_results(batch_id: str, output_file: str):
    """Monitors batch job and processes results when complete."""
    while True:
        # Check batch status
        batch = client.batches.retrieve(batch_id)
        
        if batch.status == "completed":
            # Get results
            results = client.batches.list_events(batch_id=batch_id)
            
            # Process and write results
            with open(output_file, 'w', encoding='utf-8') as out_f:
                for event in results.data:
                    if event.type == "completion":
                        custom_id = event.request.custom_id
                        summary = event.completion.choices[0].message.content
                        
                        # Extract original filename from custom_id
                        file_id = custom_id.split("-", 1)[1]
                        
                        out_f.write(f"# {file_id}\n\n")
                        out_f.write(summary)
                        out_f.write("\n\n" + "="*80 + "\n\n")
            
            break
        
        elif batch.status == "failed":
            print("Batch job failed!")
            break
        
        # Wait before checking again
        time.sleep(60)

def main():
    docs_dir = "docs/book/how-to"
    output_file = "docs.txt"
    
    # Get markdown files
    exclude_files = ["toc.md"]
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [file for file in md_files if file.name not in exclude_files]
    
    # Prepare and submit batch job
    batch_requests = prepare_batch_requests(md_files)
    batch_id = submit_batch_job(batch_requests)
    
    print(f"Batch job submitted with ID: {batch_id}")
    print("Waiting for results...")
    
    # Process results
    # process_batch_results(batch_id, output_file)
    print("Processing complete!")

if __name__ == "__main__":
    main() 