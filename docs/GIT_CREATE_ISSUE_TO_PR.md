# AGENT GUIDE — Create Issue from `issue.md`, Branch from `dev`, and Open PR

```
`File: GIT_CREATE_ISSUE_TO_PR.md`
`Version: 1.0`
`Date: 2025-10-02`
```



---

## Changelog

| Date       | Filename                  | Version | Changes made  | Author   |
| ---------- | ------------------------- | ------- | ------------- | -------- |
| 2025-10-02 | GIT_CREATE_ISSUE_TO_PR.md | 1.0     | First version | Chat GPT |



## Purpose

Standardize how we create issues, branch work from `dev`, and deliver changes via Pull Request (PR) that auto-closes the issue.

## Preconditions

- You have Git, GitHub CLI (`gh`), and VS Code installed.

- You are authenticated:

  ```
  gh auth status
  ```

- VS Code extension “GitHub Pull Requests and Issues” is installed (optional but recommended).

## Naming Rules

- Local file copy of the issue (for audit trail): `issues/YYYY-MM-DD_issue-slug.md`
- Branch name (from `dev`): `feat/<slug>-<short-desc>` or `fix/<slug>-<short-desc>`
- Commit messages include the issue number and use Conventional Commits:
  - `feat: add X (refs #123)`
  - Final commit/PR description must include closing keyword: `Fixes #123`

## 1) Create a local `issue.md` and commit it

1. Create the file:

   ```
   issues/2025-10-02_user-login-timeout.md
   ```

2. Use this template:

   ```
   # Title
   Concise, action-oriented title (imperative).
   
   ## Context
   - Current behavior
   - Expected behavior
   - Business value / risk
   
   ## Definition of Done
   - [ ] Functional acceptance criteria
   - [ ] Tests (unit/e2e)
   - [ ] Docs/Changelog updated
   - [ ] Performance/Security considerations reviewed
   
   ## Scope & Constraints
   - In scope:
   - Out of scope:
   
   ## Links
   - Logs / Runbooks / Design docs / Screens
   
   ## Labels
   bug, backend, high-priority
   
   ## Assignees
   @github-handle
   
   ## Milestone/Project
   vX.Y or Project Board column
   ```

3. Add and commit:

   ```
   git add issues/2025-10-02_user-login-timeout.md
   git commit -m "docs(issues): add 2025-10-02 user-login-timeout issue draft"
   git push
   ```

## 2) Create the GitHub Issue from the file

Preferred (via GitHub CLI, uses the local file as body):

```
# From repository root
gh issue create \
  --title "User login times out after 15s" \
  --body-file issues/2025-10-02_user-login-timeout.md \
  --label bug --label backend --label "high-priority" \
  --assignee your-github-handle \
  --milestone "vX.Y"
```

- The command prints the issue URL and number, e.g. `#123`.

> VS Code alternative: Use the “GitHub” view → **Issues** → **+** New Issue. Paste the same content. Then note the created issue number.

## 3) Create a working branch from `dev` linked to the issue

1. Sync `dev`:

   ```
   git checkout dev
   git pull --ff-only
   ```

2. Create and switch to a feature/fix branch:

   ```
   git checkout -b feat/user-login-timeout-123
   ```

3. (Optional, VS Code) Use “Start working on issue” to auto-create the branch tied to `#123`.

## 4) Implement, commit, and push

- Commit often with clear messages:

  ```
  git add .
  git commit -m "feat: extend session keepalive (refs #123)"
  git push --set-upstream origin feat/user-login-timeout-123
  ```

## 5) Open a PR that **closes** the issue

1. Via CLI:

   ```
   gh pr create \
     --base dev \
     --head feat/user-login-timeout-123 \
     --title "Fix: stabilize user session keepalive" \
     --body "Fixes #123
   
   ## Summary
   - What changed
   - Risk/Impact
   - Rollback plan
   
   ## Tests
   - Unit/E2E references
   
   ## Checklist
   - [x] DoD met
   "
   --draft=false
   ```

2. Or in VS Code: open the branch → “Create Pull Request”. Ensure the PR description contains `Fixes #123`.

3. Assign reviewers, add labels/milestone/project as needed.

## 6) Review → Merge Strategy

- Resolve review comments and CI checks.
- Preferred merge: **Squash and merge** into `dev` (keeps history tidy).
- Verify the issue is auto-closed on merge (via `Fixes #123`).

## 7) Post-merge Cleanup

```
git checkout dev
git pull --ff-only
git branch -d feat/user-login-timeout-123
git push origin --delete feat/user-login-timeout-123
```

- If required, backport or cherry-pick to release branches following release policy.

## 8) Optional — Project Automation

- Link the issue/PR to GitHub Projects column (e.g., “In progress” → “In review” → “Done”).
- Use branch protection + required status checks on `dev`.

## Quick VS Code Flow (no CLI)

1. **Issues** view → **+ New Issue** → fill with the same template.
2. Click **Start working on issue** → branch is created from `dev`.
3. Implement, commit, push from Source Control.
4. **Create Pull Request** from the GitHub panel; ensure description contains `Fixes #<issueNumber>`.
5. Complete review and **Squash and merge**.
6. Verify issue is closed and clean up branch.

------

### Rationale (why this matters)

- Keeping a local `issues/` copy gives auditability and offline edit history.
- `gh issue create --body-file` guarantees parity between local doc and GitHub Issue.
- `Fixes #<n>` ensures traceability from code → PR → issue closure.
- Squash merge keeps `dev` linear and easy to revert.

> Drop this file into your repo (e.g., `@docs/AGENTS_ISSUE_TO_PR.md`) and link it from CONTRIBUTING.md.