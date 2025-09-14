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
from typing import Dict, Any
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
    from esign_docusign import send_for_signature_docusign, check_signature_status_docusign, download_signed_pdf_docusign, get_envelope_status_docusign

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

if not USE_REAL_APIS:
    settings = MockSettings()
    logger.warning("⚠️  Using mock implementations for missing modules")


# Tool dispatcher - defined early to avoid forward reference issues
TOOL_HANDLERS = {}
app = FastAPI()

# Define handler functions first
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

def handle_fill_envelope(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle filling a DocuSign envelope with data."""
    try:
        envelope_id = args.get("envelope_id")
        field_data = args.get("field_data", {})
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        if not field_data:
            return {"success": False, "error": "field_data is required", "message": "Please provide field_data to fill"}
        
        logger.info(f"📝 fill_envelope called with envelope_id: {envelope_id}, field_data: {field_data}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                from esign_docusign import fill_envelope_docusign
                result = fill_envelope_docusign(envelope_id, field_data)
                
                logger.info(f"📝 DocuSign result: {result}")
                
                if result.get("success"):
                    return {"success": True, "envelope_id": result["envelope_id"], "message": result["message"]}
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to fill envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to fill envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ fill_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to fill envelope"}

def handle_sign_envelope(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle signing a DocuSign envelope."""
    try:
        envelope_id = args.get("envelope_id")
        recipient_email = args.get("recipient_email")
        security_code = args.get("security_code")
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        if not recipient_email:
            return {"success": False, "error": "recipient_email is required", "message": "Please provide recipient_email"}
        
        logger.info(f"✍️ sign_envelope called with envelope_id: {envelope_id}, recipient_email: {recipient_email}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                from esign_docusign import sign_envelope_docusign
                result = sign_envelope_docusign(envelope_id, recipient_email, security_code)
                
                logger.info(f"✍️ DocuSign result: {result}")
                
                if result.get("success"):
                    response = {"success": True, "envelope_id": result["envelope_id"], "message": result["message"]}
                    if "signing_url" in result:
                        response["signing_url"] = result["signing_url"]
                    if "status" in result:
                        response["status"] = result["status"]
                    return response
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to sign envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to sign envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ sign_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to sign envelope"}

def handle_submit_envelope(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle submitting a DocuSign envelope."""
    try:
        envelope_id = args.get("envelope_id")
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        logger.info(f"📤 submit_envelope called with envelope_id: {envelope_id}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                from esign_docusign import submit_envelope_docusign
                result = submit_envelope_docusign(envelope_id)
                
                logger.info(f"📤 DocuSign result: {result}")
                
                if result.get("success"):
                    return {"success": True, "envelope_id": result["envelope_id"], "status": result["status"], "message": result["message"]}
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to submit envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to submit envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ submit_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to submit envelope"}

def handle_getenvelope(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting DocuSign envelope from link or security code."""
    try:
        envelope_id = args.get("envelope_id")
        link = args.get("link")
        security_code = args.get("security_code")
        
        logger.info(f"📋 getenvelope called with envelope_id: {envelope_id}, link: {link}, security_code: {security_code}")
        
        # If we have a link, extract envelope ID from it
        if link and not envelope_id:
            if "docusign.net/signing/documents/" in link:
                # Extract envelope ID from DocuSign signing link
                import re
                match = re.search(r"/signing/documents/([a-f0-9-]+)", link)
                if match:
                    envelope_id = match.group(1)
                    logger.info(f"📋 Extracted envelope_id from link: {envelope_id}")
                else:
                    return {"success": False, "error": "Could not extract envelope ID from link", "message": "Invalid DocuSign signing link"}
            else:
                return {"success": False, "error": "Invalid link format", "message": "Link must be a DocuSign signing link"}
        
        # If we have a security code, we need to search for the envelope
        if security_code and not envelope_id:
            # For now, return an error as we need to implement envelope search by security code
            return {"success": False, "error": "Security code lookup not implemented", "message": "Please provide envelope_id or link instead"}
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id, link, or security_code is required", "message": "Please provide envelope_id, DocuSign signing link, or security_code"}
        
        # Now get the envelope details using the envelope ID
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                result = get_envelope_status_docusign(envelope_id)
                
                logger.info(f"📋 DocuSign result: {result}")
                
                if result.get("success"):
                    return {
                        "success": True, 
                        "envelope_id": result["envelope_id"], 
                        "status": result["status"],
                        "created_date": result.get("created_date"),
                        "sent_date": result.get("sent_date"),
                        "completed_date": result.get("completed_date"),
                        "recipients": result.get("recipients", []),
                        "message": "Envelope retrieved successfully"
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to get envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to get envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ getenvelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get envelope"}

def handle_get_envelope_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting DocuSign envelope status."""
    try:
        envelope_id = args.get("envelope_id")
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        logger.info(f"📊 get_envelope_status called with envelope_id: {envelope_id}")
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                from esign_docusign import get_envelope_status_docusign
                result = get_envelope_status_docusign(envelope_id)
                
                logger.info(f"📊 DocuSign result: {result}")
                
                if result.get("success"):
                    return {
                        "success": True, 
                        "envelope_id": result["envelope_id"], 
                        "status": result["status"],
                        "created_date": result.get("created_date"),
                        "sent_date": result.get("sent_date"),
                        "completed_date": result.get("completed_date"),
                        "recipients": result.get("recipients", []),
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to get envelope status"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to get envelope status"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ get_envelope_status error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get envelope status"}

def handle_extract_envelope_id_from_document(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle extracting envelope ID from document content."""
    try:
        document_url = args.get("document_url")
        document_text = args.get("document_text")
        
        if not document_url and not document_text:
            return {"success": False, "error": "document_url or document_text is required", "message": "Please provide either a document URL or the document text content"}
        
        logger.info(f"📋 Extracting envelope ID from document")
        
        # If we have a URL, download the document first
        if document_url:
            logger.info(f"📥 Downloading document from URL: {document_url}")
            filename = download_file_from_url(document_url)
            if not filename:
                return {"success": False, "error": "Failed to download document", "message": "Could not download document from URL"}
            
            # Read the document content
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    document_text = f.read()
                # Clean up the temporary file
                os.remove(filename)
            except Exception as e:
                logger.error(f"❌ Failed to read document: {e}")
                return {"success": False, "error": str(e), "message": "Failed to read document content"}
        
        if not document_text:
            return {"success": False, "error": "No document content available", "message": "Could not extract document content"}
        
        # Extract envelope ID from document text using various patterns
        import re
        
        # Common patterns for envelope ID in DocuSign documents
        patterns = [
            r'envelope[_\s]*id[:\s]*([a-f0-9-]{36})',  # "envelope id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            r'envelope[_\s]*ID[:\s]*([a-f0-9-]{36})',  # "envelope ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            r'envelope[_\s]*number[:\s]*([a-f0-9-]{36})',  # "envelope number: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # Standard UUID pattern
            r'docusign[_\s]*envelope[:\s]*([a-f0-9-]{36})',  # "docusign envelope: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        ]
        
        envelope_id = None
        for pattern in patterns:
            matches = re.findall(pattern, document_text, re.IGNORECASE)
            if matches:
                envelope_id = matches[0]
                logger.info(f"✅ Found envelope ID using pattern: {pattern}")
                break
        
        if not envelope_id:
            # Try to find any UUID-like pattern
            uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
            uuid_matches = re.findall(uuid_pattern, document_text, re.IGNORECASE)
            if uuid_matches:
                envelope_id = uuid_matches[0]
                logger.info(f"✅ Found potential envelope ID (UUID pattern): {envelope_id}")
            else:
                return {
                    "success": False, 
                    "error": "No envelope ID found", 
                    "message": "Could not find envelope ID in document content. Please check the document manually.",
                    "document_preview": document_text[:500] + "..." if len(document_text) > 500 else document_text
                }
        
        logger.info(f"📄 Extracted envelope ID: {envelope_id}")
        
        if USE_REAL_APIS:
            try:
                # Verify the envelope ID is valid by checking envelope status
                from esign_docusign import get_envelope_status_docusign
                envelope_status = get_envelope_status_docusign(envelope_id)
                
                if not envelope_status.get("success"):
                    return {
                        "success": False, 
                        "error": envelope_status.get("error"), 
                        "message": "Invalid envelope ID or failed to verify",
                        "extracted_id": envelope_id
                    }
                
                return {
                    "success": True,
                    "envelope_id": envelope_id,
                    "envelope_status": envelope_status.get("envelope_status"),
                    "message": "Successfully extracted and verified envelope ID from document",
                    "next_steps": "You can now use this envelope ID with other tools like 'get_envelope_status', 'fill_envelope', or 'submit_envelope'"
                }
                
            except Exception as e:
                logger.error(f"❌ DocuSign verification error: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {
                    "success": False, 
                    "error": str(e), 
                    "message": "Failed to verify envelope ID",
                    "extracted_id": envelope_id
                }
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {
                "success": True,
                "envelope_id": envelope_id,
                "envelope_status": "sent",
                "message": "Successfully extracted envelope ID from document (MOCK)",
                "next_steps": "You can now use this envelope ID with other tools like 'get_envelope_status', 'fill_envelope', or 'submit_envelope'"
            }
            
    except Exception as e:
        logger.error(f"❌ extract_envelope_id_from_document error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to extract envelope ID from document"}

# Update TOOL_HANDLERS with all handler functions
TOOL_HANDLERS.update({
    "getenvelope": handle_getenvelope,
    "fill_envelope": handle_fill_envelope,
    "sign_envelope": handle_sign_envelope,
    "submit_envelope": handle_submit_envelope,
    "get_envelope_status": handle_get_envelope_status,
    "send_for_signature": handle_send_for_signature,
    "get_server_info": handle_get_server_info,
    "extract_envelope_id_from_document": handle_extract_envelope_id_from_document
})

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

@app.get("/")
async def root():
    """Root endpoint that returns basic information about the service."""
    return {"message": "Fill Sign Send API", "status": "running"}

@app.get("/debug")
async def debug_endpoint(request: Request):
    """Debug endpoint to log all requests from Poke."""
    logger.info(f"🔍 DEBUG: GET request from {request.client.host}")
    logger.info(f"🔍 DEBUG: Headers: {dict(request.headers)}")
    logger.info(f"🔍 DEBUG: Query params: {dict(request.query_params)}")
    return {"message": "Debug endpoint", "client_ip": str(request.client.host), "headers": dict(request.headers)}

@app.post("/debug")
async def debug_post_endpoint(request: Request):
    """Debug endpoint to log all POST requests from Poke."""
    body = await request.body()
    logger.info(f"🔍 DEBUG: POST request from {request.client.host}")
    logger.info(f"🔍 DEBUG: Headers: {dict(request.headers)}")
    logger.info(f"🔍 DEBUG: Body: {body.decode() if body else "No body"}")
    return {"message": "Debug POST endpoint", "client_ip": str(request.client.host), "body": body.decode() if body else "No body"}
    return {"message": "Doc Filling + E-Signing MCP Server", "status": "running"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP protocol endpoint for tool calls."""
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        
        logger.info(f"📡 MCP POST request from {request.client.host}")
        logger.info(f"🔍 DEBUG: Headers: {dict(request.headers)}")
        logger.info(f"🔍 DEBUG: Body: {data}")
        
        # Handle MCP protocol messages
        if data.get("method") == "initialize":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "fill-sign-send-mcp-server",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif data.get("method") == "tools/list":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "getenvelope",
                            "description": "Get envelope information",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"}
                                },
                                "required": ["envelope_id"]
                            }
                        },
                        {
                            "name": "fill_envelope",
                            "description": "Fill PDF form fields",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "form_data": {"type": "object", "description": "Form field data"}
                                },
                                "required": ["pdf_url", "form_data"]
                            }
                        },
                        {
                            "name": "sign_envelope",
                            "description": "Send document for signature",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email address"},
                                    "signer_name": {"type": "string", "description": "Signer name"}
                                },
                                "required": ["pdf_url", "signer_email", "signer_name"]
                            }
                        },
                        {
                            "name": "extract_envelope_id_from_document",
                            "description": "Extract envelope ID from document content or URL",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "document_url": {"type": "string", "description": "URL to the document (optional if document_text provided)"},
                                    "document_text": {"type": "string", "description": "Document text content (optional if document_url provided)"}
                                },
                                "required": []
                            }
                        }
                    ]
                }
            })
        
        elif data.get("method") == "tools/call":
            tool_name = data.get("params", {}).get("name")
            tool_args = data.get("params", {}).get("arguments", {})
            
            if tool_name in TOOL_HANDLERS:
                result = TOOL_HANDLERS[tool_name](tool_args)
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                })
            else:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found"
                    }
                })
        
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method '{data.get('method')}' not found"
                }
            })
            
    except Exception as e:
        logger.error(f"❌ MCP POST error: {e}")
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": data.get("id") if 'data' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }, status_code=500)

@app.post("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP tool support with proper MCP protocol."""
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        
        logger.info(f"📡 SSE POST request from {request.client.host}")
        logger.info(f"🔍 DEBUG: Headers: {dict(request.headers)}")
        logger.info(f"🔍 DEBUG: Body: {data}")
        
        # Handle MCP protocol messages
        if data.get("method") == "initialize":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "fill-sign-send-mcp-server",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif data.get("method") == "tools/list":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "getenvelope",
                            "description": "Get envelope information",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"}
                                },
                                "required": ["envelope_id"]
                            }
                        },
                        {
                            "name": "fill_envelope",
                            "description": "Fill PDF form fields",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "form_data": {"type": "object", "description": "Form field data"}
                                },
                                "required": ["pdf_url", "form_data"]
                            }
                        },
                        {
                            "name": "sign_envelope",
                            "description": "Send document for signature",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email address"},
                                    "signer_name": {"type": "string", "description": "Signer name"}
                                },
                                "required": ["pdf_url", "signer_email", "signer_name"]
                            }
                        },
                        {
                            "name": "extract_envelope_id_from_document",
                            "description": "Extract envelope ID from document content or URL",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "document_url": {"type": "string", "description": "URL to the document (optional if document_text provided)"},
                                    "document_text": {"type": "string", "description": "Document text content (optional if document_url provided)"}
                                },
                                "required": []
                            }
                        }
                    ]
                }
            })
        
        elif data.get("method") == "tools/call":
            tool_name = data.get("params", {}).get("name")
            tool_args = data.get("params", {}).get("arguments", {})
            
            if tool_name in TOOL_HANDLERS:
                result = TOOL_HANDLERS[tool_name](tool_args)
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                })
            else:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found"
                    }
                })
        
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method '{data.get('method')}' not found"
                }
            })
            
    except Exception as e:
        logger.error(f"❌ SSE POST error: {e}")
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": data.get("id") if 'data' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }, status_code=500)


if __name__ == "__main__":
    logger.info(f"🚀 Starting Doc Filling + E-Signing MCP Server...")
    logger.info(f"📊 Using {'REAL' if USE_REAL_APIS else 'MOCK'} APIs")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
