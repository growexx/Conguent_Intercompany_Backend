"""
Upload API routes.

This module defines endpoints responsible for handling file upload
requests associated with chat sessions. It acts as a controller layer
that validates incoming requests and delegates file-processing logic
to the UploadService.
"""
from fastapi import APIRouter
from app.schemas.upload import FilePushRequest
from app.services.upload_service import UploadService
from fastapi import Request

# ---------------------------------------------------------
# Router initialization for upload-related endpoints
# ---------------------------------------------------------
router = APIRouter()
service = UploadService()


# ---------------------------------------------------------
# Service instance responsible for upload business logic
# ---------------------------------------------------------
@router.post("/upload")
def upload_and_process(
    request: FilePushRequest,
):
    """
    Upload and process a file .

    This endpoint receives file uploaded by the user
    and delegates the actual upload and processing logic to the
    UploadService. The route itself remains lightweight and does not
    contain any business rules.

    Args:
        request (FilePushRequest): Validated request body containing
            chat_id and file_name.
        req (Request): FastAPI request object (reserved for future
            extensions such as accessing app state or headers).

    Returns:
        dict: A structured response returned by UploadService,
            typically containing upload status and file details.
    """
    return service.upload_files(
        request.file_names,
    )
