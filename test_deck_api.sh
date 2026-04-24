#!/bin/bash
# Test deck creation via HTTP API

echo "========================================="
echo "Testing Deck Creation API"
echo "========================================="
echo ""

# Test 1: Simple 12' x 16' deck
echo "Creating a 12' x 16' ground-level deck..."
curl -s -X POST http://localhost:8080/construction/deck \
  -H "Content-Type: application/json" \
  -d '{
    "length": 12,
    "width": 16,
    "height": 24,
    "joist_size": "2x10",
    "joist_spacing": 16,
    "beam_size": "2x10",
    "post_size": "4x4",
    "footing_diameter": 18,
    "origin": [0, 0, 0]
  }' | python3 -m json.tool

echo ""
echo "========================================="
echo "Test complete!"
echo "Check SketchUp to see the 3D deck model."
echo "========================================="
