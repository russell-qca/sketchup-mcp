"""Tests for transformation tools (move, rotate, scale)."""

import pytest
from sketchup_mcp.server import call_tool


class TestTransformations:
    """Test suite for transformation tools."""

    @pytest.mark.asyncio
    async def test_move_entity(
        self, mock_httpx_client, mock_move_entity_response
    ):
        """Test move_entity translates an entity by a vector."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/move"
        ] = type('MockResponse', (), {
            'json': lambda: mock_move_entity_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

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
        assert "10" in result[0].text

    @pytest.mark.asyncio
    async def test_rotate_entity(
        self, mock_httpx_client, mock_rotate_entity_response
    ):
        """Test rotate_entity rotates an entity around an axis."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/rotate"
        ] = type('MockResponse', (), {
            'json': lambda: mock_rotate_entity_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("rotate_entity", {
            "entity_id": 12345,
            "axis_point": [0, 0, 0],
            "axis_vector": [0, 0, 1],
            "angle": 45.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "rotated" in result[0].text
        assert "12345" in result[0].text
        assert "45" in result[0].text

    @pytest.mark.asyncio
    async def test_scale_entity_uniform(
        self, mock_httpx_client, mock_scale_entity_response
    ):
        """Test scale_entity with uniform scaling."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/scale"
        ] = type('MockResponse', (), {
            'json': lambda: mock_scale_entity_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("scale_entity", {
            "entity_id": 12345,
            "scale": 2.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "scaled" in result[0].text
        assert "12345" in result[0].text
        assert "2.0" in result[0].text

    @pytest.mark.asyncio
    async def test_scale_entity_non_uniform(self, mock_httpx_client):
        """Test scale_entity with non-uniform scaling."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/scale"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "status": "scaled",
                "entity_id": 12345,
                "scale": {"x": 2.0, "y": 1.5, "z": 3.0}
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("scale_entity", {
            "entity_id": 12345,
            "scale": [2.0, 1.5, 3.0]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "scaled" in result[0].text
        assert "12345" in result[0].text

    @pytest.mark.asyncio
    async def test_scale_entity_with_origin(self, mock_httpx_client):
        """Test scale_entity with custom origin point."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/transform/scale"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "status": "scaled",
                "entity_id": 12345,
                "scale": {"uniform": 2.0}
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("scale_entity", {
            "entity_id": 12345,
            "scale": 2.0,
            "origin": [10, 10, 0]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "scaled" in result[0].text
