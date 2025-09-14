#!/usr/bin/env python3
"""
Doc Filling + E-Signing MCP Server - Simple Version
Handles MCP tools through SSE endpoint for Poke integration
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
from fastapi.responses import JSONResponse
import uvicorn

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
    logger.info(f"📧 send_for_signature called with args: {args}")
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

@app.get("/sse")
async def sse_endpoint(request: Request, tool: str = None, args: str = None):
    """
    SSE endpoint for MCP tool support - Poke can call this endpoint with tool parameters.
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
        "available_tools": list(TOOL_HANDLERS.keys()),
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
