"""
Schema for upload request for gathering reconciliation data
"""
from typing import List
from pydantic import BaseModel

class FilePushRequest(BaseModel):
    """
    File upload  Request only requires file_name and chat_id
    """
    file_names:List[str]
