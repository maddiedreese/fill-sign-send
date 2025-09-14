#!/bin/bash
# Smoke test script for local MCP server testing

set -e

echo "🚀 MCP Doc Filling + E-Signing Server - Local Smoke Test"
echo "======================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "src/server.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the mcp-server-template root directory${NC}"
    exit 1
fi

# Check if sample PDF exists
if [ ! -f "samples/nda.pdf" ]; then
    echo -e "${YELLOW}⚠️  Sample PDF not found. Creating it now...${NC}"
    python3 create_sample_pdf.py
fi

echo -e "${BLUE}📋 Pre-flight checks:${NC}"

# Check Python version
python_version=$(python3 --version 2>&1)
echo "  ✓ Python: $python_version"

# Check if required packages are installed
echo "  📦 Checking dependencies..."
pip_check_result=0

for package in fastmcp uvicorn pypdfform docusign-esign requests python-dotenv cryptography reportlab PyJWT; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "    ✓ $package"
    else
        echo -e "    ${RED}❌ $package (missing)${NC}"
        pip_check_result=1
    fi
done

if [ $pip_check_result -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Some dependencies are missing. Installing...${NC}"
    pip3 install -r requirements.txt
fi

echo ""
echo -e "${BLUE}🔧 Environment Configuration:${NC}"
echo "  📁 Sample PDF: samples/nda.pdf"
echo "  🌐 Server will start on: http://localhost:8000"
echo "  🔗 MCP endpoint: http://localhost:8000/mcp"
echo ""

# Show environment variable status
echo -e "${BLUE}🔐 Configuration Status:${NC}"
if [ -n "$DOCUSIGN_ACCOUNT_ID" ]; then
    echo "  ✓ DocuSign Account ID: Set"
else
    echo -e "  ${YELLOW}⚠️  DocuSign Account ID: Not set${NC}"
fi

if [ -n "$DOCUSIGN_INTEGRATION_KEY" ]; then
    echo "  ✓ DocuSign Integration Key: Set"
else
    echo -e "  ${YELLOW}⚠️  DocuSign Integration Key: Not set${NC}"
fi

if [ -n "$DOCUSIGN_USER_ID" ]; then
    echo "  ✓ DocuSign User ID: Set"
else
    echo -e "  ${YELLOW}⚠️  DocuSign User ID: Not set${NC}"
fi

if [ -n "$DOCUSIGN_PRIVATE_KEY" ]; then
    echo "  ✓ DocuSign Private Key: Set"
else
    echo -e "  ${YELLOW}⚠️  DocuSign Private Key: Not set${NC}"
fi

if [ -n "$POKE_API_KEY" ]; then
    echo "  ✓ Poke API Key: Set"
else
    echo -e "  ${YELLOW}⚠️  Poke API Key: Not set${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Starting MCP Server...${NC}"
echo "  Press Ctrl+C to stop the server"
echo ""

# Start the server in background
python3 src/server.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server is running
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Server started successfully!${NC}"
    echo ""
    echo -e "${BLUE}🔍 Testing MCP Inspector Connection:${NC}"
    echo ""
    echo "1. Open a new terminal and run:"
    echo -e "   ${YELLOW}npx @modelcontextprotocol/inspector${NC}"
    echo ""
    echo "2. The MCP Inspector will open in your browser (usually http://localhost:3000)"
    echo "   If it opens on a different port, use that port instead."
    echo ""
    echo "3. In the Inspector, connect using:"
    echo -e "   ${YELLOW}Transport: Streamable HTTP${NC}"
    echo -e "   ${YELLOW}URL: http://localhost:8000/mcp${NC}"
    echo ""
    echo -e "${BLUE}🧪 Example Tool Calls:${NC}"
    echo ""
    echo "1. Test PDF field detection:"
    echo '   Tool: detect_pdf_fields'
    echo '   Args: {"file_url": "samples/nda.pdf"}'
    echo ""
    echo "2. Test PDF filling:"
    echo '   Tool: fill_pdf_fields'
    echo '   Args: {'
    echo '     "file_url": "samples/nda.pdf",'
    echo '     "field_values": {'
    echo '       "company_name": "Acme Corp",'
    echo '       "individual_name": "John Doe",'
    echo '       "agreement_date": "2024-01-15",'
    echo '       "purpose": "Software development collaboration",'
    echo '       "agree_to_terms": true'
    echo '     }'
    echo '   }'
    echo ""
    echo "3. Test server info:"
    echo '   Tool: get_server_info'
    echo '   Args: {}'
    echo ""
    echo "4. Test Poke notification (if configured):"
    echo '   Tool: notify_poke'
    echo '   Args: {'
    echo '     "message": "Test notification from MCP server",'
    echo '     "thread_ref": "test-thread"'
    echo '   }'
    echo ""
    
    if [ -n "$DOCUSIGN_ACCOUNT_ID" ] && [ -n "$DOCUSIGN_INTEGRATION_KEY" ] && [ -n "$DOCUSIGN_USER_ID" ] && [ -n "$DOCUSIGN_PRIVATE_KEY" ]; then
        echo "5. Test DocuSign (requires valid credentials):"
        echo '   Tool: send_for_signature'
        echo '   Args: {'
        echo '     "service": "docusign",'
        echo '     "recipients": [{"email": "test@example.com", "name": "Test User"}],'
        echo '     "subject": "Test NDA Signature",'
        echo '     "message": "Please sign this test NDA",'
        echo '     "file_url": "samples/nda.pdf"'
        echo '   }'
        echo ""
    else
        echo -e "${YELLOW}5. DocuSign testing: Set environment variables to test e-signature features${NC}"
        echo ""
    fi
    
    echo -e "${GREEN}✨ Server is running and ready for testing!${NC}"
    echo -e "${RED}Press Ctrl+C to stop the server${NC}"
    echo ""
    
    # Wait for user to stop the server
    wait $SERVER_PID
else
    echo -e "${RED}❌ Failed to start server${NC}"
    exit 1
fi
