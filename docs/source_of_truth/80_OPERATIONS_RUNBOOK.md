# docs/source_of_truth/80_OPERATIONS_RUNBOOK.md

# Mind – Operations Runbook (Source of Truth)

> This runbook is for operators and developers responsible for keeping Mind healthy in daily operations.

## 1. Environments

List existing environments and their purpose:

- **Development** – Local/Docker-based, used by developers.
- **Test/Staging** – Integration environment.
- **Production** – Live system used by real customers.

> TODO: For each environment, specify URLs, access instructions and configuration differences.

## 2. Starting and Stopping the System

- **Local/Docker**:
  - Start: `docker-compose up` or equivalent script.
  - Stop: `docker-compose down`.

- **Hosted/Production**:
  - Document the actual deployment method (Docker, VM, managed services).

## 3. Health Checks

- How to verify that the system is functional:
  - Check web UI is reachable.
  - Verify API health endpoint (if available).
  - Smoke-test: upload a small receipt and ensure it reaches `ready_for_review`.

## 4. Logs and Debugging

- Where logs are stored (per component).
- How to tail logs locally.
- How to correlate requests across services.

> TODO: Fill in concrete paths/commands based on current setup.

## 5. Common Incidents

Examples of typical incidents and first-line response:

- **OCR failures spike**
  - Check connectivity to OCR service.
  - Inspect latest errors in logs.

- **AI errors or timeouts**
  - Check AI provider status.
  - Review rate limits and request volume.

- **Import not running**
  - Verify scheduled jobs/cron are running.
  - Check FTP/email connections and credentials.

## 6. Backups and Restore

- Describe backup strategy for the database and file storage.
- Describe restore procedure and testing.

## 7. Deployment and Rollback

- High-level description of how new versions are deployed.
- How to perform a rollback if a release causes issues.