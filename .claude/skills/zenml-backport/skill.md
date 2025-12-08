---
name: zenml-backport
description: Backport docs/examples changes to a pre-existing ZenML release. Use when changes merged to `develop` need to be reflected in a live release version. Triggers include "backport", "cherry-pick to release", "update release docs", or when docs/examples changes need to be applied to an existing release branch.
---

# ZenML Backport Workflow

Backporting applies changes from `develop` to a live release. Only docs and examples can be backported (not `src/` changes, which require a new release).

## Inputs Required

Before starting, gather:
1. **Target release version** (e.g., `0.5.7`)
2. **Commit SHAs** from `develop` to backport (get via `git log origin/develop`)

## Workflow Steps

### Step 1: Create Backport Branch

```bash
git fetch
git checkout release/<VERSION>
git pull
git checkout -b backport/<descriptive-name>
```

### Step 2: Cherry-pick Commits

For each commit SHA from develop:

```bash
git cherry-pick -x <commit-sha>
```

The `-x` flag adds a reference to the original commit in the cherry-pick message.

If conflicts occur, resolve them, then:

```bash
git add .
git cherry-pick --continue
```

### Step 3: Push and Create PR

```bash
git push -u origin backport/<descriptive-name>
```

Create PR against `release/<VERSION>` (NOT `develop` or `main`):
- **Base branch**: `release/<VERSION>`
- **Labels**: Add `backport`, `no-release-notes`, `internal`
- **Reviewers**: None required

Use GitHub CLI if available:

```bash
gh pr create \
  --base release/<VERSION> \
  --title "Backport: <description>" \
  --body "Backports commits from develop to release/<VERSION>" \
  --label backport --label no-release-notes --label internal
```

### Step 4: Sync to Main (Manual - Hamza Only)

⚠️ **STOP HERE** - The final sync from `release/<VERSION>` to `main` requires htahir1 (Hamza) to perform:

```bash
git fetch
git checkout main
git pull
git reset --hard origin/release/<VERSION>
git push --force
```

**Tell the user**: "The backport PR is ready. Once merged, Hamza (htahir1) needs to force-push `release/<VERSION>` to `main` to complete the sync."
