import re
from code_modules.sql_query_loader import SQLQueryProvider


class TestSQLQueryProvider:
    """Unit tests for SQLQueryProvider"""

    def test_get_data_reset_query_list(self):
        result = SQLQueryProvider.get_data_reset_query_list()

        assert isinstance(result, list)
        assert len(result) == 3

        expected_tables = [
            "intercompany_ap_data",
            "intercompany_ar_data",
            "intercompany_recon_result"
        ]

        for query, table in zip(result, expected_tables):
            assert isinstance(query, str)
            assert query.startswith("TRUNCATE TABLE")
            assert table in query

    def test_get_base_tables(self):
        result = SQLQueryProvider.get_base_tables()

        assert isinstance(result, dict)
        assert set(result.keys()) == {"ap_data", "ar_data"}

        assert result["ap_data"] == "SELECT * FROM intercompany_ap_data"
        assert result["ar_data"] == "SELECT * FROM intercompany_ar_data"

    def test_insert_recon_result_query_returns_string(self):
        query = SQLQueryProvider.insert_recon_result_query()

        assert isinstance(query, str)
        assert "INSERT INTO INTERCOMPANY_RECON_RESULT" in query

    def test_insert_recon_result_query_contains_all_named_parameters(self):
        query = SQLQueryProvider.insert_recon_result_query()

        expected_placeholders = {
            "AR_REGION", "ar_company_code", "ar_unit_name",
            "ap_region", "ap_company_code", "customer_number",
            "booking_number", "ar_reference_number", "ar_document_date",
            "ar_document_type", "ar_document_currency",
            "ar_document_description", "ar_due_date",
            "ap_supplier_number", "ap_reference_number", "ap_document_type",
            "ap_document_date", "ap_document_currency",
            "ap_document_description", "ap_posting_date",
            "reconciliation_status", "message", "module",
            "ar_document_amount", "ap_document_amount",
            "ar_invoice_year"
        }

        found_placeholders = set(re.findall(r":([a-zA-Z_]+)", query))

        assert expected_placeholders == found_placeholders

    def test_rename_final_table_fields(self):
        result = SQLQueryProvider.rename_final_table_fields()

        assert isinstance(result, dict)
        assert len(result) > 10

        # AR mappings
        assert result["AR_COCD"] == "ar_company_code"
        assert result["AR_UNIT_NAME"] == "ar_unit_name"
        assert result["INVOICE_YEAR"] == "ar_invoice_year"

        # AP mappings
        assert result["SUPPLIER"] == "ap_supplier_number"
        assert result["REFERENCE_NO"] == "ap_reference_number"
        assert result["POSTING_DATE"] == "ap_posting_date"

        # Status mappings
        assert result["status"] == "reconciliation_status"
        assert result["message"] == "message"

    def test_rename_final_table_fields_values_are_strings(self):
        result = SQLQueryProvider.rename_final_table_fields()

        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

from code_modules.sql_query_loader import SQLQueryProvider


def test_ar_insert_sql_returns_valid_query():
    query = SQLQueryProvider.ar_insert_sql()

    assert isinstance(query, str)
    assert "INSERT INTO INTERCOMPANY_AR_DATA" in query
    assert ":AR_REGION" in query
    assert ":INVOICE_YEAR" in query
    assert "DELIVERY_NOTE" in query


def test_ap_insert_sql_returns_valid_query():
    query = SQLQueryProvider.ap_insert_sql()

    assert isinstance(query, str)
    assert "INSERT INTO INTERCOMPANY_AP_DATA" in query
    assert ":COMPANY_CODE" in query
    assert ":SUPPLIER" in query
    assert ":CLEARING_DATE" in query
