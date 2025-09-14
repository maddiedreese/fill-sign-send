#!/usr/bin/env python3
"""
Minimal test server to debug production issues
"""
import json
import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Minimal test server", "status": "running"}

@app.get("/sse")
async def sse_endpoint(request: Request, tool: str = None, args: str = None):
    """SSE endpoint for MCP tool support."""
    logger.info(f"📡 SSE GET request - tool: {tool}, args: {args}")
    
    if tool == "getenvelope":
        return JSONResponse(content={
            "success": True, 
            "envelope_id": "test-envelope-123", 
            "status": "sent",
            "message": "Test envelope retrieved successfully"
        })
    
    return JSONResponse(content={
        "message": "Minimal test server",
        "status": "running",
        "available_tools": ["getenvelope"]
    })

@app.post("/sse")
async def sse_post_endpoint(request: Request):
    """POST endpoint for SSE with MCP tool support."""
    try:
        body = await request.body()
        if body:
            data = json.loads(body.decode())
            logger.info(f"📨 SSE POST request: {data}")
            
            tool = data.get("tool")
            args = data.get("args", {})
            
            if tool == "getenvelope":
                return JSONResponse(content={
                    "success": True, 
                    "envelope_id": "test-envelope-123", 
                    "status": "sent",
                    "message": "Test envelope retrieved successfully"
                })
            else:
                return JSONResponse(content={"error": f"Tool '{tool}' not found"}, status_code=404)
        else:
            return JSONResponse(content={"error": "No data provided"}, status_code=400)
            
    except Exception as e:
        logger.error(f"❌ SSE POST error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    logger.info("🚀 Starting minimal test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
