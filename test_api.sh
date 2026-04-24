#!/bin/bash
# Test the Deck Designer API

API_URL="http://localhost:8000"

echo "========================================="
echo "Testing Deck Designer API"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1. Health Check"
echo "   GET /health"
curl -s "$API_URL/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: List Building Codes
echo "2. List Available Building Codes"
echo "   GET /api/codes"
curl -s "$API_URL/api/codes" | python3 -m json.tool
echo ""
echo ""

# Test 3: Deck Calculations
echo "3. Calculate 12' x 16' Deck Structure"
echo "   POST /api/deck/calculate"
curl -s -X POST "$API_URL/api/deck/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "length_ft": 12,
    "width_ft": 16,
    "height_in": 24,
    "joist_spacing": 16,
    "species": "Southern_Pine"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 4: Check SketchUp Status
echo "4. Check SketchUp Connection"
echo "   GET /api/sketchup/status"
curl -s "$API_URL/api/sketchup/status" | python3 -m json.tool
echo ""
echo ""

# Test 5: Generate 3D Deck (only if SketchUp is running)
echo "5. Generate 3D Deck in SketchUp"
echo "   POST /api/deck/generate"
echo "   (This will only work if SketchUp is running)"
curl -s -X POST "$API_URL/api/deck/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "length": 12,
    "width": 16,
    "height": 24,
    "joist_size": "2x10",
    "joist_spacing": 16,
    "beam_size": "2x10",
    "post_size": "4x4",
    "footing_diameter": 18
  }' | python3 -m json.tool
echo ""
echo ""

echo "========================================="
echo "API Test Complete!"
echo "========================================="
