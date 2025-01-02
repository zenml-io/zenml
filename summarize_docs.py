import os
import re
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_content_and_codeblocks(md_content):
    """
    Separates markdown content into text and code blocks while preserving order.
    Returns list of tuples (is_code, content)
    """
    # Split by code blocks (```...)
    parts = re.split(r'(```[\s\S]*?```)', md_content)
    
    # Collect parts with their type
    processed_parts = []
    
    for part in parts:
        if part.startswith('```'):
            processed_parts.append((True, part))  # (is_code, content)
        else:
            # Clean up text content
            cleaned_text = re.sub(r'\s+', ' ', part).strip()
            if cleaned_text:
                processed_parts.append((False, cleaned_text))  # (is_code, content)
    
    return processed_parts

def summarize_text(text):
    """
    Uses OpenAI API to summarize the text content
    """
    if not text.strip():
        return ""
        
    prompt = """Please summarize the following documentation text. 
    Keep all important technical information and key points while removing redundancy and verbose explanations.
    Make it concise but ensure no critical information is lost:
    
    {text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical documentation summarizer."},
                {"role": "user", "content": prompt.format(text=text)}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in summarization: {e}")
        return text

def process_markdown_file(file_path):
    """
    Processes a single markdown file and returns the summarized content
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract parts while preserving order
        parts = extract_content_and_codeblocks(content)
        
        # Process each part
        final_content = f"# {file_path}\n\n"
        current_text_block = []
        
        for is_code, part in parts:
            if is_code:
                # If we have accumulated text, summarize and add it first
                if current_text_block:
                    text_to_summarize = ' '.join(current_text_block)
                    summarized = summarize_text(text_to_summarize)
                    final_content += summarized + "\n\n"
                    current_text_block = []
                
                # Add the code block
                final_content += f"{part}\n\n"
            else:
                current_text_block.append(part)
        
        # Handle any remaining text
        if current_text_block:
            text_to_summarize = ' '.join(current_text_block)
            summarized = summarize_text(text_to_summarize)
            final_content += summarized + "\n\n"
            
        return final_content
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    # Directory containing markdown files
    docs_dir = "docs/book/how-to"  # Update this path
    output_file = "docs.txt"
    
    # Files to exclude from processing
    exclude_files = [
        "toc.md",
    ]

    # Get all markdown files
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [file for file in md_files if file.name not in exclude_files]

    with open(output_file, 'a', encoding='utf-8') as out_f:
        for md_file in md_files:
            print(f"Processing: {md_file}")
            processed_content = process_markdown_file(md_file)
            
            if processed_content:
                out_f.write(processed_content)
                out_f.write("\n\n" + "="*80 + "\n\n")  # Separator between files

if __name__ == "__main__":
    main() 