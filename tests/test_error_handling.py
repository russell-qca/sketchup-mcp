"""Tests for error handling in the MCP server."""

import pytest
import httpx
from unittest.mock import Mock
from sketchup_mcp.server import call_tool


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_connection_error(self, monkeypatch):
        """Test handling of connection errors when SketchUp is not running."""

        async def mock_client_context(*args, **kwargs):
            class MockClient:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def get(self, *args, **kwargs):
                    raise httpx.ConnectError("Connection refused")

            return MockClient()

        monkeypatch.setattr("httpx.AsyncClient", mock_client_context)

        # Call the tool - should get a RuntimeError
        result = await call_tool("get_model_info", {})

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Cannot connect to SketchUp" in result[0].text

    @pytest.mark.asyncio
    async def test_timeout_error(self, monkeypatch):
        """Test handling of timeout errors."""

        async def mock_client_context(*args, **kwargs):
            class MockClient:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def get(self, *args, **kwargs):
                    raise httpx.TimeoutException("Request timed out")

            return MockClient()

        monkeypatch.setattr("httpx.AsyncClient", mock_client_context)

        # Call the tool
        result = await call_tool("get_model_info", {})

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "timed out" in result[0].text

    @pytest.mark.asyncio
    async def test_http_status_error(self, monkeypatch):
        """Test handling of HTTP status errors (4xx, 5xx)."""

        async def mock_client_context(*args, **kwargs):
            class MockResponse:
                status_code = 500
                text = "Internal server error"

                def raise_for_status(self):
                    raise httpx.HTTPStatusError(
                        "500 Internal Server Error",
                        request=Mock(),
                        response=self
                    )

            class MockClient:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def get(self, *args, **kwargs):
                    return MockResponse()

            return MockClient()

        monkeypatch.setattr("httpx.AsyncClient", mock_client_context)

        # Call the tool
        result = await call_tool("get_model_info", {})

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "500" in result[0].text

    @pytest.mark.asyncio
    async def test_sketchup_error_in_response(self, mock_httpx_client):
        """Test handling of error field in SketchUp response."""
        # Setup mock response with error field
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/face"
        ] = type('MockResponse', (), {
            'json': lambda: {"error": "Need at least 3 points"},
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool with invalid data
        result = await call_tool("create_face", {
            "points": [[0, 0, 0], [10, 0, 0]]  # Only 2 points
        })

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "SketchUp error" in result[0].text
        assert "at least 3 points" in result[0].text

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, monkeypatch):
        """Test handling of invalid JSON in response."""

        async def mock_client_context(*args, **kwargs):
            class MockResponse:
                status_code = 200
                text = "Not valid JSON"

                def json(self):
                    raise ValueError("Invalid JSON")

                def raise_for_status(self):
                    pass

            class MockClient:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def get(self, *args, **kwargs):
                    return MockResponse()

            return MockClient()

        monkeypatch.setattr("httpx.AsyncClient", mock_client_context)

        # Call the tool
        result = await call_tool("get_model_info", {})

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Invalid JSON" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self, mock_httpx_client):
        """Test handling of unknown tool name."""
        # Call with non-existent tool
        result = await call_tool("nonexistent_tool", {})

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_entity_not_found_error(self, mock_httpx_client):
        """Test handling of entity not found errors."""
        # Setup mock response with entity not found error
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/move"
        ] = type('MockResponse', (), {
            'json': lambda: {"error": "Entity not found: 99999"},
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool with non-existent entity
        result = await call_tool("move_entity", {
            "entity_id": 99999,
            "vector": [10, 0, 0]
        })

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Entity not found" in result[0].text

    @pytest.mark.asyncio
    async def test_ruby_execution_error(self, mock_httpx_client):
        """Test handling of Ruby execution errors."""
        # Setup mock response with Ruby error
        mock_httpx_client.post_responses[
            "http://localhost:8080/ruby/execute"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "error": "undefined method `foo' for nil:NilClass",
                "backtrace": [
                    "(eval):1:in `<main>'",
                    "sketchup_mcp_server.rb:203:in `eval'",
                    "sketchup_mcp_server.rb:203:in `handle_execute_ruby'"
                ]
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool with bad Ruby code
        result = await call_tool("execute_ruby", {
            "code": "nil.foo"
        })

        # Verify error message
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Ruby error" in result[0].text
        assert "undefined method" in result[0].text
