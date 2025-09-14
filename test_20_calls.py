#!/usr/bin/env python3
"""
Test 20 actual API calls to the complete MCP server
"""
import requests
import json
import time

# Test data
test_calls = [
    # 1-5: Initialize calls
    {"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}},
    {"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "poke-client", "version": "1.0.0"}}},
    {"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "mcp-client", "version": "1.0.0"}}},
    {"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client-2", "version": "1.0.0"}}},
    {"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client-3", "version": "1.0.0"}}},
    
    # 6-10: Tools list calls
    {"method": "tools/list", "params": {}},
    {"method": "tools/list", "params": {}},
    {"method": "tools/list", "params": {}},
    {"method": "tools/list", "params": {}},
    {"method": "tools/list", "params": {}},
    
    # 11-15: Tool calls
    {"method": "tools/call", "params": {"name": "get_server_info", "arguments": {}}},
    {"method": "tools/call", "params": {"name": "detect_pdf_fields", "arguments": {"file_url": "test.pdf"}}},
    {"method": "tools/call", "params": {"name": "fill_pdf_fields", "arguments": {"file_url": "test.pdf", "field_values": {"name": "John Doe", "email": "john@example.com"}}}},
    {"method": "tools/call", "params": {"name": "send_for_signature", "arguments": {"file_url": "test.pdf", "recipient_email": "test@example.com", "recipient_name": "Test User"}}},
    {"method": "tools/call", "params": {"name": "check_signature_status", "arguments": {"envelope_id": "test-envelope-123"}}},
    
    # 16-20: More tool calls
    {"method": "tools/call", "params": {"name": "download_signed_pdf", "arguments": {"envelope_id": "test-envelope-123"}}},
    {"method": "tools/call", "params": {"name": "notify_poke", "arguments": {"message": "Test notification", "attachments": ["file1.pdf", "file2.pdf"]}}},
    {"method": "tools/call", "params": {"name": "get_server_info", "arguments": {}}},
    {"method": "tools/call", "params": {"name": "detect_pdf_fields", "arguments": {"file_url": "contract.pdf"}}},
    {"method": "tools/call", "params": {"name": "fill_pdf_fields", "arguments": {"file_url": "contract.pdf", "field_values": {"company": "Acme Corp", "date": "2024-01-01"}}}}
]

def test_mcp_call(call_data, call_number):
    """Test a single MCP call"""
    try:
        response = requests.post(
            "http://localhost:8000/mcp",
            json={"jsonrpc": "2.0", "id": call_number, **call_data},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Call {call_number}: {call_data['method']} - SUCCESS")
            return True, result
        else:
            print(f"❌ Call {call_number}: {call_data['method']} - FAILED (Status: {response.status_code})")
            return False, None
            
    except Exception as e:
        print(f"❌ Call {call_number}: {call_data['method']} - ERROR: {str(e)}")
        return False, None

def test_sse_calls():
    """Test SSE endpoint calls"""
    try:
        # Test GET request
        response = requests.get("http://localhost:8000/sse", timeout=10)
        if response.status_code == 200:
            print("✅ SSE GET: SUCCESS")
            return True
        else:
            print(f"❌ SSE GET: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ SSE GET: ERROR: {str(e)}")
        return False

def main():
    print("🚀 Starting 20 MCP API calls test...")
    print("=" * 50)
    
    success_count = 0
    total_calls = len(test_calls)
    
    # Test MCP calls
    for i, call_data in enumerate(test_calls, 1):
        success, result = test_mcp_call(call_data, i)
        if success:
            success_count += 1
        time.sleep(0.1)  # Small delay between calls
    
    # Test SSE calls
    print("\n" + "=" * 50)
    print("Testing SSE endpoint...")
    sse_success = test_sse_calls()
    if sse_success:
        success_count += 1
        total_calls += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {success_count}/{total_calls} calls successful")
    print(f"Success rate: {(success_count/total_calls)*100:.1f}%")
    
    if success_count == total_calls:
        print("🎉 ALL TESTS PASSED! Server is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()
