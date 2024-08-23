import argparse
import logging
import os
import shutil
from pathlib import Path
import nbconvert
from traitlets.config import Config
import tempfile
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_badges(notebook_path: str, is_local: bool) -> str:
    if is_local:
        return ""
    repo_name = os.environ.get('GITHUB_REPOSITORY', 'zenml-io/zenml')
    relative_path = os.path.relpath(notebook_path, start='tutorials')
    colab_badge = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{repo_name}/blob/main/tutorials/{relative_path})"
    local_badge = f"[![Run Locally](https://img.shields.io/badge/run-locally-blue)](https://github.com/{repo_name})"
    return f"{colab_badge} {local_badge}\n\n"

def convert_notebook_to_markdown(notebook_path: str, output_dir: str, is_local: bool) -> str:
    c = Config()
    c.MarkdownExporter.preprocessors = ["nbconvert.preprocessors.ExtractOutputPreprocessor"]
    
    exporter = nbconvert.MarkdownExporter(config=c)
    output, _ = exporter.from_filename(notebook_path)
    
    badges = add_badges(notebook_path, is_local)
    output = badges + output
    
    output_filename = Path(notebook_path).stem + '.md'
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    logger.info(f"Successfully converted {notebook_path} to {output_path}")
    return output_filename

def generate_suggested_toc(guide_type: str, converted_files: List[str]) -> str:
    toc = f"## {guide_type}\n\n"
    toc += f"* [🐣 {guide_type}](user-guide/{guide_type.lower().replace(' ', '-')}/README.md)\n"
    for file in converted_files:
        if file != 'README.md':
            file_name = os.path.splitext(file)[0]
            title = ' '.join(word.capitalize() for word in file_name.split('_')[1:])
            toc += f"  * [{title}](user-guide/{guide_type.lower().replace(' ', '-')}/{file_name}.md)\n"
    return toc

def process_guide(guide_type: str, is_local: bool) -> tuple[str, List[str], List[str]]:
    tutorials_dir = Path('tutorials')
    guide_dir = next((d for d in tutorials_dir.iterdir() if d.is_dir() and d.name.replace('-', ' ') == guide_type.lower()), None)
    
    if not guide_dir:
        raise ValueError(f"No matching directory found for guide type: {guide_type}")

    output_dir = Path(f'docs/book/user-guide/{guide_dir.name}')
    temp_dir = Path(tempfile.mkdtemp())

    converted_files = []
    for notebook_path in sorted(guide_dir.glob('*.ipynb')):
        output_filename = convert_notebook_to_markdown(str(notebook_path), str(temp_dir), is_local)
        converted_files.append(output_filename)

    if not converted_files:
        raise ValueError(f"No files were converted for {guide_type}")

    existing_files = [f for f in output_dir.glob('*.md') if f.is_file()] if output_dir.exists() else []
    deleted_files = [f.name for f in existing_files if f.name not in converted_files]
    retained_files = [f.name for f in existing_files if f.name in converted_files]

    suggested_toc = generate_suggested_toc(guide_type, converted_files)

    # If everything is successful, update the actual output directory
    if output_dir.exists():
        for file in output_dir.glob('*.md'):
            if file.name not in converted_files:
                file.unlink()
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    for file in converted_files:
        shutil.copy(temp_dir / file, output_dir / file)

    shutil.rmtree(temp_dir)

    return suggested_toc, deleted_files, retained_files

def main():
    parser = argparse.ArgumentParser(description='Update GitBook content from Jupyter notebooks.')
    parser.add_argument('--guide-type', type=str, default='Starter guide', help='Type of guide to process')
    parser.add_argument('--local', action='store_true', help='Run in local mode (skips adding badges)')
    args = parser.parse_args()

    try:
        suggested_toc, deleted_files, retained_files = process_guide(args.guide_type, args.local)
        
        logger.info(f"Suggested TOC for {args.guide_type}:\n{suggested_toc}")
        logger.info(f"Deleted files: {deleted_files}")
        logger.info(f"Retained files: {retained_files}")
        
        # At the end of the main() function, add:
        if os.environ.get('GITHUB_ACTIONS'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"suggested_toc<<EOF\n{suggested_toc}\nEOF\n")
                f.write(f"deleted_files={','.join(deleted_files) if deleted_files else ''}\n")
                f.write(f"retained_files={','.join(retained_files) if retained_files else ''}\n")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::error::An error occurred: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main()