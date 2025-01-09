import json
from openai import OpenAI
from huggingface_hub import HfApi
import os

client = OpenAI()

def process_batch_output():
    # Read the batch ID from file
    with open("batch_id.txt", "r") as f:
        batch_id = f.read().strip()
    
    # Get the batch results file
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        raise Exception(f"Batch job {batch_id} is not completed. Status: {batch.status}")
    
    # Get the output file
    file_response = client.files.content(batch.output_file_id)
    text = file_response.text

    # Process the results and write to file
    with open("zenml_docs.txt", "w") as f:
        for line in text.splitlines():
            json_line = json.loads(line)
            
            # Extract and format the file path from custom_id
            file_path = "-".join(json_line["custom_id"].split("-")[2:]).replace("_", "/")
            
            # Write the file path and content
            f.write(f"File: {file_path}\n\n")
            f.write(json_line["response"]["body"]["choices"][0]["message"]["content"])
            f.write("\n\n" + "="*80 + "\n\n")

def upload_to_huggingface():
    api = HfApi()
    
    # Upload OpenAI summary
    api.upload_file(
        token=os.environ["HF_TOKEN"],
        repo_id="zenml/llms.txt",
        repo_type="dataset",
        path_in_repo="how-to-guides.txt",
        path_or_fileobj="zenml_docs.txt",
    )
    
    # Upload repomix outputs
    for filename in ["component-guide.txt", "basics.txt", "llms-full.txt"]:
        api.upload_file(
            token=os.environ["HF_TOKEN"],
            repo_id="zenml/llms.txt",
            repo_type="dataset",
            path_in_repo=filename,
            path_or_fileobj=f"repomix-outputs/{filename}",
        )

def main():
    process_batch_output()
    upload_to_huggingface()

if __name__ == "__main__":
    main() 