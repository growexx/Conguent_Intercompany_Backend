"""
Reconciliation API routes.

This module defines HTTP endpoints related to reconciliation-based
interactions for the Intercompany data reconciliation API.
"""
from fastapi import APIRouter
from app.schemas.reconcile import ReconcileRequest
from app.services.reconciliation_service import ReconcileService
from fastapi import Request
from fastapi import BackgroundTasks, Depends,  status

# ---------------------------------------------------------
# Router initialization for reconciliation-related endpoints
# ---------------------------------------------------------

router = APIRouter()
service = ReconcileService()

@router.post("/recon",status_code=202)
async def reconcile_inquiry(
    background_tasks: BackgroundTasks
):
    """
    Intercompany Data Reconciliation API endpoint.
    """
    background_tasks.add_task(service.handle_inquiry)
    return {
        "status": "accepted",
        "message": "Reconciliation started in background"
    }


@router.get("/delete")
def delete_data():
    """
    Intercompany Data Reconciliation API endpoint.
    """
    service.data_deletion()
    return {
        "status": "accepted",
        "message": "Data deleted"
    }
