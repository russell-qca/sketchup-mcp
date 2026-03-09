"""Tests for geometry creation tools."""

import pytest
from sketchup_mcp.server import call_tool


class TestBasicGeometry:
    """Test suite for basic geometry tools."""

    @pytest.mark.asyncio
    async def test_create_face(self, mock_httpx_client, mock_create_face_response):
        """Test create_face creates a polygon."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/face"
        ] = type('MockResponse', (), {
            'json': lambda: mock_create_face_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_face", {
            "points": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "99999" in result[0].text
        assert "Face" in result[0].text

    @pytest.mark.asyncio
    async def test_create_edge(self, mock_httpx_client):
        """Test create_edge creates a line segment."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/edge"
        ] = type('MockResponse', (), {
            'json': lambda: {"id": 88888, "type": "Edge", "length": 10.0},
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_edge", {
            "start": [0, 0, 0],
            "end": [10, 0, 0]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "88888" in result[0].text
        assert "Edge" in result[0].text

    @pytest.mark.asyncio
    async def test_create_group(self, mock_httpx_client):
        """Test create_group creates a named group."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/group"
        ] = type('MockResponse', (), {
            'json': lambda: {"id": 77777, "name": "TestGroup"},
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_group", {"name": "TestGroup"})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "77777" in result[0].text
        assert "TestGroup" in result[0].text

    @pytest.mark.asyncio
    async def test_create_box(self, mock_httpx_client, mock_create_box_response):
        """Test create_box creates a rectangular prism."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/box"
        ] = type('MockResponse', (), {
            'json': lambda: mock_create_box_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_box", {
            "width": 10.0,
            "depth": 10.0,
            "height": 5.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "created" in result[0].text
        assert "10.0" in result[0].text


class TestAdvancedGeometry:
    """Test suite for advanced geometry tools."""

    @pytest.mark.asyncio
    async def test_create_circle(
        self, mock_httpx_client, mock_create_circle_response
    ):
        """Test create_circle creates a circle."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/circle"
        ] = type('MockResponse', (), {
            'json': lambda: mock_create_circle_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_circle", {"radius": 12.0})

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "created" in result[0].text
        assert "12.0" in result[0].text
        assert "24" in result[0].text  # edge_count

    @pytest.mark.asyncio
    async def test_create_arc(self, mock_httpx_client):
        """Test create_arc creates an arc."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/arc"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "status": "created",
                "edge_count": 12,
                "center": {"x": 0, "y": 0, "z": 0},
                "radius": 10.0,
                "start_angle": 0.0,
                "end_angle": 180.0
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_arc", {
            "radius": 10.0,
            "start_angle": 0.0,
            "end_angle": 180.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "created" in result[0].text
        assert "10.0" in result[0].text

    @pytest.mark.asyncio
    async def test_create_polygon(self, mock_httpx_client):
        """Test create_polygon creates a regular polygon."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/polygon"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "status": "created",
                "edge_count": 6,
                "face_id": 55555,
                "center": {"x": 0, "y": 0, "z": 0},
                "radius": 10.0,
                "num_sides": 6
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("create_polygon", {
            "radius": 10.0,
            "num_sides": 6
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "created" in result[0].text
        assert "6" in result[0].text

    @pytest.mark.asyncio
    async def test_push_pull(self, mock_httpx_client, mock_push_pull_response):
        """Test push_pull extrudes a face."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/pushpull"
        ] = type('MockResponse', (), {
            'json': lambda: mock_push_pull_response,
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("push_pull", {
            "entity_id": 12345,
            "distance": 10.0
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "completed" in result[0].text
        assert "12345" in result[0].text

    @pytest.mark.asyncio
    async def test_follow_me(self, mock_httpx_client):
        """Test follow_me extrudes along a path."""
        # Setup mock response
        mock_httpx_client.post_responses[
            "http://localhost:8080/geometry/followme"
        ] = type('MockResponse', (), {
            'json': lambda: {
                "status": "completed",
                "face_id": 12345,
                "path_edge_count": 3
            },
            'raise_for_status': lambda: None,
            'status_code': 200
        })()

        # Call the tool
        result = await call_tool("follow_me", {
            "face_id": 12345,
            "path_ids": [100, 101, 102]
        })

        # Verify response
        assert len(result) == 1
        assert result[0].type == "text"
        assert "completed" in result[0].text
        assert "12345" in result[0].text
