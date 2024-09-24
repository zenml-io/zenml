import os
import requests
import openai

MAX_CHARS = 400000  # Maximum characters for changes summary

def truncate_changes(changes_summary):
    """Truncates the changes summary to fit within MAX_CHARS."""
    total_chars = 0
    truncated_summary = []
    for change in changes_summary:
        change_chars = len(change)
        if total_chars + change_chars > MAX_CHARS:
            remaining_chars = MAX_CHARS - total_chars
            if remaining_chars > 50:  # Ensure we're not adding just a few characters
                truncated_change = change[:remaining_chars]
                truncated_summary.append(truncated_change + "...")
            break
        total_chars += change_chars
        truncated_summary.append(change)
    return truncated_summary

def generate_pr_description():
    # GitHub API setup
    token = os.environ['GITHUB_TOKEN']
    repo = os.environ['GITHUB_REPOSITORY']
    
    # Get PR number from the event payload
    with open(os.environ['GITHUB_EVENT_PATH']) as f:
        event = json.load(f)
    pr_number = event['pull_request']['number']
    
    headers = {'Authorization': f'token {token}'}
    api_url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}'

    # Get current PR description
    pr_info = requests.get(api_url, headers=headers).json()
    current_description = pr_info['body'] or ''

    # Check if description matches the default template
    default_template_indicator = "I implemented/fixed _ to achieve _."

    if default_template_indicator in current_description:
        # Get PR files
        files_url = f'{api_url}/files'
        files = requests.get(files_url, headers=headers).json()

        # Process files
        changes_summary = []
        for file in files:
            filename = file['filename']
            status = file['status']

            if status == 'added':
                changes_summary.append(f"Added new file: {filename}")
            elif status == 'removed':
                changes_summary.append(f"Removed file: {filename}")
            elif status == 'modified':
                if file['binary']:
                    changes_summary.append(f"Modified binary file: {filename}")
                else:
                    patch = file.get('patch', '')
                    if patch:
                        changes_summary.append(f"Modified {filename}:")
                        changes_summary.append(patch)
            elif status == 'renamed':
                changes_summary.append(f"Renamed file from {file['previous_filename']} to {filename}")

        # Truncate changes summary if it's too long
        truncated_changes = truncate_changes(changes_summary)
        changes_text = "\n".join(truncated_changes)

        # Generate description using OpenAI
        openai.api_key = os.environ['OPENAI_API_KEY']
        response = openai.OpenAI().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise pull request descriptions based on changes to files."},
                {"role": "user", "content": f"Generate a brief, informative pull request description based on these changes:\n\n{changes_text}"}
            ],
            max_tokens=1000
        )

        generated_description = response.choices[0].message['content'].strip()

        # Replace the placeholder in the template with the generated description
        updated_description = current_description.replace(default_template_indicator, generated_description)

        # Update PR description
        data = {'body': generated_description}
        requests.patch(api_url, json=data, headers=headers)
        print(f"Updated PR description with generated content")
        return True
    else:
        print("PR already has a non-default description. No action taken.")
        return False

if __name__ == "__main__":
    generate_pr_description()
