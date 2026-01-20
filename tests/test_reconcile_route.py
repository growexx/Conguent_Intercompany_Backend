from unittest.mock import patch
from fastapi import status


def test_reconcile_inquiry_accepted(client):
    """
    Test that reconciliation request is accepted
    and background task is executed.
    """

    with patch(
        "app.api.routes.reconcile.ReconcileService.handle_inquiry"
    ) as mock_handle_inquiry:

        response = client.post(
            "/api/InterCompany/v1/reconcile/recon"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": 1,
            "message": "Reconciliation started in background"
        }

        # FastAPI TestClient executes background tasks immediately
        mock_handle_inquiry.assert_called_once()


def test_delete_data_success(client):
    """
    Test that delete endpoint triggers data deletion.
    """

    with patch(
        "app.api.routes.reconcile.ReconcileService.data_deletion"
    ) as mock_delete:

        response = client.get(
            "/api/InterCompany/v1/reconcile/delete"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "accepted",
            "message": "Data deleted"
        }

        mock_delete.assert_called_once()
