"""
SSE handler for MCP protocol over Server-Sent Events
"""
import json
import asyncio
from typing import Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse

async def handle_mcp_sse(request: Request) -> JSONResponse:
    """Handle MCP protocol over SSE for Poke compatibility."""
    
    try:
        # Handle POST request body if present
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    # Parse the MCP request
                    mcp_request = json.loads(body.decode())
                    
                    # Process MCP request and send response
                    if mcp_request.get("method") == "initialize":
                        response = {
                            "jsonrpc": "2.0",
                            "id": mcp_request.get("id"),
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {
                                    "tools": {}
                                },
                                "serverInfo": {
                                    "name": "Doc Filling + E-Signing MCP Server",
                                    "version": "1.0.0"
                                }
                            }
                        }
                        return JSONResponse(content=response, status_code=200)
                    else:
                        # Handle other MCP methods
                        response = {
                            "jsonrpc": "2.0",
                            "id": mcp_request.get("id"),
                            "result": {
                                "message": f"Method {mcp_request.get('method')} not implemented yet"
                            }
                        }
                        return JSONResponse(content=response, status_code=200)
                else:
                    # No body, return basic response
                    return JSONResponse(content={
                        "status": "connected",
                        "message": "MCP server connected",
                        "serverInfo": {
                            "name": "Doc Filling + E-Signing MCP Server",
                            "version": "1.0.0"
                        }
                    }, status_code=200)
            except Exception as e:
                return JSONResponse(content={
                    "error": "Invalid request",
                    "message": str(e)
                }, status_code=400)
        else:
            # GET request - return basic server info
            return JSONResponse(content={
                "status": "connected",
                "message": "MCP server connected",
                "serverInfo": {
                    "name": "Doc Filling + E-Signing MCP Server",
                    "version": "1.0.0"
                }
            }, status_code=200)
            
    except Exception as e:
        return JSONResponse(content={
            "error": "Internal server error",
            "message": str(e)
        }, status_code=500)
