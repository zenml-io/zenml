import json
import os
import re
import yaml

def read_metadata(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
        metadata_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if metadata_match:
            return yaml.safe_load(metadata_match.group(1))
    return {}

def get_mdx_files(version_folder):
    mdx_files = []
    for root, _, files in os.walk(f"docs/mintlify/{version_folder}"):
        for file in files:
            if file.endswith('.mdx'):
                mdx_files.append(os.path.relpath(os.path.join(root, file), f"docs/mintlify/{version_folder}"))
    return mdx_files

def update_mint_json():
    # Load the existing mint.json file
    with open('docs/mintlify/mint.json', 'r') as f:
        mint_data = json.load(f)

    # Find all version folders in docs/mintlify
    version_folders = sorted([d for d in os.listdir('docs/mintlify') if re.match(r'v\d+', d)], reverse=True)

    # Get the current navigation
    current_navigation = mint_data.get('navigation', [])

    # Find the latest and second latest versions in the current navigation
    current_versions = sorted(set(group['version'] for group in current_navigation if 'version' in group), reverse=True)
    latest_version = current_versions[0] if current_versions else None

    # If there's a new version folder that's not in the navigation, we need to add it
    if version_folders[0] != latest_version:
        new_version = version_folders[0]
        
        # Use the structure from the previous latest version
        new_version_groups = [
            group.copy() for group in current_navigation 
            if group.get('version') == latest_version
        ]

        # Get all MDX files in the new version folder
        all_mdx_files = get_mdx_files(new_version)

        # Update the version and pages for the new version
        for group in new_version_groups:
            group['version'] = new_version
            new_pages = []
            for page in group.get('pages', []):
                breakpoint()
                page_path = page if isinstance(page, str) else page.get('path', '')
                file_path = f"{page_path}.mdx"
                
                if file_path in all_mdx_files:
                    all_mdx_files.remove(file_path)  # Remove from the list as it's processed
                    full_file_path = f"docs/mintlify/{new_version}/{file_path}"
                    metadata = read_metadata(full_file_path)
                    if 'group' in metadata:
                        # Find or create the group specified in the metadata
                        target_group = next((g for g in new_version_groups if g['group'] == metadata['group']), None)
                        if not target_group:
                            target_group = {'group': metadata['group'], 'version': new_version, 'pages': []}
                            new_version_groups.append(target_group)
                        target_group['pages'].append(f"{new_version}/{page_path}")
                    else:
                        new_pages.append(f"{new_version}/{page_path}")
                else:
                    new_pages.append(page_path)
            
            group['pages'] = new_pages

        # Add new files that weren't in the original structure
        for new_file in all_mdx_files:
            full_file_path = f"docs/mintlify/{new_version}/{new_file}"
            breakpoint()
            metadata = read_metadata(full_file_path)
            page_path = new_file[:-4]  # Remove .mdx extension
            if 'group' in metadata:
                target_group = next((g for g in new_version_groups if g['group'] == metadata['group']), None)
                if not target_group:
                    target_group = {'group': metadata['group'], 'version': new_version, 'pages': []}
                    new_version_groups.append(target_group)
                target_group['pages'].append(f"{new_version}/{page_path}")
            else:
                # Add to a default group if no group is specified
                default_group = next((g for g in new_version_groups if g['group'] == 'Other'), None)
                if not default_group:
                    default_group = {'group': 'Other', 'version': new_version, 'pages': []}
                    new_version_groups.append(default_group)
                default_group['pages'].append(f"{new_version}/{page_path}")

        # Remove empty groups
        new_version_groups = [group for group in new_version_groups if group['pages']]

        # Add the new version groups to the navigation
        mint_data['navigation'] = new_version_groups + [
            group for group in current_navigation 
            if group.get('version') != latest_version
        ]
        breakpoint()
        # Update the versions array
        mint_data['versions'] = version_folders

    # Write the updated mint.json file
    with open('docs/mintlify/mint.json', 'w') as f:
        json.dump(mint_data, f, indent=2)

if __name__ == "__main__":
    update_mint_json()