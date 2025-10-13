import json
import sys
import types
from datetime import datetime
from decimal import Decimal
from pathlib import Path


class StubCursor:
    def __init__(self, state, executed):
        self.state = state
        self.executed = executed
        self._result = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        params = params or ()
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()
        if sql_upper.startswith("DELETE FROM RECEIPT_ITEMS"):
            self.state["items"].clear()
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("INSERT INTO RECEIPT_ITEMS"):
            values = list(params)
            next_id = self.state.setdefault("next_item_id", 2)
            self.state["items"].append(
                {
                    "id": next_id,
                    "article_id": values[1],
                    "name": values[2],
                    "number": values[3],
                    "item_price_ex_vat": values[4],
                    "item_price_inc_vat": values[5],
                    "item_total_price_ex_vat": values[6],
                    "item_total_price_inc_vat": values[7],
                    "currency": values[8],
                    "vat": values[9],
                    "vat_percentage": values[10],
                }
            )
            self.state["next_item_id"] = next_id + 1
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("DELETE FROM AI_ACCOUNTING_PROPOSALS"):
            self.state["proposals"].clear()
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("INSERT INTO AI_ACCOUNTING_PROPOSALS"):
            values = list(params)
            next_id = self.state.setdefault("next_proposal_id", 2)
            self.state["proposals"].append(
                {
                    "id": next_id,
                    "account_code": values[1],
                    "debit": Decimal(str(values[2])),
                    "credit": Decimal(str(values[3])),
                    "vat_rate": Decimal(str(values[4])) if values[4] is not None else None,
                    "notes": values[5],
                }
            )
            self.state["next_proposal_id"] = next_id + 1
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("DELETE FROM FILE_TAGS"):
            self.state["tags"] = []
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("INSERT INTO FILE_TAGS"):
            tag = params[1]
            self.state.setdefault("tags", [])
            self.state["tags"].append(tag)
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("UPDATE UNIFIED_FILES SET"):
            assignments = sql.split("SET", 1)[1].split("WHERE")[0]
            assignments = assignments.replace(", updated_at=NOW()", "")
            columns = [part.split("=")[0].strip().strip("`") for part in assignments.split(",") if "%s" in part]
            values = list(params[:-1])
            float_columns = {
                "gross_amount",
                "net_amount",
                "gross_amount_sek",
                "net_amount_sek",
                "total_vat_25",
                "total_vat_12",
                "total_vat_6",
                "exchange_rate",
                "ai_confidence",
            }
            for column, value in zip(columns, values):
                if column in float_columns:
                    self.state["unified"][column] = Decimal(str(value)) if value is not None else None
                else:
                    self.state["unified"][column] = value
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("UPDATE COMPANIES SET"):
            assignments = sql.split("SET", 1)[1].split("WHERE")[0]
            assignments = assignments.replace(", updated_at=NOW()", "")
            columns = [part.split("=")[0].strip().strip("`") for part in assignments.split(",") if "%s" in part]
            values = list(params[:-1])
            company = self.state.setdefault("company", {})
            for column, value in zip(columns, values):
                company[column] = value
            self.rowcount = 1
            self._result = []
        elif sql_upper.startswith("INSERT INTO COMPANIES"):
            columns_section = sql_clean.split("(", 1)[1].split(")", 1)[0]
            columns = [col.strip().strip("`") for col in columns_section.split(",")]
            values = list(params)
            new_company_id = self.state.setdefault("next_company_id", 2)
            company = {"id": new_company_id}
            for column, value in zip(columns, values):
                company[column] = value
            self.state["company"] = company
            self.state["unified"]["company_id"] = new_company_id
            self.state["next_company_id"] = new_company_id + 1
            self.rowcount = 1
            self._result = []
        elif "FROM UNIFIED_FILES" in sql_upper and "LEFT JOIN" in sql_upper:
            u = self.state["unified"]
            company = self.state.get("company", {})
            tags_csv = ",".join(self.state.get("tags", []))
            self._result = [
                (
                    u["id"],
                    company.get("name"),
                    u.get("company_id"),
                    u.get("vat"),
                    u.get("purchase_datetime"),
                    u.get("receipt_number"),
                    u.get("payment_type"),
                    u.get("expense_type"),
                    u.get("credit_card_number"),
                    u.get("credit_card_last_4_digits"),
                    u.get("credit_card_type"),
                    u.get("credit_card_brand_full"),
                    u.get("credit_card_brand_short"),
                    u.get("credit_card_payment_variant"),
                    u.get("credit_card_token"),
                    u.get("credit_card_entering_mode"),
                    u.get("currency"),
                    u.get("exchange_rate"),
                    u.get("gross_amount"),
                    u.get("net_amount"),
                    u.get("gross_amount_sek"),
                    u.get("net_amount_sek"),
                    u.get("total_vat_25"),
                    u.get("total_vat_12"),
                    u.get("total_vat_6"),
                    u.get("ai_status"),
                    u.get("ai_confidence"),
                    u.get("other_data"),
                    u.get("ocr_raw"),
                    tags_csv,
                )
            ]
        elif "FROM COMPANIES" in sql_upper and "WHERE ID" in sql_upper:
            company = self.state.get("company", {})
            if company:
                self._result = [
                    (
                        company.get("id"),
                        company.get("name"),
                        company.get("orgnr"),
                        company.get("address"),
                        company.get("address2"),
                        company.get("zip"),
                        company.get("city"),
                        company.get("country"),
                        company.get("phone"),
                        company.get("www"),
                        company.get("email"),
                    )
                ]
                self.rowcount = 1
            else:
                self._result = []
                self.rowcount = 0
        elif "FROM RECEIPT_ITEMS" in sql_upper:
            items = []
            for item in self.state["items"]:
                items.append(
                    (
                        item["id"],
                        item["article_id"],
                        item["name"],
                        item["number"],
                        item["item_price_ex_vat"],
                        item["item_price_inc_vat"],
                        item["item_total_price_ex_vat"],
                        item["item_total_price_inc_vat"],
                        item["currency"],
                        item["vat"],
                        item["vat_percentage"],
                    )
                )
            self._result = items
        elif "FROM AI_ACCOUNTING_PROPOSALS" in sql_upper:
            proposals = []
            for entry in self.state["proposals"]:
                proposals.append(
                    (
                        entry["id"],
                        entry["account_code"],
                        entry["debit"],
                        entry["credit"],
                        entry["vat_rate"],
                        entry["notes"],
                    )
                )
            self._result = proposals
        else:
            self.rowcount = 0
            self._result = []

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)


def prepare_app(monkeypatch, tmp_path, state, executed):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    for module in ["api.app", "api.receipts"]:
        if module in sys.modules:
            sys.modules.pop(module)

    class DummyLimiter:
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            return None

        def limit(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    limiter_module = types.SimpleNamespace(Limiter=DummyLimiter)
    limiter_util_module = types.SimpleNamespace(get_remote_address=lambda *args, **kwargs: "127.0.0.1")
    monkeypatch.setitem(sys.modules, "flask_limiter", limiter_module)
    monkeypatch.setitem(sys.modules, "flask_limiter.util", limiter_util_module)

    class DummyConnection:
        def cursor(self):
            return self

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    dummy_connector = types.SimpleNamespace(connect=lambda *args, **kwargs: DummyConnection())
    mysql_module = types.SimpleNamespace(connector=dummy_connector)
    monkeypatch.setitem(sys.modules, "mysql", mysql_module)
    monkeypatch.setitem(sys.modules, "mysql.connector", dummy_connector)

    from importlib import import_module

    receipts_module = import_module("api.receipts")
    monkeypatch.setattr(receipts_module, "db_cursor", lambda: StubCursor(state, executed))

    app_module = import_module("api.app")
    return app_module.app


def build_initial_state(rid: str):
    return {
        "unified": {
            "id": rid,
            "company_id": 1,
            "vat": "SE556677889901",
            "purchase_datetime": datetime(2024, 9, 25, 12, 0, 0),
            "receipt_number": "R-100",
            "payment_type": "card",
            "expense_type": "corporate",
            "credit_card_number": "123456******",
            "credit_card_last_4_digits": "6789",
            "credit_card_type": "visa",
            "credit_card_brand_full": "Visa",
            "credit_card_brand_short": "VISA",
            "credit_card_payment_variant": "chip",
            "credit_card_token": "token-abc",
            "credit_card_entering_mode": "chip",
            "currency": "SEK",
            "exchange_rate": Decimal("0"),
            "gross_amount": Decimal("125.00"),
            "net_amount": Decimal("100.00"),
            "gross_amount_sek": Decimal("125.00"),
            "net_amount_sek": Decimal("100.00"),
            "total_vat_25": Decimal("25.00"),
            "total_vat_12": Decimal("0.00"),
            "total_vat_6": Decimal("0.00"),
            "ai_status": "completed",
            "ai_confidence": Decimal("0.92"),
            "other_data": '{"example":"data"}',
            "ocr_raw": "Merchant AB 125.00 SEK",
        },
        "company": {
            "id": 1,
            "name": "Merchant AB",
            "orgnr": "556677-8899",
            "address": "Huvudgatan 1",
            "address2": "",
            "zip": "12345",
            "city": "Stockholm",
            "country": "SE",
            "phone": "010-123456",
            "www": "https://merchant.example",
            "email": "info@merchant.example",
        },
        "tags": ["food", "lunch"],
        "items": [
            {
                "id": 1,
                "article_id": "A1",
                "name": "Lunch",
                "number": 1,
                "item_price_ex_vat": Decimal("80.00"),
                "item_price_inc_vat": Decimal("100.00"),
                "item_total_price_ex_vat": Decimal("80.00"),
                "item_total_price_inc_vat": Decimal("100.00"),
                "currency": "SEK",
                "vat": Decimal("20.00"),
                "vat_percentage": Decimal("25.00"),
            }
        ],
        "proposals": [
            {
                "id": 1,
                "account_code": "4010",
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "vat_rate": Decimal("25.00"),
                "notes": "Lunch",
            }
        ],
    }


def test_receipt_modal_get(monkeypatch, tmp_path):
    rid = "RID-100"
    state = build_initial_state(rid)
    executed = []

    receipt_dir = tmp_path / rid
    receipt_dir.mkdir(parents=True, exist_ok=True)
    boxes = [{"field": "merchant", "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}]
    (receipt_dir / "boxes.json").write_text(json.dumps(boxes), encoding="utf-8")

    app = prepare_app(monkeypatch, tmp_path, state, executed)
    client = app.test_client()

    response = client.get(f"/receipts/{rid}/modal")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["receipt"]["merchant"] == "Merchant AB"
    assert payload["receipt"]["tags"] == ["food", "lunch"]
    assert payload["items"][0]["name"] == "Lunch"
    assert payload["proposals"][0]["account"] == "4010"
    assert payload["boxes"][0]["field"] == "merchant"
    # Ensure DB was queried for all sections
    assert any("FROM unified_files" in sql for sql, _ in executed)
    assert any("FROM receipt_items" in sql for sql, _ in executed)
    assert any("FROM ai_accounting_proposals" in sql for sql, _ in executed)


def test_receipt_modal_put_updates_entities(monkeypatch, tmp_path):
    rid = "RID-200"
    state = build_initial_state(rid)
    executed = []

    receipt_dir = tmp_path / rid
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / "boxes.json").write_text("[]", encoding="utf-8")

    app = prepare_app(monkeypatch, tmp_path, state, executed)
    client = app.test_client()

    payload = {
        "receipt": {"gross_amount": 150.5, "tags": "updated,tag"},
        "company": {"name": "New Merchant AB", "orgnr": "556677-0000"},
        "items": [
            {
                "name": "Dinner",
                "number": 2,
                "item_price_inc_vat": 50.25,
                "item_total_price_inc_vat": 100.5,
                "item_price_ex_vat": 40.2,
                "item_total_price_ex_vat": 80.4,
                "vat": 20.1,
                "vat_percentage": 25,
                "currency": "SEK",
            }
        ],
        "proposals": [
            {"account": "5810", "debit": 100.5, "credit": 0, "vat_rate": 25, "notes": "Dinner"}
        ],
    }

    response = client.put(f"/receipts/{rid}/modal", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert data["receipt_updated"] is True
    assert data["items_updated"] is True
    assert data["proposals_updated"] is True
    assert data["company_updated"] is True
    assert data["tags_updated"] is True
    assert data["data"]["receipt"]["merchant"] == "New Merchant AB"
    assert data["data"]["receipt"]["tags"] == ["updated", "tag"]
    assert data["data"]["company"]["name"] == "New Merchant AB"
    assert data["data"]["items"][0]["name"] == "Dinner"
    assert data["data"]["proposals"][0]["account"] == "5810"

    joined_sql = "\n".join(sql for sql, _ in executed)
    assert "UPDATE unified_files" in joined_sql
    assert "DELETE FROM receipt_items" in joined_sql
    assert "INSERT INTO receipt_items" in joined_sql
    assert "DELETE FROM ai_accounting_proposals" in joined_sql
    assert "INSERT INTO ai_accounting_proposals" in joined_sql
    assert "UPDATE companies" in joined_sql
    assert "DELETE FROM file_tags" in joined_sql
    assert "INSERT INTO file_tags" in joined_sql
