"""API endpoints for AI LLM configuration"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

try:
    from services.db.connection import db_cursor
except Exception:
    db_cursor = None

from api.middleware import auth_required

logger = logging.getLogger(__name__)

ai_config_bp = Blueprint('ai_config', __name__, url_prefix='/ai-config')

@ai_config_bp.route('/providers', methods=['GET'])
@auth_required
def get_providers():
    """Get all AI LLM providers with their models"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    try:
        with db_cursor() as cursor:
            # Get all providers
            cursor.execute("""
                SELECT id, provider_name, own_name, api_key, endpoint_url, enabled, created_at
                FROM ai_llm
                ORDER BY provider_name
            """)

            providers = []
            provider_rows = cursor.fetchall()

            for row in provider_rows:
                provider = {
                    'id': row[0],
                    'provider_name': row[1],
                    'own_name': row[2],
                    'api_key': row[3] if row[3] else '',  # Mask in frontend if needed
                    'endpoint_url': row[4],
                    'enabled': bool(row[5]),
                    'created_at': row[6].isoformat() if row[6] else None,
                    'models': []
                }

                # Get models for this provider
                cursor.execute("""
                    SELECT id, model_name, display_name, is_active, created_at
                    FROM ai_llm_model
                    WHERE llm_id = %s
                    ORDER BY model_name
                """, (provider['id'],))

                for model_row in cursor.fetchall():
                    provider['models'].append({
                        'id': model_row[0],
                        'model_name': model_row[1],
                        'display_name': model_row[2],
                        'is_active': bool(model_row[3]),
                        'created_at': model_row[4].isoformat() if model_row[4] else None
                    })

                providers.append(provider)

        return jsonify({'providers': providers}), 200

    except Exception as e:
        logger.error(f"Error fetching providers: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/providers', methods=['POST'])
@auth_required
def create_provider():
    """Create a new AI LLM provider"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    data = request.json

    try:
        with db_cursor() as cursor:
            # Insert provider
            cursor.execute("""
                INSERT INTO ai_llm (provider_name, own_name, api_key, endpoint_url, enabled)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data.get('provider_name'),
                data.get('own_name'),
                data.get('api_key'),
                data.get('endpoint_url'),
                data.get('enabled', False)
            ))

            provider_id = cursor.lastrowid

            # Insert models if provided
            models = data.get('models', [])
            for model in models:
                cursor.execute("""
                    INSERT INTO ai_llm_model (llm_id, model_name, display_name, is_active)
                    VALUES (%s, %s, %s, %s)
                """, (
                    provider_id,
                    model.get('model_name'),
                    model.get('display_name'),
                    model.get('is_active', True)
                ))

        return jsonify({'id': provider_id, 'message': 'Provider created successfully'}), 201

    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/providers/<int:provider_id>', methods=['PUT'])
@auth_required
def update_provider(provider_id):
    """Update an AI LLM provider"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    data = request.json

    try:
        with db_cursor() as cursor:
            # Update provider
            cursor.execute("""
                UPDATE ai_llm
                SET provider_name = %s, own_name = %s, api_key = %s,
                    endpoint_url = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                data.get('provider_name'),
                data.get('own_name'),
                data.get('api_key'),
                data.get('endpoint_url'),
                data.get('enabled'),
                provider_id
            ))

        return jsonify({'message': 'Provider updated successfully'}), 200

    except Exception as e:
        logger.error(f"Error updating provider: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/providers/<int:provider_id>', methods=['DELETE'])
@auth_required
def delete_provider(provider_id):
    """Delete an AI LLM provider"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute("DELETE FROM ai_llm WHERE id = %s", (provider_id,))

        return jsonify({'message': 'Provider deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting provider: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/providers/<int:provider_id>/models', methods=['POST'])
@auth_required
def add_model(provider_id):
    """Add a model to a provider"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    data = request.json

    try:
        with db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO ai_llm_model (llm_id, model_name, display_name, is_active)
                VALUES (%s, %s, %s, %s)
            """, (
                provider_id,
                data.get('model_name'),
                data.get('display_name'),
                data.get('is_active', True)
            ))

            model_id = cursor.lastrowid

        return jsonify({'id': model_id, 'message': 'Model added successfully'}), 201

    except Exception as e:
        logger.error(f"Error adding model: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/models/<int:model_id>', methods=['DELETE'])
@auth_required
def delete_model(model_id):
    """Delete a model"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute("DELETE FROM ai_llm_model WHERE id = %s", (model_id,))

        return jsonify({'message': 'Model deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/prompts', methods=['GET'])
@auth_required
def get_prompts():
    """Get all system prompts"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    try:
        with db_cursor() as cursor:
            cursor.execute("""
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
                        WHEN 'credit_card_matching' THEN 5
                        ELSE 99
                    END
            """)

            prompts = []
            for row in cursor.fetchall():
                prompts.append({
                    'id': row[0],
                    'prompt_key': row[1],
                    'title': row[2],
                    'description': row[3],
                    'prompt_content': row[4],
                    'selected_model_id': row[5],
                    'selected_model_name': row[6],
                    'selected_provider': row[7]
                })

        return jsonify({'prompts': prompts}), 200

    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        return jsonify({'error': str(e)}), 500


@ai_config_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
@auth_required
def update_prompt(prompt_id):
    """Update a system prompt"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    data = request.json

    try:
        with db_cursor() as cursor:
            cursor.execute("""
                UPDATE ai_system_prompts
                SET title = %s, description = %s, prompt_content = %s,
                    selected_model_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                data.get('title'),
                data.get('description'),
                data.get('prompt_content'),
                data.get('selected_model_id'),
                prompt_id
            ))

        return jsonify({'message': 'Prompt updated successfully'}), 200

    except Exception as e:
        logger.error(f"Error updating prompt: {e}")
        return jsonify({'error': str(e)}), 500