"""
Private key loader that handles PKCS#1 RSA private keys from .env files
"""
import os
from dotenv import load_dotenv

def load_private_key_from_env() -> str:
    """
    Load private key from .env file, handling multi-line format.
    
    Returns:
        Private key as a single string with proper PEM format
    """
    # Load environment variables
    load_dotenv()
    
    # Try to get from environment variable first
    private_key = os.getenv('DOCUSIGN_PRIVATE_KEY', '')
    
    if not private_key or len(private_key) < 100:
        # If the private key is too short, it might be truncated
        # Read the .env file directly to get the full private key
        try:
            with open('.env', 'r') as f:
                content = f.read()
            
            # Find the private key section
            lines = content.split('\n')
            private_key_lines = []
            in_private_key = False
            
            for line in lines:
                if line.startswith('DOCUSIGN_PRIVATE_KEY='):
                    # Get the first line
                    private_key_lines.append(line.split('=', 1)[1])
                    in_private_key = True
                elif in_private_key and line and not line.startswith('#'):
                    # Continue reading private key lines
                    private_key_lines.append(line)
                elif in_private_key and (line.startswith('#') or line.startswith('DOCUSIGN_') or line.startswith('POKE_') or line.startswith('ENVIRONMENT=')):
                    # End of private key
                    break
            
            # Join all private key lines
            private_key = ''.join(private_key_lines)
            
        except Exception as e:
            raise ValueError(f"Could not load private key from .env file: {e}")
    
    # Ensure proper PEM format
    private_key = private_key.strip()
    
    # The private key should already have proper headers from .env
    if not private_key.startswith("-----BEGIN"):
        raise ValueError("Private key must have proper PEM headers")
    
    return private_key
