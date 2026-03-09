"""Pytest configuration and fixtures for SketchUp MCP Server tests."""

import pytest
from unittest.mock import AsyncMock, Mock
import httpx


class MockResponse:
    """Mock HTTP response for testing."""
    def __init__(self, json_data, status_code=200, text=""):
        self._json_data = json_data
        self.status_code = status_code
        self.text = text or str(json_data)

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=Mock(),
                response=self
            )

    def __str__(self):
        return self.text


@pytest.fixture
def mock_response():
    """Factory fixture to create mock HTTP responses."""
    return MockResponse


@pytest.fixture
def mock_httpx_client(monkeypatch):
    """Mock httpx.AsyncClient for testing HTTP requests without actual network calls."""

    class _MockResponse:
        def __init__(self, json_data, status_code=200, text=""):
            self._json_data = json_data
            self.status_code = status_code
            self.text = text or str(json_data)

        def json(self):
            return self._json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"HTTP {self.status_code}",
                    request=Mock(),
                    response=self
                )

        def __str__(self):
            return self.text

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.get_responses = {}
            self.post_responses = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            if url in self.get_responses:
                return self.get_responses[url]
            return MockResponse({"error": "Mock not configured for GET " + url}, 500)

        async def post(self, url, **kwargs):
            if url in self.post_responses:
                return self.post_responses[url]
            return MockResponse({"error": "Mock not configured for POST " + url}, 500)

    mock_client = MockAsyncClient()

    def mock_async_client_factory(*args, **kwargs):
        return mock_client

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client_factory)

    return mock_client


@pytest.fixture
def mock_sketchup_model_info():
    """Sample SketchUp model info response."""
    return {
        "name": "Test Model",
        "description": "A test model",
        "path": "/path/to/model.skp",
        "modified": False,
        "unit": 0,  # Inches
        "entity_count": 10,
        "layer_count": 2,
        "material_count": 3
    }


@pytest.fixture
def mock_sketchup_layers():
    """Sample SketchUp layers response."""
    return [
        {"name": "Layer0", "visible": True},
        {"name": "Walls", "visible": True},
        {"name": "Hidden", "visible": False}
    ]


@pytest.fixture
def mock_sketchup_materials():
    """Sample SketchUp materials response."""
    return [
        {
            "name": "Material1",
            "color": {"r": 255, "g": 0, "b": 0, "a": 255},
            "texture": None
        },
        {
            "name": "Wood",
            "color": {"r": 139, "g": 90, "b": 43, "a": 255},
            "texture": "/path/to/texture.jpg"
        }
    ]


@pytest.fixture
def mock_sketchup_entities():
    """Sample SketchUp entities response."""
    return [
        {
            "id": 12345,
            "type": "Sketchup::Face",
            "area": 144.0,
            "layer": "Layer0",
            "normal": {"x": 0, "y": 0, "z": 1}
        },
        {
            "id": 67890,
            "type": "Sketchup::Edge",
            "length": 12.0,
            "layer": "Layer0"
        },
        {
            "id": 11111,
            "type": "Sketchup::Group",
            "name": "Group1",
            "layer": "Layer0"
        }
    ]


@pytest.fixture
def mock_sketchup_components():
    """Sample SketchUp components response."""
    return [
        {
            "name": "Chair",
            "description": "Office chair",
            "path": "/components/chair.skp",
            "instance_count": 3,
            "entity_count": 20
        },
        {
            "name": "Table",
            "description": "",
            "path": "",
            "instance_count": 1,
            "entity_count": 5
        }
    ]


@pytest.fixture
def mock_create_face_response():
    """Sample create face response."""
    return {
        "id": 99999,
        "type": "Face",
        "area": 100.0,
        "normal": {"x": 0, "y": 0, "z": 1}
    }


@pytest.fixture
def mock_create_circle_response():
    """Sample create circle response."""
    return {
        "status": "created",
        "edge_count": 24,
        "center": {"x": 0, "y": 0, "z": 0},
        "radius": 12.0,
        "segments": 24
    }


@pytest.fixture
def mock_create_box_response():
    """Sample create box response."""
    return {
        "status": "created",
        "width": 10.0,
        "depth": 10.0,
        "height": 5.0
    }


@pytest.fixture
def mock_push_pull_response():
    """Sample push/pull response."""
    return {
        "status": "completed",
        "entity_id": 12345,
        "distance": 10.0,
        "result_valid": True
    }


@pytest.fixture
def mock_move_entity_response():
    """Sample move entity response."""
    return {
        "status": "moved",
        "entity_id": 12345,
        "vector": {"x": 10, "y": 0, "z": 5}
    }


@pytest.fixture
def mock_rotate_entity_response():
    """Sample rotate entity response."""
    return {
        "status": "rotated",
        "entity_id": 12345,
        "angle_degrees": 45.0
    }


@pytest.fixture
def mock_scale_entity_response():
    """Sample scale entity response."""
    return {
        "status": "scaled",
        "entity_id": 12345,
        "scale": {"uniform": 2.0}
    }
