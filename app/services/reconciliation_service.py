"""
Service module for the Intercompany Reconciliation application.

This module contains:
- Utility helpers
- Reconciliation business logic
- Database interaction orchestration
"""

from code_modules.oracle_adb_handler import OracleADBClient
from config_loader import load_adw_config
from code_modules.sql_query_loader import SQLQueryProvider
import pandas as pd
import traceback
from decimal import Decimal


def check_if_df_all_null_or_zero(df: pd.DataFrame) -> bool:
    """
    Check whether all values in the dataframe are null or zero.

    Args:
        df (pd.DataFrame): Dataframe to evaluate.

    Returns:
        bool: True if all values are null or zero, otherwise False.
    """
    return bool(((df.isna()) | (df == 0)).all().all())


class JumpToFinally(Exception):
    """Custom exception just to jump to finally"""
    pass

class ReconcileService:
    """
    Service class responsible for executing the
    Intercompany reconciliation workflow.
    """
    def __init__(self):
        """
        Initialize ChatService with LLM clients, prompt generator,
        and response extractor.
        """
        self.oracle_adb_client = OracleADBClient(load_adw_config())
        self.sql_query_provider = SQLQueryProvider()

    def data_deletion(self):
        """
        Truncate all reconciliation-related tables.

        Used before running a fresh reconciliation cycle.
        """
        delete_statements = self.sql_query_provider.get_data_reset_query_list()
        for statement in delete_statements:
            self.oracle_adb_client.execute_single_non_query(statement)
        return {
            "status": "accepted",
            "message": "Data deleted"
        }

    def _fetch_base_data(self):
        """
        Fetch AR and AP base data from Oracle DB
        and remove audit columns not required for reconciliation.
        """
        queries = self.sql_query_provider.get_base_tables()

        ar_df = self.oracle_adb_client.execute_query_df(queries["ar_data"])
        ap_df = self.oracle_adb_client.execute_query_df(queries["ap_data"])

        ar_df.drop(columns=["CREATED_AT"], inplace=True)
        ap_df.drop(columns=["CREATED_AT"], inplace=True)

        return ar_df, ap_df

    @staticmethod
    def _merge_ar_ap(ar_df, ap_df):
        """
        Perform outer join between AR and AP datasets
        using VIN / Reference number linkage.
        """
        return ar_df.merge(
            ap_df,
            how="outer",
            left_on="ASSIGNMENT_VIN_SHIPMENT",
            right_on="REFERENCE_NO",
            indicator=True,
            suffixes=("_AR", "_AP")
        )

    @staticmethod
    def _split_merge_results(merged_df):
        """
        Split merged dataframe into:
        - AR only records
        - AP only records
        - Matched AR-AP records
        """
        ar_only = merged_df[merged_df["_merge"] == "left_only"].drop(columns="_merge")
        ap_only = merged_df[merged_df["_merge"] == "right_only"].drop(columns="_merge")
        matched = merged_df[merged_df["_merge"] == "both"].drop(columns="_merge")

        return (
            ar_only.reset_index(drop=True),
            ap_only.reset_index(drop=True),
            matched.reset_index(drop=True)
        )

    @staticmethod
    def _reconcile_matches(matched_df):
        """
        Apply reconciliation rules on matched AR/AP records.

        Rules:
        - Document dates must match
        - Currency must match
        - Amounts must net to zero
        """
        recon_mask = (
            (matched_df["DOC_DATE"].dt.date == matched_df["DOCUMENT_DATE"].dt.date) &
            (matched_df["INVOICE_DOC_CURRENCY"] == matched_df["DOCUMENT_CURRENCY"]) &
            ((matched_df["INVOICE_DOC_AMOUNT"] + matched_df["AMOUNT_DOC_CURRENCY"]) == 0)
        )

        reconciled = matched_df[recon_mask].reset_index(drop=True)
        rejected = matched_df[~recon_mask].reset_index(drop=True)

        return reconciled, rejected

    @staticmethod
    def _process_ap_multiple_records(ap_multiple_df):
        """
        Handle AP records having multiple entries
        for the same reference number.

        Special handling for L8 document types.
        """
        refs_with_l8 = ap_multiple_df.loc[
            ap_multiple_df["DOCUMENT_TYPE"] == "L8", "REFERENCE_NO"
        ].unique()

        ap_with_l8_df = ap_multiple_df[
            (ap_multiple_df["REFERENCE_NO"].isin(refs_with_l8)) &
            (ap_multiple_df["DOCUMENT_TYPE"] == "L8")
        ]

        ap_without_l8_df = ap_multiple_df[
            ~ap_multiple_df["REFERENCE_NO"].isin(refs_with_l8)
        ]
        return ap_with_l8_df.reset_index(drop=True), ap_without_l8_df.reset_index(drop=True)

    @staticmethod
    def _convert_types(final_df):
        """
        Convert dataframe columns into Oracle-compatible types:
        - Dates → date
        - Amounts → Decimal
        - Strings → VARCHAR
        """
        date_cols = ['ar_document_date', 'ap_document_date', 'ap_posting_date', 'ar_due_date']
        for col in date_cols:
            final_df[col] = pd.to_datetime(final_df[col], errors="coerce").dt.date


        varchar_cols = [
            "AR_REGION", "ar_company_code", "ar_unit_name",
            "ap_region", "ap_company_code", "customer_number",
            "booking_number", "ar_reference_number", "ar_document_type", "ar_document_currency",
            "ar_document_description", "ap_supplier_number", "ap_reference_number", "ap_document_type",
            "ap_document_currency", "ap_document_description", "reconciliation_status",
            "message", "module"
        ]

        for col in varchar_cols:
            final_df[col] = final_df[col].astype("string")

        num_float_cols = ["ar_document_amount", "ap_document_amount"]
        for col in num_float_cols:
            final_df[col] = final_df[col].apply(lambda x: float(x) if pd.notna(x) else None)

        # Convert decimals
        final_df["ar_document_amount"] = final_df["ar_document_amount"].apply(lambda x: Decimal(str(x)) if pd.notna(x) else None)
        final_df["ap_document_amount"] = final_df["ap_document_amount"].apply(lambda x: Decimal(str(x)) if pd.notna(x) else None)
        final_df["ar_invoice_year"] = final_df["ar_invoice_year"].apply(lambda x: Decimal(str(x)) if pd.notna(x) else None)


        return final_df

    def handle_inquiry(self):
        """
        Main reconciliation execution pipeline.
        Orchestrates fetching, matching, reconciling,
        transforming, and persisting results.
        """
        try:
            int_ar_df , int_ap_df = self._fetch_base_data()
            if check_if_df_all_null_or_zero(int_ap_df) and check_if_df_all_null_or_zero(int_ar_df):
                print("No data found")
                return

            int_merged_df = self._merge_ar_ap(int_ar_df , int_ap_df)

            ar_without_ap ,ap_without_ar ,ar_ap_matched = self._split_merge_results(int_merged_df)

            reconciled_df ,rejected_df   = self._reconcile_matches(ar_ap_matched)

            ref_counts = ap_without_ar["REFERENCE_NO"].value_counts()
            single_ref_mask   = ap_without_ar["REFERENCE_NO"].map(ref_counts) == 1
            multiple_ref_mask = ap_without_ar["REFERENCE_NO"].map(ref_counts) > 1

            ap_single_df = ap_without_ar[single_ref_mask].reset_index(drop=True)
            ap_multiple_df = ap_without_ar[multiple_ref_mask].reset_index(drop=True)

            print(f"multiple ap records {ap_multiple_df.info()}")

            refs_with_l8 = ap_multiple_df.loc[
                ap_multiple_df["DOCUMENT_TYPE"] == "L8", "REFERENCE_NO"
            ].unique()

            ap_with_l8_df = ap_multiple_df[
                (ap_multiple_df["REFERENCE_NO"].isin(refs_with_l8)) &
                (ap_multiple_df["DOCUMENT_TYPE"] == "L8")
            ]

            ap_without_l8_df = ap_multiple_df[
                ~ap_multiple_df["REFERENCE_NO"].isin(refs_with_l8)
            ]
            print('-'*100)
            print(ap_multiple_df.shape)
            print(ap_with_l8_df.shape)
            print(ap_without_l8_df.shape)

            ap_single_df['message'] = 'Missing AR Details'
            ap_single_df['status']='Unreconciled'

            ap_with_l8_df['message'] = 'Raise : AP Approval rejected'
            ap_with_l8_df['status']= 'Reconciled'

            ap_without_l8_df['message'] = 'Aps with multiple invoice records but no L8 document, Likely error.'
            ap_without_l8_df['status']= 'UnReconciled'

            reconciled_df['message'] = 'Reconciled'
            reconciled_df['status'] = 'Reconciled'

            ar_without_ap['message'] = 'Missing AP Details'
            ar_without_ap['status'] = 'Unreconciled'

            rejected_df['message'] = 'Fields value Mismatch'
            rejected_df['status'] = 'Unreconciled'

            final_recon_df = pd.concat(
                [
                    reconciled_df,
                    ar_without_ap,
                    ap_single_df,
                    ap_with_l8_df,
                    rejected_df,
                    ap_without_l8_df
                ],
                ignore_index=True
            )
            final_recon_df["AMOUNT_DOC_CURRENCY"] = (
                final_recon_df["AMOUNT_DOC_CURRENCY"]
                .abs()
            )
            final_recon_df["INVOICE_DOC_AMOUNT"] = (
                final_recon_df["INVOICE_DOC_AMOUNT"]
                .abs()
            )

            final_recon_df = final_recon_df[[
                "AR_REGION", "AR_COCD", "AR_UNIT_NAME",
                "AP_REGION", "AP_COCD", "CUSTOMER_NO_LOCAL_SYSTEM",
                "BOOKING_NO_AR", "INVOICE_REFERENCE", "DOC_DATE",
                "INVOICE_DOC_TYPE", "INVOICE_DOC_AMOUNT", "INVOICE_DOC_CURRENCY",
                "DOCUMENT_DESCRIPTION", "DUE_DATE", "INVOICE_YEAR",
                "SUPPLIER", "REFERENCE_NO", "DOCUMENT_TYPE",
                "DOCUMENT_DATE","AMOUNT_DOC_CURRENCY", "DOCUMENT_CURRENCY",
                "AP_COMMENT", "POSTING_DATE","status", "message"
                ]
            ]
            final_recon_df["module"] = "Intercompany"
            final_recon_df = final_recon_df.rename(columns=self.sql_query_provider.rename_final_table_fields())

            final_recon_df = self._convert_types(final_recon_df)

            final_recon_df = final_recon_df[[
                    "AR_REGION" , "ar_company_code", "ar_unit_name",
                    "ap_region", "ap_company_code", 'customer_number',
                    "booking_number", "ar_reference_number", "ar_document_date",
                    "ar_document_type",  "ar_document_currency",
                    "ar_document_description", "ar_due_date",
                    "ap_supplier_number","ap_reference_number","ap_document_type",
                    "ap_document_date",  "ap_document_currency",
                    "ap_document_description", "ap_posting_date", "reconciliation_status",
                    "message", "module",
                    "ar_document_amount","ap_document_amount" , "ar_invoice_year"
                ]]


            records = final_recon_df.to_dict(orient="records")
            insert_sql = self.sql_query_provider.insert_recon_result_query()
            self.oracle_adb_client.execute_multiple_non_query(insert_sql, records)

        except Exception as e:
            traceback.print_exc()
            print(e)
        finally:
            print("Inference code is executed.")

