"""
Upload service module for handling user-provided data files.

This module is responsible for:
- Fetching uploaded files from OCI Object Storage
- Reading CSV or Excel files into Pandas DataFrames
- Validating file structure against an expected schema
- Transforming and cleaning data where required
- Inserting validated data into Oracle Autonomous Database

It acts as the backend service layer for file-upload workflows
"""
from typing import List
from code_modules.oracle_adb_handler import OracleADBClient
from code_modules.oci_object_storage import OCIObjectStorageClient
from code_modules.sql_query_loader import SQLQueryProvider

from config_loader import load_adw_config
from pathlib import Path
import pandas as pd
import traceback
import os
import json
import numpy as np
from datetime import datetime

DATE_FORMAT = "DD/MM/YYYY"

def validate_columns(df,schema):
    """
    Validate that all required columns are present in the DataFrame,
    and print a warning for any extra columns.
    """
    missing = set(schema.keys()) - set(df.columns)
    extra = set(df.columns) - set(schema.keys())

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if extra:
        print(f"⚠️ Extra columns ignored: {extra}")

def preprocess_ar_df(df):
    """
    Preprocess Ar df so that we can insert it in  Oracle ADW
    """
    # Dates
    df["DOC_DATE"] = pd.to_datetime(df["DOC_DATE"], errors="coerce")
    df["DUE_DATE"] = pd.to_datetime(df["DUE_DATE"], errors="coerce")

    # Numeric → string (Oracle columns are VARCHAR2)
    varchar_numeric_cols = [
        "AR_TBR_CODE", "AR_COCD", "AP_TBR_CODE", "AP_COCD",
        "BOOKING_NO_AR","INVOICE_REFERENCE","REF_KEY_1", "BILL_DOC_NO", "DELIVERY_NOTE"
    ]

    for col in varchar_numeric_cols:
        df[col] = df[col].astype("string")

    # Invoice year (NUMBER(4,0))
    df["INVOICE_YEAR"] = pd.to_numeric(df["INVOICE_YEAR"], errors="coerce")

    # Replace NaN / NaT → None (Oracle NULL)
    df = df.where(pd.notnull(df), None)

    return df

def preprocess_ap_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess AP df so that we can insert it in  Oracle ADW
    """
    df = df.copy()

    # ---- DATE columns ----
    date_cols = [
        "DOCUMENT_DATE",
        "POSTING_DATE",
        "NET_DUE_DATE",
        "CLEARING_DATE",
    ]

    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    # ---- NUMBER columns ----
    amount_cols = [
        "AMOUNT_LOCAL_CURRENCY",
        "AMOUNT_DOC_CURRENCY",
    ]

    for col in amount_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("", np.nan)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---- VARCHAR numeric-looking columns ----
    varchar_cols = [
        "COMPANY_CODE", "SUPPLIER", "TRADING_PARTNER",
        'VIN','DOCUMENT_TYPE', 'REFERENCE_NO', 'AP_COMMENT',
        "PROFIT_CENTER", "GL_ACCOUNT", "DOCUMENT_NUMBER",
        "ASSIGNMENT", "OFFSETTING_ACCOUNT_1", "OFFSETTING_ACCOUNT_2",
        "PURCHASING_DOCUMENT", "CLEARING_DOCUMENT","TEXT_NOTE",
        "PAYMENT_BLOCK"
    ]

    for col in varchar_cols:
        df[col] = df[col].astype("string")

    # ---- Oracle NULL handling ----
    df = df.where(pd.notnull(df), None)

    return df


AR_COLUMNS = {
    "A/R Region": "AR_REGION",
    "A/R TBR Code": "AR_TBR_CODE",
    "AR CoCd": "AR_COCD",
    "A/R Unit Name": "AR_UNIT_NAME",
    "Comment": "RECON_COMMENT",
    "A/P Region": "AP_REGION",
    "A/P TBR Code": "AP_TBR_CODE",
    "AP CoCd": "AP_COCD",
    "Customer No# (Local System)": "CUSTOMER_NO_LOCAL_SYSTEM",
    "A/P Unit Name": "AP_UNIT_NAME",
    "Booking No# A/R": "BOOKING_NO_AR",
    "Invoice Reference / Description": "INVOICE_REFERENCE",
    "Doc Date (mm/dd/yyyy)": "DOC_DATE",
    "Invoice / Doc Type": "INVOICE_DOC_TYPE",
    "Invoice / Doc Amount": "INVOICE_DOC_AMOUNT",
    "Invoice / Doc Currency": "INVOICE_DOC_CURRENCY",
    "Document Description": "DOCUMENT_DESCRIPTION",
    "Due Date": "DUE_DATE",
    "Text / Remarks": "TEXT_REMARKS",
    "Assignment / VIN / Shipment #": "ASSIGNMENT_VIN_SHIPMENT",
    "Ref# Key 1": "REF_KEY_1",
    "Bill#Doc#": "BILL_DOC_NO",
    "Invoice Year": "INVOICE_YEAR",
    "Delivery Note": "DELIVERY_NOTE",
}

AP_COLUMNS = {
    "Company Code": "COMPANY_CODE",
    "Supplier": "SUPPLIER",
    "Trading partner": "TRADING_PARTNER",
    "Name 1": "SUPPLIER_NAME",
    "VIN": "VIN",
    "Document Type": "DOCUMENT_TYPE",
    "Reference": "REFERENCE_NO",
    "Comment": "AP_COMMENT",
    "Document Date": "DOCUMENT_DATE",
    "Posting Date": "POSTING_DATE",
    "Amount in local currency": "AMOUNT_LOCAL_CURRENCY",
    "Local Currency": "LOCAL_CURRENCY",
    "Amount in doc. curr.": "AMOUNT_DOC_CURRENCY",
    "Document currency": "DOCUMENT_CURRENCY",
    "Profit Center": "PROFIT_CENTER",
    "G/L Account": "GL_ACCOUNT",
    "Document Number": "DOCUMENT_NUMBER",
    "Assignment": "ASSIGNMENT",
    "Special G/L ind.": "SPECIAL_GL_INDICATOR",
    "Offsetting acct no.": "OFFSETTING_ACCOUNT_1",
    "Offsetting acct no.2": "OFFSETTING_ACCOUNT_2",
    "Text": "TEXT_NOTE",
    "Net due date": "NET_DUE_DATE",
    "Payment Block": "PAYMENT_BLOCK",
    "Purchasing Document": "PURCHASING_DOCUMENT",
    "Clearing Document": "CLEARING_DOCUMENT",
    "Clearing date": "CLEARING_DATE",
}

class UploadService:
    """
    Service class responsible for validating and uploading user data files.

    The UploadService handles the complete lifecycle of an uploaded file:
    - Downloads the file from OCI Object Storage
    - Parses the file into a DataFrame
    - Validates schema consistency
    - Loads data into Oracle Autonomous Database
    - Returns structured success or failure responses

    This class is designed to be stateless and safe for use
    within FastAPI request handlers.
    """

    def __init__(self):
        self.oracle_adb_client = OracleADBClient(config=load_adw_config())
        self.oracle_bucket_client = OCIObjectStorageClient()
        self.sql_query_provider = SQLQueryProvider()


    @staticmethod
    def file_2_df(file_name):
        """
        Convert a CSV or Excel file into a Pandas DataFrame.

        The file format is determined based on the file extension.
        Supported formats:
        - .csv
        - .xlsx

        Args:
            file_name (str): Absolute or relative path to the input file.

        Returns:
            pd.DataFrame: Parsed dataframe containing file data.

        Raises:
            ValueError: If the file format is unsupported.
        """
        if file_name.endswith(".csv"):
            input_df = pd.read_csv(file_name)
        elif file_name.endswith(".xlsx"):
            input_df = pd.read_excel(file_name)
        return input_df

    def file_upload(self, file_name:str):
        try:
            print(f"file names are 1) ap_file {file_name}")
            schema = []
            is_ar_file = False
            if "_ar_" in file_name.lower():
                is_ar_file = True
                schema =    AR_COLUMNS
                insert_query = self.sql_query_provider.ar_insert_sql()

            elif "_ap_" in file_name.lower():
                is_ar_file = False
                schema = AP_COLUMNS
                insert_query = self.sql_query_provider.ap_insert_sql()

            else:
                return {
                    "status": 0,
                    "error": f"Invalid file name {file_name}",
                }
            df = self.file_2_df(file_name)

            validate_columns(df,schema)
            df = df.rename(columns=schema)
            if is_ar_file:
                df = preprocess_ar_df(df)
            else:
                df = preprocess_ap_df(df)
            records = df.to_dict(orient="records")
            self.oracle_adb_client.execute_multiple_non_query(insert_query, records)
            return {
                "status": 1,
                "message": f"File uploaded successfully and data pushed to db"
            }
        except Exception as e:
            print(f"Error is {e}")
            print(traceback.print_exc())
            return {
                "status": 0,
                "message": f"File upload failed"
            }

    def upload_files(self, file_names: List[str]):
        """
        Validate and upload a user-provided data file into Oracle ADB.

        This method performs the following steps:
        1. Downloads the file from OCI Object Storage
        2. Converts the file into a Pandas DataFrame
        3. Validates the dataframe schema against the expected structure
        4. Cleans and transforms data where required
        5. Inserts records into the property_sales_summary table
        6. Returns a structured success or failure response

        Args:
            chat_id (str): Chat session identifier associated with the upload.
            file_name (str): Object storage path or filename of the uploaded file.

        Returns:
            dict: Response dictionary containing:
                - status (int): 1 for success, 0 for failure
                - message (str): Success or failure message
                - error (str, optional): Detailed error in case of schema mismatch
        """
        try:
            for file_name in file_names:
                file_name = self.oracle_bucket_client.get_file_from_bucket(file_name)
                self.file_upload(file_name)
                os.remove(file_name)
            return {
                "status": 1,
                "message": f"Files uploaded successfully"
            }
        except Exception as e:
            print(f"Error is {e}")
            print(traceback.print_exc())
            return {
                "status": 0,
                "message": f"File upload failed"
            }
