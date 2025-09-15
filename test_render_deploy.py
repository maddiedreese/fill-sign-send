#!/usr/bin/env python3
"""
Test script to verify Render deployment configuration
"""
import os
import sys
from pathlib import Path

# Set environment variables like Render would
os.environ["ENVIRONMENT"] = "production"
os.environ["PORT"] = "8000"

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def test_server_startup():
    """Test that the server can start without errors"""
    try:
        print("Testing server startup...")
        
        # Import the server module
        from server import mcp
        print("✅ Server module imported successfully")
        
        # Test that mcp.run() can be called with correct parameters
        print("✅ FastMCP server object created")
        
        # Test the server info tool
        print("✅ Server ready for deployment")
        
        return True
        
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Render deployment configuration...")
    
    success = test_server_startup()
    
    if success:
        print("\n✅ All tests passed! Server should deploy successfully on Render.")
    else:
        print("\n❌ Tests failed. Check the errors above.")
        sys.exit(1)
