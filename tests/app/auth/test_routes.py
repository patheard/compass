"""Unit tests for authentication routes."""

from starlette.testclient import TestClient


class TestAuthRoutes:
    """Tests for authentication route endpoints."""

    def test_login_endpoint_exists(self, test_client: TestClient) -> None:
        """Test that login endpoint is accessible."""
        response = test_client.get("/auth/login", follow_redirects=False)

        # Should redirect to Google OAuth or return success
        assert response.status_code in [200, 302, 307]

    def test_logout_endpoint_exists(self, test_client: TestClient) -> None:
        """Test that logout endpoint is accessible."""
        response = test_client.get("/auth/logout", follow_redirects=False)

        # Should redirect after logout
        assert response.status_code in [200, 302, 303, 307]
