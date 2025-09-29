---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 16:01:06
title: GIT_SANITY_CHECK
---

1§---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 16:00:57
title: GIT_SANITY_CHECK
version: 1.1
---

# GIT_SANITY_CHECK
## GIT_SANITY_CHECK: Verifying the Health of Your Git Repo

vers

This guide contains a series of commands to verify that your local Git repository is in a "healthy" state. Run this if you suspect something is wrong.

## Step 1: Basic Status Check

This is the same as in `GIT_START.md`, but it is the most crucial check.

```bash
git status
```

- **Goal:** Should show `working tree clean`. If not, use `GIT_FILES_EXISTS.md`.
- **Goal:** Should show that you are on the correct branch.



## Step 2: Compare with the remote repo (GitHub)



Check that you don't have local commits that haven't been pushed, or that the remote repo has changes you haven't fetched.

1. **Fetch the latest information from the server (without merging):** `git fetch` is safer than `pull` for pure inspection.

   Bash

   ```
   git fetch origin
   ```

2. **Run `status` again:**

   Bash

   ```
   git status
   ```

   Now Git will tell you how your local branch relates to `origin/your-branch`.

   - **"Your branch is up to date with 'origin/...'":** Perfect.
   - **"Your branch is ahead of 'origin/...' by X commits":** You have local commits that you need to push (`git push`).
   - **"Your branch is behind 'origin/...' by Y commits":** You need to download changes (`git pull`).
   - **"Your branch and 'origin/...' have diverged":** Both you and the server have new changes. This requires a `git pull` to create a merge commit.



## Step 3: Check Git's internal database



This looks for corruption or "garbage" in Git's database.

Bash

```
git fsck --full
```

- **Goal:** This command should produce no output at all, or just a list of "dangling" objects.
- **Warning signs:** If you see error messages like "error:", "missing", "sha1 mismatch", or "corrupt", your repo has a serious problem. Cloning the repo again from the server is often the easiest solution. "Dangling commits" or "dangling blobs" are usually harmless and are the result of normal work, but can be removed to clean up.



## Step 4: List all branches and their status



Make sure you don't have old, forgotten branches locally.

Bash

```
# The -vv flag shows detailed info, including the link to the remote branch
git branch -vv
```

This provides a good overview. Local branches that no longer exist on the server (`origin`) can usually be cleaned up.



### Summary of a "perfect" repo:



- `git status` is `clean`.
- `git status` shows `up to date` with `origin`.
- `git fsck` is silent.
- `git stash list` is empty.
- You have no unexpected or forgotten local branches.