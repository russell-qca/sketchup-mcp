# Deck Designer API

FastAPI backend for structural deck calculations, Claude AI chat, and SketchUp 3D generation.

## Architecture

```
Web UI (React)
      ↓ HTTP REST
FastAPI Backend (Port 8000)
      ├→ Claude API (chat)
      ├→ Deck Calculations (Python)
      └→ SketchUp Plugin (Port 8080)
```

## Installation

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
nano .env
```

Add your Claude API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### 3. Start the Server

```bash
./run_api_server.sh
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

## API Endpoints

### Health & Status

#### `GET /health`
Health check for all services
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "api": "running",
    "sketchup": "connected",
    "claude": "configured"
  }
}
```

### Deck Calculations

#### `POST /api/deck/calculate`
Calculate structural requirements for a deck

Request:
```json
{
  "length_ft": 12,
  "width_ft": 16,
  "height_in": 24,
  "joist_spacing": 16,
  "species": "Southern_Pine",
  "code": "ohio_2019"
}
```

Response:
```json
{
  "dimensions": {
    "length_ft": 12.0,
    "width_ft": 16.0,
    "area_sqft": 192.0
  },
  "joists": {
    "size": "2x10",
    "spacing_inches": 16,
    "max_span_ft": 17.5,
    "compliant": true
  },
  "beams": {
    "size": "(2) 2x10",
    "max_span_ft": 10.0,
    "compliant": true
  },
  "posts": {
    "size": "4x4",
    "load_lbs": 2400,
    "capacity_lbs": 4000,
    "safety_factor": 1.67
  },
  "footings": {
    "diameter_inches": 18,
    "depth_inches": 32,
    "bearing_pressure_psf": 1358
  },
  "compliant": true
}
```

#### `GET /api/codes`
List available building codes
```bash
curl http://localhost:8000/api/codes
```

#### `GET /api/lumber/species`
List available lumber species
```bash
curl http://localhost:8000/api/lumber/species
```

### SketchUp Integration

#### `POST /api/deck/generate`
Generate 3D deck model in SketchUp

**Prerequisites**: SketchUp must be running with the MCP plugin loaded

Request:
```json
{
  "length": 12,
  "width": 16,
  "height": 24,
  "joist_size": "2x10",
  "joist_spacing": 16,
  "beam_size": "2x10",
  "post_size": "4x4",
  "footing_diameter": 18,
  "origin": [0, 0, 0]
}
```

Response:
```json
{
  "status": "created",
  "type": "deck",
  "group_name": "DECK_12x16_1234567890",
  "components": [
    "4 footings",
    "4 posts",
    "2 beams",
    "10 joists",
    "35 deck boards"
  ]
}
```

#### `GET /api/sketchup/status`
Check if SketchUp is accessible
```bash
curl http://localhost:8000/api/sketchup/status
```

### Claude AI Chat

#### `POST /api/chat`
Chat with Claude AI about deck design

Request (non-streaming):
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What joist size do I need for a 16-foot span?"
    }
  ],
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 1024,
  "stream": false
}
```

Response:
```json
{
  "role": "assistant",
  "content": "For a 16-foot span with typical deck loading...",
  "model": "claude-3-5-sonnet-20241022",
  "usage": {
    "input_tokens": 45,
    "output_tokens": 123
  }
}
```

Request (streaming):
```json
{
  "messages": [...],
  "stream": true
}
```

Response: Server-Sent Events (SSE) stream

#### `GET /api/chat/status`
Check if Claude API is configured
```bash
curl http://localhost:8000/api/chat/status
```

## Testing

### Run All Tests
```bash
./test_api.sh
```

### Individual Tests

Test calculations:
```bash
curl -X POST http://localhost:8000/api/deck/calculate \
  -H "Content-Type: application/json" \
  -d '{"length_ft": 12, "width_ft": 16, "height_in": 24}'
```

Test SketchUp generation (requires SketchUp running):
```bash
curl -X POST http://localhost:8000/api/deck/generate \
  -H "Content-Type: application/json" \
  -d '{"length": 12, "width": 16, "height": 24}'
```

Test Claude chat:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

## Development

### Interactive API Docs

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Hot Reload

The server runs with `--reload` flag, so code changes are automatically picked up.

### Adding New Endpoints

1. Add the endpoint function in `src/deck_designer/api.py`
2. Use Pydantic models for request/response validation
3. Test with `/docs` or `curl`

## Production Deployment

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
SKETCHUP_BASE_URL=http://localhost:8080
API_HOST=0.0.0.0
API_PORT=8000
```

### CORS Configuration

Update CORS origins in `api.py` for production:
```python
allow_origins=["https://yourdomain.com"]
```

### Run with Production Server

```bash
uvicorn deck_designer.api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Claude API not configured" | Set `ANTHROPIC_API_KEY` in `.env` |
| "Cannot connect to SketchUp" | Make sure SketchUp is running with MCP plugin loaded |
| Port 8000 already in use | Change `API_PORT` in `.env` or kill process on port 8000 |
| CORS errors from web UI | Update `allow_origins` in `api.py` |

## Next Steps

- Build the web UI (React frontend)
- Add user authentication
- Add deck design templates
- Add material cost estimation
- Add PDF report generation
