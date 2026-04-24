"""
FastAPI backend for Deck Designer
Provides REST API for deck calculations, Claude chat, and SketchUp integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import os
from anthropic import Anthropic
import json

from deck_designer.code_loader import BuildingCode
from deck_designer.calculations import DeckCalculator, DeckDimensions

# Initialize FastAPI app
app = FastAPI(
    title="Deck Designer API",
    description="Structural calculations and 3D generation for residential decks",
    version="0.1.0"
)

# Add CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SKETCHUP_BASE_URL = "http://localhost:8080"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize Anthropic client if API key is available
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# ============================================================================
# Request/Response Models
# ============================================================================

class DeckCalculationRequest(BaseModel):
    """Request model for deck structural calculations"""
    length_ft: float = Field(..., description="Deck length in feet", gt=0)
    width_ft: float = Field(..., description="Deck width in feet", gt=0)
    height_in: float = Field(24.0, description="Deck height above grade in inches", ge=0, le=30)
    joist_spacing: int = Field(16, description="Joist spacing in inches (12, 16, or 24)")
    species: str = Field("Southern_Pine", description="Lumber species")
    code: str = Field("ohio_2019", description="Building code to use")


class DeckGenerationRequest(BaseModel):
    """Request model for 3D deck generation in SketchUp"""
    length: float = Field(..., description="Deck length in feet")
    width: float = Field(..., description="Deck width in feet")
    height: float = Field(24.0, description="Deck height in inches")
    joist_size: str = Field("2x10", description="Joist size")
    joist_spacing: int = Field(16, description="Joist spacing in inches")
    beam_size: str = Field("2x10", description="Beam size")
    post_size: str = Field("4x4", description="Post size")
    footing_diameter: float = Field(18.0, description="Footing diameter in inches")
    origin: Optional[List[float]] = Field([0, 0, 0], description="Origin point [x, y, z]")


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for Claude chat"""
    messages: List[ChatMessage] = Field(..., description="Chat message history")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    model: str = Field("claude-3-5-sonnet-20241022", description="Claude model to use")
    max_tokens: int = Field(4096, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Stream the response")


# ============================================================================
# Deck Calculation Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Deck Designer API",
        "version": "0.1.0",
        "endpoints": {
            "calculations": "/api/deck/calculate",
            "generate": "/api/deck/generate",
            "chat": "/api/chat",
            "sketchup": "/api/sketchup/*"
        }
    }


@app.post("/api/deck/calculate")
async def calculate_deck(request: DeckCalculationRequest) -> Dict[str, Any]:
    """
    Calculate structural requirements for a deck

    Returns:
        Complete structural analysis with member sizes and code compliance
    """
    try:
        # Load building code
        code = BuildingCode.load(request.code)

        # Create calculator
        calc = DeckCalculator(code)

        # Define deck dimensions
        dimensions = DeckDimensions(
            length=request.length_ft * 12,  # Convert to inches
            width=request.width_ft * 12,
            height=request.height_in
        )

        # Perform calculations
        results = calc.calculate_deck(
            dimensions=dimensions,
            joist_spacing=request.joist_spacing,
            species=request.species
        )

        return results

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@app.get("/api/codes")
async def list_building_codes() -> Dict[str, Any]:
    """List available building codes"""
    # For now, just return Ohio 2019
    # Could scan the codes directory in the future
    return {
        "codes": [
            {
                "id": "ohio_2019",
                "name": "2019 Ohio Residential Code",
                "jurisdiction": "Ohio",
                "base": "IRC 2018"
            }
        ]
    }


@app.get("/api/lumber/species")
async def list_lumber_species() -> Dict[str, List[str]]:
    """List available lumber species"""
    return {
        "species": [
            "Southern_Pine",
            "Douglas_Fir_Larch",
            "Hem_Fir",
            "SPF"
        ]
    }


# ============================================================================
# SketchUp Integration Endpoints
# ============================================================================

@app.post("/api/deck/generate")
async def generate_deck_3d(request: DeckGenerationRequest) -> Dict[str, Any]:
    """
    Generate 3D deck model in SketchUp

    This endpoint proxies the request to the SketchUp HTTP server
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SKETCHUP_BASE_URL}/construction/deck",
                json=request.model_dump(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to SketchUp. Make sure SketchUp is running with the MCP plugin loaded."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="SketchUp request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SketchUp error: {str(e)}")


@app.get("/api/sketchup/status")
async def check_sketchup_status() -> Dict[str, Any]:
    """Check if SketchUp is running and accessible"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SKETCHUP_BASE_URL}/model/info",
                timeout=5.0
            )
            response.raise_for_status()
            return {
                "status": "connected",
                "sketchup": response.json()
            }
    except httpx.ConnectError:
        return {
            "status": "disconnected",
            "error": "SketchUp is not running or plugin is not loaded"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# Claude API Chat Endpoints
# ============================================================================

@app.post("/api/chat")
async def chat_with_claude(request: ChatRequest):
    """
    Chat with Claude AI

    Supports both streaming and non-streaming responses
    """
    if not anthropic_client:
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured. Set ANTHROPIC_API_KEY environment variable."
        )

    try:
        # Convert messages to Anthropic format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # System prompt for deck design context
        system_prompt = request.system_prompt or """You are a helpful assistant specializing in residential deck design and construction.
You have access to structural calculations and can help users design code-compliant decks.
When discussing deck specifications, provide accurate information based on building codes and engineering principles."""

        if request.stream:
            # Streaming response
            async def generate_stream():
                with anthropic_client.messages.stream(
                    model=request.model,
                    max_tokens=request.max_tokens,
                    system=system_prompt,
                    messages=messages
                ) as stream:
                    for text in stream.text_stream:
                        yield f"data: {json.dumps({'content': text})}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            message = anthropic_client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                system=system_prompt,
                messages=messages
            )

            return {
                "role": "assistant",
                "content": message.content[0].text,
                "model": request.model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")


@app.get("/api/chat/status")
async def check_claude_status() -> Dict[str, Any]:
    """Check if Claude API is configured"""
    return {
        "configured": anthropic_client is not None,
        "api_key_set": ANTHROPIC_API_KEY is not None
    }


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""

    # Check SketchUp connection
    sketchup_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SKETCHUP_BASE_URL}/model/info", timeout=2.0)
            if response.status_code == 200:
                sketchup_status = "connected"
    except:
        sketchup_status = "disconnected"

    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "sketchup": sketchup_status,
            "claude": "configured" if anthropic_client else "not_configured"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
