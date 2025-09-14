#!/usr/bin/env python3
import os
import sys
import logging
from typing import Dict, Any
from pathlib import Path
import json
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="DocuSign MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_sse_response(data: Dict[str, Any]) -> Response:
    """Create a Server-Sent Events response"""
    json_str = json.dumps(data)
    sse_content = f"event: message\ndata: {json_str}\n\n"
    return Response(
        content=sse_content,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

def get_available_tools():
    """Get list of available tools"""
    return [
        {
            "name": "getenvelope",
            "description": "Get DocuSign envelope status and details",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "envelope_id": {
                        "type": "string",
                        "description": "DocuSign envelope ID"
                    }
                },
                "required": ["envelope_id"]
            }
        },
        {
            "name": "fill_envelope",
            "description": "Fill form fields in a DocuSign envelope",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "envelope_id": {
                        "type": "string",
                        "description": "DocuSign envelope ID"
                    },
                    "field_data": {
                        "type": "object",
                        "description": "Form field data to fill"
                    }
                },
                "required": ["envelope_id", "field_data"]
            }
        },
        {
            "name": "sign_envelope",
            "description": "Sign a DocuSign envelope",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "envelope_id": {
                        "type": "string",
                        "description": "DocuSign envelope ID"
                    },
                    "recipient_email": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "security_code": {
                        "type": "string",
                        "description": "Security code for signing"
                    }
                },
                "required": ["envelope_id", "recipient_email", "security_code"]
            }
        },
        {
            "name": "create_demo_envelope",
            "description": "Create a demo envelope for testing",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recipient_email": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "recipient_name": {
                        "type": "string",
                        "description": "Recipient name"
                    }
                },
                "required": ["recipient_email", "recipient_name"]
            }
        },
        {
            "name": "debug_docusign",
            "description": "Debug DocuSign configuration",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]

async def call_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Call a tool by name with arguments"""
    try:
        if tool_name == "getenvelope":
            envelope_id = args.get("envelope_id")
            if not envelope_id:
                return {"success": False, "error": "envelope_id is required"}
            
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": "sent",
                "message": "Mock envelope status - DocuSign integration not available locally"
            }
        
        elif tool_name == "fill_envelope":
            envelope_id = args.get("envelope_id")
            field_data = args.get("field_data", {})
            if not envelope_id:
                return {"success": False, "error": "envelope_id is required"}
            
            return {
                "success": True,
                "message": "Mock envelope filled - DocuSign integration not available locally"
            }
        
        elif tool_name == "sign_envelope":
            envelope_id = args.get("envelope_id")
            recipient_email = args.get("recipient_email")
            security_code = args.get("security_code")
            if not envelope_id or not recipient_email or not security_code:
                return {"success": False, "error": "envelope_id, recipient_email, and security_code are required"}
            
            return {
                "success": True,
                "message": "Mock envelope signed - DocuSign integration not available locally"
            }
        
        elif tool_name == "create_demo_envelope":
            recipient_email = args.get("recipient_email")
            recipient_name = args.get("recipient_name")
            if not recipient_email or not recipient_name:
                return {"success": False, "error": "recipient_email and recipient_name are required"}
            
            return {
                "success": True,
                "envelope_id": "mock-envelope-123",
                "message": "Mock demo envelope created - DocuSign integration not available locally"
            }
        
        elif tool_name == "debug_docusign":
            return {
                "success": True,
                "environment": "local",
                "docusign_configured": False,
                "message": "Mock DocuSign configuration - running locally without DocuSign integration"
            }
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        logger.error(f"❌ Error calling tool {tool_name}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "DocuSign MCP Server is running", "version": "1.0.0"}

@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """Handle MCP requests with SSE format"""
    try:
        # Enhanced logging for debugging
        logger.info(f"🔍 POKE DEBUG: Headers: {dict(request.headers)}")
        logger.info(f"🔍 POKE DEBUG: Method: {request.method}")
        logger.info(f"🔍 POKE DEBUG: URL: {request.url}")
        logger.info(f"🔍 POKE DEBUG: Client: {request.client}")
        
        # Read raw body
        body = await request.body()
        logger.info(f"🔍 POKE DEBUG: Body: {body}")
        logger.info(f"🔍 POKE DEBUG: Body length: {len(body)}")
        
        # Check if body is empty
        if not body:
            logger.error("❌ Empty request body from Poke")
            return create_sse_response({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Empty request body"},
                "id": None
            })
        
        # Parse JSON
        try:
            data = json.loads(body)
            logger.info(f"🔍 POKE DEBUG: Parsed JSON: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error from Poke: {e}")
            logger.error(f"❌ Raw body that failed to parse: {body}")
            return create_sse_response({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            })
        
        method = data.get("method")
        request_id = data.get("id")
        
        logger.info(f"🔍 POKE DEBUG: Method: {method}, ID: {request_id}")
        
        # Handle different MCP methods
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"listChanged": True, "subscribe": False},
                    "prompts": {"listChanged": True},
                    "experimental": {}
                },
                "serverInfo": {
                    "name": "DocuSign MCP Server",
                    "version": "1.0.0"
                }
            }
            logger.info(f"🔍 POKE DEBUG: Returning initialize result: {result}")
            return create_sse_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })
        
        elif method == "tools/list":
            tools = get_available_tools()
            logger.info(f"🔍 POKE DEBUG: Returning tools list: {len(tools)} tools")
            return create_sse_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools}
            })
        
        elif method == "tools/call":
            tool_name = data.get("params", {}).get("name")
            tool_args = data.get("params", {}).get("arguments", {})
            
            logger.info(f"🔍 POKE DEBUG: Calling tool: {tool_name} with args: {tool_args}")
            
            result = await call_tool(tool_name, tool_args)
            logger.info(f"🔍 POKE DEBUG: Tool result: {result}")
            return create_sse_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })
        
        else:
            logger.warning(f"⚠️ Unknown method from Poke: {method}")
            return create_sse_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    
    except Exception as e:
        logger.error(f"❌ Error processing Poke request: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return create_sse_response({
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else None,
            "error": {"code": -32603, "message": "Internal error"}
        })

if __name__ == "__main__":
    logger.info("Starting enhanced SSE-compatible MCP server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
