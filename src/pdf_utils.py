#!/usr/bin/env python3
"""
PDF utilities for field detection, filling, and flattening.
Uses PyPDFForm for AcroForm handling.
"""
import os
import requests
from typing import List, Dict, Any, Union
from urllib.parse import urlparse
import tempfile
import logging

try:
    from PyPDFForm import PdfWrapper
except ImportError:
    raise ImportError("PyPDFForm is required. Install with: pip install pypdfform")

logger = logging.getLogger(__name__)

def fetch_pdf(file_url: str) -> bytes:
    """
    Fetch PDF content from a URL or local file path.
    
    Args:
        file_url: URL (http/https) or local file path
        
    Returns:
        PDF content as bytes
        
    Raises:
        ValueError: If the file cannot be accessed or is not a valid PDF
        requests.RequestException: If HTTP request fails
    """
    try:
        parsed_url = urlparse(file_url)
        
        if parsed_url.scheme in ('http', 'https'):
            # Fetch from URL
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            # Basic PDF validation
            content = response.content
            if not content.startswith(b'%PDF'):
                raise ValueError("Downloaded content is not a valid PDF file")
                
            return content
            
        elif parsed_url.scheme == 'file' or not parsed_url.scheme:
            # Local file path
            file_path = parsed_url.path if parsed_url.scheme == 'file' else file_url
            
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
                
            with open(file_path, 'rb') as f:
                content = f.read()
                
            # Basic PDF validation
            if not content.startswith(b'%PDF'):
                raise ValueError("File is not a valid PDF")
                
            return content
            
        else:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")
            
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to fetch PDF from URL: {e}")
    except Exception as e:
        raise ValueError(f"Error accessing PDF file: {e}")

def extract_acroform_fields(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract AcroForm field information from PDF.
    
    Args:
        pdf_bytes: PDF content as bytes
        
    Returns:
        List of field dictionaries with name, type, and other properties
        
    Raises:
        ValueError: If PDF cannot be processed or has no form fields
    """
    try:
        # Create a temporary file for PyPDFForm
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_file_path = temp_file.name
        
        try:
            # Load PDF with PyPDFForm
            pdf_wrapper = PdfWrapper(temp_file_path)
            
            # Get form fields
            fields = []
            
            # PyPDFForm provides sample_data which shows available fields
            try:
                sample_data = pdf_wrapper.sample_data
                if sample_data:
                    for field_name, sample_value in sample_data.items():
                        field_info = {
                            "name": field_name,
                            "type": _guess_field_type(sample_value),
                            "sample_value": sample_value,
                            "required": False  # PyPDFForm doesn't provide this info directly
                        }
                        fields.append(field_info)
                else:
                    logger.warning("No form fields found in PDF")
                    
            except Exception as e:
                logger.warning(f"Could not extract field information: {e}")
                
            return fields
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        raise ValueError(f"Failed to extract form fields from PDF: {e}")

def _guess_field_type(sample_value: Any) -> str:
    """
    Guess the field type based on the sample value from PyPDFForm.
    
    Args:
        sample_value: Sample value from PyPDFForm
        
    Returns:
        Guessed field type as string
    """
    if isinstance(sample_value, bool):
        return "checkbox"
    elif isinstance(sample_value, (int, float)):
        return "number"
    elif isinstance(sample_value, str):
        if len(sample_value) > 50:
            return "textarea"
        else:
            return "text"
    else:
        return "text"

def fill_and_flatten(pdf_bytes: bytes, field_values: Dict[str, Any]) -> bytes:
    """
    Fill PDF form fields and flatten the result.
    
    Args:
        pdf_bytes: Original PDF content as bytes
        field_values: Dictionary mapping field names to values
        
    Returns:
        Filled and flattened PDF as bytes
        
    Raises:
        ValueError: If PDF cannot be processed or fields cannot be filled
    """
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as input_file:
            input_file.write(pdf_bytes)
            input_file_path = input_file.name
            
        output_file_path = None
        
        try:
            # Load PDF with PyPDFForm
            pdf_wrapper = PdfWrapper(input_file_path)
            
            # Convert and validate field values
            processed_values = {}
            sample_data = pdf_wrapper.sample_data or {}
            
            for field_name, value in field_values.items():
                if field_name in sample_data:
                    # Type coercion based on sample data
                    sample_value = sample_data[field_name]
                    processed_values[field_name] = _coerce_field_value(value, sample_value)
                else:
                    # Field not found in sample data, use as-is but convert to string
                    processed_values[field_name] = str(value) if value is not None else ""
                    logger.warning(f"Field '{field_name}' not found in PDF form, using as text")
            
            # Fill the form
            filled_pdf = pdf_wrapper.fill(processed_values)
            
            # Get the filled PDF bytes directly
            result_bytes = filled_pdf.read()
                
            return result_bytes
            
        finally:
            # Clean up temporary files
            if os.path.exists(input_file_path):
                os.unlink(input_file_path)
                
    except Exception as e:
        raise ValueError(f"Failed to fill and flatten PDF: {e}")

def _coerce_field_value(value: Any, sample_value: Any) -> Any:
    """
    Coerce a field value to match the expected type based on sample data.
    
    Args:
        value: Input value to coerce
        sample_value: Sample value from PyPDFForm indicating expected type
        
    Returns:
        Coerced value
    """
    if isinstance(sample_value, bool):
        # Checkbox field
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'checked')
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return False
            
    elif isinstance(sample_value, (int, float)):
        # Numeric field
        try:
            if isinstance(sample_value, int):
                return int(float(value))  # Convert via float to handle "1.0" -> 1
            else:
                return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert '{value}' to number, using 0")
            return 0
            
    else:
        # Text field
        return str(value) if value is not None else ""

def save_temp_pdf(pdf_bytes: bytes, prefix: str = "temp_pdf_") -> str:
    """
    Save PDF bytes to a temporary file and return the file path.
    
    Args:
        pdf_bytes: PDF content as bytes
        prefix: Prefix for the temporary filename
        
    Returns:
        Path to the temporary file
    """
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(
        suffix='.pdf', 
        prefix=prefix, 
        dir=temp_dir, 
        delete=False
    ) as temp_file:
        temp_file.write(pdf_bytes)
        return temp_file.name
