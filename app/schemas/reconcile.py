"""
Schema for chat inquiry request
"""
from pydantic import BaseModel

class ReconcileRequest(BaseModel):
    """
    Chat Inquiry Request only requires user input and Chat id, We are fixing same format
    """
    ap_file:str
    ar_file:str

