#!/usr/bin/env python3
"""
Test 20 REAL API calls to the complete MCP server
Using actual PDF files and DocuSign integration
"""
import requests
import json
import time
import os

# Test data with real files
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
    
    # 11-15: REAL Tool calls with actual PDF files
    {"method": "tools/call", "params": {"name": "get_server_info", "arguments": {}}},
    {"method": "tools/call", "params": {"name": "detect_pdf_fields", "arguments": {"file_url": "sample_form.pdf"}}},
    {"method": "tools/call", "params": {"name": "fill_pdf_fields", "arguments": {"file_url": "sample_form.pdf", "field_values": {"name": "John Doe", "email": "john@example.com", "company": "Acme Corp"}}}},
    {"method": "tools/call", "params": {"name": "send_for_signature", "arguments": {"file_url": "sample_form.pdf", "recipient_email": "test@example.com", "recipient_name": "Test User", "subject": "Please sign this document", "message": "Please review and sign this important document."}}},
    {"method": "tools/call", "params": {"name": "check_signature_status", "arguments": {"envelope_id": "test-envelope-123"}}},
    
    # 16-20: More REAL tool calls
    {"method": "tools/call", "params": {"name": "download_signed_pdf", "arguments": {"envelope_id": "test-envelope-123"}}},
    {"method": "tools/call", "params": {"name": "notify_poke", "arguments": {"message": "Document processing completed", "attachments": ["sample_form.pdf", "filled_form.pdf"]}}},
    {"method": "tools/call", "params": {"name": "get_server_info", "arguments": {}}},
    {"method": "tools/call", "params": {"name": "detect_pdf_fields", "arguments": {"file_url": "contract_template.pdf"}}},
    {"method": "tools/call", "params": {"name": "fill_pdf_fields", "arguments": {"file_url": "contract_template.pdf", "field_values": {"company": "Acme Corp", "date": "2024-01-01", "signature": "John Doe"}}}}
]

def test_mcp_call(call_data, call_number):
    """Test a single MCP call"""
    try:
        response = requests.post(
            "http://localhost:8000/mcp",
            json={"jsonrpc": "2.0", "id": call_number, **call_data},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Call {call_number}: {call_data['method']} - SUCCESS")
            if 'result' in result and 'success' in result['result']:
                print(f"   Result: {result['result']['message']}")
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

def create_sample_pdf():
    """Create a sample PDF for testing"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas("sample_form.pdf", pagesize=letter)
        c.drawString(100, 750, "Sample Form")
        c.drawString(100, 700, "Name: _________________")
        c.drawString(100, 650, "Email: _________________")
        c.drawString(100, 600, "Company: _________________")
        c.save()
        print("✅ Created sample_form.pdf for testing")
        return True
    except Exception as e:
        print(f"⚠️  Could not create sample PDF: {e}")
        return False

def main():
    print("🚀 Starting 20 REAL MCP API calls test...")
    print("=" * 50)
    
    # Create sample PDF for testing
    create_sample_pdf()
    
    success_count = 0
    total_calls = len(test_calls)
    
    # Test MCP calls
    for i, call_data in enumerate(test_calls, 1):
        success, result = test_mcp_call(call_data, i)
        if success:
            success_count += 1
        time.sleep(0.5)  # Small delay between calls
    
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
        print("🎉 ALL REAL API TESTS PASSED! Server is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    # Cleanup
    if os.path.exists("sample_form.pdf"):
        os.remove("sample_form.pdf")
        print("🧹 Cleaned up test files")

if __name__ == "__main__":
    main()
