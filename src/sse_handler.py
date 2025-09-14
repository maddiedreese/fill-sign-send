"""
SSE handler for MCP protocol over Server-Sent Events
"""
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi import Request
from fastapi.responses import StreamingResponse

async def handle_mcp_sse(request: Request) -> StreamingResponse:
    """Handle MCP protocol over SSE for Poke compatibility."""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'message': 'MCP server connected'})}\n\n"
            
            # Handle POST request body if present
            if request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        # Parse the MCP request
                        mcp_request = json.loads(body.decode())
                        yield f"data: {json.dumps({'type': 'mcp_request', 'data': mcp_request})}\n\n"
                        
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
                            yield f"data: {json.dumps({'type': 'mcp_response', 'data': response})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
            # Keep connection alive with heartbeat
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control, Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        }
    )
