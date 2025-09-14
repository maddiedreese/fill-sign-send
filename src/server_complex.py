#!/usr/bin/env python3
"""
Doc Filling + E-Signing MCP Server - Production Ready with SSE + MCP
Handles both SSE and MCP functionality for Poke integration
"""
import json
import sys
import os
import time
import logging
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import asyncio

# Import real implementations with proper error handling
try:
    from settings import settings
    from pdf_utils import extract_acroform_fields, fill_and_flatten
    from esign_docusign import send_for_signature_docusign, check_signature_status_docusign, download_signed_pdf_docusign

    logger.info("✅ Successfully imported all modules")
    USE_REAL_APIS = True
except ImportError as e:
    logger.error(f"⚠️  Import error: {e}")
    USE_REAL_APIS = False

# Create mock implementations for missing modules
class MockSettings:
    def get_poke_config(self):
        return {"base_url": "https://poke.example.com"}
    def validate_docusign_config(self):
        return False
    def validate_poke_config(self):
        return False
    ENVIRONMENT = "production"

def detect_pdf_fields(file_url):
    return [{"name": "field1", "type": "text"}, {"name": "field2", "type": "text"}]

def fill_pdf_fields(file_url, field_values):
    return {"filled_pdf_url": f"file://filled_{os.path.basename(file_url)}"}

def send_for_signature_docusign(file_url, recipient_email, recipient_name, subject, message):
    return {"envelope_id": "mock-envelope-123"}

def check_signature_status_docusign(envelope_id):
    return {"status": "completed"}

def download_signed_pdf_docusign(envelope_id):
    return {"signed_pdf_url": f"file://signed_{envelope_id}.pdf"}

# Use mock settings if real ones failed
if not USE_REAL_APIS:
    settings = MockSettings()
    logger.warning("⚠️  Using mock implementations for missing modules")

app = FastAPI()

# MCP Tools Definition
MCP_TOOLS = [
    {
        "name": "detect_pdf_fields",
        "description": "Detect form fields in a PDF document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {"type": "string", "description": "URL or path to the PDF file"}
            },
            "required": ["file_url"]
        }
    },
    {
        "name": "fill_pdf_fields",
        "description": "Fill form fields in a PDF document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {"type": "string", "description": "URL or path to the PDF file"},
                "field_values": {"type": "object", "description": "Dictionary of field names and values"}
            },
            "required": ["file_url", "field_values"]
        }
    },
    {
        "name": "send_for_signature",
        "description": "Send a document for e-signature via DocuSign",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {"type": "string", "description": "URL or path to the PDF file"},
                "recipient_email": {"type": "string", "description": "Email address of the recipient"},
                "recipient_name": {"type": "string", "description": "Name of the recipient"},
                "subject": {"type": "string", "description": "Subject line for the email"},
                "message": {"type": "string", "description": "Message body for the email"}
            },
            "required": ["file_url", "recipient_email", "recipient_name"]
        }
    },
    {
        "name": "check_signature_status",
        "description": "Check the status of a signature request",
        "inputSchema": {
            "type": "object",
            "properties": {
                "envelope_id": {"type": "string", "description": "Envelope ID from the signature request"}
            },
            "required": ["envelope_id"]
        }
    },
    {
        "name": "download_signed_pdf",
        "description": "Download the signed PDF document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "envelope_id": {"type": "string", "description": "Envelope ID from the signature request"}
            },
            "required": ["envelope_id"]
        }
    },
    {
        "name": "notify_poke",
        "description": "Send a notification to Poke",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to send to Poke"},
                "attachments": {"type": "array", "description": "List of attachments"}
            },
            "required": ["message"]
        }
    },
    {
        "name": "get_server_info",
        "description": "Get server information and configuration status",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers
def handle_detect_pdf_fields(args):
    """Handle detect_pdf_fields tool call."""
    logger.info(f"🔍 detect_pdf_fields called with args: {args}")
    try:
        file_url = args.get("file_url", "")
        if USE_REAL_APIS:
            fields = extract_acroform_fields(file_url)
        else:
            fields = detect_pdf_fields(file_url)
        return {"success": True, "fields": fields, "message": f"Found {len(fields)} form fields"}
    except Exception as e:
        logger.error(f"❌ detect_pdf_fields error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to detect PDF fields"}

def handle_fill_pdf_fields(args):
    """Handle fill_pdf_fields tool call."""
    logger.info(f"📝 fill_pdf_fields called with args: {args}")
    try:
        file_url = args.get("file_url", "")
        field_values = args.get("field_values", {})
        if USE_REAL_APIS:
            result = fill_and_flatten(file_url, field_values)
        else:
            result = fill_pdf_fields(file_url, field_values)
        return {"success": True, "filled_pdf_url": result["filled_pdf_url"], "message": f"Successfully filled {len(field_values)} fields"}
    except Exception as e:
        logger.error(f"❌ fill_pdf_fields error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to fill PDF fields"}

def handle_send_for_signature(args):
    """Handle send_for_signature tool call."""
    logger.info(f"�� send_for_signature called with args: {args}")
    try:
        file_url = args.get("file_url", "")
        recipient_email = args.get("recipient_email", "")
        recipient_name = args.get("recipient_name", "")
        subject = args.get("subject", "Please sign this document")
        message = args.get("message", "Please review and sign this document.")
        
        logger.info(f"📧 Sending document for signature: {file_url} to {recipient_email}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            result = send_for_signature_docusign(file_url, recipient_email, recipient_name, subject, message)
            logger.info(f"📧 DocuSign result: {result}")
            if result.get("success"):
                return {"success": True, "envelope_id": result["envelope_id"], "message": "Document sent for signature via DocuSign"}
            else:
                return {"success": False, "error": result.get("error", "Unknown error"), "message": "Failed to send document for signature"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            result = send_for_signature_docusign(file_url, recipient_email, recipient_name, subject, message)
            return {"success": True, "envelope_id": result["envelope_id"], "message": "Document sent for signature via DocuSign (MOCK)"}
    except Exception as e:
        logger.error(f"❌ send_for_signature error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to send document for signature via DocuSign"}

def handle_check_signature_status(args):
    """Handle check_signature_status tool call."""
    logger.info(f"📊 check_signature_status called with args: {args}")
    try:
        envelope_id = args.get("envelope_id", "")
        if USE_REAL_APIS:
            result = check_signature_status_docusign(envelope_id)
            if result.get("success"):
                return {"success": True, "status": result["status"], "message": f"Signature status: {result['status']}"}
            else:
                return {"success": False, "error": result.get("error", "Unknown error"), "message": "Failed to check signature status"}
        else:
            result = check_signature_status_docusign(envelope_id)
            return {"success": True, "status": result["status"], "message": f"Signature status: {result['status']} (MOCK)"}
    except Exception as e:
        logger.error(f"❌ check_signature_status error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to check signature status via DocuSign"}

def handle_download_signed_pdf(args):
    """Handle download_signed_pdf tool call."""
    logger.info(f"📥 download_signed_pdf called with args: {args}")
    try:
        envelope_id = args.get("envelope_id", "")
        if USE_REAL_APIS:
            result = download_signed_pdf_docusign(envelope_id)
            if result.get("success"):
                return {"success": True, "signed_pdf_url": result["signed_pdf_url"], "message": "Signed PDF downloaded successfully"}
            else:
                return {"success": False, "error": result.get("error", "Unknown error"), "message": "Failed to download signed PDF"}
        else:
            result = download_signed_pdf_docusign(envelope_id)
            return {"success": True, "signed_pdf_url": result["signed_pdf_url"], "message": "Signed PDF downloaded successfully (MOCK)"}
    except Exception as e:
        logger.error(f"❌ download_signed_pdf error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to download signed PDF via DocuSign"}

def handle_notify_poke(args):
    """Handle notify_poke tool call."""
    logger.info(f"🔔 notify_poke called with args: {args}")
    try:
        import requests
        
        message = args.get("message", "")
        attachments = args.get("attachments", [])
        
        if USE_REAL_APIS:
            poke_config = settings.get_poke_config()
            webhook_url = f"{poke_config['base_url']}/webhooks/mcp"
            
            payload = {"message": message, "attachments": attachments, "timestamp": time.time()}
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            return {"success": True, "message": "Notification sent to Poke successfully"}
        else:
            return {"success": True, "message": "Notification sent to Poke successfully (MOCK)"}
    except Exception as e:
        logger.error(f"❌ notify_poke error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to send notification to Poke"}

def handle_get_server_info(args):
    """Handle get_server_info tool call."""
    logger.info(f"ℹ️  get_server_info called with args: {args}")
    try:
        if USE_REAL_APIS:
            docusign_valid = settings.validate_docusign_config()
            poke_valid = settings.validate_poke_config()
        else:
            docusign_valid = False
            poke_valid = False
        
        return {
            "success": True,
            "server": {"name": "Doc Filling + E-Signing MCP Server", "version": "1.0.0", "status": "running"},
            "config": {
                "docusign": {"configured": docusign_valid, "environment": settings.ENVIRONMENT},
                "poke": {"configured": poke_valid}
            },
            "message": "Server is running and ready"
        }
    except Exception as e:
        logger.error(f"❌ get_server_info error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get server info"}

# Tool dispatcher
TOOL_HANDLERS = {
    "detect_pdf_fields": handle_detect_pdf_fields,
    "fill_pdf_fields": handle_fill_pdf_fields,
    "send_for_signature": handle_send_for_signature,
    "check_signature_status": handle_check_signature_status,
    "download_signed_pdf": handle_download_signed_pdf,
    "notify_poke": handle_notify_poke,
    "get_server_info": handle_get_server_info
}

@app.get("/")
async def root():
    return {"message": "Doc Filling + E-Signing MCP Server", "status": "running"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        logger.info(f"📨 MCP request received: {request.method}")
        
        # Handle POST request body if present
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    # Parse the MCP request
                    mcp_request = json.loads(body.decode())
                    logger.info(f"📨 MCP request: {mcp_request}")
                    
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
                        return JSONResponse(content=response)
                    
                    elif mcp_request.get("method") == "tools/list":
                        response = {
                            "jsonrpc": "2.0",
                            "id": mcp_request.get("id"),
                            "result": {
                                "tools": MCP_TOOLS
                            }
                        }
                        return JSONResponse(content=response)
                    
                    elif mcp_request.get("method") == "tools/call":
                        tool_name = mcp_request.get("params", {}).get("name")
                        tool_args = mcp_request.get("params", {}).get("arguments", {})
                        
                        logger.info(f"🔧 Tool call: {tool_name} with args: {tool_args}")
                        
                        if tool_name in TOOL_HANDLERS:
                            result = TOOL_HANDLERS[tool_name](tool_args)
                            logger.info(f"✅ Tool result: {result}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": mcp_request.get("id"),
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(result, indent=2)
                                        }
                                    ]
                                }
                            }
                            return JSONResponse(content=response)
                        else:
                            logger.error(f"❌ Tool not found: {tool_name}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": mcp_request.get("id"),
                                "error": {
                                    "code": -32601,
                                    "message": f"Tool '{tool_name}' not found"
                                }
                            }
                            return JSONResponse(content=response)
                    
                    else:
                        logger.error(f"❌ Method not found: {mcp_request.get('method')}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": mcp_request.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Method '{mcp_request.get('method')}' not found"
                            }
                        }
                        return JSONResponse(content=response)
                
            except json.JSONDecodeError:
                logger.error("❌ Invalid JSON in request")
                return JSONResponse(content={"error": "Invalid JSON"}, status_code=400)
            except Exception as e:
                logger.error(f"❌ Request processing error: {e}")
                return JSONResponse(content={"error": str(e)}, status_code=500)
        
        return JSONResponse(content={"message": "Doc Filling + E-Signing MCP Server", "status": "running"})
    
    except Exception as e:
        logger.error(f"❌ MCP endpoint error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/sse")
async def sse_endpoint(request: Request, tool: str = None, args: str = None):
    """
    Server-Sent Events endpoint for real-time updates with MCP tool support.
    Poke can call this endpoint with tool parameters to execute MCP functions.
    """
    logger.info(f"📡 SSE request received - tool: {tool}, args: {args}")
    
    # If tool is specified, execute the MCP tool
    if tool:
        try:
            # Parse arguments if provided
            tool_args = {}
            if args:
                try:
                    tool_args = json.loads(args)
                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON in args: {args}")
                    tool_args = {}
            
            logger.info(f"🔧 Executing tool: {tool} with args: {tool_args}")
            
            if tool in TOOL_HANDLERS:
                result = TOOL_HANDLERS[tool](tool_args)
                logger.info(f"✅ Tool result: {result}")
                
                # Return the result as JSON instead of streaming
                return JSONResponse(content=result)
            else:
                logger.error(f"❌ Tool not found: {tool}")
                return JSONResponse(content={"error": f"Tool '{tool}' not found"}, status_code=404)
                
        except Exception as e:
            logger.error(f"❌ Tool execution error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    # If no tool specified, return available tools
    logger.info("📋 Returning available tools")
    return JSONResponse(content={
        "message": "Doc Filling + E-Signing MCP Server",
        "status": "running",
        "available_tools": [tool["name"] for tool in MCP_TOOLS],
        "usage": "Add ?tool=<tool_name>&args=<json_args> to execute a tool"
    })

@app.post("/sse")
async def sse_post_endpoint(request: Request):
    """
    POST endpoint for SSE with MCP tool support.
    Poke can POST to this endpoint with tool data.
    """
    try:
        body = await request.body()
        if body:
            data = json.loads(body.decode())
            logger.info(f"📨 SSE POST request: {data}")
            
            tool = data.get("tool")
            args = data.get("args", {})
            
            if tool:
                logger.info(f"🔧 Executing tool: {tool} with args: {args}")
                
                if tool in TOOL_HANDLERS:
                    result = TOOL_HANDLERS[tool](args)
                    logger.info(f"✅ Tool result: {result}")
                    return JSONResponse(content=result)
                else:
                    logger.error(f"❌ Tool not found: {tool}")
                    return JSONResponse(content={"error": f"Tool '{tool}' not found"}, status_code=404)
            else:
                return JSONResponse(content={"error": "No tool specified"}, status_code=400)
        else:
            return JSONResponse(content={"error": "No data provided"}, status_code=400)
            
    except Exception as e:
        logger.error(f"❌ SSE POST error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    logger.info(f"🚀 Starting Doc Filling + E-Signing MCP Server...")
    logger.info(f"📊 Using {'REAL' if USE_REAL_APIS else 'MOCK'} APIs")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
