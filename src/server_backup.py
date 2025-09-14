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
from fastapi import FastAPI, Request, HTTPException
# Import SSE handler with fallback
try:
    from src.sse_handler import handle_mcp_sse
except ImportError:
    from sse_handler import handle_mcp_sse
from pydantic import BaseModel
import uvicorn
import time

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
    pass


# SSE endpoint for Poke compatibility
@app.get("/sse")
@app.post("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for Poke MCP compatibility."""
    return await handle_mcp_sse(request)

# MCP endpoint for protocol communication
@app.get("/mcp")
async def mcp_get():
    """GET endpoint for MCP server health check."""
    return {"message": "MCP server is running", "status": "healthy"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """POST endpoint for MCP protocol communication."""
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id", 1)
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
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
                "id": request_id,
                "result": {
                    "tools": list(MCP_TOOLS.values())
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name == "detect_pdf_fields":
                result = detect_pdf_fields_impl(tool_args.get("file_url", ""))
            elif tool_name == "fill_pdf_fields":
                result = fill_pdf_fields_impl(tool_args.get("file_url", ""), tool_args.get("field_values", {}))
            elif tool_name == "send_for_signature":
                result = send_for_signature_impl(
                    tool_args.get("file_url", ""),
                    tool_args.get("recipient_email", ""),
                    tool_args.get("recipient_name", ""),
                    tool_args.get("subject", "Please sign this document"),
                    tool_args.get("message", "Please review and sign this document.")
                )
            elif tool_name == "check_signature_status":
                result = check_signature_status_impl(tool_args.get("envelope_id", ""))
            elif tool_name == "download_signed_pdf":
                result = download_signed_pdf_impl(tool_args.get("envelope_id", ""))
            elif tool_name == "notify_poke":
                result = notify_poke_impl(tool_args.get("message", ""), tool_args.get("attachments", []))
            elif tool_name == "get_server_info":
                result = get_server_info_impl()
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", 1) if "body" in locals() else 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )

# SSE endpoint for Poke compatibility
async def sse_endpoint(request: Request):
    """SSE endpoint for Poke MCP compatibility."""
    pass

