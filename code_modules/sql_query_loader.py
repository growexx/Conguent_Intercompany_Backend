"""
SQL Query Provider module.

This module centralizes all SQL statements used by the
Intercompany Reconciliation application.

Purpose:
- Avoid hardcoding SQL across services
- Improve maintainability and readability
- Provide a single source of truth for DB queries
"""


class SQLQueryProvider:
    """
    Centralized SQL query definitions.

    Each method returns either:
    - A SQL query string
    - A list of SQL statements
    - A mapping used during dataframe transformations

    This class contains **no business logic**.
    """

    @staticmethod
    def get_data_reset_query_list():
        """
        Returns a list of SQL statements used to reset application data.

        Used during:
        - Fresh reconciliation runs
        - Cleanup before new file ingestion

        Tables affected:
        - AP base data
        - AR base data
        - Final reconciliation result
        """
        delete_statements = [
            "TRUNCATE TABLE intercompany_ap_data",
            "TRUNCATE TABLE intercompany_ar_data",
            "TRUNCATE TABLE intercompany_recon_result"
        ]
        return delete_statements

    @staticmethod
    def get_base_tables():
        """
        Returns SQL queries to fetch base AR and AP data.

        These queries are executed at the start of the
        reconciliation process to load raw transactional data
        into pandas DataFrames.
        """
        base_tables = {
            "ap_data": "SELECT * FROM intercompany_ap_data",
            "ar_data": "SELECT * FROM intercompany_ar_data"
        }
        return base_tables

    @staticmethod
    def insert_recon_result_query():
        """
        Returns the INSERT SQL used to persist final reconciliation results.

        This query is executed using:
        - execute_multiple_non_query
        - list of dictionaries (records) generated from pandas DataFrame

        Bind variables are aligned with renamed dataframe columns.
        """
        insert_sql = """
        INSERT INTO INTERCOMPANY_RECON_RESULT (
            AR_REGION, AR_COMPANY_CODE, AR_UNIT_NAME,
            AP_REGION, AP_COMPANY_CODE, CUSTOMER_NUMBER,
            BOOKING_NUMBER, AR_REFERENCE_NUMBER, AR_DOCUMENT_DATE,
            AR_DOCUMENT_TYPE,  AR_DOCUMENT_CURRENCY,
            AR_DOCUMENT_DESCRIPTION, AR_DUE_DATE,
            AP_SUPPLIER_NUMBER, AP_REFERENCE_NUMBER, AP_DOCUMENT_TYPE,
            AP_DOCUMENT_DATE,  AP_DOCUMENT_CURRENCY,
            AP_DOCUMENT_DESCRIPTION, AP_POSTING_DATE, RECONCILIATION_STATUS,
            MESSAGE, MODULE,
            AR_DOCUMENT_AMOUNT, AP_DOCUMENT_AMOUNT,
            AR_INVOICE_YEAR
        ) VALUES (
            :AR_REGION ,:ar_company_code, :ar_unit_name,
            :ap_region, :ap_company_code, :customer_number ,
            :booking_number, :ar_reference_number, :ar_document_date,
            :ar_document_type, :ar_document_currency,
            :ar_document_description, :ar_due_date,
            :ap_supplier_number, :ap_reference_number, :ap_document_type,
            :ap_document_date,  :ap_document_currency,
            :ap_document_description, :ap_posting_date, :reconciliation_status,
            :message, :module,
            :ar_document_amount , :ap_document_amount ,:ar_invoice_year
        )
        """
        return insert_sql

    @staticmethod
    def rename_final_table_fields():
        """
        Returns a mapping of original dataframe column names
        to standardized database-friendly column names.

        Used after reconciliation logic to:
        - Normalize column names
        - Match DB insert statement placeholders
        """
        rename_field_map = {
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
            "INVOICE_DOC_AMOUNT": "ar_document_amount",
            "DOCUMENT_DESCRIPTION": "ar_document_description",
            "DUE_DATE": "ar_due_date",
            "INVOICE_YEAR": "ar_invoice_year",

            # ---------- AP ----------
            "SUPPLIER": "ap_supplier_number",
            "REFERENCE_NO": "ap_reference_number",
            "DOCUMENT_TYPE": "ap_document_type",
            "DOCUMENT_DATE": "ap_document_date",
            "DOCUMENT_CURRENCY": "ap_document_currency",
            "AMOUNT_DOC_CURRENCY": "ap_document_amount",
            "AP_COMMENT": "ap_document_description",
            "POSTING_DATE": "ap_posting_date",

            # ---------- STATUS ----------
            "status": "reconciliation_status",
            "message": "message"
        }
        return rename_field_map

    @staticmethod
    def ar_insert_sql():
        """
        Returns INSERT SQL for AR base data.

        Used during:
        - AR Excel ingestion
        - Initial AR data load into database
        """
        insert_query = """
            INSERT INTO INTERCOMPANY_AR_DATA (
                AR_REGION ,AR_TBR_CODE, AR_COCD, AR_UNIT_NAME, RECON_COMMENT,
                AP_REGION, AP_TBR_CODE, AP_COCD, CUSTOMER_NO_LOCAL_SYSTEM,
                AP_UNIT_NAME, BOOKING_NO_AR, INVOICE_REFERENCE , DOC_DATE,
                INVOICE_DOC_TYPE, INVOICE_DOC_AMOUNT, INVOICE_DOC_CURRENCY,
                DOCUMENT_DESCRIPTION, DUE_DATE, TEXT_REMARKS,
                ASSIGNMENT_VIN_SHIPMENT, REF_KEY_1, BILL_DOC_NO,
                INVOICE_YEAR, DELIVERY_NOTE
            ) VALUES (
                :AR_REGION , :AR_TBR_CODE, :AR_COCD , :AR_UNIT_NAME, :RECON_COMMENT,
                :AP_REGION, :AP_TBR_CODE, :AP_COCD, :CUSTOMER_NO_LOCAL_SYSTEM,
                :AP_UNIT_NAME, :BOOKING_NO_AR, :INVOICE_REFERENCE ,:DOC_DATE,
                :INVOICE_DOC_TYPE, :INVOICE_DOC_AMOUNT, :INVOICE_DOC_CURRENCY,
                :DOCUMENT_DESCRIPTION, :DUE_DATE, :TEXT_REMARKS,
                :ASSIGNMENT_VIN_SHIPMENT, :REF_KEY_1, :BILL_DOC_NO,
                :INVOICE_YEAR, :DELIVERY_NOTE
            )
        """
        return insert_query

    @staticmethod
    def ap_insert_sql():
        """
        Returns INSERT SQL for AP base data.

        Used during:
        - AP Excel ingestion
        - Initial AP data load into database
        """
        insert_query = """
            INSERT INTO INTERCOMPANY_AP_DATA (
                COMPANY_CODE, SUPPLIER, TRADING_PARTNER, SUPPLIER_NAME, VIN,
                DOCUMENT_TYPE, REFERENCE_NO, AP_COMMENT, DOCUMENT_DATE, POSTING_DATE,
                AMOUNT_LOCAL_CURRENCY, LOCAL_CURRENCY, AMOUNT_DOC_CURRENCY, DOCUMENT_CURRENCY,
                PROFIT_CENTER, GL_ACCOUNT, DOCUMENT_NUMBER, ASSIGNMENT,
                SPECIAL_GL_INDICATOR, OFFSETTING_ACCOUNT_1, OFFSETTING_ACCOUNT_2,
                TEXT_NOTE, NET_DUE_DATE, PAYMENT_BLOCK,
                PURCHASING_DOCUMENT, CLEARING_DOCUMENT, CLEARING_DATE
            ) VALUES (
                :COMPANY_CODE, :SUPPLIER, :TRADING_PARTNER, :SUPPLIER_NAME, :VIN,
                :DOCUMENT_TYPE, :REFERENCE_NO, :AP_COMMENT, :DOCUMENT_DATE, :POSTING_DATE,
                :AMOUNT_LOCAL_CURRENCY, :LOCAL_CURRENCY, :AMOUNT_DOC_CURRENCY, :DOCUMENT_CURRENCY,
                :PROFIT_CENTER, :GL_ACCOUNT, :DOCUMENT_NUMBER, :ASSIGNMENT,
                :SPECIAL_GL_INDICATOR, :OFFSETTING_ACCOUNT_1, :OFFSETTING_ACCOUNT_2,
                :TEXT_NOTE, :NET_DUE_DATE, :PAYMENT_BLOCK,
                :PURCHASING_DOCUMENT, :CLEARING_DOCUMENT, :CLEARING_DATE
            )
        """
        return insert_query
