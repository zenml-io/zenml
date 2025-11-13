---
description: Read all changed files in the current git branch
allowed-tools:
  - Bash
---

# Catchup on current branch changes

! git diff --name-only $(git merge-base HEAD origin/develop)

Please read all the files listed above that were changed in this branch compared to the base branch (develop). For each file:
1. Use the `view` tool to read its contents
2. Provide a brief summary of what changed

After reviewing all files, give me a concise summary of:
- What areas of the codebase were modified
- The overall purpose/theme of these changes
- Any potential concerns or questions I should be aware of
