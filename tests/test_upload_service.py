import pytest
import pandas as pd
from app.services.upload_service import validate_columns

def test_validate_columns_success():
    df = pd.DataFrame(columns=["A", "B"])
    schema = {"A": "a", "B": "b"}

    # should not raise
    validate_columns(df, schema)


def test_validate_columns_missing_columns():
    df = pd.DataFrame(columns=["A"])
    schema = {"A": "a", "B": "b"}

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_columns(df, schema)


from app.services.upload_service import preprocess_ar_df

def test_preprocess_ar_df_basic():
    df = pd.DataFrame({
        "DOC_DATE": ["2024-01-01"],
        "DUE_DATE": ["2024-01-10"],
        "AR_TBR_CODE": [123],
        "AR_COCD": [1000],
        "AP_TBR_CODE": [2000],
        "AP_COCD": [3000],
        "BOOKING_NO_AR": [111],
        "INVOICE_REFERENCE": [222],
        "REF_KEY_1": [333],
        "BILL_DOC_NO": [444],
        "DELIVERY_NOTE": [555],
        "INVOICE_YEAR": ["2024"],
    })

    result = preprocess_ar_df(df)

    assert pd.api.types.is_datetime64_any_dtype(result["DOC_DATE"])
    assert result["AR_COCD"].dtype.name == "string"
    assert result["INVOICE_YEAR"].iloc[0] == 2024


from app.services.upload_service import preprocess_ap_df

def test_preprocess_ap_df_basic():
    df = pd.DataFrame({
        "DOCUMENT_DATE": ["01/01/2024"],
        "POSTING_DATE": ["02/01/2024"],
        "NET_DUE_DATE": ["03/01/2024"],
        "CLEARING_DATE": ["04/01/2024"],
        "AMOUNT_LOCAL_CURRENCY": ["1,000"],
        "AMOUNT_DOC_CURRENCY": ["2000"],
        "COMPANY_CODE": ["1000"],
        "SUPPLIER": ["SUP1"],
        "TRADING_PARTNER": ["TP1"],   # 🔑 REQUIRED
        "REFERENCE_NO": ["REF1"],
        "DOCUMENT_TYPE": ["KR"],
        "AP_COMMENT": ["ok"],
        "PAYMENT_BLOCK": ["A"],
        "VIN":["12345"],
        "PROFIT_CENTER": ["PC1"],
        "GL_ACCOUNT": ["GL1"],
        "DOCUMENT_NUMBER": ["DOC1"],
        "ASSIGNMENT": ["ASS1"],
        "OFFSETTING_ACCOUNT_1": ["OFF1"],
        "OFFSETTING_ACCOUNT_2": ["OFF2"],
        "PURCHASING_DOCUMENT": ["PD1"],
        "CLEARING_DOCUMENT": ["CD1"],
        "TEXT_NOTE": ["TEXT"],
    })

    result = preprocess_ap_df(df)

    assert result["AMOUNT_LOCAL_CURRENCY"].iloc[0] == 1000
    assert result["COMPANY_CODE"].dtype.name == "string"


from app.services.upload_service import UploadService

def test_file_2_df_csv(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text("a,b\n1,2")

    df = UploadService.file_2_df(str(file))

    assert df.shape == (1, 2)


def test_file_2_df_excel(tmp_path):
    file = tmp_path / "test.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(file, index=False)

    df = UploadService.file_2_df(str(file))

    assert "a" in df.columns


from unittest.mock import MagicMock
from app.services.upload_service import UploadService

@pytest.fixture
def upload_service(monkeypatch):
    service = UploadService()
    service.oracle_adb_client = MagicMock()
    service.oracle_bucket_client = MagicMock()
    service.sql_query_provider = MagicMock()
    return service


def test_file_upload_ar_success(upload_service, monkeypatch):
    df = pd.DataFrame({
        "A/R Region": ["NA"],
        "A/R Unit Name": ["UNIT1"],
        "AR CoCd": ["1000"],
        "A/R TBR Code": ["TB1"],
        "A/P Region": ["AP1"],
        "A/P Unit Name": ["APUNIT"],
        "AP CoCd": ["2000"],
        "A/P TBR Code": ["TB2"],
        "Customer No# (Local System)": ["CUST1"],
        "Invoice / Doc Type": ["DR"],
        "Invoice Reference / Description": ["INV1"],
        "Invoice / Doc Amount": [100],
        "Invoice / Doc Currency": ["USD"],
        "Doc Date (mm/dd/yyyy)": ["2024-01-01"],
        "Due Date": ["2024-01-10"],
        "Assignment / VIN / Shipment #": ["ASN1"],
        "Booking No# A/R": ["B1"],
        "Bill#Doc#": ["BD1"],
        "Delivery Note": ["DN1"],
        "Ref# Key 1": ["REF1"],
        "Document Description": ["DESC"],
        "Text / Remarks": ["OK"],
        "Comment": ["NONE"],
        "Invoice Year": [2024],
    })

    monkeypatch.setattr(upload_service, "file_2_df", lambda _: df)
    upload_service.sql_query_provider.ar_insert_sql.return_value = "AR_INSERT"

    result = upload_service.file_upload("test_ar_file.xlsx")

    upload_service.oracle_adb_client.execute_multiple_non_query.assert_called_once()
    assert result["status"] == 1


def test_file_upload_ap_success(upload_service, monkeypatch):
    df = pd.DataFrame({
        "Company Code": ["1000"],
        "Supplier": ["SUP1"],
        "Trading partner": ["TP1"],
        "Name 1": ["Supplier Name"],
        "VIN": ["VIN1"],
        "Document Type": ["KR"],
        "Reference": ["REF1"],
        "Comment": ["OK"],
        "Document Date": ["01/01/2024"],
        "Posting Date": ["02/01/2024"],
        "Amount in local currency": ["1000"],
        "Local Currency": ["USD"],
        "Amount in doc. curr.": ["1000"],
        "Document currency": ["USD"],
        "Profit Center": ["PC1"],
        "G/L Account": ["GL1"],
        "Document Number": ["DOC1"],
        "Assignment": ["ASG1"],
        "Special G/L ind.": ["S"],
        "Offsetting acct no.": ["OFF1"],
        "Offsetting acct no.2": ["OFF2"],
        "Text": ["TEXT"],
        "Net due date": ["03/01/2024"],
        "Payment Block": ["A"],
        "Purchasing Document": ["PO1"],
        "Clearing date": ["04/01/2024"],
        "Clearing Document": ["CD1"],
    })

    monkeypatch.setattr(upload_service, "file_2_df", lambda _: df)
    upload_service.sql_query_provider.ap_insert_sql.return_value = "AP_INSERT"

    result = upload_service.file_upload("test_ap_file.xlsx")

    upload_service.oracle_adb_client.execute_multiple_non_query.assert_called_once()
    assert result["status"] == 1


def test_file_upload_invalid_filename(upload_service):
    result = upload_service.file_upload("random_file.xlsx")

    assert result["status"] == 0
    assert "Invalid file name" in result["error"]

def test_file_upload_exception(upload_service, monkeypatch):
    monkeypatch.setattr(upload_service, "file_2_df", lambda _: 1 / 0)

    result = upload_service.file_upload("test_ar_file.xlsx")

    upload_service.oracle_adb_client.execute_multiple_non_query.assert_not_called()
    assert result["status"] == 0

def test_upload_files_success(upload_service, monkeypatch):
    upload_service.file_upload = MagicMock(return_value={"status": 1})
    upload_service.oracle_bucket_client.get_file_from_bucket = MagicMock()
    monkeypatch.setattr("os.remove", MagicMock())

    result = upload_service.upload_files(["file1.xlsx", "file2.xlsx"])

    assert upload_service.file_upload.call_count == 2
    assert result["status"] == 1


def test_upload_files_exception(upload_service):
    upload_service.oracle_bucket_client.get_file_from_bucket.side_effect = Exception("OCI down")

    result = upload_service.upload_files(["file1.xlsx"])

    assert result["status"] == 0


import pandas as pd
import pytest

from app.services.upload_service import validate_columns


def test_validate_columns_with_extra_columns(capsys):
    schema = {
        "COL_A": "string",
        "COL_B": "int",
    }

    df = pd.DataFrame({
        "COL_A": ["a"],
        "COL_B": [1],
        "EXTRA_COL": ["ignore me"],  # 👈 extra column
    })

    # Should NOT raise
    validate_columns(df, schema)

    # Capture printed output
    captured = capsys.readouterr()

    assert "Extra columns ignored" in captured.out
    assert "EXTRA_COL" in captured.out
