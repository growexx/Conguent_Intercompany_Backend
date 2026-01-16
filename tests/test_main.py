from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestMainApplication:
    """Tests for FastAPI application setup in main.py"""

    def test_app_metadata(self):
        assert app.title == "Conguent Intercompany Data reconciliation App"
        assert app.version == "1.0.0"

    def test_reconcile_router_registered(self):
        routes = [route.path for route in app.routes]
        assert any(
            route.startswith("/api/InterCompany/v1/reconcile")
            for route in routes
        )


    def test_upload_router_registered(self):
        routes = [route.path for route in app.routes]
        assert any(
            route.startswith("/api/InterCompany/v1/upload")
            for route in routes
        )



    def test_cors_headers_present(self):
        origin = "http://example.com"

        response = client.options(
            "/api/InterCompany/v1",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.headers.get("access-control-allow-origin") == origin
        assert "access-control-allow-methods" in response.headers


    def test_application_starts_successfully(self):
        response = client.get("/docs")

        assert response.status_code == 200
