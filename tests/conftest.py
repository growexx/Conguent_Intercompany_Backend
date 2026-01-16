import pytest
from fastapi.testclient import TestClient
from app.main import app


import pandas as pd
from unittest.mock import MagicMock
from datetime import datetime


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.services.reconciliation_service import ReconcileService


@pytest.fixture
def reconcile_service(monkeypatch):
    service = ReconcileService()

    service.oracle_adb_client = MagicMock()
    service.sql_query_provider = MagicMock()

    service.sql_query_provider.rename_final_table_fields.return_value = {
        "AR_COCD": "ar_company_code",
        "AR_UNIT_NAME": "ar_unit_name",
        "AP_COCD": "ap_company_code",
        "CUSTOMER_NO_LOCAL_SYSTEM": "customer_number",
        "BOOKING_NO_AR": "booking_number",
        "INVOICE_REFERENCE": "ar_reference_number",
        "DOC_DATE": "ar_document_date",
        "INVOICE_DOC_TYPE": "ar_document_type",
        "INVOICE_DOC_CURRENCY": "ar_document_currency",
        "DOCUMENT_DESCRIPTION": "ar_document_description",
        "DUE_DATE": "ar_due_date",
        "SUPPLIER": "ap_supplier_number",
        "REFERENCE_NO": "ap_reference_number",
        "DOCUMENT_TYPE": "ap_document_type",
        "DOCUMENT_DATE": "ap_document_date",
        "DOCUMENT_CURRENCY": "ap_document_currency",
        "AP_COMMENT": "ap_document_description",
        "POSTING_DATE": "ap_posting_date",
        "status": "reconciliation_status",
    }

    service.sql_query_provider.insert_recon_result_query.return_value = "INSERT SQL"
    return service
