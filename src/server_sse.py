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

# Import real implementations with proper error handling
try:
    from settings import settings
    from esign_docusign import (
        get_envelope_status_docusign, 
        fill_envelope_docusign, 
        sign_envelope_docusign,
        create_demo_envelope_docusign,
        create_recipient_view_with_code
    )
    logger.info("✅ Successfully imported all modules")
    USE_REAL_APIS = True
except ImportError as e:
    logger.error(f"⚠️  Import error: {e}")
    USE_REAL_APIS = False

app = FastAPI(title="DocuSign MCP Server")

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def getenvelope(envelope_id: str) -> Dict[str, Any]:
    """Get DocuSign envelope information and status."""
    logger.info(f"📋 Getting envelope status for: {envelope_id}")
    
    if USE_REAL_APIS:
        try:
            result = get_envelope_status_docusign(envelope_id)
            if result.get("success"):
                return {
                    "success": True,
                    "envelope_id": result.get("envelope_id"),
                    "status": result.get("status"),
                    "created_date": result.get("created_date"),
                    "sent_date": result.get("sent_date"),
                    "completed_date": result.get("completed_date"),
                    "recipients": result.get("recipients", []),
                    "message": result.get("message", "Envelope retrieved successfully")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": result.get("message", "Failed to get envelope")
                }
        except Exception as e:
            logger.error(f"❌ DocuSign API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "DocuSign API error occurred"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

def fill_document_fields(envelope_id: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fill form fields in existing DocuSign document."""
    logger.info(f"📝 Filling document fields for envelope: {envelope_id}")
    logger.info(f"📊 Field data: {field_data}")
    
    if USE_REAL_APIS:
        try:
            result = fill_envelope_docusign(envelope_id, field_data)
            if result.get("success"):
                return {
                    "success": True,
                    "envelope_id": envelope_id,
                    "filled_fields": result.get("filled_fields", []),
                    "message": result.get("message", "Document fields filled successfully"),
                    "next_steps": "You can now open the document for signing using 'sign_envelope'"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": result.get("message", "Failed to fill document fields")
                }
        except Exception as e:
            logger.error(f"❌ DocuSign API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "DocuSign API error occurred"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

def sign_envelope(envelope_id: str, recipient_email: str, security_code: str = None) -> Dict[str, Any]:
    """Sign existing DocuSign envelope."""
    logger.info(f"✍️ Signing envelope: {envelope_id}")
    logger.info(f"📧 Recipient email: {recipient_email}")
    
    if USE_REAL_APIS:
        try:
            result = sign_envelope_docusign(envelope_id, recipient_email, security_code)
            if result.get("success"):
                return {
                    "success": True,
                    "envelope_id": envelope_id,
                    "message": result.get("message", f"Envelope {envelope_id} status: {result.get('status', 'unknown')}"),
                    "status": result.get("status", "unknown")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": result.get("message", "Failed to sign envelope")
                }
        except Exception as e:
            logger.error(f"❌ DocuSign API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "DocuSign API error occurred"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

def create_demo_envelope(pdf_url: str, signer_email: str = "test@example.com", signer_name: str = "Test Signer", subject: str = None, message: str = None) -> Dict[str, Any]:
    """Create a demo envelope for testing in DocuSign demo environment."""
    logger.info(f"📄 Creating demo envelope with PDF: {pdf_url}")
    logger.info(f"📧 Signer: {signer_name} <{signer_email}>")
    
    if USE_REAL_APIS:
        try:
            result = create_demo_envelope_docusign(pdf_url, signer_email, signer_name, subject, message)
            if result.get("success"):
                return {
                    "success": True,
                    "envelope_id": result.get("envelope_id"),
                    "signer_email": signer_email,
                    "signer_name": signer_name,
                    "subject": result.get("subject", "Demo Document for Testing"),
                    "message": result.get("message", "Demo envelope created successfully"),
                    "next_steps": [
                        "1. Use 'getenvelope' to check the envelope status",
                        "2. Use 'fill_document_fields' to fill any form fields",
                        "3. Use 'sign_envelope' to complete signing",
                        "4. Check your email for the signing link"
                    ],
                    "note": "This envelope was created in the demo environment and can be used for testing"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": result.get("message", "Failed to create demo envelope")
                }
        except Exception as e:
            logger.error(f"❌ DocuSign API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "DocuSign API error occurred"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

def create_recipient_view_with_code(envelope_id: str, recipient_email: str, access_code: str, return_url: str = "https://www.docusign.com") -> Dict[str, Any]:
    """Create recipient view URL using access code for document access."""
    logger.info(f"🔗 Creating recipient view for envelope: {envelope_id}")
    logger.info(f"📧 Recipient: {recipient_email}")
    logger.info(f"🔑 Access code: {access_code}")
    
    if USE_REAL_APIS:
        try:
            result = create_recipient_view_with_code(envelope_id, recipient_email, access_code, return_url)
            if result.get("success"):
                return {
                    "success": True,
                    "signing_url": result.get("signing_url"),
                    "envelope_id": envelope_id,
                    "recipient_email": recipient_email,
                    "message": "Recipient view URL created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "message": "Failed to create recipient view"
                }
        except Exception as e:
            logger.error(f"❌ DocuSign API exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "DocuSign API error occurred"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

def debug_docusign_config() -> Dict[str, Any]:
    """Debug DocuSign configuration and environment settings."""
    logger.info("🔍 Debugging DocuSign configuration")
    
    if USE_REAL_APIS:
        try:
            return {
                "success": True,
                "environment": settings.ENVIRONMENT,
                "docusign_base_path": settings.DOCUSIGN_BASE_PATH,
                "docusign_account_id": settings.DOCUSIGN_ACCOUNT_ID,
                "docusign_integration_key": settings.DOCUSIGN_INTEGRATION_KEY,
                "docusign_user_id": settings.DOCUSIGN_USER_ID,
                "has_private_key": bool(settings.DOCUSIGN_PRIVATE_KEY),
                "message": "DocuSign configuration retrieved successfully",
                "troubleshooting": {
                    "common_issues": [
                        "404 errors: Check if envelope ID exists in the correct DocuSign environment",
                        "Authentication errors: Verify integration key and private key",
                        "Account ID errors: Ensure account ID matches the DocuSign environment"
                    ],
                    "environment_check": f"Using {settings.DOCUSIGN_BASE_PATH} environment",
                    "account_check": f"Account ID: {settings.DOCUSIGN_ACCOUNT_ID}"
                }
            }
        except Exception as e:
            logger.error(f"❌ Configuration error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve DocuSign configuration"
            }
    else:
        return {
            "success": False,
            "error": "DocuSign not available",
            "message": "DocuSign integration not available"
        }

@app.get("/")
async def root():
    return {"message": "DocuSign MCP Server is running", "status": "healthy"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP endpoint that returns Server-Sent Events format like the template."""
    try:
        # Get the raw body
        body = await request.body()
        logger.info(f"📨 Received request: {body}")
        
        # Parse JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            return Response(
                content=f"event: message\ndata: {json.dumps(error_response)}\n\n",
                media_type="text/event-stream"
            )
        
        # Handle different MCP methods
        method = data.get("method")
        request_id = data.get("id")
        params = data.get("params", {})
        
        logger.info(f"🔧 Processing method: {method}")
        
        if method == "initialize":
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "experimental": {},
                        "prompts": {"listChanged": True},
                        "resources": {"subscribe": False, "listChanged": True},
                        "tools": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "DocuSign MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
            return Response(
                content=f"event: message\ndata: {json.dumps(response_data)}\n\n",
                media_type="text/event-stream"
            )
        
        elif method == "tools/list":
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "getenvelope",
                            "description": "Get DocuSign envelope information and status",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "title": "Envelope Id"}
                                },
                                "required": ["envelope_id"]
                            }
                        },
                        {
                            "name": "fill_document_fields",
                            "description": "Fill form fields in existing DocuSign document",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "title": "Envelope Id"},
                                    "field_data": {"type": "object", "title": "Field Data"}
                                },
                                "required": ["envelope_id", "field_data"]
                            }
                        },
                        {
                            "name": "sign_envelope",
                            "description": "Sign existing DocuSign envelope",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "title": "Envelope Id"},
                                    "recipient_email": {"type": "string", "title": "Recipient Email"},
                                    "security_code": {"type": "string", "title": "Security Code", "default": None}
                                },
                                "required": ["envelope_id", "recipient_email"]
                            }
                        },
                        {
                            "name": "create_demo_envelope",
                            "description": "Create a demo envelope for testing in DocuSign demo environment",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "title": "Pdf Url"},
                                    "signer_email": {"type": "string", "title": "Signer Email", "default": "test@example.com"},
                                    "signer_name": {"type": "string", "title": "Signer Name", "default": "Test Signer"},
                                    "subject": {"type": "string", "title": "Subject", "default": None},
                                    "message": {"type": "string", "title": "Message", "default": None}
                                },
                                "required": ["pdf_url"]
                            }
                        },
                        {
                            "name": "create_recipient_view_with_code",
                            "description": "Create recipient view URL using access code for document access",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "title": "Envelope Id"},
                                    "recipient_email": {"type": "string", "title": "Recipient Email"},
                                    "access_code": {"type": "string", "title": "Access Code"},
                                    "return_url": {"type": "string", "title": "Return Url", "default": "https://www.docusign.com"}
                                },
                                "required": ["envelope_id", "recipient_email", "access_code"]
                            }
                        },
                        {
                            "name": "debug_docusign_config",
                            "description": "Debug DocuSign configuration and environment settings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
            return Response(
                content=f"event: message\ndata: {json.dumps(response_data)}\n\n",
                media_type="text/event-stream"
            )
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"🔧 Calling tool: {tool_name} with args: {arguments}")
            
            if tool_name == "getenvelope":
                result = getenvelope(arguments.get("envelope_id", ""))
            elif tool_name == "fill_document_fields":
                result = fill_document_fields(arguments.get("envelope_id", ""), arguments.get("field_data", {}))
            elif tool_name == "sign_envelope":
                result = sign_envelope(
                    arguments.get("envelope_id", ""),
                    arguments.get("recipient_email", ""),
                    arguments.get("security_code")
                )
            elif tool_name == "create_demo_envelope":
                result = create_demo_envelope(
                    arguments.get("pdf_url", ""),
                    arguments.get("signer_email", "test@example.com"),
                    arguments.get("signer_name", "Test Signer"),
                    arguments.get("subject"),
                    arguments.get("message")
                )
            elif tool_name == "create_recipient_view_with_code":
                result = create_recipient_view_with_code(
                    arguments.get("envelope_id", ""),
                    arguments.get("recipient_email", ""),
                    arguments.get("access_code", ""),
                    arguments.get("return_url", "https://www.docusign.com")
                )
            elif tool_name == "debug_docusign_config":
                result = debug_docusign_config()
            else:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}
            
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "structuredContent": result,
                    "isError": False
                }
            }
            return Response(
                content=f"event: message\ndata: {json.dumps(response_data)}\n\n",
                media_type="text/event-stream"
            )
        
        else:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
            return Response(
                content=f"event: message\ndata: {json.dumps(error_response)}\n\n",
                media_type="text/event-stream"
            )
    
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }
        return Response(
            content=f"event: message\ndata: {json.dumps(error_response)}\n\n",
            media_type="text/event-stream"
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting SSE-compatible MCP server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
