#!/usr/bin/env python3
"""
Minimal MCP server test
"""
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/mcp")
async def mcp_post(request: Request):
    print("DEBUG: MCP POST called!")
    body = await request.json()
    print(f"DEBUG: Body: {body}")
    
    return {
        "jsonrpc": "2.0",
        "id": body.get("id", 1),
        "result": {
            "message": "SUCCESS - MCP POST endpoint working!",
            "method": body.get("method", "unknown")
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
