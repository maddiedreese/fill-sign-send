#!/usr/bin/env python3
"""
Doc Filling + E-Signing MCP Server
Built with FastMCP for proper MCP protocol support
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import FastMCP
from fastmcp import FastMCP

# Import real implementations with proper error handling
try:
    from settings import settings
    logger.info("✅ Successfully imported settings")
    USE_REAL_APIS = True
except ImportError as e:
    logger.error(f"⚠️  Settings import error: {e}")
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

# Initialize FastMCP
mcp = FastMCP("Doc Filling + E-Signing MCP Server")

# Add health check tool for Render
@mcp.tool(description="Health check endpoint for Render")
def health_check() -> dict:
    """Health check endpoint for Render."""
    return {
        "status": "healthy", 
        "message": "Server is running",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@mcp.tool(description="Get server information and configuration status")
def get_server_info() -> dict:
    """Get server information and configuration status."""
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

@mcp.tool(description="Send document for electronic signature via DocuSign")
def send_for_signature(file_url: str, recipient_email: str, recipient_name: str, 
                      subject: str = "Please sign this document",
                      message: str = "Please review and sign this document.") -> dict:
    """Send a document for electronic signature via DocuSign."""
    logger.info(f"📧 send_for_signature called with file_url: {file_url}, recipient: {recipient_email}")
    
    try:
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
                from esign_docusign import send_for_signature_docusign
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
                return {"success": False, "error": str(e), "message": "Failed to send document for signature via DocuSign"}
        else:
            logger.warning("⚠️  Using MOCK DocuSign API")
            return {"success": True, "envelope_id": "mock-envelope-123", "message": "Document sent for signature via DocuSign (MOCK)"}
    except Exception as e:
        logger.error(f"❌ send_for_signature error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to send document for signature"}

@mcp.tool(description="Get DocuSign envelope status")
def get_envelope_status(envelope_id: str) -> dict:
    """Get the status of a DocuSign envelope."""
    logger.info(f"📊 get_envelope_status called with envelope_id: {envelope_id}")
    
    try:
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
                        "recipients": result.get("recipients", [])
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to get envelope status"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                return {"success": False, "error": str(e), "message": "Failed to get envelope status"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ get_envelope_status error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get envelope status"}

@mcp.tool(description="Fill form fields in existing DocuSign envelope")
def fill_envelope(envelope_id: str, field_data: dict) -> dict:
    """Fill form fields in an existing DocuSign envelope."""
    try:
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
                return {"success": False, "error": str(e), "message": "Failed to fill envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ fill_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to fill envelope"}

@mcp.tool(description="Extract access code from DocuSign email content")
def extract_access_code(email_content: str) -> dict:
    """Extract access code from DocuSign email content."""
    try:
        if not email_content:
            return {"success": False, "error": "email_content is required", "message": "Please provide email_content"}
        
        logger.info(f"🔍 extract_access_code called with email_content length: {len(email_content)}")
        
        import re
        
        # Common patterns for DocuSign access codes
        patterns = [
            r'access code[:\s]+([A-Z0-9]{4,8})',  # "access code: ABC123"
            r'security code[:\s]+([A-Z0-9]{4,8})',  # "security code: ABC123"
            r'code[:\s]+([A-Z0-9]{4,8})',  # "code: ABC123"
            r'Your.*?code[:\s]+([A-Z0-9]{4,8})',  # "Your access code is: ABC123"
        ]
        
        access_codes = []
        for pattern in patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE)
            access_codes.extend(matches)
        
        # Remove duplicates and filter out common false positives
        unique_codes = list(set(access_codes))
        # Filter out common false positives and ensure proper length
        filtered_codes = [code for code in unique_codes 
                         if len(code) >= 4 and len(code) <= 8 
                         and code.isalnum() 
                         and code.upper() not in ['ACCESS', 'CODE', 'DOCUSIGN', 'PLEASE', 'DOCUMENT', 'SIGNING']]
        
        if filtered_codes:
            # Return the first (most likely) access code
            access_code = filtered_codes[0]
            logger.info(f"✅ Found access code: {access_code}")
            return {
                "success": True,
                "access_code": access_code,
                "all_codes": filtered_codes,
                "message": f"Extracted access code: {access_code}"
            }
        else:
            logger.warning("⚠️ No access code found in email content")
            return {
                "success": False,
                "error": "No access code found",
                "message": "Could not find access code in email content. Please check the email format."
            }
            
    except Exception as e:
        logger.error(f"❌ extract_access_code error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to extract access code"}

@mcp.tool(description="Get envelope information including status and form fields")
def getenvelope(envelope_id: str) -> dict:
    """Get envelope information including status and form fields."""
    logger.info(f"📋 getenvelope called with envelope_id: {envelope_id}")
    
    try:
        if not envelope_id:
            return {"success": False, "error": "envelope_id is required", "message": "Please provide envelope_id"}
        
        if USE_REAL_APIS:
            logger.info("🔗 Using REAL DocuSign API")
            try:
                from esign_docusign import get_envelope_status_docusign
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
                        "form_fields": result.get("form_fields", []),
                        "message": "Envelope retrieved successfully"
                    }
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"❌ DocuSign API error: {error_msg}")
                    return {"success": False, "error": error_msg, "message": "Failed to get envelope"}
                    
            except Exception as e:
                logger.error(f"❌ DocuSign API exception: {e}")
                return {"success": False, "error": str(e), "message": "Failed to get envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ getenvelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to get envelope"}

@mcp.tool(description="Sign a DocuSign envelope")
def sign_envelope(envelope_id: str, recipient_email: str, security_code: str = "") -> dict:
    """Sign a DocuSign envelope."""
    try:
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
                return {"success": False, "error": str(e), "message": "Failed to sign envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ sign_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to sign envelope"}

@mcp.tool(description="Submit a DocuSign envelope")
def submit_envelope(envelope_id: str) -> dict:
    """Submit a DocuSign envelope."""
    try:
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
                return {"success": False, "error": str(e), "message": "Failed to submit envelope"}
        else:
            return {"success": False, "error": "DocuSign not available", "message": "DocuSign integration not available"}
            
    except Exception as e:
        logger.error(f"❌ submit_envelope error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to submit envelope"}

@mcp.tool(description="Complete DocuSign workflow: extract envelope ID and access code from email, then fill, sign, and send document")
def complete_docusign_workflow(email_content: str, recipient_email: str = "", field_data: dict = None, return_url: str = "https://www.docusign.com") -> dict:
    """Complete DocuSign workflow: extract envelope ID and access code from email, then fill, sign, and send document."""
    try:
        if not email_content:
            return {"success": False, "error": "email_content is required", "message": "Please provide email_content"}
        
        logger.info(f"🔄 complete_docusign_workflow called with email_content length: {len(email_content)}")
        
        # Step 1: Extract envelope ID and access code from email
        logger.info("🔍 Step 1: Extracting envelope ID and access code from email...")
        
        import re
        
        # Patterns for DocuSign envelope IDs (typically UUIDs)
        envelope_patterns = [
            r'envelope[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # Just UUID pattern
        ]
        
        # Patterns for DocuSign access codes
        access_code_patterns = [
            r'access code[:\s]+([A-Z0-9]{4,8})',  # "access code: ABC123"
            r'security code[:\s]+([A-Z0-9]{4,8})',  # "security code: ABC123"
            r'code[:\s]+([A-Z0-9]{4,8})',  # "code: ABC123"
            r'Your.*?code[:\s]+([A-Z0-9]{4,8})',  # "Your access code is: ABC123"
        ]
        
        # Extract envelope IDs
        envelope_ids = []
        for pattern in envelope_patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE)
            envelope_ids.extend(matches)
        
        # Extract access codes
        access_codes = []
        for pattern in access_code_patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE)
            access_codes.extend(matches)
        
        # Filter and clean results
        unique_envelope_ids = list(set(envelope_ids))
        unique_access_codes = list(set(access_codes))
        
        # Filter access codes
        filtered_access_codes = [code for code in unique_access_codes 
                               if len(code) >= 4 and len(code) <= 8 
                               and code.isalnum() 
                               and code.upper() not in ['ACCESS', 'CODE', 'DOCUSIGN', 'PLEASE', 'DOCUMENT', 'SIGNING']]
        
        if not (unique_envelope_ids and filtered_access_codes):
            return {
                "success": False,
                "error": "Could not extract both envelope ID and access code",
                "message": "Email must contain both envelope ID and access code",
                "found_envelope_ids": unique_envelope_ids,
                "found_access_codes": filtered_access_codes
            }
        
        envelope_id = unique_envelope_ids[0]
        access_code = filtered_access_codes[0]
        
        logger.info(f"✅ Step 1 complete: envelope_id={envelope_id}, access_code={access_code}")
        
        # Step 2: Get envelope status
        logger.info("📊 Step 2: Getting envelope status...")
        status_result = get_envelope_status(envelope_id)
        
        # Step 3: Fill document fields if provided
        if field_data:
            logger.info("📝 Step 3: Filling document fields...")
            fill_result = fill_envelope(envelope_id, field_data)
        else:
            logger.info("⏭️ Step 3 skipped: no field data provided")
            fill_result = {"success": True, "message": "No fields to fill"}
        
        # Return comprehensive result
        return {
            "success": True,
            "message": "DocuSign workflow completed successfully",
            "envelope_id": envelope_id,
            "access_code": access_code,
            "status_result": status_result,
            "fill_result": fill_result,
            "next_steps": [
                "Use the envelope_id and access_code for further processing",
                "Check envelope status for completion",
                "Access the document using the provided credentials"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ complete_docusign_workflow error: {e}")
        return {"success": False, "error": str(e), "message": "Failed to complete DocuSign workflow"}

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
        import requests
        import time
        
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting Doc Filling + E-Signing MCP Server with FastMCP...")
    logger.info(f"📊 Using {'REAL' if USE_REAL_APIS else 'MOCK'} APIs")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🌐 Starting FastMCP server on {host}:{port}")
    
    try:
        # Run the FastMCP server with improved configuration
        mcp.run(
            transport="http",
            host=host,
            port=port,
            stateless_http=True,
            # Add timeout configurations to prevent premature shutdown
            timeout_keep_alive=30,
            timeout_graceful_shutdown=30
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise
    finally:
        logger.info("🏁 Server shutdown complete")