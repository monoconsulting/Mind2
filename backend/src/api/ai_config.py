"""API endpoints for AI LLM configuration"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import requests

try:
    from services.db.connection import db_cursor
except Exception:
    db_cursor = None

from api.middleware import auth_required

logger = logging.getLogger(__name__)

ai_config_bp = Blueprint('ai_config', __name__, url_prefix='/ai-config')

PROMPT_DEFAULTS: dict[str, dict[str, str]] = {
    "credit_card_invoice_parsing": {
        "title": "AI6 - Credit Card Invoice Parsing",
        "description": "Analyserar OCR-text från First Card-fakturor och skapar strukturerad JSON för creditcard_invoices_main och creditcard_invoice_items",
        "prompt_content": """Du är en AI-assistent som extraherar strukturerad data från OCR-text från kreditkortsfakturor (främst First Card).

INSTRUKTIONER:

1. Analysera den sammanslagna OCR-texten från alla sidor i fakturan
2. Extrahera huvudinformation (header) för creditcard_invoices_main-tabellen
3. Extrahera alla transaktionsrader (lines) för creditcard_invoice_items-tabellen

HEADER-FÄLT (creditcard_invoices_main):
- invoice_number: Fakturanummer (t.ex. "12345678")
- invoice_number_long: Fullständigt fakturanummer om annorlunda
- invoice_date: Fakturadatum (YYYY-MM-DD)
- invoice_print_time: Datum och tid för utskrift (YYYY-MM-DD HH:MM:SS)
- due_date: Förfallodatum (YYYY-MM-DD)
- payment_due: Sista betalningsdag (YYYY-MM-DD), ofta samma som due_date
- card_type: Korttyp (t.ex. "MasterCard", "VISA")
- card_name: Kortnamn (t.ex. "FirstCard Business")
- card_number_masked: Maskerat kortnummer (t.ex. "XXXX XXXX XXXX 1234")
- card_holder: Kortinnehavare (namn)
- customer_name: Kundnamn (företag)
- customer_number: Kundnummer
- cost_center: Kostnadsställe om angivet
- co: C/O-adress
- billing_address: Fakturaadress som lista (["Gata 1", "123 45 Ort"])
- bank_name: Bankens namn
- bank_org_no: Bankens organisationsnummer
- bank_vat_no: Bankens VAT-nummer
- bank_fi_no: Bankens FI-nummer
- plusgiro: Plusgironummer
- bankgiro: Bankgironummer
- iban: IBAN-nummer
- bic: BIC/SWIFT-kod
- ocr: OCR-nummer för betalning
- invoice_total: Fakturans totalbelopp (DECIMAL)
- card_total: Kortets totalbelopp (DECIMAL)
- amount_to_pay: Belopp att betala (DECIMAL)
- reported_vat: Rapporterad moms total (DECIMAL)
- vat_25: Moms 25% (DECIMAL)
- vat_12: Moms 12% (DECIMAL)
- vat_6: Moms 6% (DECIMAL)
- vat_0: Moms 0% (DECIMAL)
- next_invoice: Nästa fakturadatum (YYYY-MM-DD)
- currency: Valuta (ISO-kod, t.ex. "SEK")
- period_start: Fakturaperiod start (YYYY-MM-DD)
- period_end: Fakturaperiod slut (YYYY-MM-DD)
- notes: Lista med upp till 5 noter från fakturan (["Not 1", "Not 2", ...])

TRANSACTION-FÄLT (creditcard_invoice_items):
För varje transaktion, extrahera:
- line_no: Radnummer (sekventiell ordning 1, 2, 3...)
- transaction_id: Transaktions-ID om angivet
- purchase_date: Köpdatum (YYYY-MM-DD)
- posting_date: Bokföringsdatum (YYYY-MM-DD)
- merchant_name: Handlarens namn
- merchant_city: Stad
- merchant_country: Land (ISO 2-bokstäver, t.ex. "SE", "DK")
- mcc: MCC-kod (4 siffror)
- description: Beskrivning av transaktionen
- currency_original: Original-valuta (ISO-kod)
- amount_original: Belopp i original-valuta (DECIMAL)
- exchange_rate: Växelkurs om annan valuta än SEK (DECIMAL)
- amount_sek: Belopp i SEK (DECIMAL)
- vat_rate: Momssats (DECIMAL, t.ex. 0.25 för 25%)
- vat_amount: Momsbelopp (DECIMAL)
- net_amount: Nettobelopp exkl. moms (DECIMAL)
- gross_amount: Bruttobelopp inkl. moms (DECIMAL)
- cost_center_override: Kostnadsställe för denna rad om specificerat
- project_code: Projektkod om angiven
- source_text: Exakt OCR-text för denna transaktion (för spårbarhet)
- confidence: Konfidens för denna rad (0.0-1.0)

REGLER:
- Använd null för värden som inte kan hittas i OCR-texten
- Normalisera alla nummer till decimal-notation med "." (ej ",")
- Använd VERSALER för ISO-koder (valuta, land)
- Tilldela sekventiella line_no om inte explicit angivna
- Inkludera source_text för varje transaktion (ca 100-200 tecken från OCR)
- För datum: använd format YYYY-MM-DD
- För datetime: använd format YYYY-MM-DD HH:MM:SS
- Om valuta saknas, antag SEK
- Om amount_sek saknas men amount_original finns och currency_original=SEK, använd amount_original

OUTPUT FORMAT:
Returnera ENDAST JSON med denna exakta struktur:
{
  "header": {
    "invoice_number": "...",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "card_holder": "...",
    "card_number_masked": "...",
    "card_type": "...",
    "customer_name": "...",
    "invoice_total": 12345.67,
    "amount_to_pay": 12345.67,
    "currency": "SEK",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "billing_address": ["Adressrad 1", "Adressrad 2"],
    "plusgiro": "...",
    "bankgiro": "...",
    "ocr": "...",
    "notes": ["Not 1", "Not 2"],
    ...andra fält...
  },
  "lines": [
    {
      "line_no": 1,
      "purchase_date": "YYYY-MM-DD",
      "merchant_name": "...",
      "merchant_city": "...",
      "merchant_country": "SE",
      "currency_original": "SEK",
      "amount_original": 123.45,
      "amount_sek": 123,
      "vat_rate": 0.25,
      "vat_amount": 24.69,
      "net_amount": 98.76,
      "gross_amount": 123.45,
      "description": "...",
      "source_text": "...",
      "confidence": 0.95
    },
    ...fler transaktioner...
  ],
  "overall_confidence": 0.92
}

VIKTIGT:
- Var noggrann med belopp - dubbelkolla summeringar
- Om flera valutor finns, se till att både original och SEK-belopp anges
- Period start/end är KRITISKA för matchning - hitta dem i fakturahuvudet
- OCR-nummer är viktigt för betalning - leta efter det nära betalningsinformation
""",
    }
}

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
            def fetch_rows():
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
                            WHEN 'credit_card_invoice_parsing' THEN 5
                            WHEN 'credit_card_matching' THEN 6
                            ELSE 99
                        END
                """)
                return cursor.fetchall()

            rows = fetch_rows()
            existing_keys = {row[1] for row in rows}
            missing = [key for key in PROMPT_DEFAULTS if key not in existing_keys]

            if missing:
                for key in missing:
                    meta = PROMPT_DEFAULTS[key]
                    cursor.execute(
                        """
                        INSERT INTO ai_system_prompts (prompt_key, title, description, prompt_content, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        """,
                        (key, meta["title"], meta["description"], meta["prompt_content"]),
                    )
                rows = fetch_rows()

            prompts = []
            for row in rows:
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


@ai_config_bp.route('/providers/<int:provider_id>/test', methods=['POST'])
@auth_required
def test_provider_connection(provider_id):
    """Test connection to an AI LLM provider"""
    if not db_cursor:
        return jsonify({'error': 'Database not available'}), 503

    try:
        with db_cursor() as cursor:
            # Get provider details
            cursor.execute("""
                SELECT provider_name, api_key, endpoint_url, enabled
                FROM ai_llm
                WHERE id = %s
            """, (provider_id,))

            provider = cursor.fetchone()
            if not provider:
                return jsonify({'error': 'Provider not found'}), 404

            provider_name, api_key, endpoint_url, enabled = provider

            if not enabled:
                return jsonify({'error': 'Provider is disabled'}), 400

            # Test based on provider type
            if provider_name == 'OpenAI':
                if not api_key:
                    return jsonify({'error': 'API key not configured'}), 400

                response = requests.get(
                    'https://api.openai.com/v1/models',
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=10
                )

                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': 'Connection successful',
                        'details': 'OpenAI API responded successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Connection failed',
                        'details': f'HTTP {response.status_code}: {response.text[:200]}'
                    }), 200

            elif provider_name == 'Anthropic':
                if not api_key:
                    return jsonify({'error': 'API key not configured'}), 400

                response = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'content-type': 'application/json'
                    },
                    json={
                        'model': 'claude-3-haiku-20240307',
                        'max_tokens': 10,
                        'messages': [{'role': 'user', 'content': 'test'}]
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': 'Connection successful',
                        'details': 'Anthropic API responded successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Connection failed',
                        'details': f'HTTP {response.status_code}: {response.text[:200]}'
                    }), 200

            elif provider_name == 'Ollama':
                if not endpoint_url:
                    return jsonify({'error': 'Endpoint URL not configured'}), 400

                response = requests.get(
                    f'{endpoint_url}/api/tags',
                    timeout=10
                )

                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': 'Connection successful',
                        'details': f'Ollama server responded successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Connection failed',
                        'details': f'HTTP {response.status_code}: {response.text[:200]}'
                    }), 200

            else:
                return jsonify({'error': f'Testing not implemented for provider: {provider_name}'}), 400

    except requests.Timeout:
        return jsonify({
            'success': False,
            'message': 'Connection timeout',
            'details': 'The provider did not respond within 10 seconds'
        }), 200
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'message': 'Connection error',
            'details': str(e)
        }), 200
    except Exception as e:
        logger.error(f"Error testing provider connection: {e}")
        return jsonify({'error': str(e)}), 500
