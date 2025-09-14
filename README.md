# Doc Filling + E-Signing MCP Server

A production-ready MCP server for document filling and electronic signature workflows. Built with [FastMCP](https://github.com/jlowin/fastmcp) and designed for seamless integration with Poke and DocuSign.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/InteractionCo/mcp-server-template)

## Features

Complete "Inbox → Fill → Sign → Return" workflow with 6 MCP tools:

1. **`detect_pdf_fields`** - Detect and list form fields in PDF documents
2. **`fill_pdf_fields`** - Fill PDF forms and flatten for non-editable output
3. **`send_for_signature`** - Send documents via DocuSign (Adobe Sign planned)
4. **`check_signature_status`** - Monitor signature request status
5. **`download_signed_pdf`** - Retrieve completed signed documents
6. **`notify_poke`** - Send progress updates to Poke inbound webhook

## Quick Start

### Local Development

1. **Clone and Setup**
   ```bash
   git clone <your-repo-url>
   cd mcp-server-template
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create Sample PDF** (optional)
   ```bash
   python3 create_sample_pdf.py
   ```

3. **Run Smoke Test**
   ```bash
   ./scripts/smoke_local.sh
   ```

4. **Test with MCP Inspector**
   ```bash
   # Terminal 1: Start server
   python src/server.py
   
   # Terminal 2: Start inspector
   npx @modelcontextprotocol/inspector
   ```
   
   Connect to `http://localhost:8000/mcp` using "Streamable HTTP" transport.

## Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DOCUSIGN_BASE_PATH` | No | DocuSign API base URL | `https://demo.docusign.net` |
| `DOCUSIGN_ACCOUNT_ID` | Yes* | DocuSign account ID | `3c08c9cc-3c87-4a5e-9f59-8ee3670ba4f4` |
| `DOCUSIGN_INTEGRATION_KEY` | Yes* | DocuSign client ID | `d5866028-eab7-4a93-a595-130664eaac6b` |
| `DOCUSIGN_USER_ID` | Yes* | DocuSign user GUID | `55269937-f820-4015-8f1f-415ce75b03f9` |
| `DOCUSIGN_PRIVATE_KEY` | Yes* | RSA private key (PEM format) | `MIIEoAIBAAKCAQEA...` |
| `POKE_API_KEY` | No | Poke API key for notifications | `pk_SrRDm-Dpg6wiszN-XYKyBPT4GRK0cBh4WwaOCDC0PEM` |
| `PORT` | No | Server port | `8000` |
| `ENVIRONMENT` | No | Environment name | `development` |

*Required for DocuSign e-signature features

### DocuSign Setup

1. **Create DocuSign Developer Account**
   - Visit [DocuSign Developer Center](https://developers.docusign.com/)
   - Create a free developer account

2. **Create Integration**
   - Go to Apps & Keys in your DocuSign admin
   - Create a new app
   - Note the Integration Key (Client ID)

3. **Generate RSA Key Pair**
   - In your app settings, add an RSA keypair
   - Download the private key
   - Set `DOCUSIGN_PRIVATE_KEY` to the full PEM content

4. **Get Account & User IDs**
   - Account ID: Found in your DocuSign admin settings
   - User ID: Your user GUID from the admin panel

### Poke Integration

Set `POKE_API_KEY` to enable progress notifications:
```bash
export POKE_API_KEY="pk_SrRDm-Dpg6wiszN-XYKyBPT4GRK0cBh4WwaOCDC0PEM"
```

## Usage Examples

### 1. Detect PDF Fields
```json
{
  "tool": "detect_pdf_fields",
  "arguments": {
    "file_url": "samples/nda.pdf"
  }
}
```

### 2. Fill PDF Form
```json
{
  "tool": "fill_pdf_fields",
  "arguments": {
    "file_url": "samples/nda.pdf",
    "field_values": {
      "company_name": "Acme Corp",
      "individual_name": "John Doe",
      "agreement_date": "2024-01-15",
      "purpose": "Software development collaboration",
      "agree_to_terms": true
    }
  }
}
```

### 3. Send for Signature
```json
{
  "tool": "send_for_signature",
  "arguments": {
    "service": "docusign",
    "recipients": [
      {"email": "signer@example.com", "name": "John Doe"}
    ],
    "subject": "Please sign this NDA",
    "message": "Please review and sign the attached NDA.",
    "file_url": "samples/nda.pdf"
  }
}
```

### 4. Check Status
```json
{
  "tool": "check_signature_status",
  "arguments": {
    "service": "docusign",
    "envelope_id": "envelope-id-from-send-response"
  }
}
```

### 5. Download Signed PDF
```json
{
  "tool": "download_signed_pdf",
  "arguments": {
    "service": "docusign",
    "envelope_id": "envelope-id-from-send-response"
  }
}
```

### 6. Send Poke Notification
```json
{
  "tool": "notify_poke",
  "arguments": {
    "message": "Document signed successfully!",
    "thread_ref": "nda-signing-thread",
    "attachments": [
      {"name": "signed_nda.pdf", "url": "file://path/to/signed.pdf"}
    ]
  }
}
```

## Deployment

### Render Deployment

#### Option 1: One-Click Deploy
Click the "Deploy to Render" button above.

#### Option 2: Manual Deployment
1. Fork this repository
2. Connect your GitHub account to Render
3. Create a new Web Service on Render
4. Connect your forked repository
5. Set environment variables in Render dashboard
6. Deploy

Your server will be available at `https://your-service-name.onrender.com/mcp`

### Poke Integration

1. **Add MCP Server to Poke**
   - Go to Poke → Settings → Connections → Integrations
   - Click "New Integration"
   - Select "Custom MCP Server"
   - URL: `https://your-service-name.onrender.com/mcp`
   - Transport: "Streamable HTTP"

2. **Configure Webhook** (optional)
   - Set `POKE_API_KEY` in your environment
   - The server will send progress updates to Poke automatically

## Development

### Project Structure
```
mcp-server-template/
├── src/
│   ├── server.py           # Main MCP server with 6 tools
│   ├── settings.py         # Environment configuration
│   ├── pdf_utils.py        # PDF processing utilities
│   ├── esign_docusign.py   # DocuSign integration
│   └── esign_adobe.py      # Adobe Sign (placeholder)
├── samples/
│   └── nda.pdf            # Sample PDF with form fields
├── scripts/
│   └── smoke_local.sh     # Local testing script
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
└── README.md              # This file
```

### Adding New Tools

```python
@mcp.tool(description="Your tool description")
def your_tool_name(param1: str, param2: int) -> dict:
    """
    Your tool implementation.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        Dictionary with results
    """
    try:
        # Your logic here
        return {"success": True, "result": "data"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Testing

Run the smoke test to verify everything works:
```bash
./scripts/smoke_local.sh
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **DocuSign Authentication Fails**
   - Verify all DocuSign environment variables are set
   - Check private key format (should be full PEM)
   - Ensure user has API access permissions

3. **PDF Processing Errors**
   - Verify PDF has AcroForm fields (not XFA)
   - Check file permissions and accessibility

4. **MCP Inspector Connection Issues**
   - Ensure server is running on correct port
   - Use exact URL: `http://localhost:8000/mcp`
   - Check firewall settings

### Logs

Server logs include:
- PDF processing status
- DocuSign API responses
- Poke webhook delivery status
- Error details with stack traces

## License

MIT License - see LICENSE file for details.
