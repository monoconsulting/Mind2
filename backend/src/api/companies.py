from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request

try:
    from services.db.connection import db_cursor
except Exception:
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)

companies_bp = Blueprint("companies", __name__)


@companies_bp.route("/companies", methods=["GET"])
def search_companies():
    """
    GET /ai/api/companies?search={query}

    Söker företag baserat på namn.
    Returnerar max 20 träffar sorterade alfabetiskt.
    """
    search_term = request.args.get("search", "").strip()
    limit_param = request.args.get("limit")
    try:
        limit = int(limit_param) if limit_param is not None else 20
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))

    if db_cursor is None:
        logger.error("Database connection not available")
        return jsonify({"error": "Database unavailable"}), 503

    try:
        with db_cursor(dictionary=True) as cursor:
            if search_term:
                # Söker med LIKE för att hitta partiella matchningar
                # Returnerar id, name, orgnr och city för autocomplete
                search_pattern = f"%{search_term}%"
                cursor.execute(
                    """
                    SELECT
                        id,
                        name,
                        orgnr,
                        city
                    FROM companies
                    WHERE name LIKE %s
                    ORDER BY
                        CASE
                            WHEN name = %s THEN 0
                            WHEN name LIKE %s THEN 1
                            ELSE 2
                        END,
                        name ASC
                    LIMIT %s
                    """,
                    (search_pattern, search_term, f"{search_term}%", limit),
                )
            else:
                # Ingen sökterm => visa första företagen alfabetiskt
                cursor.execute(
                    """
                    SELECT
                        id,
                        name,
                        orgnr,
                        city
                    FROM companies
                    ORDER BY name ASC
                    LIMIT %s
                    """,
                    (limit,),
                )

            companies = cursor.fetchall() or []

            # Konvertera till lista med dictionaries (cursor returnerar dicts)
            result = []
            for company in companies:
                result.append(
                    {
                        "id": company.get("id"),
                        "name": company.get("name"),
                        "orgnr": company.get("orgnr") or None,
                        "city": company.get("city") or None,
                    }
                )

            return jsonify(result), 200

    except Exception as e:
        logger.error(f"Failed to search companies: {e}", exc_info=True)
        return jsonify({"error": "Failed to search companies"}), 500


@companies_bp.route("/companies/<int:company_id>", methods=["GET"])
def get_company(company_id: int):
    """
    GET /ai/api/companies/{id}

    Hämtar fullständig information om ett specifikt företag.
    """
    if db_cursor is None:
        logger.error("Database connection not available")
        return jsonify({"error": "Database unavailable"}), 503

    try:
        with db_cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    orgnr,
                    address,
                    address2,
                    zip,
                    city,
                    country,
                    phone,
                    www,
                    email,
                    created_at,
                    updated_at
                FROM companies
                WHERE id = %s
                """,
                (company_id,)
            )

            company = cursor.fetchone()

            if not company:
                return jsonify({"error": "Company not found"}), 404

            # Konvertera datetime till ISO-format
            result = dict(company)
            if result.get("created_at"):
                result["created_at"] = result["created_at"].isoformat()
            if result.get("updated_at"):
                result["updated_at"] = result["updated_at"].isoformat()

            return jsonify(result), 200

    except Exception as e:
        logger.error(f"Failed to get company {company_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get company"}), 500
