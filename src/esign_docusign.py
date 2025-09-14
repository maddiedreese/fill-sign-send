#!/usr/bin/env python3
"""
DocuSign e-signature adapter for MCP server.
Handles JWT authentication and envelope operations.
"""
import base64
import time
import logging
from typing import List, Dict, Any, Optional
import tempfile
import os

try:
    from docusign_esign import ApiClient, EnvelopesApi, AuthenticationApi
    from docusign_esign.client.api_exception import ApiException
    from docusign_esign.models import (
        EnvelopeDefinition, Document, Recipients, Signer,
        SignHere, Tabs
    )
except ImportError:
    raise ImportError("docusign-esign is required. Install with: pip install docusign-esign")

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt
except ImportError:
    raise ImportError("cryptography and PyJWT are required for JWT authentication")

try:
    from .settings import settings
except ImportError:
    from settings import settings

logger = logging.getLogger(__name__)

class DocuSignClient:
    """DocuSign API client with JWT authentication."""
    
    def __init__(self):
        self.api_client: Optional[ApiClient] = None
        self.access_token: Optional[str] = None
        self.token_expiry: float = 0
        
    def get_api_client(self) -> ApiClient:
        """
        Get authenticated DocuSign API client.
        Handles JWT authentication and token refresh.
        
        Returns:
            Authenticated ApiClient instance
            
        Raises:
            ValueError: If DocuSign configuration is invalid
            ApiException: If authentication fails
        """
        # Check if we need to refresh the token
        if (self.api_client is None or 
            self.access_token is None or 
            time.time() >= self.token_expiry - 300):  # Refresh 5 minutes before expiry
            
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
            private_key = self._parse_private_key(config["private_key"])
            
            # JWT payload
            now = int(time.time())
            payload = {
                "iss": config["integration_key"],  # Client ID
                "sub": config["user_id"],          # User ID to impersonate
                "aud": "account-d.docusign.com",   # DocuSign audience
                "iat": now,
                "exp": now + 3600,  # 1 hour expiration
                "scope": "signature impersonation"
            }
            
            # Sign JWT
            token = jwt.encode(payload, private_key, algorithm="RS256")
            
            # Exchange JWT for access token
            auth_api = AuthenticationApi(self.api_client)
            
            # Request access token
            oauth_response = auth_api.request_jwt_user_token(
                client_id=config["integration_key"],
                user_id=config["user_id"],
                oauth_host_name="account-d.docusign.com",
                private_key_bytes=private_key,
                expires_in=3600
            )
            
            # Set access token
            self.access_token = oauth_response.access_token
            self.token_expiry = time.time() + oauth_response.expires_in
            
            # Configure API client with access token
            self.api_client.set_default_header("Authorization", f"Bearer {self.access_token}")
            
            logger.info("Successfully authenticated with DocuSign")
            
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
    recipients: List[Dict[str, str]], 
    subject: str, 
    message: str, 
    filled_pdf_bytes: bytes
) -> str:
    """
    Send PDF for signature via DocuSign.
    
    Args:
        recipients: List of recipient dicts with 'email' and 'name' keys
        subject: Email subject line
        message: Email message body
        filled_pdf_bytes: PDF content as bytes
        
    Returns:
        DocuSign envelope ID
        
    Raises:
        ValueError: If operation fails
        ApiException: If DocuSign API call fails
    """
    try:
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Create document
        document = Document(
            document_base64=base64.b64encode(filled_pdf_bytes).decode('utf-8'),
            name="Document.pdf",
            file_extension="pdf",
            document_id="1"
        )
        
        # Create signers
        signers = []
        for i, recipient in enumerate(recipients, 1):
            # Create sign here tab (signature placement)
            sign_here = SignHere(
                document_id="1",
                page_number="1",
                x_position="100",
                y_position="100"
            )
            
            signer = Signer(
                email=recipient["email"],
                name=recipient["name"],
                recipient_id=str(i),
                routing_order=str(i),
                tabs=Tabs(sign_here_tabs=[sign_here])
            )
            signers.append(signer)
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=subject,
            email_blurb=message,
            documents=[document],
            recipients=Recipients(signers=signers),
            status="sent"  # Send immediately
        )
        
        # Create envelope
        envelope_summary = envelopes_api.create_envelope(account_id, envelope_definition)
        
        logger.info(f"DocuSign envelope created: {envelope_summary.envelope_id}")
        return envelope_summary.envelope_id
        
    except ApiException as e:
        logger.error(f"DocuSign API error: {e}")
        raise ValueError(f"DocuSign API error: {e.reason}")
    except Exception as e:
        logger.error(f"Failed to send for signature: {e}")
        raise ValueError(f"Failed to send document for signature: {e}")

def get_status_docusign(envelope_id: str) -> str:
    """
    Get DocuSign envelope status.
    
    Args:
        envelope_id: DocuSign envelope ID
        
    Returns:
        Envelope status string
        
    Raises:
        ValueError: If operation fails
    """
    try:
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Get envelope status
        envelope = envelopes_api.get_envelope(account_id, envelope_id)
        
        return envelope.status
        
    except ApiException as e:
        logger.error(f"DocuSign API error: {e}")
        raise ValueError(f"Failed to get envelope status: {e.reason}")
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise ValueError(f"Failed to get envelope status: {e}")

def download_completed_pdf_docusign(envelope_id: str) -> bytes:
    """
    Download completed/signed PDF from DocuSign.
    
    Args:
        envelope_id: DocuSign envelope ID
        
    Returns:
        Signed PDF content as bytes
        
    Raises:
        ValueError: If operation fails or envelope is not completed
    """
    try:
        api_client = get_docusign_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Check envelope status first
        status = get_status_docusign(envelope_id)
        if status.lower() != "completed":
            raise ValueError(f"Envelope is not completed. Current status: {status}")
        
        # Download the completed document
        document_bytes = envelopes_api.get_document(
            account_id, 
            envelope_id, 
            "combined"  # Get all documents combined
        )
        
        return document_bytes
        
    except ApiException as e:
        logger.error(f"DocuSign API error: {e}")
        raise ValueError(f"Failed to download signed document: {e.reason}")
    except Exception as e:
        logger.error(f"Failed to download document: {e}")
        raise ValueError(f"Failed to download signed document: {e}")

def validate_docusign_config() -> bool:
    """
    Validate DocuSign configuration.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        return settings.validate_docusign_config()
    except Exception:
        return False
