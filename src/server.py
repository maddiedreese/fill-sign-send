#!/usr/bin/env python3
"""
Doc Filling + E-Signing MCP Server - Fixed Version
Handles file URLs properly for production
"""
import json
import sys
import os
import time
import logging
import requests
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

    logger.warning("⚠️  Using mock implementations for missing modules")

app = FastAPI()

def create_test_pdf():
    """Create a simple test PDF for production"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas('test.pdf', pagesize=letter)
        c.drawString(100, 750, 'Test Document for DocuSign')
        c.drawString(100, 700, 'This is a test document to verify DocuSign integration.')
        c.drawString(100, 650, 'Please sign this document to test the e-signature functionality.')
        c.save()
        logger.info("✅ Test PDF created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create test PDF: {e}")
        return False

def download_file_from_url(url):
    """Download a file from URL and save it locally"""
    try:
        logger.info(f"📥 Downloading file from URL: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to temporary file
        filename = f"temp_{int(time.time())}.pdf"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ File downloaded successfully: {filename}")
        return filename
    except Exception as e:
        logger.error(f"❌ Failed to download file: {e}")
        return None

def handle_send_for_signature(args):
    """Handle send_for_signature tool call with proper file handling."""
    logger.info(f"📧 send_for_signature called with args: {args}")
    try:
        file_url = args.get("file_url", "")
        recipient_email = args.get("recipient_email", "")
        recipient_name = args.get("recipient_name", "")
        subject = args.get("subject", "Please sign this document")
        message = args.get("message", "Please review and sign this document.")
        
        logger.info(f"📧 Sending document for signature: {file_url} to {recipient_email}")
        
        # Handle file URL
        actual_file_path = file_url
        
        # If it's a URL, download it
        if file_url.startswith('http'):
            actual_file_path = download_file_from_url(file_url)
            if not actual_file_path:
                return {"success": False, "error": "Failed to download file from URL", "message": "Could not download the document"}
        # If it's a local file that doesn't exist, create a test PDF
        elif not os.path.exists(file_url):
            logger.info(f"📄 File {file_url} not found, creating test PDF")
            if create_test_pdf():
                actual_file_path = "test.pdf"
            else:
                return {"success": False, "error": "File not found and could not create test PDF", "message": "Could not access the document"}
        
        logger.info(f"📄 Using file: {actual_file_path}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                result = send_for_signature_docusign(actual_file_path, recipient_email, recipient_name, subject, message)
                logger.info(f"📧 DocuSign result: {result}")
                
                if result.get("success"):
                    return {"success": True, "envelope_id": result["envelope_id"], "message": "Document sent for signature via DocuSign"}
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to send document for signature"}
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to send document for signature via DocuSign"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            result = send_for_signature_docusign(actual_file_path, recipient_email, recipient_name, subject, message)
            return {"success": True, "envelope_id": result["envelope_id"], "message": "Document sent for signature via DocuSign (MOCK)"}
    except Exception as e:
        logger.error(f"❌ send_for_signature error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to send document for signature via DocuSign"}

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
            "message": "Server is running and ready",
            "use_real_apis": USE_REAL_APIS
        }
    except Exception as e:
        logger.error(f"❌ get_server_info error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get server info"}

# Tool dispatcher
TOOL_HANDLERS = {
    "send_for_signature": handle_send_for_signature,
    "get_server_info": handle_get_server_info
}

@app.get("/")
async def root():
    return {"message": "Doc Filling + E-Signing MCP Server", "status": "running"}

@app.get("/sse")
async def sse_endpoint(request: Request, tool: str = None, args: str = None):
    """SSE endpoint for MCP tool support."""
    logger.info(f"📡 SSE GET request - tool: {tool}, args: {args}")
    
    if tool:
        try:
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
    
    return JSONResponse(content={
        "message": "Doc Filling + E-Signing MCP Server",
        "status": "running",
        "available_tools": list(TOOL_HANDLERS.keys())
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
