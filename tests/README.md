# Test Suite for SketchUp MCP Server

This directory contains the test suite for the SketchUp MCP Server. Tests use `pytest` with async support and mock HTTP responses to test the server without requiring a running SketchUp instance.

## Status

✅ **Working**: Basic test infrastructure with mocked HTTP client
✅ **Working**: test_basic.py with 5 passing tests demonstrating the pattern
⚠️ **Needs Update**: Other test files need mock response syntax updated (see test_basic.py for correct pattern)

## Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_query_tools.py

# Run specific test
pytest tests/test_query_tools.py::TestQueryTools::test_get_model_info

# Run with coverage
pytest --cov=sketchup_mcp --cov-report=html
```

## Test Structure

- **conftest.py**: Pytest configuration and fixtures for mocking HTTP responses
- **test_query_tools.py**: Tests for query tools (get_model_info, list_layers, etc.)
- **test_geometry_tools.py**: Tests for geometry creation (boxes, circles, arcs, polygons)
- **test_transformation_tools.py**: Tests for transformations (move, rotate, scale)
- **test_error_handling.py**: Tests for error scenarios (connection errors, HTTP errors, etc.)

## Fixtures

All fixtures are defined in `conftest.py` and provide:

- **mock_httpx_client**: Mock HTTP client that doesn't make real network calls
- **mock_sketchup_***: Sample SketchUp API responses for different endpoints

## Test Coverage

The test suite covers:

- ✅ All query tools (model info, layers, materials, entities, components)
- ✅ Basic geometry creation (faces, edges, groups, boxes)
- ✅ Advanced geometry (circles, arcs, polygons, push-pull, follow-me)
- ✅ All transformation tools (move, rotate, scale)
- ✅ Error handling (connection errors, timeouts, HTTP errors, SketchUp errors)
- ✅ Edge cases (invalid JSON, missing entities, Ruby execution errors)

## Adding New Tests

To add tests for a new tool:

1. Add mock response fixture to `conftest.py`
2. Create test method in appropriate test file
3. Setup mock response using `mock_httpx_client`
4. Call the tool and verify response

Example (see test_basic.py for working examples):

```python
from tests.conftest import MockResponse

@pytest.mark.asyncio
async def test_my_tool(self, mock_httpx_client):
    # Setup mock response
    mock_data = {"status": "success", "result": "data"}
    mock_httpx_client.post_responses[
        "http://localhost:8080/my/endpoint"
    ] = MockResponse(mock_data)

    # Call tool
    result = await call_tool("my_tool", {"param": "value"})

    # Verify
    assert len(result) == 1
    assert result[0].type == "text"
    assert "success" in result[0].text
```
