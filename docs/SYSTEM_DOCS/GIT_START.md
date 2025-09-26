---
date created: 2025-09-07 11:34:43
date modified: 2025-09-07 21:20:48
title: GIT_START
version: 1.1
---

# GIT_START
### GIT_START.md

```
Version: 1.0
Date: 2025-09-07
```

------

## GIT_START: Starting a New Task in a 100% Safe Way

This guide ensures that you start your work from a completely clean and up-to-date `dev` branch. This minimizes the risk of future merge conflicts and problems.

## IMPORTANT!
Every step in this guide should be reported

## Step 1: Switch to the `dev` branch

All new work should originate from `dev`.

```bash
git checkout dev
```

Report: "Step 1: Switched to dev" (report even if you already stays on dev)

## Step 2: Fetch the latest changes from GitHub

Ensure your local `dev` branch is identical to the one on the server. The `pull` command is a combination of `fetch` (get) and `merge`.

Bash

```
git pull origin dev
```

Report: "Step 2: pull ok"
## Step 3: Bomb-proof check of the workspace

This is the most important step. We check that absolutely nothing is left lying around.

Bash

```
git status
```

**The output MUST be exactly this:**

```
On branch dev
Your branch is up to date with 'origin/dev'.

nothing to commit, working tree clean
```

- **"Your branch is up to date"**: Perfect, you have the latest version.
- **"nothing to commit, working tree clean"**: Extremely important. This means you have no modified files that haven't been committed.

**If you DO NOT get "working tree clean"**: 
```
git add . 
git commit -m "Comitt to get clean working tree"
git push
```

If this doesn't work: 
Stop! Do not proceed. Use the `GIT_FILES_EXISTS.md` guide to clean up.

Report: "Step 3: Working tree clean"

## Step 4: Check that the stash is empty (mandatory)

A "stash" is a place where Git can temporarily save changes. Sometimes things are forgotten there.

Bash

```
git stash list
```
Report: "Step 4: Stash empty"
This command should produce no output at all. If it lists one or more stashes, use `GIT_FILES_EXISTS.md` to handle them.

## Step 5: Create your new branch

Now that everything is guaranteed to be clean, you can create your new branch. Replace `TMXXX-description` with your actual task number and a short description.

**Example:** `TM133-update-headers-indexpage`

Bash

```
# Replace TMXXX-description with your name
git checkout -b TMXXX-description
```

Report: "Step 5: New branch created - TMXXX-description"

This command creates a new branch from `dev` and automatically switches to it.

## DONE!

You are now on your new, safe branch and can start working. Everything you do here is completely isolated from `dev` until you are ready to merge back using `GIT_END.md`