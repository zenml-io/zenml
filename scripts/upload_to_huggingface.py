from huggingface_hub import HfApi
import os

def upload_to_huggingface():
    api = HfApi(token=os.environ["HF_TOKEN"])
    
    # Upload OpenAI summary
    api.upload_file(
        path_or_fileobj="summarized_docs.txt",
        path_in_repo="how-to-guides.txt",
        repo_id="zenml/llms.txt",
        repo_type="dataset"
    )
    
    # Upload repomix outputs
    for filename in ["component-guide.txt", "basics.txt", "llms-full.txt"]:
        api.upload_file(
            path_or_fileobj=f"repomix-outputs/{filename}",
            path_in_repo=filename,
            repo_id="zenml/llms.txt",
            repo_type="dataset"
        )

if __name__ == "__main__":
    upload_to_huggingface() 