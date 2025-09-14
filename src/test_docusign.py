#!/usr/bin/env python3
"""
Test DocuSign integration directly
"""
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from esign_docusign import send_for_signature_docusign

def create_test_pdf():
    """Create a simple test PDF"""
    c = canvas.Canvas('test.pdf', pagesize=letter)
    c.drawString(100, 750, 'Test Document for DocuSign')
    c.drawString(100, 700, 'This is a test document to verify DocuSign integration.')
    c.drawString(100, 650, 'Please sign this document to test the e-signature functionality.')
    c.save()
    print("✅ Test PDF created successfully")

def test_docusign():
    """Test DocuSign integration"""
    try:
        # Create test PDF
        create_test_pdf()
        
        # Test DocuSign integration
        result = send_for_signature_docusign(
            file_url='test.pdf',
            recipient_email='test@example.com',
            recipient_name='Test User',
            subject='Test Document',
            message='Please sign this test document.'
        )
        
        print(f"DocuSign result: {result}")
        
        if result.get('success'):
            print(f"✅ SUCCESS: Envelope ID {result['envelope_id']}")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_docusign()
