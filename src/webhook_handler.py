#!/usr/bin/env python3
"""
Poke Webhook Handler
Handles incoming webhook requests from Poke
"""
import os
import sys
import logging
from pathlib import Path
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            
            # Process the message (you can expand this)
            response_message = f"Received message: {message}"
            
            # Here you could call MCP tools based on the message content
            # For example, if the message contains "send document", call send_for_signature
            
            # Send response
            response = {
                "status": "success",
                "message": response_message,
                "original_message": message
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
                "name": "Poke Webhook Handler",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "webhook": "/poke-webhook",
                    "health": "/health"
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
