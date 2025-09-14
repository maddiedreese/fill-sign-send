#!/usr/bin/env python3
"""
Settings module for MCP Doc Filling + E-Signing server.
Handles environment variable loading and validation.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings:
    """Configuration settings loaded from environment variables."""
    
    # DocuSign Configuration
    DOCUSIGN_BASE_PATH: str = os.getenv("DOCUSIGN_BASE_PATH", "https://demo.docusign.net")
    DOCUSIGN_ACCOUNT_ID: Optional[str] = os.getenv("DOCUSIGN_ACCOUNT_ID")
    DOCUSIGN_INTEGRATION_KEY: Optional[str] = os.getenv("DOCUSIGN_INTEGRATION_KEY")
    DOCUSIGN_USER_ID: Optional[str] = os.getenv("DOCUSIGN_USER_ID")
    DOCUSIGN_PRIVATE_KEY: Optional[str] = os.getenv("DOCUSIGN_PRIVATE_KEY")
    
    # Poke Configuration
    POKE_API_KEY: Optional[str] = os.getenv("POKE_API_KEY")
    POKE_WEBHOOK_URL: str = "https://poke.com/api/v1/inbound-sms/webhook"
    
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    @classmethod
    def validate_docusign_config(cls) -> bool:
        """Validate that all required DocuSign environment variables are set."""
        required_vars = [
            cls.DOCUSIGN_ACCOUNT_ID,
            cls.DOCUSIGN_INTEGRATION_KEY,
            cls.DOCUSIGN_USER_ID,
            cls.DOCUSIGN_PRIVATE_KEY
        ]
        return all(var is not None and var.strip() != "" for var in required_vars)
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def get_docusign_base_url(cls) -> str:
        """Get the correct DocuSign base URL based on environment."""
        if cls.is_production():
            return "https://www.docusign.net"
        else:
            return "https://demo.docusign.net"
    
    @classmethod
    def validate_poke_config(cls) -> bool:
        """Validate that Poke API key is set."""
        return cls.POKE_API_KEY is not None and cls.POKE_API_KEY.strip() != ""
    
    @classmethod
    def get_docusign_config(cls) -> dict:
        """Get DocuSign configuration as a dictionary."""
        if not cls.validate_docusign_config():
            raise ValueError("DocuSign configuration is incomplete. Please set all required environment variables.")
        
        return {
            "base_path": cls.DOCUSIGN_BASE_PATH,
            "account_id": cls.DOCUSIGN_ACCOUNT_ID,
            "integration_key": cls.DOCUSIGN_INTEGRATION_KEY,
            "user_id": cls.DOCUSIGN_USER_ID,
            "private_key": cls.DOCUSIGN_PRIVATE_KEY
        }

# Global settings instance
settings = Settings()
