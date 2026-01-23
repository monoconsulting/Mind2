import sys
import types
from contextlib import contextmanager
from unittest.mock import ANY, MagicMock, patch

import pytest
from flask import Flask

from api.reconciliation_firstcard import recon_bp


def _stub_services_tasks_module() -> types.ModuleType:
    mod = types.ModuleType("services.tasks")
    mod.dispatch_workflow = MagicMock()
    mod.log_import_event = MagicMock()
    mod.refresh_invoice_match_state = MagicMock()
    mod.auto_match_invoice_lines = MagicMock()
    return mod


@contextmanager
def _with_stubbed_services_tasks():
    stub = _stub_services_tasks_module()
    with patch.dict(sys.modules, {"services.tasks": stub}):
        yield


# Import routes under a temporary `services.tasks` stub so that route package imports
# do not pull in the full Celery/task graph during test collection.
with _with_stubbed_services_tasks():
    import api.reconciliation_firstcard.routes.statements as statements


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(recon_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _mock_db_cursor(*fetchone_results):
    cursor = MagicMock()
    cursor.fetchone.side_effect = list(fetchone_results)
    ctx = MagicMock()
    ctx.__enter__.return_value = cursor
    return MagicMock(return_value=ctx), cursor


def _mock_workflow_coordinator_module():
    mod = types.ModuleType("services.workflow_coordinator")
    mod.FirstCardWorkflowCoordinator = MagicMock()
    return mod


def test_resume_integration(client):
    workflow_run_id = 123
    db_cursor_mock, _ = _mock_db_cursor((workflow_run_id, "failed", "some_stage"))

    coordinator_mod = _mock_workflow_coordinator_module()
    coordinator = coordinator_mod.FirstCardWorkflowCoordinator.return_value
    coordinator.dispatch_fc_workflow.return_value = True

    with patch.object(statements, "load_invoice_document", return_value=True):
        with patch.object(statements, "log_event"):
            with patch.object(statements, "transition_processing_status"):
                with patch.object(statements, "transition_document_status"):
                    with patch.object(statements, "db_cursor", db_cursor_mock):
                        with patch.dict(sys.modules, {"services.workflow_coordinator": coordinator_mod}):
                            response = client.post("/reconciliation/firstcard/statements/inv-123/resume")

    assert response.status_code == 200
    assert response.json["ok"] is True
    assert response.json["workflow_run_id"] == workflow_run_id
    assert response.json["action"] == "resumed"

    coordinator.begin_fc_import_stage.assert_called_with(
        workflow_run_id, "resume_dispatch", message=ANY
    )
    coordinator.complete_fc_import_stage.assert_called_with(
        workflow_run_id, "resume_dispatch", success=True, message="Resume dispatched"
    )
    coordinator.dispatch_fc_workflow.assert_called_with(workflow_run_id)


def test_restart_integration(client):
    workflow_run_id = 456
    db_cursor_mock, _ = _mock_db_cursor(("hash",), ('{"some": "meta"}',))

    coordinator_mod = _mock_workflow_coordinator_module()
    coordinator = coordinator_mod.FirstCardWorkflowCoordinator.return_value
    coordinator.create_workflow_run_for_fc_document.return_value = workflow_run_id
    coordinator.dispatch_fc_workflow.return_value = True

    with patch.object(statements, "load_invoice_document", return_value=True):
        with patch.object(statements, "write_invoice_metadata"):
            with patch.object(statements, "invoice_documents_supports_updated_at", return_value=True):
                with patch.object(statements, "log_event"):
                    with patch.object(statements, "transition_processing_status"):
                        with patch.object(statements, "transition_document_status"):
                            with patch.object(statements, "db_cursor", db_cursor_mock):
                                with patch.dict(sys.modules, {"services.workflow_coordinator": coordinator_mod}):
                                    response = client.post(
                                        "/reconciliation/firstcard/statements/inv-123/restart"
                                    )

    assert response.status_code == 200
    assert response.json["ok"] is True
    assert response.json["workflow_run_id"] == workflow_run_id
    assert response.json["action"] == "restarted"

    coordinator.create_workflow_run_for_fc_document.assert_called_with(
        file_id="inv-123",
        workflow_key="WF3_FIRSTCARD_INVOICE",
    )
    coordinator.dispatch_fc_workflow.assert_called_with(workflow_run_id)

