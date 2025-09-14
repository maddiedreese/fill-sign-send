"""
DocuSign e-signature integration with proper JWT authentication
"""
import time
import jwt
import requests
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
            
            # Prepare JWT token
            private_key = self._parse_private_key(load_private_key_from_env())
            
            # JWT payload
            now = int(time.time())
            payload = {
                "iss": config["integration_key"],  # Client ID
                "sub": config["user_id"],          # User ID to impersonate
                "aud": "account.docusign.com",   # DocuSign audience
                "iat": now,
                "exp": now + 3600,  # 1 hour expiration
                "scope": "signature impersonation"
            }
            
            # Sign JWT
            token = jwt.encode(payload, private_key, algorithm="RS256")
            
            # Exchange JWT for access token using direct HTTP request
            auth_url = "https://account.docusign.com/oauth/token"
            
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
    
    def _parse_private_key(self, private_key_str: str) -> bytes:
        """
        Parse private key string to bytes.
        
        Args:
            private_key_str: Private key as PEM string or raw key data
            
        Returns:
            Private key as bytes
        """
        try:
            # If it looks like a PEM key, use it directly
            if "-----BEGIN" in private_key_str:
                return private_key_str.encode('utf-8')
            
            # Otherwise, try to construct PEM format
            # Remove any whitespace and newlines
            key_data = private_key_str.strip().replace('\n', '').replace('\r', '')
            
            # Add PEM headers if missing
            pem_key = f"-----BEGIN RSA PRIVATE KEY-----\n"
            # Split into 64-character lines
            for i in range(0, len(key_data), 64):
                pem_key += key_data[i:i+64] + "\n"
            pem_key += "-----END RSA PRIVATE KEY-----"
            
            return pem_key.encode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Invalid private key format: {e}")

# Global DocuSign client instance
_docusign_client = DocuSignClient()

def get_docusign_api_client() -> ApiClient:
    """Get authenticated DocuSign API client."""
    return _docusign_client.get_api_client()

def send_for_signature_docusign(
    file_url: str,
    recipient_email: str,
    recipient_name: str,
    subject: str = "Please sign this document",
    message: str = "Please review and sign this document."
) -> Dict[str, Any]:
    """
    Send a document for signature via DocuSign.
    
    Args:
        file_url: URL or path to the PDF file
        recipient_email: Email address of the signer
        recipient_name: Name of the signer
        subject: Email subject line
        message: Email message body
        
    Returns:
        Dictionary with envelope ID and status
    """
    try:
        # Get authenticated API client
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        
        # Download the PDF file
        if file_url.startswith('http'):
            import requests
            response = requests.get(file_url)
            pdf_content = response.content
        else:
            with open(file_url, 'rb') as f:
                pdf_content = f.read()
        
        # Create document
        document = Document(
            document_base64=pdf_content,
            name="Document to Sign",
            file_extension="pdf",
            document_id="1"
        )
        
        # Create signer
        signer = Signer(
            email=recipient_email,
            name=recipient_name,
            recipient_id="1",
            routing_order="1"
        )
        
        # Create sign here tab
        sign_here = SignHere(
            document_id="1",
            page_number="1",
            recipient_id="1",
            tab_label="SignHereTab",
            x_position="100",
            y_position="100"
        )
        
        # Add tabs to signer
        signer.tabs = Tabs(sign_here_tabs=[sign_here])
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=subject,
            documents=[document],
            recipients=Recipients(signers=[signer]),
            status="sent"
        )
        
        # Send envelope
        envelope = envelopes_api.create_envelope(
            account_id=settings.DOCUSIGN_ACCOUNT_ID,
            envelope_definition=envelope_definition
        )
        
        return {
            "success": True,
            "envelope_id": envelope.envelope_id,
            "status": envelope.status,
            "message": f"Document sent for signature to {recipient_email}"
        }
        
    except Exception as e:
        logger.error(f"Error sending document for signature: {e}")
        return {
            "success": False,
            "error": str(e),
            "envelope_id": None
        }

def get_status_docusign(envelope_id: str) -> str:
    """
    Get the status of a DocuSign envelope.
    
    Args:
        envelope_id: The envelope ID
        
    Returns:
        Envelope status
    """
    try:
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        
        envelope = envelopes_api.get_envelope(
            account_id=settings.DOCUSIGN_ACCOUNT_ID,
            envelope_id=envelope_id
        )
        
        return envelope.status
        
    except Exception as e:
        logger.error(f"Error getting envelope status: {e}")
        return "error"

def download_completed_pdf_docusign(envelope_id: str) -> bytes:
    """
    Download the completed PDF from DocuSign.
    
    Args:
        envelope_id: The envelope ID
        
    Returns:
        PDF content as bytes
    """
    try:
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        
        # Get the completed document
        document = envelopes_api.get_document(
            account_id=settings.DOCUSIGN_ACCOUNT_ID,
            envelope_id=envelope_id,
            document_id="combined"
        )
        
        return document
        
    except Exception as e:
        logger.error(f"Error downloading completed PDF: {e}")
        raise ValueError(f"Failed to download PDF: {e}")

def validate_docusign_config() -> bool:
    """Validate DocuSign configuration."""
    try:
        settings.validate_docusign_config()
        return True
    except Exception as e:
        logger.error(f"DocuSign configuration validation failed: {e}")
        return False
