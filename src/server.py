#!/usr/bin/env python3
"""
MCP Doc Filling + E-Signing Server
Provides tools for PDF form detection, filling, and e-signature workflows.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
try:
    from .settings import settings
    from .pdf_utils import fetch_pdf, extract_acroform_fields, fill_and_flatten, save_temp_pdf
    from .esign_docusign import (
        send_for_signature_docusign, 
        get_status_docusign, 
        download_completed_pdf_docusign,
        validate_docusign_config
    )
    from .esign_adobe import (
        send_for_signature_adobe,
        get_status_adobe,
        download_completed_pdf_adobe,
        validate_adobe_config
    )
except ImportError:
    from settings import settings
    from pdf_utils import fetch_pdf, extract_acroform_fields, fill_and_flatten, save_temp_pdf
    from esign_docusign import (
        send_for_signature_docusign, 
        get_status_docusign, 
        download_completed_pdf_docusign,
        validate_docusign_config
    )
    from esign_adobe import (
        send_for_signature_adobe,
        get_status_adobe,
        download_completed_pdf_adobe,
        validate_adobe_config
    )

# Pydantic models for MCP protocol
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

# FastAPI app
app = FastAPI(title="Doc Filling + E-Signing MCP Server", version="1.0.0")

# MCP Tools Definition
MCP_TOOLS = {
    "detect_pdf_fields": {
        "name": "detect_pdf_fields",
        "description": "Detect form fields in a PDF document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {
                    "type": "string",
                    "description": "URL or path to the PDF file"
                }
            },
            "required": ["file_url"]
        }
    },
    "fill_pdf_fields": {
        "name": "fill_pdf_fields",
        "description": "Fill PDF form fields with provided values and return flattened PDF",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_url": {
                    "type": "string",
                    "description": "URL or path to the PDF file"
                },
                "field_values": {
                    "type": "object",
                    "description": "Dictionary mapping field names to values"
                }
            },
            "required": ["file_url", "field_values"]
        }
    },
    "send_for_signature": {
        "name": "send_for_signature",
        "description": "Send a PDF for e-signature via DocuSign or Adobe Sign",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": ["docusign", "adobe"],
                    "description": "E-signature service to use"
                },
                "recipients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "name": {"type": "string"}
                        },
                        "required": ["email", "name"]
                    },
                    "description": "List of recipients for signing"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject for the signature request"
                },
                "message": {
                    "type": "string",
                    "description": "Email message for the signature request"
                },
                "file_url": {
                    "type": "string",
                    "description": "URL or path to the PDF file to be signed"
                }
            },
            "required": ["service", "recipients", "subject", "message", "file_url"]
        }
    },
    "check_signature_status": {
        "name": "check_signature_status",
        "description": "Check the status of a signature envelope",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": ["docusign", "adobe"],
                    "description": "E-signature service used"
                },
                "envelope_id": {
                    "type": "string",
                    "description": "Envelope ID from the signature service"
                }
            },
            "required": ["service", "envelope_id"]
        }
    },
    "download_signed_pdf": {
        "name": "download_signed_pdf",
        "description": "Download the completed signed PDF",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "enum": ["docusign", "adobe"],
                    "description": "E-signature service used"
                },
                "envelope_id": {
                    "type": "string",
                    "description": "Envelope ID from the signature service"
                }
            },
            "required": ["service", "envelope_id"]
        }
    },
    "notify_poke": {
        "name": "notify_poke",
        "description": "Send a notification to Poke via webhook",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to send to Poke"
                },
                "thread_ref": {
                    "type": "string",
                    "description": "Optional thread reference"
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "url": {"type": "string"}
                        }
                    },
                    "description": "Optional attachments"
                }
            },
            "required": ["message"]
        }
    },
    "get_server_info": {
        "name": "get_server_info",
        "description": "Get information about the MCP server",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
}

# Tool Implementation Functions
def detect_pdf_fields_impl(file_url: str) -> Dict[str, Any]:
    """Detect form fields in a PDF document."""
    try:
        pdf_bytes = fetch_pdf(file_url)
        fields = extract_acroform_fields(pdf_bytes)
        
        return {
            "success": True,
            "fields": fields,
            "field_count": len(fields)
        }
    except Exception as e:
        raise ValueError(f"Failed to detect PDF fields: {e}")

def fill_pdf_fields_impl(file_url: str, field_values: Dict[str, Any]) -> Dict[str, Any]:
    """Fill PDF form fields with provided values."""
    try:
        pdf_bytes = fetch_pdf(file_url)
        filled_pdf_bytes = fill_and_flatten(pdf_bytes, field_values)
        
        # Save to temporary file for local access
        temp_path = save_temp_pdf(filled_pdf_bytes, "filled_pdf_")
        
        return {
            "success": True,
            "file_url": f"file://{temp_path}",
            "message": "PDF filled and flattened successfully"
        }
    except Exception as e:
        raise ValueError(f"Failed to fill PDF fields: {e}")

def send_for_signature_impl(service: str, recipients: List[Dict[str, str]], subject: str, message: str, file_url: str) -> Dict[str, Any]:
    """Send a PDF for e-signature."""
    try:
        if not recipients:
            raise ValueError("At least one recipient is required")
        
        for recipient in recipients:
            if not recipient.get("email") or not recipient.get("name"):
                raise ValueError("Each recipient must have 'email' and 'name' fields")
        
        pdf_bytes = fetch_pdf(file_url)
        
        if service.lower() == "docusign":
            if not settings.validate_docusign_config():
                raise ValueError("DocuSign is not properly configured. Please set required environment variables.")
            
            envelope_id = send_for_signature_docusign(recipients, subject, message, pdf_bytes)
            
            return {
                "success": True,
                "envelope_id": envelope_id,
                "service": "docusign",
                "message": "Envelope sent for signature successfully"
            }
            
        elif service.lower() == "adobe":
            if not validate_adobe_config():
                raise ValueError("Adobe Sign is not properly configured.")
            
            agreement_id = send_for_signature_adobe(recipients, subject, message, pdf_bytes)
            
            return {
                "success": True,
                "agreement_id": agreement_id,
                "service": "adobe",
                "message": "Agreement sent for signature successfully"
            }
        else:
            raise ValueError("Service must be 'docusign' or 'adobe'")
            
    except Exception as e:
        raise ValueError(f"Failed to send for signature: {e}")

def check_signature_status_impl(service: str, envelope_id: str) -> Dict[str, Any]:
    """Check the status of a signature envelope."""
    try:
        if service.lower() not in ["docusign", "adobe"]:
            raise ValueError("Service must be 'docusign' or 'adobe'")
        
        if service.lower() == "docusign":
            if not settings.validate_docusign_config():
                raise ValueError("DocuSign is not properly configured.")
            
            status = get_status_docusign(envelope_id)
            
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": status,
                "service": "docusign"
            }
            
        elif service.lower() == "adobe":
            if not validate_adobe_config():
                raise ValueError("Adobe Sign is not properly configured.")
            
            status = get_status_adobe(envelope_id)
            
            return {
                "success": True,
                "agreement_id": envelope_id,
                "status": status,
                "service": "adobe"
            }
            
    except Exception as e:
        raise ValueError(f"Failed to check signature status: {e}")

def download_signed_pdf_impl(service: str, envelope_id: str) -> Dict[str, Any]:
    """Download the completed signed PDF."""
    try:
        if service.lower() not in ["docusign", "adobe"]:
            raise ValueError("Service must be 'docusign' or 'adobe'")
        
        if service.lower() == "docusign":
            if not settings.validate_docusign_config():
                raise ValueError("DocuSign is not properly configured.")
            
            signed_pdf_bytes = download_completed_pdf_docusign(envelope_id)
            
        elif service.lower() == "adobe":
            if not validate_adobe_config():
                raise ValueError("Adobe Sign is not properly configured.")
            
            signed_pdf_bytes = download_completed_pdf_adobe(envelope_id)
        
        # Save to temporary file for local access
        temp_path = save_temp_pdf(signed_pdf_bytes, "signed_pdf_")
        
        return {
            "success": True,
            "file_url": f"file://{temp_path}",
            "envelope_id": envelope_id,
            "service": service,
            "message": "Signed PDF downloaded successfully"
        }
            
    except Exception as e:
        raise ValueError(f"Failed to download signed PDF: {e}")

def notify_poke_impl(message: str, thread_ref: Optional[str] = None, attachments: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Send a notification to Poke via webhook."""
    try:
        if not settings.validate_poke_config():
            raise ValueError("Poke API key is not configured.")
        
        import requests
        
        payload = {
            "message": message,
            "thread_ref": thread_ref,
            "attachments": attachments or []
        }
        
        headers = {
            "Authorization": f"Bearer {settings.POKE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(settings.POKE_WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        return {
            "success": True,
            "message": "Notification sent to Poke successfully",
            "status_code": response.status_code
        }
        
    except Exception as e:
        raise ValueError(f"Failed to notify Poke: {e}")

def get_server_info_impl() -> Dict[str, Any]:
    """Get information about the MCP server."""
    return {
        "server_name": "Doc Filling + E-Signing MCP Server",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "python_version": sys.version.split()[0],
        "docusign_configured": settings.validate_docusign_config(),
        "adobe_configured": validate_adobe_config(),
        "poke_configured": settings.validate_poke_config()
    }

# MCP Protocol Endpoints
@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP protocol endpoint."""
    try:
        method = request.method
        params = request.params or {}
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
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
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "tools": list(MCP_TOOLS.values())
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "detect_pdf_fields":
                result = detect_pdf_fields_impl(**arguments)
            elif tool_name == "fill_pdf_fields":
                result = fill_pdf_fields_impl(**arguments)
            elif tool_name == "send_for_signature":
                result = send_for_signature_impl(**arguments)
            elif tool_name == "check_signature_status":
                result = check_signature_status_impl(**arguments)
            elif tool_name == "download_signed_pdf":
                result = download_signed_pdf_impl(**arguments)
            elif tool_name == "notify_poke":
                result = notify_poke_impl(**arguments)
            elif tool_name == "get_server_info":
                result = get_server_info_impl()
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}",
                        "data": None
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}",
                    "data": None
                }
            }
    
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}",
                "data": None
            }
        }

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {
        "message": "Doc Filling + E-Signing MCP Server",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Starting Doc Filling + E-Signing MCP server on 0.0.0.0:8000")
    print("MCP endpoint will be available at: http://0.0.0.0:8000/mcp")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
