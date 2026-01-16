"""
Application entry point for the Intercompany data reconciliation API.

This module initializes the FastAPI application, configures global
middleware such as CORS, sets up shared application state, and
registers all API route modules.
"""
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import reconcile,upload
from fastapi import FastAPI, BackgroundTasks, Depends,  status

# ---------------------------------------------------------
# Create FastAPI application instance
# ---------------------------------------------------------

app = FastAPI(title="Conguent Intercompany Data reconciliation App",version="1.0.0")


# ---------------------------------------------------------
# Configure CORS middleware
# Allows cross-origin requests for frontend integration
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Register API routers
# ---------------------------------------------------------
app.include_router(reconcile.router, prefix="/api/InterCompany/v1/reconcile", tags=["reconcile"])
app.include_router(upload.router, prefix="/api/InterCompany/v1/upload", tags=["upload"])

