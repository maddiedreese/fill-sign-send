#!/usr/bin/env python3
"""
Poke Webhook Handler
Handles incoming webhook requests from Poke and calls MCP tools
"""
import os
import sys
import logging
from pathlib import Path
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import re

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import MCP tools
try:
    from server import (
        get_server_info,
        send_for_signature,
        get_envelope_status,
        fill_envelope,
        extract_access_code,
        getenvelope,
        sign_envelope,
        submit_envelope,
        complete_docusign_workflow
    )
    logger.info("✅ Successfully imported MCP tools")
    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.error(f"⚠️  MCP tools import error: {e}")
    MCP_TOOLS_AVAILABLE = False

def process_poke_message(message: str) -> dict:
    """Process Poke message and call appropriate MCP tools"""
    try:
        logger.info(f"📱 Processing Poke message: {message}")
        
        if not MCP_TOOLS_AVAILABLE:
            return {
                "success": False,
                "error": "MCP tools not available",
                "message": "MCP tools could not be imported"
            }
        
        # Convert message to lowercase for easier matching
        message_lower = message.lower()
        
        # Check for different commands
        if "send document" in message_lower or "send for signature" in message_lower:
            logger.info("📧 Detected send document command")
            # Extract email from message if present
            email_match = re.search(r'(\S+@\S+\.\S+)', message)
            if email_match:
                recipient_email = email_match.group(1)
                recipient_name = recipient_email.split('@')[0]
                
                result = send_for_signature(
                    file_url="test.pdf",  # Use test PDF
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    subject="Document for Signature",
                    message="Please review and sign this document."
                )
                return {
                    "success": True,
                    "action": "send_for_signature",
                    "result": result,
                    "message": f"Document sent for signature to {recipient_email}"
                }
            else:
                return {
                    "success": False,
                    "error": "No email found in message",
                    "message": "Please include an email address in your message"
                }
        
        elif "envelope status" in message_lower or "check status" in message_lower:
            logger.info("📊 Detected envelope status command")
            # Extract envelope ID from message
            envelope_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', message)
            if envelope_match:
                envelope_id = envelope_match.group(1)
                result = get_envelope_status(envelope_id)
                return {
                    "success": True,
                    "action": "get_envelope_status",
                    "result": result,
                    "message": f"Retrieved status for envelope {envelope_id}"
                }
            else:
                return {
                    "success": False,
                    "error": "No envelope ID found in message",
                    "message": "Please include an envelope ID in your message"
                }
        
        elif "extract code" in message_lower or "access code" in message_lower:
            logger.info("🔍 Detected extract access code command")
            result = extract_access_code(message)
            return {
                "success": True,
                "action": "extract_access_code",
                "result": result,
                "message": "Extracted access code from message"
            }
        
        elif "complete workflow" in message_lower or "docusign workflow" in message_lower:
            logger.info("🔄 Detected complete workflow command")
            result = complete_docusign_workflow(message)
            return {
                "success": True,
                "action": "complete_docusign_workflow",
                "result": result,
                "message": "Completed DocuSign workflow"
            }
        
        elif "server info" in message_lower or "status" in message_lower:
            logger.info("📊 Detected server info command")
            result = get_server_info()
            return {
                "success": True,
                "action": "get_server_info",
                "result": result,
                "message": "Retrieved server information"
            }
        
        else:
            # Default response for unrecognized commands
            return {
                "success": True,
                "action": "echo",
                "message": f"Received message: {message}",
                "available_commands": [
                    "send document [email] - Send document for signature",
                    "envelope status [envelope_id] - Check envelope status",
                    "extract code - Extract access code from message",
                    "complete workflow - Complete DocuSign workflow",
                    "server info - Get server information"
                ]
            }
    
    except Exception as e:
        logger.error(f"❌ Error processing Poke message: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to process message"
        }

class PokeWebhookHandler(BaseHTTPRequestHandler):
    """Handle Poke webhook requests"""
    
    def do_POST(self):
        """Handle POST requests from Poke"""
        try:
            # Only handle /poke-webhook endpoint
            if self.path != '/poke-webhook':
                self.send_response(404)
                self.end_headers()
                return
            
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read the request body
            post_data = self.rfile.read(content_length)
            
            # Parse JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error("❌ Invalid JSON in webhook request")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return
            
            logger.info(f"📱 Received Poke webhook: {data}")
            
            # Extract message from Poke
            message = data.get("message", "")
            if not message:
                logger.warning("⚠️ No message in webhook request")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No message provided"}).encode())
                return
            
            logger.info(f"📱 Processing Poke message: {message}")
            
            # Process the message and call MCP tools
            processing_result = process_poke_message(message)
            
            # Send response
            response = {
                "status": "success" if processing_result.get("success", False) else "error",
                "message": processing_result.get("message", "Unknown error"),
                "action": processing_result.get("action", "unknown"),
                "original_message": message,
                "result": processing_result.get("result", {}),
                "available_commands": processing_result.get("available_commands", [])
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        """Handle GET requests for health checks"""
        if self.path == '/health':
            response = {"status": "healthy", "message": "Webhook handler is running"}
        elif self.path == '/':
            response = {
                "name": "Poke Webhook Handler with MCP Integration",
                "version": "1.0.0",
                "status": "running",
                "mcp_tools_available": MCP_TOOLS_AVAILABLE,
                "endpoints": {
                    "webhook": "/poke-webhook",
                    "health": "/health"
                },
                "available_commands": [
                    "send document [email] - Send document for signature",
                    "envelope status [envelope_id] - Check envelope status", 
                    "extract code - Extract access code from message",
                    "complete workflow - Complete DocuSign workflow",
                    "server info - Get server information"
                ],
                "example_usage": {
                    "send_document": "send document john@example.com",
                    "check_status": "envelope status 12345678-1234-1234-1234-123456789012",
                    "extract_code": "extract code from this email: Your access code is ABC123",
                    "server_info": "server info"
                }
            }
        else:
            self.send_response(404)
            self.end_headers()
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"📱 {format % args}")

def run_webhook_server():
    """Run the webhook server"""
    port = int(os.environ.get("WEBHOOK_PORT", 8001))
    host = "0.0.0.0"
    
    server = HTTPServer((host, port), PokeWebhookHandler)
    logger.info(f"🚀 Starting Poke webhook handler on {host}:{port}")
    logger.info(f"📱 Webhook endpoint: http://{host}:{port}/poke-webhook")
    logger.info(f"📱 Health check: http://{host}:{port}/health")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Webhook server shutdown requested")
        server.shutdown()
    except Exception as e:
        logger.error(f"❌ Webhook server error: {e}")
        server.shutdown()

if __name__ == "__main__":
    run_webhook_server()
