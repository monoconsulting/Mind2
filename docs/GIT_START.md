# GIT_START

```
Version: 1.2
Date: 2025-11-05
```

------

## GIT_START: Starting a New Task in a 100% Safe Way

This guide ensures that you start your work from a completely clean and up-to-date `dev` branch. This minimizes the risk of future merge conflicts and problems.

## IMPORTANT!

Every step in this guide should be reported.

> **Guard Rules (New in 1.2)**
>
> 1. **If `dev` does not exist** (locally or on origin):
>    - Use `master` as the source branch.
>    - Ensure `master` is fully committed, pushed, and the working tree is clean.
>    - Create `dev` from `master`, then continue with the steps below.
> 2. **If `dev` exists but you are currently on a feature branch** (anything other than `dev` or `master`):
>    - You **must complete** `@docs\GIT_END.md` for your current branch **before** you run `@docs\GIT_START.md`.
>    - After finishing `GIT_END.md`, return here and continue.
>
> **Note:** If your repository uses `main` instead of `master`, replace the word `master` with `main` in the commands below.

------

## Step 0: Branch Pre-flight (New in 1.2)

Check where you are and whether `dev` exists.

```bash
# Where am I?
git branch --show-current

# Does dev exist locally?
git branch --list dev

# Does dev exist on origin?
git ls-remote --heads origin dev
```

- **If you are on a feature branch** (neither `dev` nor `master`):
   **Stop here and run `@docs\GIT_END.md` for your current branch.** Then return to this guide.
- **If `dev` does NOT exist** (both checks show nothing), create it from `master`:

```bash
git checkout master
git pull origin master

# Working tree must be clean before creating dev
git status
# Expected: "On branch master" + "Your branch is up to date with 'origin/master'." + "nothing to commit, working tree clean"

# If not clean:
git add .
git commit -m "Commit to get clean working tree before creating dev"
git push origin master

# Create dev from master and publish it
git checkout -b dev
git push -u origin dev
```

Report:

- "Step 0: Guard rules applied"
- If created: "Step 0: Created dev from master and pushed to origin"

------

## Step 1: Switch to the `dev` branch

All new work should originate from `dev`.

```bash
git checkout dev
```

Report: "Step 1: Switched to dev" (report even if you already are on dev)

------

## Step 2: Fetch the latest changes from GitHub

Ensure your local `dev` branch is identical to the one on the server. The `pull` command is a combination of `fetch` (get) and `merge`.

```bash
git pull origin dev
```

Report: "Step 2: pull ok"

------

## Step 3: Bomb-proof check of the workspace

This is the most important step. We check that absolutely nothing is left lying around.

```bash
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

**If you DO NOT get "working tree clean":**

```bash
git add .
git commit -m "Commit to get clean working tree"
git push
```

If this still doesn’t produce a clean tree:
 **Stop! Do not proceed.** Use the `GIT_FILES_EXISTS.md` guide to clean up.

Report: "Step 3: Working tree clean"

------

## Step 4: Check that the stash is empty (mandatory)

A "stash" is a place where Git can temporarily save changes. Sometimes things are forgotten there.

```bash
git stash list
```

This command should produce **no output at all**. If it lists one or more stashes, use `GIT_FILES_EXISTS.md` to handle them.

Report: "Step 4: Stash empty"

------

## Step 5: Create your new branch

Now that everything is guaranteed to be clean, you can create your new branch. Replace `TMXXX-description` with your actual task number and a short description.

**Example:** `TM133-update-headers-indexpage`

```bash
# Replace TMXXX-description with your task identifier
git checkout -b TMXXX-description
```

This command creates a new branch from `dev` and automatically switches to it.

Report: "Step 5: New branch created - TMXXX-description"

------

## DONE!

You are now on your new, safe branch and can start working. Everything you do here is completely isolated from `dev` until you are ready to merge back using `GIT_END.md`.