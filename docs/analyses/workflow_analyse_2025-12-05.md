# Workflow Analysis - 2025-12-05

## Initial Findings

### Queue System
- The queue is retrieved via `GET /queue/`.
- Items are considered "stalled" if `status` is "queued" or "running" and `idle_seconds` > 300 (5 minutes).
- The queue is ordered by status (running, queued, others) and then by timestamp.

### Stalled Tasks
- The "stalled" status is a derived property in the API response, not a database state.
- A task is stalled if it hasn't updated its `updated_at` timestamp in the database for over 5 minutes.
- This suggests that long-running tasks (like AI processing) might be falsely flagged as stalled if they don't heartbeat or update status frequently enough, OR that tasks are genuinely getting stuck/lost by Celery.

### Restart Mechanism
- **To be investigated:** How the frontend triggers a restart.
- **To be investigated:** What backend endpoint handles the restart.

## Potential Issues
1.  **Timeout Configuration:** 300 seconds might be too short for some AI tasks if they don't provide intermediate updates.
2.  **Celery Worker Issues:** Workers might be crashing or getting stuck, leaving tasks in "running" state without updates.
3.  **Missing Heartbeats:** Long-running tasks should update `updated_at` periodically to avoid being marked as stalled.
4.  **Restart Logic:** The restart button might be calling a deprecated or non-existent endpoint, or the backend logic for restarting might be flawed (e.g., not resetting state correctly).

## Next Steps
1.  Analyze frontend code for restart button.
2.  Identify backend restart endpoint.
3.  Trace a stalled task to see where it stopped.
4.  Verify Celery worker logs (if accessible).
