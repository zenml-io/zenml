#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os
import re
from pathlib import Path

from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_content_blocks(md_content: str) -> str:
    """Extracts content blocks while preserving order and marking code blocks."""
    parts = re.split(r"(```[\s\S]*?```)", md_content)

    processed_content = ""
    for part in parts:
        if part.startswith("```"):
            processed_content += (
                "\n[CODE_BLOCK_START]\n" + part + "\n[CODE_BLOCK_END]\n"
            )
        else:
            cleaned_text = re.sub(r"\s+", " ", part).strip()
            if cleaned_text:
                processed_content += "\n" + cleaned_text + "\n"

    return processed_content


def summarize_content(content: str, file_path: str) -> str:
    """Summarizes content using OpenAI API."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical documentation summarizer.",
                },
                {
                    "role": "user",
                    "content": f"""Please summarize the following documentation text for another LLM to be able to answer questions about it with enough detail. 
                    Keep all important technical information and key points while removing redundancy and verbose explanations. 
                    Make it concise but ensure NO critical information is lost and some details that you think are important are kept.
                    Make the code shorter where possible keeping only the most important parts while preserving syntax and accuracy:

                    {content}""",
                },
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing {file_path}: {e}")
        return ""


def main():
    docs_dir = "docs/book"
    output_file = "summarized_docs.txt"

    # Get markdown files
    exclude_files = ["toc.md"]
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [file for file in md_files if file.name not in exclude_files]

    # Process each file and write summaries
    with open(output_file, "w", encoding="utf-8") as out_f:
        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                processed_content = extract_content_blocks(content)
                summary = summarize_content(processed_content, str(file_path))

                if summary:
                    out_f.write(f"=== File: {file_path} ===\n\n")
                    out_f.write(summary)
                    out_f.write("\n\n" + "=" * 50 + "\n\n")

                    print(f"Processed: {file_path}")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
