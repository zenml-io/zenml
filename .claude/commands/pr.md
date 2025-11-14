---
description: Format code, stage changes, and create a pull request
allowed-tools:
  - Bash
argument-hint: [base-branch]
---

# Prepare and create pull request

First, let me run the formatting script:

! bash scripts/format.sh

Now let me check what files were modified:

! git status --short

Let me also check if there's a CLAUDE.md with PR instructions:

@CLAUDE.md

## Steps to create PR:

1. **Review the changed files** listed above and determine which ones are related to our current work
2. **Stage only the relevant files** - I'll ask you to confirm which files to stage if there are unrelated changes
3. **Determine the base branch**:
   - If you provided an argument: use `$1`
   - Otherwise, I'll ask you to confirm if it should be `develop` (the usual default) or another branch
4. **Create the PR** using the `gh` CLI tool according to any instructions in CLAUDE.md
5. **Ask you for**:
   - PR title (if not obvious from the changes)
   - PR description (I'll draft one based on the changes)

Let's proceed! Based on the git status above, which files should we stage for this PR?
