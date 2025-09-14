"""
DocuSign e-signature integration with proper JWT authentication
"""
import time
import jwt
import requests
import base64
from typing import Dict, Any, Optional
from docusign_esign import ApiClient, AuthenticationApi, EnvelopesApi
from docusign_esign.models import EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients
from settings import settings
from private_key_loader import load_private_key_from_env
import logging

logger = logging.getLogger(__name__)

class DocuSignClient:
    """DocuSign client for e-signature operations."""
    
    def __init__(self):
        self.api_client = None
        self.access_token = None
        self.token_expiry = None
    
    def get_api_client(self) -> ApiClient:
        """Get authenticated DocuSign API client."""
        if not self.api_client or time.time() >= self.token_expiry:
            self._authenticate()
            
        return self.api_client
    
    def _authenticate(self):
        """Perform JWT authentication with DocuSign."""
        try:
            config = settings.get_docusign_config()
            
            # Create API client
            self.api_client = ApiClient()
            # Use production URL if in production environment
            self.api_client.host = settings.get_docusign_base_url()
            
            # Prepare JWT token - Use string format directly
            private_key = load_private_key_from_env()
            
            # JWT payload
            now = int(time.time())
            payload = {
                "iss": config["integration_key"],  # Client ID
                "sub": config["user_id"],          # User ID to impersonate
                "aud": "account-d.docusign.com",  # Use correct audience for production
                "iat": now,
                "exp": now + 3600,  # 1 hour expiration
                "scope": "signature impersonation"
            }
            
            # Sign JWT - Use string format
            token = jwt.encode(payload, private_key, algorithm="RS256")
            
            # Exchange JWT for access token using direct HTTP request
            auth_url = "https://account-d.docusign.com/oauth/token"
            
            auth_data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": token
            }
            
            response = requests.post(auth_url, data=auth_data)
            
            if response.status_code == 200:
                oauth_response = response.json()
                self.access_token = oauth_response["access_token"]
                self.token_expiry = time.time() + oauth_response["expires_in"]
                
                # Configure API client with access token
                self.api_client.set_default_header("Authorization", f"Bearer {self.access_token}")
                
                logger.info("Successfully authenticated with DocuSign")
            else:
                raise ValueError(f"Authentication failed: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"DocuSign authentication failed: {e}")
            raise ValueError(f"Failed to authenticate with DocuSign: {e}")

# Global client instance
_docusign_client = DocuSignClient()

def send_for_signature_docusign(file_url: str, recipient_email: str, recipient_name: str, 
                               subject: str = "Please sign this document", 
                               message: str = "Please review and sign this document.") -> Dict[str, Any]:
    """
    Send a document for e-signature via DocuSign.
    
    Args:
        file_url: URL or file path to the PDF document
        recipient_email: Email address of the recipient
        recipient_name: Name of the recipient
        subject: Subject line for the email
        message: Message body for the email
        
    Returns:
        Dictionary with success status and envelope ID
    """
    try:
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=subject,
            email_blurb=message,
            status="sent"
        )
        
        # Add document - FIXED: Use base64.b64encode instead of .encode('base64')
        with open(file_url, 'rb') as file:
            file_content = file.read()
        
        document = Document(
            document_base64=base64.b64encode(file_content).decode('utf-8'),  # FIXED
            name=file_url.split('/')[-1],
            file_extension="pdf",
            document_id="1"
        )
        envelope_definition.documents = [document]
        
        # Add recipient
        signer = Signer(
            email=recipient_email,
            name=recipient_name,
            recipient_id="1",
            routing_order="1"
        )
        
        # Add signature tab
        sign_here = SignHere(
            document_id="1",
            page_number="1",
            recipient_id="1",
            tab_label="SignHereTab",
            x_position="100",
            y_position="100"
        )
        
        signer.tabs = Tabs(sign_here_tabs=[sign_here])
        envelope_definition.recipients = Recipients(signers=[signer])
        
        # Create envelope
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        result = envelopes_api.create_envelope(
            account_id=account_id,
            envelope_definition=envelope_definition
        )
        
        return {
            "success": True,
            "envelope_id": result.envelope_id,
            "message": "Document sent for signature via DocuSign"
        }
        
    except Exception as e:
        logger.error(f"Error sending document for signature: {e}")
        return {
            "success": False,
            "error": str(e),
            "envelope_id": None
        }

def check_signature_status_docusign(envelope_id: str) -> Dict[str, Any]:
    """
    Check the status of a signature request.
    
    Args:
        envelope_id: Envelope ID from the signature request
        
    Returns:
        Dictionary with success status and current status
    """
    try:
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        
        # Get envelope status
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        result = envelopes_api.get_envelope(
            account_id=account_id,
            envelope_id=envelope_id
        )
        
        return {
            "success": True,
            "status": result.status,
            "message": f"Envelope status: {result.status}"
        }
        
    except Exception as e:
        logger.error(f"Error checking signature status: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": None
        }

def download_signed_pdf_docusign(envelope_id: str) -> Dict[str, Any]:
    """
    Download the signed PDF document.
    
    Args:
        envelope_id: Envelope ID from the signature request
        
    Returns:
        Dictionary with success status and signed PDF URL
    """
    try:
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        
        # Download signed document
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        result = envelopes_api.get_document(
            account_id=account_id,
            envelope_id=envelope_id,
            document_id="combined"
        )
        
        # Save to temporary file
        signed_pdf_path = f"signed_{envelope_id}.pdf"
        with open(signed_pdf_path, 'wb') as f:
            f.write(result)
        
        return {
            "success": True,
            "signed_pdf_url": f"file://{signed_pdf_path}",
            "message": "Signed PDF downloaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error downloading signed PDF: {e}")
        return {
            "success": False,
            "error": str(e),
            "signed_pdf_url": None
        }
