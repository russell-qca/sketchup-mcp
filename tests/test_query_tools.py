"""Tests for query tools (get_model_info, list_layers, list_materials, etc.)"""

import pytest
from mcp import types
from sketchup_mcp.server import call_tool
from tests.conftest import MockResponse


class TestQueryTools:
    """Test suite for query tools."""

    @pytest.mark.asyncio
    async def test_get_model_info(
        self, mock_httpx_client, mock_sketchup_model_info
    ):
        """Test get_model_info returns model information."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/info"
        ] = MockResponse(mock_sketchup_model_info)

        # Call the tool
        result = await call_tool("get_model_info", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Test Model" in result[0].text
        assert "entity_count" in result[0].text

    @pytest.mark.asyncio
    async def test_list_layers(self, mock_httpx_client, mock_sketchup_layers):
        """Test list_layers returns all layers."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/layers"
        ] = type('MockResponse', (), {
            'json': lambda: mock_sketchup_layers,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("list_layers", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Layer0" in result[0].text
        assert "Walls" in result[0].text
        assert "Hidden" in result[0].text

    @pytest.mark.asyncio
    async def test_list_materials(self, mock_httpx_client, mock_sketchup_materials):
        """Test list_materials returns all materials."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/materials"
        ] = type('MockResponse', (), {
            'json': lambda: mock_sketchup_materials,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("list_materials", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Material1" in result[0].text
        assert "Wood" in result[0].text

    @pytest.mark.asyncio
    async def test_list_entities(self, mock_httpx_client, mock_sketchup_entities):
        """Test list_entities returns all entities."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/entities"
        ] = type('MockResponse', (), {
            'json': lambda: mock_sketchup_entities,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("list_entities", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "12345" in result[0].text
        assert "Sketchup::Face" in result[0].text
        assert "67890" in result[0].text

    @pytest.mark.asyncio
    async def test_list_entities_with_group(
        self, mock_httpx_client, mock_sketchup_entities
    ):
        """Test list_entities with group_name parameter."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/entities?group_name=TestGroup"
        ] = type('MockResponse', (), {
            'json': lambda: mock_sketchup_entities,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool with group_name
        result = await call_tool("list_entities", {"group_name": "TestGroup"})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "12345" in result[0].text

    @pytest.mark.asyncio
    async def test_list_components(self, mock_httpx_client, mock_sketchup_components):
        """Test list_components returns all component definitions."""
        # Setup mock response
        mock_httpx_client.get_responses[
            "http://localhost:8080/model/components"
        ] = type('MockResponse', (), {
            'json': lambda: mock_sketchup_components,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("list_components", {})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Chair" in result[0].text
        assert "Table" in result[0].text
