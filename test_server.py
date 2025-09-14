#!/usr/bin/env python3
"""
Test script to verify the server works
"""
import subprocess
import time
import requests
import json

def test_server():
    print("🚀 Starting server test...")
    
    # Start the server
    print("📡 Starting server...")
    process = subprocess.Popen(['python3', 'src/server.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Test the server
    try:
        print("🧪 Testing server...")
        response = requests.post('http://localhost:8000/sse', 
                               json={'tool': 'get_server_info', 'args': {}},
                               timeout=10)
        
        print(f"✅ Server response: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        
        if response.status_code == 200:
            print("🎉 Server is working!")
        else:
            print("❌ Server returned error")
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
    
    finally:
        # Clean up
        print("🧹 Stopping server...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_server()
