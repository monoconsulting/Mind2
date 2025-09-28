---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 21:43:01
title: GIT_END
version: 1.1
---

# GIT_END
## GIT_END: Merging a feature branch into dev - 100% Bomb-proof
## IMPORTANT!!##
**Every step in this guide MUST be reported back with the report status after each step!"

```
Version: 1.0
Date: 2025-09-07
```

------

This guide ensures that **all** of your changes from your feature branch (e.g., `TM133-update-headers-indexpage`) are merged into the `dev` branch in a safe, traceable, and complete manner.

## Step 1: Ensure your feature branch is "clean"

Before merging, make sure all work on your current branch is committed.

```bash
# Switch to your branch if you are not already there
git checkout TMXXX-description

# Check the status
git status
```

The result **MUST** be `working tree clean`. If not, commit your final changes:

Report: "Working Tree Clean"

Bash

```
git add .
git commit -m "Final commit for TMXXX"
```

Report: "Step 1: Final Commit Made"

## Step 2: Update your feature branch with the latest from `dev`



This is a critical step to avoid problems. You are "previewing" the merge on your own branch first.

Bash

```
git pull origin dev
```

If any merge conflicts arise, you resolve them now, in your own branch. This keeps the `dev` branch completely clean from conflict resolution. Once the conflicts are resolved, create a commit:
**IMPORTANT!! GIT ADD . MUST BE USED!!!!!**
Bash

```
git add .
git commit -m "Resolved merge conflict with latest dev"
```

Report: "Step 2: Pull ok"

## Step 3: Create a safety tag



A tag is a permanent pointer to a specific commit. This is your "undo button". If anything goes wrong, you can always go back to this exact state.

Bash

```
# Replace TMXXX with your task number
git tag TMXXX
```

Report:"Step 3: Safety Tag Created"

## Step 4: Switch to `dev` and prepare for the merge



Now that your feature branch is updated and backed up, it's time to go to `dev`.

Bash

```
git checkout dev
git pull origin dev # Double-check that dev is up-to-date
```

Report "Step 4: Dev Checkout OK"

## Step 5: Execute the bomb-proof merge



We use two flags that guarantee the history is preserved and that nothing "magical" happens.

- `--no-ff`: (no fast-forward) Always creates a merge commit, even if it's not technically necessary. This makes the history extremely clear – you can see exactly when a branch was merged in.
- `--no-squash`: Ensures that all your individual commits from your branch are included. You lose no detailed history.

Bash

```
# Replace TMXXX-description with the name of your branch
git merge --no-ff --no-squash TMXXX-description
```

Git will now open a text editor for you to write a merge message. The default message is usually fine. Save and close.

Report: "Step 5: Bomb-proof merge OK"

## Step 6: Push everything to GitHub (Extremely important!)



Now you must push both the updated `dev` branch AND your new tag to the server.

1. **Push the `dev` branch:**

   Bash

   ```
   git push origin dev
   ```

2. **Push the tag:**

   Bash

   ```
   # Replace TMXXX with the name of your tag
   git push origin TMXXX
   ```

Report "Step 6: Push OK"

## Step 7: Verification



Go to GitHub in your web browser.

1. Check the `dev` branch's history. You should see your new merge commit at the top.
2. Go to "Releases" or "Tags". Your new tag (e.g., `TMXXX`) should be there.



## DONE!



You have now completed a merge in the safest way possible. Your entire work history is preserved, no files have been lost, and you have a permanent tag to revert to if needed. Your feature branch (`TMXXX-description`) can now be left as is or be deleted; it doesn't affect the stability of the `dev` branch.