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
| `OPENAI_API_KEY` | API key used if the OpenAI provider entry in `ai_llm` does not supply one. | unset |
| `AZURE_OPENAI_API_KEY` | API key used if the Azure provider entry in `ai_llm` does not supply one. | unset |
| `AZURE_OPENAI_ENDPOINT` | Endpoint URL fallback for Azure OpenAI deployments. | unset |

All provider, model, and endpoint selections are sourced from the database
tables `ai_llm`, `ai_llm_model`, and `ai_system_prompts`. Missing provider
configuration causes the workflow to fall back to deterministic rule-based
parsing while logging the degraded mode.
