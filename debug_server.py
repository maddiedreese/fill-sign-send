#!/usr/bin/env python3
"""
Debug server to test MCP endpoint
"""
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Debug server is running"}

@app.get("/mcp")
async def mcp_get():
    return {"message": "MCP GET endpoint"}

@app.post("/mcp")
async def mcp_post(request: Request):
    print(f"DEBUG: MCP POST endpoint called")
    body = await request.json()
    print(f"DEBUG: Request body: {body}")
    return {
        "jsonrpc": "2.0",
        "id": body.get("id", 1),
        "result": {
            "message": "MCP POST endpoint working",
            "method": body.get("method", "unknown")
        }
    }

if __name__ == "__main__":
    print("DEBUG: Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
