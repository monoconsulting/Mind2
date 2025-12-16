"""API endpoints for AI LLM configuration."""

import logging

import requests
from flask import Blueprint, jsonify, request

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None

from api.middleware import auth_required

logger = logging.getLogger(__name__)

ai_config_bp = Blueprint("ai_config", __name__, url_prefix="/ai-config")


def _normalise_text(value: object) -> str:
    """Normalise values to UTF-8 strings for API responses.

    This helper is intentionally **read-only**: it must never mutate stored
    prompt content implicitly (prompts are edited in the UI and must not be
    overwritten automatically).
    """

    if value is None:
        return ""

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception as exc:
            logger.warning("Failed to decode DB bytes as UTF-8, falling back to latin-1: %s", exc)
            try:
                return value.decode("latin-1")
            except Exception as exc2:
                logger.warning("Failed to decode DB bytes as latin-1, using replacement characters: %s", exc2)
                return value.decode("utf-8", errors="replace")

    if isinstance(value, str):
        return value

    return str(value)


@ai_config_bp.route("/providers", methods=["GET"])
@auth_required
def get_providers():
    """Get all AI LLM providers with their models."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, provider_name, own_name, api_key, endpoint_url, enabled, created_at
                FROM ai_llm
                ORDER BY provider_name
                """
            )

            providers = []
            provider_rows = cursor.fetchall()

            for row in provider_rows:
                provider = {
                    "id": row[0],
                    "provider_name": _normalise_text(row[1]),
                    "own_name": _normalise_text(row[2]),
                    "api_key": row[3] if row[3] else "",  # Mask in frontend if needed
                    "endpoint_url": _normalise_text(row[4]),
                    "enabled": bool(row[5]),
                    "created_at": row[6].isoformat() if row[6] else None,
                    "models": [],
                }

                cursor.execute(
                    """
                    SELECT id, model_name, display_name, is_active, created_at
                    FROM ai_llm_model
                    WHERE llm_id = %s
                    ORDER BY model_name
                    """,
                    (provider["id"],),
                )

                for model_row in cursor.fetchall():
                    provider["models"].append(
                        {
                            "id": model_row[0],
                            "model_name": _normalise_text(model_row[1]),
                            "display_name": _normalise_text(model_row[2]),
                            "is_active": bool(model_row[3]),
                            "created_at": model_row[4].isoformat() if model_row[4] else None,
                        }
                    )

                providers.append(provider)

        return jsonify({"providers": providers}), 200

    except Exception as exc:
        logger.error("Error fetching providers: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/providers", methods=["POST"])
@auth_required
def create_provider():
    """Create a new AI LLM provider."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    data = request.json or {}

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_llm (provider_name, own_name, api_key, endpoint_url, enabled)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    data.get("provider_name"),
                    data.get("own_name"),
                    data.get("api_key"),
                    data.get("endpoint_url"),
                    data.get("enabled", False),
                ),
            )

            provider_id = cursor.lastrowid

            models = data.get("models", [])
            for model in models:
                cursor.execute(
                    """
                    INSERT INTO ai_llm_model (llm_id, model_name, display_name, is_active)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        provider_id,
                        model.get("model_name"),
                        model.get("display_name"),
                        model.get("is_active", True),
                    ),
                )

        return jsonify({"id": provider_id, "message": "Provider created successfully"}), 201

    except Exception as exc:
        logger.error("Error creating provider: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/providers/<int:provider_id>", methods=["PUT"])
@auth_required
def update_provider(provider_id):
    """Update an AI LLM provider."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    data = request.json or {}

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE ai_llm
                SET provider_name = %s, own_name = %s, api_key = %s,
                    endpoint_url = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    data.get("provider_name"),
                    data.get("own_name"),
                    data.get("api_key"),
                    data.get("endpoint_url"),
                    data.get("enabled"),
                    provider_id,
                ),
            )

        return jsonify({"message": "Provider updated successfully"}), 200

    except Exception as exc:
        logger.error("Error updating provider: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/providers/<int:provider_id>", methods=["DELETE"])
@auth_required
def delete_provider(provider_id):
    """Delete an AI LLM provider."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute("DELETE FROM ai_llm WHERE id = %s", (provider_id,))

        return jsonify({"message": "Provider deleted successfully"}), 200

    except Exception as exc:
        logger.error("Error deleting provider: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/providers/<int:provider_id>/models", methods=["POST"])
@auth_required
def add_model(provider_id):
    """Add a model to a provider."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    data = request.json or {}

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_llm_model (llm_id, model_name, display_name, is_active)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    provider_id,
                    data.get("model_name"),
                    data.get("display_name"),
                    data.get("is_active", True),
                ),
            )

            model_id = cursor.lastrowid

        return jsonify({"id": model_id, "message": "Model added successfully"}), 201

    except Exception as exc:
        logger.error("Error adding model: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/models/<int:model_id>", methods=["DELETE"])
@auth_required
def delete_model(model_id):
    """Delete a model."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute("DELETE FROM ai_llm_model WHERE id = %s", (model_id,))

        return jsonify({"message": "Model deleted successfully"}), 200

    except Exception as exc:
        logger.error("Error deleting model: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/prompts", methods=["GET"])
@auth_required
def get_prompts():
    """Get all system prompts.

    NOTE: This endpoint must be read-only with respect to prompt_content.
    Prompt seeding is handled by migrations, and prompt editing is handled via
    PUT /ai-config/prompts/<id> in the UI.
    """

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT sp.id, sp.prompt_key, sp.title, sp.description,
                       sp.prompt_content, sp.selected_model_id,
                       m.model_name, l.provider_name
                FROM ai_system_prompts sp
                LEFT JOIN ai_llm_model m ON sp.selected_model_id = m.id
                LEFT JOIN ai_llm l ON m.llm_id = l.id
                ORDER BY
                    CASE sp.prompt_key
                        WHEN 'document_analysis' THEN 1
                        WHEN 'expense_classification' THEN 2
                        WHEN 'data_extraction' THEN 3
                        WHEN 'accounting_classification' THEN 4
                        WHEN 'credit_card_invoice_parsing' THEN 5
                        WHEN 'credit_card_matching' THEN 6
                        ELSE 99
                    END
                """
            )
            rows = cursor.fetchall()

            prompts = []
            for row in rows:
                prompts.append(
                    {
                        "id": row[0],
                        "prompt_key": row[1],
                        "title": _normalise_text(row[2]),
                        "description": _normalise_text(row[3]),
                        "prompt_content": _normalise_text(row[4]),
                        "selected_model_id": row[5],
                        "selected_model_name": _normalise_text(row[6]),
                        "selected_provider": _normalise_text(row[7]),
                    }
                )

        return jsonify({"prompts": prompts}), 200

    except Exception as exc:
        logger.error("Error fetching prompts: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/prompts/<int:prompt_id>", methods=["PUT"])
@auth_required
def update_prompt(prompt_id):
    """Update a system prompt."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    data = request.json or {}

    try:
        with db_cursor() as cursor:
            clean_title = _normalise_text(data.get("title"))
            clean_description = _normalise_text(data.get("description"))
            clean_content = _normalise_text(data.get("prompt_content"))
            cursor.execute(
                """
                UPDATE ai_system_prompts
                SET title = %s, description = %s, prompt_content = %s,
                    selected_model_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    clean_title,
                    clean_description,
                    clean_content,
                    data.get("selected_model_id"),
                    prompt_id,
                ),
            )

        return jsonify({"message": "Prompt updated successfully"}), 200

    except Exception as exc:
        logger.error("Error updating prompt: %s", exc)
        return jsonify({"error": str(exc)}), 500


@ai_config_bp.route("/providers/<int:provider_id>/test", methods=["POST"])
@auth_required
def test_provider_connection(provider_id):
    """Test connection to an AI LLM provider."""

    if not db_cursor:
        return jsonify({"error": "Database not available"}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT provider_name, api_key, endpoint_url, enabled
                FROM ai_llm
                WHERE id = %s
                """,
                (provider_id,),
            )

            provider = cursor.fetchone()
            if not provider:
                return jsonify({"error": "Provider not found"}), 404

            provider_name, api_key, endpoint_url, enabled = provider

            if not enabled:
                return jsonify({"error": "Provider is disabled"}), 400

            if provider_name == "OpenAI":
                if not api_key:
                    return jsonify({"error": "API key not configured"}), 400

                response = requests.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )

                if response.status_code == 200:
                    return (
                        jsonify(
                            {
                                "success": True,
                                "message": "Connection successful",
                                "details": "OpenAI API responded successfully",
                            }
                        ),
                        200,
                    )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Connection failed",
                            "details": f"HTTP {response.status_code}: {response.text[:200]}",
                        }
                    ),
                    200,
                )

            if provider_name == "Anthropic":
                if not api_key:
                    return jsonify({"error": "API key not configured"}), 400

                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "test"}],
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    return (
                        jsonify(
                            {
                                "success": True,
                                "message": "Connection successful",
                                "details": "Anthropic API responded successfully",
                            }
                        ),
                        200,
                    )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Connection failed",
                            "details": f"HTTP {response.status_code}: {response.text[:200]}",
                        }
                    ),
                    200,
                )

            if provider_name == "Ollama":
                if not endpoint_url:
                    return jsonify({"error": "Endpoint URL not configured"}), 400

                response = requests.get(f"{endpoint_url}/api/tags", timeout=10)

                if response.status_code == 200:
                    return (
                        jsonify(
                            {
                                "success": True,
                                "message": "Connection successful",
                                "details": "Ollama server responded successfully",
                            }
                        ),
                        200,
                    )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Connection failed",
                            "details": f"HTTP {response.status_code}: {response.text[:200]}",
                        }
                    ),
                    200,
                )

            return jsonify({"error": f"Testing not implemented for provider: {provider_name}"}), 400

    except requests.Timeout:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Connection timeout",
                    "details": "The provider did not respond within 10 seconds",
                }
            ),
            200,
        )
    except requests.RequestException as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Connection error",
                    "details": str(exc),
                }
            ),
            200,
        )
    except Exception as exc:
        logger.error("Error testing provider connection: %s", exc)
        return jsonify({"error": str(exc)}), 500

