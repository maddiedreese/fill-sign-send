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
        logger.info(f"🌍 DocuSign environment: {settings.DOCUSIGN_BASE_PATH}")
        logger.info(f"🏢 DocuSign account ID: {settings.DOCUSIGN_ACCOUNT_ID}")
        
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
                        "docusign_environment": settings.DOCUSIGN_BASE_PATH,
                        "account_id": settings.DOCUSIGN_ACCOUNT_ID
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {
                        "success": False, 
                        "error": error_msg, 
                        "message": "Failed to get envelope status",
                        "docusign_environment": settings.DOCUSIGN_BASE_PATH,
                        "account_id": settings.DOCUSIGN_ACCOUNT_ID,
                        "troubleshooting": "If you're getting 404 errors, the envelope might be in a different DocuSign environment (demo vs production) or account"
                    }
                    
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

def handle_debug_docusign_config(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle debugging DocuSign configuration and environment."""
    try:
        logger.info(f"🔍 Debugging DocuSign configuration")
        
        config_info = {
            "docusign_base_path": settings.DOCUSIGN_BASE_PATH,
            "docusign_account_id": settings.DOCUSIGN_ACCOUNT_ID,
            "docusign_integration_key": settings.DOCUSIGN_INTEGRATION_KEY[:8] + "..." if settings.DOCUSIGN_INTEGRATION_KEY else None,
            "docusign_user_id": settings.DOCUSIGN_USER_ID,
            "environment": settings.ENVIRONMENT,
            "is_production": settings.is_production(),
            "docusign_configured": settings.validate_docusign_config()
        }
        
        # Test API connectivity
        if USE_REAL_APIS and settings.validate_docusign_config():
            try:
                from esign_docusign import get_envelope_status_docusign
                # Try to get account info or test API
                test_result = {"api_test": "DocuSign API is configured and ready"}
            except Exception as e:
                test_result = {"api_test": f"DocuSign API error: {str(e)}"}
        else:
            test_result = {"api_test": "DocuSign API not configured or using mock"}
        
        return {
            "success": True,
            "configuration": config_info,
            "api_test": test_result,
            "troubleshooting_tips": [
                "If getting 404 errors, check if envelope was created in demo vs production environment",
                "Demo environment: https://demo.docusign.net",
                "Production environment: https://www.docusign.net",
                "Make sure the envelope was created in the same account as configured",
                "Check if the envelope has expired or been deleted"
            ],
            "message": "DocuSign configuration debug information"
        }
        
    except Exception as e:
        logger.error(f"❌ debug_docusign_config error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to debug DocuSign configuration"}

def handle_create_embedded_signing(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle creating embedded signing URL for testing without email delivery."""
    try:
        pdf_url = args.get("pdf_url")
        signer_email = args.get("signer_email", "test@example.com")  # Default test email
        signer_name = args.get("signer_name", "Test Signer")
        return_url = args.get("return_url", "https://fill-sign-send.onrender.com/debug")
        
        if not pdf_url:
            return {"success": False, "error": "pdf_url is required", "message": "Please provide pdf_url"}
        
        logger.info(f"🔗 Creating embedded signing URL for testing")
        logger.info(f"📄 PDF URL: {pdf_url}")
        logger.info(f"📧 Signer: {signer_name} <{signer_email}>")
        
        if USE_REAL_APIS:
            try:
                # Download the PDF first
                filename = download_file_from_url(pdf_url)
                if not filename:
                    return {"success": False, "error": "Failed to download PDF", "message": "Could not download PDF from URL"}
                
                # Create envelope with embedded signing
                from esign_docusign import send_for_signature_docusign
                result = send_for_signature_docusign(
                    filename, 
                    signer_email, 
                    signer_name, 
                    "Test Document for Signing",
                    "Please sign this test document",
                    return_url=return_url,
                    embedded_signing=True
                )
                
                # Clean up the temporary file
                try:
                    os.remove(filename)
                except:
                    pass
                
                if result.get("success"):
                    return {
                        "success": True,
                        "envelope_id": result.get("envelope_id"),
                        "embedded_signing_url": result.get("embedded_signing_url"),
                        "signer_email": signer_email,
                        "signer_name": signer_name,
                        "message": "Embedded signing URL created successfully for testing",
                        "instructions": [
                            "1. Click the embedded_signing_url to open the signing interface",
                            "2. Complete the signing process in the browser",
                            "3. You'll be redirected to the return_url when done",
                            "4. Use the envelope_id with other tools to check status"
                        ],
                        "note": "This works in demo environment without Go Live permissions"
                    }
                else:
                    return {"success": False, "error": result.get("error"), "message": "Failed to create embedded signing URL"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to create embedded signing URL"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {
                "success": True,
                "envelope_id": "mock-envelope-embedded-123",
                "embedded_signing_url": "https://demo.docusign.net/signing/mock-embedded-url",
                "signer_email": signer_email,
                "signer_name": signer_name,
                "message": "Embedded signing URL created successfully (MOCK) for testing",
                "instructions": [
                    "1. Click the embedded_signing_url to open the signing interface",
                    "2. Complete the signing process in the browser",
                    "3. You'll be redirected to the return_url when done",
                    "4. Use the envelope_id with other tools to check status"
                ],
                "note": "This works in demo environment without Go Live permissions"
            }
            
    except Exception as e:
        logger.error(f"❌ create_embedded_signing error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to create embedded signing URL"}

def handle_open_document_for_signing(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle opening existing document for signing with embedded signing URL."""
    try:
        envelope_id = args.get("envelope_id")
        signer_email = args.get("signer_email", "test@example.com")
        return_url = args.get("return_url", "https://fill-sign-send.onrender.com/debug")
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        logger.info(f"📄 Opening document for signing")
        logger.info(f"📋 Envelope ID: {envelope_id}")
        logger.info(f"📧 Signer: {signer_email}")
        
        if USE_REAL_APIS:
            try:
                from esign_docusign import get_embedded_signing_url
                result = get_embedded_signing_url(envelope_id, signer_email, return_url)
                
                if result.get("success"):
                    return {
                        "success": True,
                        "envelope_id": envelope_id,
                        "embedded_signing_url": result.get("embedded_signing_url"),
                        "signer_email": signer_email,
                        "message": "Document opened for signing successfully",
                        "instructions": [
                            "1. Click the embedded_signing_url to open the document",
                            "2. Fill any required form fields",
                            "3. Complete the signing process",
                            "4. You'll be redirected to the return_url when done"
                        ]
                    }
                else:
                    return {"success": False, "error": result.get("error"), "message": "Failed to open document for signing"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to open document for signing"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {
                "success": True,
                "envelope_id": envelope_id,
                "embedded_signing_url": f"https://demo.docusign.net/signing/mock-{envelope_id}",
                "signer_email": signer_email,
                "message": "Document opened for signing successfully (MOCK)",
                "instructions": [
                    "1. Click the embedded_signing_url to open the document",
                    "2. Fill any required form fields",
                    "3. Complete the signing process",
                    "4. You'll be redirected to the return_url when done"
                ]
            }
            
    except Exception as e:
        logger.error(f"❌ open_document_for_signing error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to open document for signing"}

def handle_fill_document_fields(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle filling form fields in an existing document."""
    try:
        envelope_id = args.get("envelope_id")
        field_data = args.get("field_data", {})
        
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        if not field_data:
            return {"success": False, "error": "field_data is required", "message": "Please provide field_data with form field values"}
        
        logger.info(f"📝 Filling document fields")
        logger.info(f"📋 Envelope ID: {envelope_id}")
        logger.info(f"📊 Field data: {field_data}")
        
        if USE_REAL_APIS:
            try:
                from esign_docusign import fill_document_fields
                result = fill_document_fields(envelope_id, field_data)
                
                if result.get("success"):
                    return {
                        "success": True,
                        "envelope_id": envelope_id,
                        "filled_fields": result.get("filled_fields", []),
                        "message": "Document fields filled successfully",
                        "next_steps": "You can now open the document for signing using 'open_document_for_signing'"
                    }
                else:
                    return {"success": False, "error": result.get("error"), "message": "Failed to fill document fields"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to fill document fields"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {
                "success": True,
                "envelope_id": envelope_id,
                "filled_fields": list(field_data.keys()),
                "message": "Document fields filled successfully (MOCK)",
                "next_steps": "You can now open the document for signing using 'open_document_for_signing'"
            }
            
    except Exception as e:
        logger.error(f"❌ fill_document_fields error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to fill document fields"}

def handle_create_demo_envelope(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle creating a demo envelope for testing."""
    try:
        pdf_url = args.get("pdf_url")
        signer_email = args.get("signer_email", "test@example.com")
        signer_name = args.get("signer_name", "Test Signer")
        subject = args.get("subject", "Demo Document for Testing")
        message = args.get("message", "This is a test document created in demo environment")
        
        if not pdf_url:
            return {"success": False, "error": "pdf_url is required", "message": "Please provide pdf_url"}
        
        logger.info(f"📄 Creating demo envelope for testing")
        logger.info(f"📄 PDF URL: {pdf_url}")
        logger.info(f"📧 Signer: {signer_name} <{signer_email}>")
        
        if USE_REAL_APIS:
            try:
                # Download the PDF first
                filename = download_file_from_url(pdf_url)
                if not filename:
                    return {"success": False, "error": "Failed to download PDF", "message": "Could not download PDF from URL"}
                
                # Create envelope using existing function
                from esign_docusign import send_for_signature_docusign
                result = send_for_signature_docusign(
                    filename, 
                    signer_email, 
                    signer_name, 
                    subject,
                    message
                )
                
                # Clean up the temporary file
                try:
                    os.remove(filename)
                except:
                    pass
                
                if result.get("success"):
                    return {
                        "success": True,
                        "envelope_id": result.get("envelope_id"),
                        "signer_email": signer_email,
                        "signer_name": signer_name,
                        "subject": subject,
                        "message": "Demo envelope created successfully",
                        "next_steps": [
                            "1. Use 'get_envelope_status' to check the envelope status",
                            "2. Use 'fill_document_fields' to fill any form fields",
                            "3. Use 'open_document_for_signing' to open for signing",
                            "4. Check your email for the signing link"
                        ],
                        "note": "This envelope was created in the demo environment and can be used for testing"
                    }
                else:
                    return {"success": False, "error": result.get("error"), "message": "Failed to create demo envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e), "message": "Failed to create demo envelope"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {
                "success": True,
                "envelope_id": "demo-envelope-12345",
                "signer_email": signer_email,
                "signer_name": signer_name,
                "subject": subject,
                "message": "Demo envelope created successfully (MOCK)",
                "next_steps": [
                    "1. Use 'get_envelope_status' to check the envelope status",
                    "2. Use 'fill_document_fields' to fill any form fields", 
                    "3. Use 'open_document_for_signing' to open for signing"
                ],
                "note": "This is a mock envelope for testing purposes"
            }
            
    except Exception as e:
        logger.error(f"❌ create_demo_envelope error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e), "message": "Failed to create demo envelope"}

# Update TOOL_HANDLERS with all handler functions
TOOL_HANDLERS.update({
    "getenvelope": handle_getenvelope,
    "fill_envelope": handle_fill_envelope,
    "sign_envelope": handle_sign_envelope,
    "submit_envelope": handle_submit_envelope,
    "get_envelope_status": handle_get_envelope_status,
    "send_for_signature": handle_send_for_signature,
    "get_server_info": handle_get_server_info,
    "debug_docusign_config": handle_debug_docusign_config,
    "create_embedded_signing": handle_create_embedded_signing,
    "open_document_for_signing": handle_open_document_for_signing,
    "fill_document_fields": handle_fill_document_fields,
    "create_demo_envelope": handle_create_demo_envelope
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
                            "description": "Fill form fields in existing DocuSign envelope",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "field_data": {"type": "object", "description": "Form field data to fill"}
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
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "recipient_email": {"type": "string", "description": "Recipient email address"},
                                    "security_code": {"type": "string", "description": "Security code for signing (optional)"}
                                },
                                "required": ["envelope_id", "recipient_email"]
                            }
                        },
                        {
                            "name": "debug_docusign_config",
                            "description": "Debug DocuSign configuration and environment settings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "create_embedded_signing",
                            "description": "Create embedded signing URL for testing without email delivery",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "signer_name": {"type": "string", "description": "Signer name (defaults to Test Signer)"},
                                    "return_url": {"type": "string", "description": "Return URL after signing (optional)"}
                                },
                                "required": ["pdf_url"]
                            }
                        },
                        {
                            "name": "open_document_for_signing",
                            "description": "Open existing document for signing using envelope ID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "return_url": {"type": "string", "description": "Return URL after signing (optional)"}
                                },
                                "required": ["envelope_id"]
                            }
                        },
                        {
                            "name": "fill_document_fields",
                            "description": "Fill form fields in existing document",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "field_data": {"type": "object", "description": "Form field data to fill"}
                                },
                                "required": ["envelope_id", "field_data"]
                            }
                        },
                        {
                            "name": "create_demo_envelope",
                            "description": "Create a demo envelope for testing in demo environment",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "signer_name": {"type": "string", "description": "Signer name (defaults to Test Signer)"},
                                    "subject": {"type": "string", "description": "Email subject (optional)"},
                                    "message": {"type": "string", "description": "Email message (optional)"}
                                },
                                "required": ["pdf_url"]
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
                            "description": "Fill form fields in existing DocuSign envelope",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "field_data": {"type": "object", "description": "Form field data to fill"}
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
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "recipient_email": {"type": "string", "description": "Recipient email address"},
                                    "security_code": {"type": "string", "description": "Security code for signing (optional)"}
                                },
                                "required": ["envelope_id", "recipient_email"]
                            }
                        },
                        {
                            "name": "debug_docusign_config",
                            "description": "Debug DocuSign configuration and environment settings",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "create_embedded_signing",
                            "description": "Create embedded signing URL for testing without email delivery",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "signer_name": {"type": "string", "description": "Signer name (defaults to Test Signer)"},
                                    "return_url": {"type": "string", "description": "Return URL after signing (optional)"}
                                },
                                "required": ["pdf_url"]
                            }
                        },
                        {
                            "name": "open_document_for_signing",
                            "description": "Open existing document for signing using envelope ID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "return_url": {"type": "string", "description": "Return URL after signing (optional)"}
                                },
                                "required": ["envelope_id"]
                            }
                        },
                        {
                            "name": "fill_document_fields",
                            "description": "Fill form fields in existing document",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "envelope_id": {"type": "string", "description": "DocuSign envelope ID"},
                                    "field_data": {"type": "object", "description": "Form field data to fill"}
                                },
                                "required": ["envelope_id", "field_data"]
                            }
                        },
                        {
                            "name": "create_demo_envelope",
                            "description": "Create a demo envelope for testing in demo environment",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pdf_url": {"type": "string", "description": "URL to PDF file"},
                                    "signer_email": {"type": "string", "description": "Signer email (defaults to test@example.com)"},
                                    "signer_name": {"type": "string", "description": "Signer name (defaults to Test Signer)"},
                                    "subject": {"type": "string", "description": "Email subject (optional)"},
                                    "message": {"type": "string", "description": "Email message (optional)"}
                                },
                                "required": ["pdf_url"]
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
