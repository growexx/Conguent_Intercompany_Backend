from unittest.mock import patch
from fastapi import status


def test_upload_and_process_success(client):
    """
    Test successful file upload request.
    """

    mock_response = {
        "status": "success",
        "files_processed": 2
    }

    with patch(
        "app.api.routes.upload.UploadService.upload_files",
        return_value=mock_response
    ) as mock_upload:

        payload = {
            "file_names": ["file1.xlsx", "file2.xlsx"]
        }

        response = client.post(
            "/api/InterCompany/v1/upload/upload",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_response

        mock_upload.assert_called_once_with(payload["file_names"])
