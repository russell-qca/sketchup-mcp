"""Basic smoke tests for the SketchUp MCP server."""

import pytest
from sketchup_mcp.server import call_tool
from tests.conftest import MockResponse


class TestBasicFunctionality:
    """Basic tests to verify the test infrastructure works."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Test that calling an unknown tool returns an error."""
        result = await call_tool("nonexistent_tool", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_get_model_info_with_mock(
        self, mock_httpx_client
    ):
        """Test get_model_info with mocked HTTP response."""
        # Setup mock response
        mock_data = {
            "name": "Test Model",
            "entity_count": 10,
            "layer_count": 2
        }
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/info"
        ] = MockResponse(mock_data)

        # Call the tool
        result = await call_tool("get_model_info", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Test Model" in result[0].text
        assert "10" in result[0].text

    @pytest.mark.asyncio
    async def test_create_box_with_mock(
        self, mock_httpx_client
    ):
        """Test create_box with mocked HTTP response."""
        # Setup mock response
        mock_data = {
            "status": "created",
            "width": 10.0,
            "depth": 5.0,
            "height": 3.0
        }
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/box"
        ] = MockResponse(mock_data)

        # Call the tool
        result = await call_tool("create_box", {
            "width": 10.0,
            "depth": 5.0,
            "height": 3.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "created" in result[0].text
        assert "10.0" in result[0].text

    @pytest.mark.asyncio
    async def test_move_entity_with_mock(
        self, mock_httpx_client
    ):
        """Test move_entity with mocked HTTP response."""
        # Setup mock response
        mock_data = {
            "status": "moved",
            "entity_id": 12345,
            "vector": {"x": 10, "y": 0, "z": 5}
        }
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/move"
        ] = MockResponse(mock_data)

        # Call the tool
        result = await call_tool("move_entity", {
            "entity_id": 12345,
            "vector": [10, 0, 5]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "moved" in result[0].text
        assert "12345" in result[0].text

    @pytest.mark.asyncio
    async def test_sketchup_error_handling(
        self, mock_httpx_client
    ):
        """Test that SketchUp errors in responses are handled properly."""
        # Setup mock response with error
        mock_data = {"error": "Entity not found: 99999"}
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/move"
        ] = MockResponse(mock_data)

        # Call the tool
        result = await call_tool("move_entity", {
            "entity_id": 99999,
            "vector": [10, 0, 0]
        })

        # Verify error is reported
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error:" in result[0].text
        assert "Entity not found" in result[0].text
