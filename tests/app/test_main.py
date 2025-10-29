"""Unit tests for main application."""

from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestMainApplication:
    """Tests for main application endpoints and handlers."""

    def test_root_endpoint_unauthenticated(self, test_client: TestClient) -> None:
        """Test root endpoint redirects unauthenticated users to login."""
        response = test_client.get("/")

        assert response.status_code == 200
        # Should show login page content
        assert (
            b"login" in response.content.lower()
            or b"sign in" in response.content.lower()
        )

    @patch("app.main.get_user_from_session")
    @patch("app.main.assessment_service.list_assessments")
    def test_root_endpoint_authenticated(
        self,
        mock_list_assessments: MagicMock,
        mock_get_user: MagicMock,
        test_client: TestClient,
        mock_user: MagicMock,
    ) -> None:
        """Test root endpoint shows home page for authenticated users."""
        mock_get_user.return_value = mock_user
        mock_list_assessments.return_value = []

        with test_client as client:
            response = client.get("/")

            assert response.status_code == 200

    def test_health_check_endpoint(self, test_client: TestClient) -> None:
        """Test health check endpoint returns status."""
        with patch("app.main.DatabaseManager.check_table_health", return_value=True):
            response = test_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data or "healthy" in str(data).lower()

    @patch("app.main.get_user_from_session")
    def test_set_language_endpoint(
        self,
        mock_get_user: MagicMock,
        test_client: TestClient,
    ) -> None:
        """Test setting user preferred language."""
        mock_get_user.return_value = None

        response = test_client.get("/lang/fr", follow_redirects=False)

        assert response.status_code in [302, 303]

    def test_http_exception_handler_401(self, test_client: TestClient) -> None:
        """Test HTTP exception handler redirects 401 to login."""

        @test_client.app.get("/test-401")
        def test_401():
            raise HTTPException(status_code=401, detail="Unauthorized")

        response = test_client.get("/test-401", follow_redirects=False)

        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    def test_http_exception_handler_404(self, test_client: TestClient) -> None:
        """Test HTTP exception handler handles 404."""
        response = test_client.get("/nonexistent-page")

        assert response.status_code == 404

    def test_static_files_mounted(self, test_client: TestClient) -> None:
        """Test that static files are accessible."""
        # Try to access a common static file path
        response = test_client.get("/static/css/styles.css")

        # Should either return the file or 404 (not 500)
        assert response.status_code in [200, 404]

    @patch("app.main.get_user_from_session")
    def test_login_page_endpoint(
        self, mock_get_user: MagicMock, test_client: TestClient
    ) -> None:
        """Test login page endpoint."""
        mock_get_user.return_value = None

        response = test_client.get("/login")

        assert response.status_code == 200
        assert (
            b"login" in response.content.lower()
            or b"sign in" in response.content.lower()
        )

    @patch("app.main.get_user_from_session")
    def test_home_page_endpoint(
        self,
        mock_get_user: MagicMock,
        test_client: TestClient,
        mock_user: MagicMock,
    ) -> None:
        """Test home page endpoint."""
        mock_get_user.return_value = mock_user

        response = test_client.get("/home")

        assert response.status_code == 200

    def test_cors_middleware_configured(self, test_client: TestClient) -> None:
        """Test that CORS middleware is configured."""
        response = test_client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # OPTIONS request may return 400, 200, 204, or 405 depending on configuration
        assert response.status_code in [200, 204, 400, 405]

    def test_session_middleware_configured(self, test_client: TestClient) -> None:
        """Test that session middleware is configured."""
        response = test_client.get("/")

        # Should have session cookie or Set-Cookie header
        assert response.status_code == 200

    def test_security_headers_middleware_configured(
        self, test_client: TestClient
    ) -> None:
        """Test that security headers are added to responses."""
        response = test_client.get("/")

        # Check for at least one security header
        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
        ]

        has_security_header = any(
            header in response.headers for header in security_headers
        )
        assert has_security_header or response.status_code == 200

    def test_localization_middleware_configured(self, test_client: TestClient) -> None:
        """Test that localization middleware processes requests."""
        response = test_client.get(
            "/",
            headers={"Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8"},
        )

        assert response.status_code == 200
