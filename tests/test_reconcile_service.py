import pandas as pd 
import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.services.reconciliation_service import ReconcileService , check_if_df_all_null_or_zero
from decimal import Decimal

@pytest.fixture
def reconcile_service(monkeypatch):
    service = ReconcileService()

    service.oracle_adb_client = MagicMock()
    service.sql_query_provider = MagicMock()

    service.sql_query_provider.rename_final_table_fields.return_value = {
        "AR_REGION": "AR_REGION",
        "AR_COCD": "ar_company_code",
        "AR_UNIT_NAME": "ar_unit_name",
        "AP_REGION": "ap_region",
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

        # 🔴 THESE WERE MISSING
        "INVOICE_DOC_AMOUNT": "ar_document_amount",
        "AMOUNT_DOC_CURRENCY": "ap_document_amount",
        "INVOICE_YEAR": "ar_invoice_year",

        "status": "reconciliation_status",
    }



    service.sql_query_provider.insert_recon_result_query.return_value = "INSERT SQL"
    return service



def test_check_if_df_all_null_or_zero_true():
    df = pd.DataFrame({"a": [0, None], "b": [0, None]})
    assert check_if_df_all_null_or_zero(df) is True


def test_check_if_df_all_null_or_zero_false():
    df = pd.DataFrame({"a": [1], "b": [0]})
    assert check_if_df_all_null_or_zero(df) is False


def test_merge_ar_ap(reconcile_service):
    ar = pd.DataFrame({
        "ASSIGNMENT_VIN_SHIPMENT": ["R1"],
        "DOC_DATE": [pd.Timestamp("2024-01-01")]
    })

    ap = pd.DataFrame({
        "REFERENCE_NO": ["R1"],
        "DOCUMENT_DATE": [pd.Timestamp("2024-01-01")]
    })

    merged = reconcile_service._merge_ar_ap(ar, ap)

    assert "_merge" in merged.columns
    assert merged["_merge"].iloc[0] == "both"


def test_split_merge_results(reconcile_service):
    df = pd.DataFrame({
        "_merge": ["left_only", "right_only", "both"],
        "val": [1, 2, 3]
    })

    ar, ap, matched = reconcile_service._split_merge_results(df)

    assert len(ar) == 1
    assert len(ap) == 1
    assert len(matched) == 1

def test_reconcile_matches(reconcile_service):
    df = pd.DataFrame({
        "DOC_DATE": [pd.Timestamp("2024-01-01")],
        "DOCUMENT_DATE": [pd.Timestamp("2024-01-01")],
        "INVOICE_DOC_CURRENCY": ["USD"],
        "DOCUMENT_CURRENCY": ["USD"],
        "INVOICE_DOC_AMOUNT": [100],
        "AMOUNT_DOC_CURRENCY": [-100],
    })

    reconciled, rejected = reconcile_service._reconcile_matches(df)

    assert len(reconciled) == 1
    assert rejected.empty

def test_process_ap_multiple_records(reconcile_service):
    df = pd.DataFrame({
        "REFERENCE_NO": ["R1", "R1", "R2"],
        "DOCUMENT_TYPE": ["L8", "KR", "KR"]
    })

    with_l8, without_l8 = reconcile_service._process_ap_multiple_records(df)

    assert len(with_l8) == 1
    assert with_l8.iloc[0]["DOCUMENT_TYPE"] == "L8"

def test_convert_types(reconcile_service):
    df = pd.DataFrame({
        "ar_document_date": ["2024-01-01"],
        "ap_document_date": ["2024-01-02"],
        "ap_posting_date": ["2024-01-03"],
        "ar_due_date": ["2024-01-10"],
        "AR_REGION": ["NA"],
        "ar_company_code": ["1000"],
        "ar_unit_name": ["UNIT"],
        "ap_region": ["NA"],
        "ap_company_code": ["2000"],
        "customer_number": ["C1"],
        "booking_number": ["B1"],
        "ar_reference_number": ["INV"],
        "ar_document_type": ["DR"],
        "ar_document_currency": ["USD"],
        "ar_document_description": ["desc"],
        "ap_supplier_number": ["SUP"],
        "ap_reference_number": ["REF"],
        "ap_document_type": ["KR"],
        "ap_document_currency": ["USD"],
        "ap_document_description": ["ok"],
        "reconciliation_status": ["Reconciled"],
        "message": ["ok"],
        "module": ["Intercompany"],
        "ar_document_amount": [100],
        "ap_document_amount": [100],
        "ar_invoice_year": [2024],
    })

    result = reconcile_service._convert_types(df)

    assert isinstance(result["ar_document_amount"].iloc[0], Decimal)


def test_handle_inquiry_happy_path(reconcile_service):
    ar_df = pd.DataFrame([{
        "ASSIGNMENT_VIN_SHIPMENT": "REF1",
        "DOC_DATE": pd.Timestamp("2024-01-01"),
        "INVOICE_DOC_AMOUNT": 100,
        "INVOICE_DOC_CURRENCY": "USD",
        "AR_REGION": "NA",
        "AR_COCD": "1000",
        "AR_UNIT_NAME": "UNIT1",
        "CUSTOMER_NO_LOCAL_SYSTEM": "C1",
        "BOOKING_NO_AR": "B1",
        "INVOICE_REFERENCE": "INV1",
        "INVOICE_DOC_TYPE": "DR",
        "DOCUMENT_DESCRIPTION": "desc",
        "DUE_DATE": pd.Timestamp("2024-01-10"),
        "INVOICE_YEAR": 2024,
        "CREATED_AT": "x"
    }])

    ap_df = pd.DataFrame([{
        "REFERENCE_NO": "REF1",
        "DOCUMENT_DATE": pd.Timestamp("2024-01-01"),
        "AMOUNT_DOC_CURRENCY": -100,
        "DOCUMENT_CURRENCY": "USD",
        "DOCUMENT_TYPE": "KR",
        "AP_REGION": "NA",
        "AP_COCD": "2000",
        "SUPPLIER": "SUP1",
        "AP_COMMENT": "ok",
        "POSTING_DATE": pd.Timestamp("2024-01-02"),
        "CREATED_AT": "x"
    }])

    reconcile_service._fetch_base_data = MagicMock(return_value=(ar_df, ap_df))

    reconcile_service.handle_inquiry()

    reconcile_service.oracle_adb_client.execute_multiple_non_query.assert_called_once()


def test_handle_inquiry_no_data(reconcile_service):
    empty = pd.DataFrame({"a": [None]})
    reconcile_service._fetch_base_data = MagicMock(return_value=(empty, empty))

    reconcile_service.handle_inquiry()

    reconcile_service.oracle_adb_client.execute_multiple_non_query.assert_not_called()


def test_fetch_base_data_drops_created_at(reconcile_service):
    ar_df = pd.DataFrame({
        "COL1": [1],
        "CREATED_AT": ["2024-01-01"]
    })

    ap_df = pd.DataFrame({
        "COL2": [2],
        "CREATED_AT": ["2024-01-01"]
    })

    reconcile_service.sql_query_provider.get_base_tables.return_value = {
        "ar_data": "AR_SQL",
        "ap_data": "AP_SQL",
    }

    reconcile_service.oracle_adb_client.execute_query_df.side_effect = [
        ar_df.copy(),
        ap_df.copy(),
    ]

    result_ar, result_ap = reconcile_service._fetch_base_data()

    # CREATED_AT must be removed
    assert "CREATED_AT" not in result_ar.columns
    assert "CREATED_AT" not in result_ap.columns

    # Ensure correct calls
    reconcile_service.oracle_adb_client.execute_query_df.assert_any_call("AR_SQL")
    reconcile_service.oracle_adb_client.execute_query_df.assert_any_call("AP_SQL")


def test_handle_inquiry_exception_path(reconcile_service):
    # Force an exception early
    reconcile_service._fetch_base_data = MagicMock(
        side_effect=Exception("DB failure")
    )

    # Should not raise
    reconcile_service.handle_inquiry()

    # Insert must NOT be called
    reconcile_service.oracle_adb_client.execute_multiple_non_query.assert_not_called()

def test_data_deletion_executes_all_queries(reconcile_service):
    delete_queries = [
        "DELETE FROM TABLE_1",
        "DELETE FROM TABLE_2",
        "DELETE FROM TABLE_3",
    ]

    reconcile_service.sql_query_provider.get_data_reset_query_list.return_value = delete_queries

    result = reconcile_service.data_deletion()

    # Ensure each delete query is executed
    assert reconcile_service.oracle_adb_client.execute_single_non_query.call_count == len(delete_queries)

    reconcile_service.oracle_adb_client.execute_single_non_query.assert_any_call("DELETE FROM TABLE_1")
    reconcile_service.oracle_adb_client.execute_single_non_query.assert_any_call("DELETE FROM TABLE_2")
    reconcile_service.oracle_adb_client.execute_single_non_query.assert_any_call("DELETE FROM TABLE_3")

    # Validate response
    assert result == {
        "status": "accepted",
        "message": "Data deleted",
    }
