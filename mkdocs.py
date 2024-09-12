import json
import os
import re
import shutil


def get_mkdocs_files():
    mkdocs_files = {
        'core_code_docs': {},
        'integration_code_docs': {}
    }
    base_path = "docs/mintlify/mkdocs"
    for version_folder in os.listdir(base_path):
        if re.match(r'v\d+', version_folder):
            for doc_type in mkdocs_files.keys():
                folder_path = os.path.join(base_path, version_folder, doc_type)
                if os.path.exists(folder_path):
                    mkdocs_files[doc_type][version_folder] = []
                    for file in os.listdir(folder_path):
                        if file.endswith('.md'):
                            mkdocs_files[doc_type][version_folder].append(file[:-3])  # Remove .md extension
    return mkdocs_files

def update_mint_json():
    # Load the existing mint.json file
    with open('docs/mintlify/mint.json', 'r') as f:
        mint_data = json.load(f)

    # Get mkdocs files
    mkdocs_files = get_mkdocs_files()

    # Update tabs
    mint_data['tabs'] = [
        tab for tab in mint_data.get('tabs', [])
        if tab['name'] not in ["Core Code Docs", "Integration Docs"]
    ]
    mint_data['tabs'].extend([
        {"name": "Core Code Docs", "url": "core-code-docs"},
        {"name": "Integration Docs", "url": "integration-docs"}
    ])

    # Update navigation
    navigation = mint_data.get('navigation', [])
    new_navigation = [
        group for group in navigation
        if group.get('group') not in ["Core Code Docs", "Integration Docs"]
    ]

    for doc_type, versions in mkdocs_files.items():
        tab_name = "Core Code Docs" if doc_type == "core_code_docs" else "Integration Docs"
        tab_url = tab_name.lower().replace(" ", "-")
        tab_navigation = []

        for version, files in versions.items():
            if files:
                # Create the new directory if it doesn't exist
                new_dir = os.path.join('docs/mintlify', tab_url, version)
                os.makedirs(new_dir, exist_ok=True)

                # Move files to the new directory
                for file in files:
                    src = os.path.join('docs/mintlify/mkdocs', version, doc_type, f"{file}.md")
                    dst = os.path.join(new_dir, f"{file}.md")
                    shutil.move(src, dst)

                tab_navigation.append({
                    "group": version,
                    "pages": [f"{tab_url}/{version}/{file}" for file in files]
                })

        if tab_navigation:
            new_navigation.append({
                "group": tab_name,
                "pages": tab_navigation
            })

    mint_data['navigation'] = new_navigation

    # Update versions
    all_versions = set()
    for versions in mkdocs_files.values():
        all_versions.update(versions.keys())
    mint_data['versions'] = sorted(all_versions, reverse=True)

    # Write the updated mint.json file
    with open('docs/mintlify/mint.json', 'w') as f:
        json.dump(mint_data, f, indent=2)

if __name__ == "__main__":
    update_mint_json()