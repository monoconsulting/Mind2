---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 15:56:05
title: GIT_LOST_FILES
---

---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 15:54:52
title: GIT_LOST_FILES
version: 1.1

# GIT_LOST_FILES
## GIT_LOST_FILES: Finding Lost Files - A Crisis Guide

```
Version: 1.0

Date: 2025-09-07
```

If a file has disappeared, it has almost certainly not been permanently deleted. It most likely exists somewhere in Git's history. Here is a step-by-step guide to find it.

## Step 1: Check your local history with `reflog`

`git reflog` (reference log) is your absolute best tool. It is a log of *everything* you have done locally (switched branches, committed, reset, etc.), even things that are no longer visible in the normal history.

1.  **Show the log:**

    ```bash
    git reflog

​    You will get a list that looks something like this:
    ```
    a1b2c3d HEAD@{0}: commit: Added new feature
    e4f5g6h HEAD@{1}: checkout: moving from TM133 to dev
    i7j8k9l HEAD@{2}: commit: Updated headers
    ...
    ```
​    `HEAD@{...}` is a timestamp for each action. `a1b2c3d` is the commit hash.

2.  **Look for clues:** Find the point in time *before* the file disappeared. Look for commit messages or branch switches that seem relevant.

3.  **Inspect an old commit:** When you find a suspicious commit hash (e.g., `i7j8k9l`), you can see which files existed then.

    ```bash
    # Lists all files in that commit
    git ls-tree -r i7j8k9l

    # You can also check out the entire commit to a temporary branch to see everything
    git checkout -b temp-recovery i7j8k9l
    ```

4.  **Restore a specific file:** If you find the file in the old commit (e.g., `i7j8k9l`), you can restore just that file to your current state.

    ```bash
    # First, go back to the branch where you want the file
    git checkout your-branch
    
    # Get the file from the old commit
    # Replace "path/to/your/file.txt"
    git checkout i7j8k9l -- path/to/your/file.txt
    ```

## Step 2: Search the entire Git database

If `reflog` doesn't help, the file might exist as a "loose" object in Git's database after an incorrect `reset` or other action.

```bash
# This looks for "dangling blobs" - file content that is no longer linked to a commit
git fsck --full --no-reflogs --unreachable --lost-found
```

Git will print a list of hashes for unreachable objects. You can then inspect each object (which is a "blob", i.e., a file) with:

Bash

```
git show <hash-from-the-list-above>
```

This can be time-consuming, but it is a powerful way to find lost data.



## Step 3: Search through all commits in history



This script searches the entire history of all branches for a file with a specific name.

Bash

```
# Replace 'filename.txt' with the name of the file you are looking for
git log --all --full-history -- "**/filename.txt"
```

This will show all commits that have ever affected a file with that name. From that list, you can see when it was last modified or deleted and from which commit you can restore it.



## Conclusion

It is extremely difficult to permanently lose data in Git as long as you have your local `.git` directory. With `reflog` and `fsck`, you can find almost anything.