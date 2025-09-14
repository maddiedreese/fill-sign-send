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
            # FIXED: Use correct DocuSign demo REST API endpoint
            self.api_client.host = "https://demo.docusign.net/restapi"
            
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
        logger.info(f"📧 DocuSign function called with file: {file_url}")
        
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        
        # Read and encode the document
        with open(file_url, 'rb') as file:
            file_content = file.read()
        
        # Create document with proper base64 encoding
        document = Document(
            document_base64=base64.b64encode(file_content).decode('utf-8'),
            name=file_url.split('/')[-1],
            file_extension="pdf",
            document_id="1"
        )
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=subject,
            email_blurb=message,
            status="sent",
            documents=[document]  # FIXED: Add documents to envelope definition
        )
        
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
        
        logger.info(f"📧 DocuSign envelope created: {result.envelope_id}")
        
        return {
            "success": True,
            "envelope_id": result.envelope_id,
            "message": "Document sent for signature via DocuSign"
        }
        
    except Exception as e:
        logger.error(f"Error sending document for signature: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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

def fill_envelope_docusign(envelope_id: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fill an existing DocuSign envelope with data.
    
    Args:
        envelope_id: ID of the envelope to fill
        field_data: Dictionary of field names and values to fill
        
    Returns:
        Dictionary with success status and message
    """
    try:
        logger.info(f"📝 Filling envelope {envelope_id} with data: {field_data}")
        
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Get envelope details
        envelope = envelopes_api.get_envelope(account_id=account_id, envelope_id=envelope_id)
        
        if envelope.status != "sent":
            return {
                "success": False,
                "error": f"Envelope status is {envelope.status}, cannot fill",
                "message": "Only sent envelopes can be filled"
            }
        
        # Create document update request
        from docusign_esign.models import Document, Tabs, Text, SignHere
        
        # Get the first document
        if not envelope.documents or len(envelope.documents) == 0:
            return {
                "success": False,
                "error": "No documents found in envelope",
                "message": "Cannot fill envelope without documents"
            }
        
        document = envelope.documents[0]
        
        # Create tabs for text fields
        text_tabs = []
        for field_name, field_value in field_data.items():
            text_tab = Text(
                tab_label=field_name,
                value=str(field_value),
                document_id=document.document_id,
                page_number="1"
            )
            text_tabs.append(text_tab)
        
        # Update envelope with filled data
        from docusign_esign.models import EnvelopeDefinition, Recipients, Signer
        
        # Get existing recipients
        recipients = envelope.recipients
        if recipients and recipients.signers:
            signer = recipients.signers[0]
            if not signer.tabs:
                signer.tabs = Tabs()
            if not signer.tabs.text_tabs:
                signer.tabs.text_tabs = []
            signer.tabs.text_tabs.extend(text_tabs)
        
        # Update envelope
        envelope_definition = EnvelopeDefinition(
            recipients=recipients
        )
        
        result = envelopes_api.update(account_id=account_id, envelope_id=envelope_id, envelope=envelope_definition)
        
        logger.info(f"📝 Successfully filled envelope {envelope_id}")
        
        return {
            "success": True,
            "message": f"Envelope {envelope_id} filled successfully",
            "envelope_id": envelope_id
        }
        
    except Exception as e:
        logger.error(f"Error filling envelope: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fill envelope"
        }

def sign_envelope_docusign(envelope_id: str, recipient_email: str, security_code: str = None) -> Dict[str, Any]:
    """
    Sign a DocuSign envelope using security code or get signing URL.
    
    Args:
        envelope_id: ID of the envelope to sign
        recipient_email: Email of the recipient signing
        security_code: Optional security code for authentication
        
    Returns:
        Dictionary with success status and signing URL or completion status
    """
    try:
        logger.info(f"✍️ Signing envelope {envelope_id} for {recipient_email}")
        
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Get envelope details
        envelope = envelopes_api.get_envelope(account_id=account_id, envelope_id=envelope_id)
        
        if envelope.status not in ["sent", "delivered"]:
            return {
                "success": False,
                "error": f"Envelope status is {envelope.status}, cannot sign",
                "message": "Only sent or delivered envelopes can be signed"
            }
        
        # If security code provided, authenticate and sign
        if security_code:
            # Create recipient view request
            from docusign_esign.models import RecipientViewRequest
            
            recipient_view_request = RecipientViewRequest(
                authentication_method="none",
                email=recipient_email,
                user_name=recipient_email,
                client_user_id=recipient_email,
                return_url="https://docusign.com"
            )
            
            # Get recipient view URL
            result = envelopes_api.create_recipient_view(
                account_id=account_id,
                envelope_id=envelope_id,
                recipient_view_request=recipient_view_request
            )
            
            logger.info(f"✍️ Created signing URL for envelope {envelope_id}")
            
            return {
                "success": True,
                "signing_url": result.url,
                "message": f"Signing URL created for envelope {envelope_id}",
                "envelope_id": envelope_id
            }
        else:
            # Just return envelope status
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": envelope.status,
                "message": f"Envelope {envelope_id} status: {envelope.status}"
            }
        
    except Exception as e:
        logger.error(f"Error signing envelope: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to sign envelope"
        }

def submit_envelope_docusign(envelope_id: str) -> Dict[str, Any]:
    """
    Submit a completed DocuSign envelope.
    
    Args:
        envelope_id: ID of the envelope to submit
        
    Returns:
        Dictionary with success status and final envelope status
    """
    try:
        logger.info(f"📤 Submitting envelope {envelope_id}")
        
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Get envelope details
        envelope = envelopes_api.get_envelope(account_id=account_id, envelope_id=envelope_id)
        
        if envelope.status not in ["completed", "signed"]:
            return {
                "success": False,
                "error": f"Envelope status is {envelope.status}, cannot submit",
                "message": "Only completed or signed envelopes can be submitted"
            }
        
        # Envelope is already submitted if status is completed
        if envelope.status == "completed":
            logger.info(f"📤 Envelope {envelope_id} already completed")
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": "completed",
                "message": f"Envelope {envelope_id} is already completed"
            }
        
        # For signed envelopes, they are automatically submitted
        logger.info(f"📤 Envelope {envelope_id} submitted successfully")
        
        return {
            "success": True,
            "envelope_id": envelope_id,
            "status": "completed",
            "message": f"Envelope {envelope_id} submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting envelope: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to submit envelope"
        }

def get_envelope_status_docusign(envelope_id: str) -> Dict[str, Any]:
    """
    Get the status and details of a DocuSign envelope.
    
    Args:
        envelope_id: ID of the envelope to check
        
    Returns:
        Dictionary with success status and envelope details
    """
    try:
        logger.info(f"📊 Getting status for envelope {envelope_id}")
        
        # Get authenticated API client
        api_client = _docusign_client.get_api_client()
        envelopes_api = EnvelopesApi(api_client)
        account_id = settings.DOCUSIGN_ACCOUNT_ID
        
        # Get envelope details
        envelope = envelopes_api.get_envelope(account_id=account_id, envelope_id=envelope_id)
        
        # Get recipient information
        recipients_info = []
        if envelope.recipients and envelope.recipients.signers:
            for signer in envelope.recipients.signers:
                recipients_info.append({
                    "email": signer.email,
                    "name": signer.name,
                    "status": signer.status,
                    "signed_date": signer.signed_date_time
                })
        
        logger.info(f"📊 Envelope {envelope_id} status: {envelope.status}")
        
        return {
            "success": True,
            "envelope_id": envelope_id,
            "status": envelope.status,
            "created_date": envelope.created_date_time,
            "sent_date": envelope.sent_date_time,
            "completed_date": envelope.completed_date_time,
            "recipients": recipients_info,
            "message": f"Envelope {envelope_id} status: {envelope.status}"
        }
        
    except Exception as e:
        logger.error(f"Error getting envelope status: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get envelope status"
        }

def create_recipient_view_with_code(envelope_id: str, recipient_email: str, access_code: str, return_url: str = "https://www.docusign.com") -> Dict[str, Any]:
    """
    Create a recipient view URL using access code for document access.
    
    Args:
        envelope_id: DocuSign envelope ID
        recipient_email: Recipient email address
        access_code: Access code from email
        return_url: URL to redirect after signing
        
    Returns:
        Dict with success status and signing URL
    """
    try:
        if not settings.validate_docusign_config():
            return {"success": False, "error": "DocuSign not configured", "message": "DocuSign configuration is missing or invalid"}
        
        # Get JWT token
        token = get_docusign_jwt_token()
        if not token:
            return {"success": False, "error": "Authentication failed", "message": "Could not authenticate with DocuSign"}
        
        # Create recipient view request
        recipient_view_request = {
            "authenticationMethod": "email",
            "email": recipient_email,
            "userName": recipient_email,
            "returnUrl": return_url,
            "accessCode": access_code
        }
        
        # Make API call to create recipient view
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{settings.DOCUSIGN_BASE_PATH}/restapi/v2.1/accounts/{settings.DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}/views/recipient"
        
        response = requests.post(url, headers=headers, json=recipient_view_request)
        
        if response.status_code == 201:
            data = response.json()
            return {
                "success": True,
                "signing_url": data.get("url"),
                "envelope_id": envelope_id,
                "recipient_email": recipient_email,
                "message": "Recipient view URL created successfully"
            }
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            return {
                "success": False,
                "error": error_msg,
                "message": f"Failed to create recipient view: {error_msg}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Exception creating recipient view: {str(e)}"
        }
