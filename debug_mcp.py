#!/usr/bin/env python3
"""
Debug MCP endpoint issue
"""
import requests
import json

def test_mcp_endpoint():
    """Test the MCP endpoint directly."""
    print("🧪 Testing MCP endpoint...")
    
    # Test local server
    try:
        response = requests.post(
            "http://localhost:8000/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            },
            timeout=10
        )
        print(f"Local server status: {response.status_code}")
        print(f"Local server response: {response.text}")
    except Exception as e:
        print(f"Local server error: {e}")
    
    print()
    
    # Test deployed server
    try:
        response = requests.post(
            "https://fill-sign-send.onrender.com/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            },
            timeout=10
        )
        print(f"Deployed server status: {response.status_code}")
        print(f"Deployed server response: {response.text}")
    except Exception as e:
        print(f"Deployed server error: {e}")

if __name__ == "__main__":
    test_mcp_endpoint()
