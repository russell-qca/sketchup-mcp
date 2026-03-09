#!/bin/bash
# Test if SketchUp server is running
echo "Testing connection to SketchUp on port 8080..."
curl -s http://localhost:8080/model/info 2>&1 | head -20
