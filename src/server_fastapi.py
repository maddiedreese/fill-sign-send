#!/usr/bin/env python3
"""
DocuSign MCP Server using FastMCP
Based on the InteractionCo/mcp-server-template
"""
import json
import sys
import os
import logging
from typing import Dict, Any
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastmcp import FastMCP

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

# Create the MCP server
mcp = FastMCP("fill-sign-send-mcp-server")

@mcp.tool()
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

@mcp.tool()
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
                    "next_steps": "You can now open the document for signing using 'open_document_for_signing'"
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp, host="0.0.0.0", port=8000)
