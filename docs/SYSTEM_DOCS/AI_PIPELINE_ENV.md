# AI Pipeline Environment Configuration

The AI processing pipeline relies on the same database settings across local
workstations, CI, and production. Configure the following variables before
starting the API or Celery worker:

| Variable  | Description | Default |
| --------- | ----------- | ------- |
| `DB_HOST` | Hostname/IP of the MySQL server. | `127.0.0.1` |
| `DB_PORT` | MySQL TCP port. | `3310` |
| `DB_NAME` | Database containing `unified_files` and related tables. | `mono_se_db_9` |
| `DB_USER` | MySQL user with read/write permissions. | `mind` |
| `DB_PASS` | Password for `DB_USER`. | `mind` |

Additional runtime settings used by the AI service:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `AI_PROVIDER` | Optional LLM provider (`openai`, `azure_openai`). | unset |
| `OPENAI_API_KEY` | API key when `AI_PROVIDER=openai`. | unset |
| `AZURE_OPENAI_API_KEY` | API key when `AI_PROVIDER=azure_openai`. | unset |
| `AZURE_OPENAI_ENDPOINT` | Endpoint URL for Azure OpenAI deployments. | unset |
| `AI_MODEL_NAME` | Overrides the active model selected from DB tables. | unset |

If provider-specific variables are missing, the AI service automatically falls
back to deterministic rule-based parsing while logging the degraded mode.
