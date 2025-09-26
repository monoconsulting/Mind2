## Agent Instruction for Using Task-Master in VSCode

```
Version: 1.0
Date: 2025-09-15
```

------

### Purpose

This instruction describes exactly how you must use Task-Master AI (via VSCode plugin / CLI / MCP) to manage tasks, branches, subtasks, commits etc. Always follow all items in this guide without omission. Use this as your workflow standard.

------

### Requirements / Preconditions

- You have a task assigned to you in **Task-Master** (in `.taskmaster/tasks/tasks.json`, managed via CLI or MCP) before you begin any work.
- You have knowledge of how to use Git, VSCode, and the Task-Master setup (CLI / MCP).
- You have access to the documents `@docs/GIT_START.md` and `GIT_END.md`, and you know where these live in the repository.

------

### Workflow Steps

1. **Always start with a task assigned in Task-Master**

   - Before writing any code or doing any work, ensure there is a task in `.taskmaster/tasks/tasks.json` that is assigned to **you** (or your agent role). If not, request one or assign appropriately using the standard procedure.

2. **Start a new Git branch**

   - Based on the instructions in `@docs/GIT_START.md`, you must create a new Git branch for the task.
   - All points in `@docs/GIT_START.md` must be followed *in full*. No skipping.
   - Branch naming, base branch, pull request template etc., must adhere strictly to what is defined in `GIT_START.md`.

3. **Structure and content of Tasks in Task-Master**

   Each **Task** in Task-Master has:

   - **Title** — a short, clear title summarizing the work.
   - **Status** — e.g. “Pending”, “In Progress”, etc., as per Task-Master conventions.
   - **Description** — detailed description of what must be done.
   - **System prompt** — a prompt that guides the executing agent on how to do the task.

   Tasks may have **subtasks**:

   - Each subtask should have its own prompt (for the agent doing that subtask).
   - Status and description for each subtask must also be clearly specified.

4. **When subtasks are done**

   - Once a **subtask** is completed, you must explicitly announce/notify that it's done.
   - After finishing one subtask, continue with the next subtask or return to main task as appropriate.

5. **When the whole Task is done**

   - Once the primary Task is completed (all subtasks done, code written), **test fully**: verify that the functionality required works correctly.
   - Only after successful testing do you report completion and await further instructions (unless otherwise directed).

6. **Ensure full functionality**

   - Your job is not done until you are certain the functionality works exactly as the Task required.
   - This includes edge cases, error handling, correct integration, passing tests etc., as applicable.

7. **Task size vs agent context window**

   - When you create or break down tasks and subtasks, ensure that no single task (or its content/prompt/description) is longer/bigger than what the agent’s context window can reasonably handle.
   - This is very important to maintain high quality and manageability.

8. **Finishing the task: GIT_END.md and closing**

   - After I (the user) have approved the completed functionality, you must **close the current Task**.
   - Follow **exactly** the procedure given in `GIT_END.md` to conclude:
     - This includes staging (e.g., `git add .`), committing, merging, PR or whatever is specified in `GIT_END.md`.
   - **IMPORTANT**: `git add .` must be run exactly as specified in `GIT_END.md` to prevent loss of functionality. Do *not* omit or alter that unless `GIT_END.md` instructs otherwise.

9. **Managing the TaskMaster file**

   - The Task file is `.taskmaster/tasks/tasks.json`
   - You may **add** and **manage** it using either the MCP tool or CLI.
   - If you edit the JSON manually, then:
     - Use the **newest unused ID** for new tasks or subtasks.
     - After adding a task, verify via CLI or MCP that the task (or subtask) is visible and correctly parsed.
     - Be very careful with formatting — JSON is sensitive; any syntax error will break the tool chain.

10. **General expectations**

    - Always keep the status of tasks/subtasks up to date.
    - Use clear, concise, but sufficiently detailed descriptions and prompts.
    - Notify when subtasks/tasks are done.
    - Wait for approval before closing tasks or merging branches.

------

### Specifics from Task-Master / VSCode Plugin / MCP

(These are based on Task-Master AI documentation / plugin behavior that I found; you must follow these plus the workflow above.)

- Task-Master CLI / MCP uses `task-master-ai`. [marketplace.visualstudio.com+2GitHub+2](https://marketplace.visualstudio.com/items?itemName=razroel.task-master-vscode-extension&utm_source=chatgpt.com)
- To use it, you must set up MCP configuration (`mcp.json`, `.env`, etc.), with the necessary API keys for your model(s) (Anthropic, OpenAI, etc.). [GitHub+1](https://github.com/eyaltoledano/claude-task-master?utm_source=chatgpt.com)
- The tasks are stored under `.taskmaster/tasks/tasks.json`. The VSCode plugin / visual interface observes this file to build the task tree or board. [marketplace.visualstudio.com+2marketplace.visualstudio.com+2](https://marketplace.visualstudio.com/items?itemName=DevDreed.claude-task-master-extension&utm_source=chatgpt.com)
- If using the VSCode extension / tree view, you can refresh tasks, view subtasks, change statuses etc., via context menus. [marketplace.visualstudio.com+1](https://marketplace.visualstudio.com/items?itemName=razroel.task-master-vscode-extension&utm_source=chatgpt.com)
- It is possible to add tasks via plugin or via CLI, as long as the JSON file is valid and parsed. Always verify after adding. [marketplace.visualstudio.com+1](https://marketplace.visualstudio.com/items?itemName=razroel.task-master-vscode-extension&utm_source=chatgpt.com)

------

### Summary / Checklist Before Starting Work

Before you begin coding on a task, ensure:

-  Task assigned in Task-Master
-  You have created the Git branch according to `GIT_START.md` and followed all its points
-  Task has title, status, description, system prompt
-  If relevant: it’s broken into subtasks with prompts

During work:

-  Subtasks status updated, completion announced
-  Testing done when task done

Before closing:

-  Functionality verified
-  Branch cleaned up, changes staged (`git add .`), commit and end according to `GIT_END.md`
-  Task closed in Task-Master

