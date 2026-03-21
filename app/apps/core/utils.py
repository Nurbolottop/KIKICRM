"""
Utility functions for the core app.
"""
import re


def normalize_phone(phone):
    """
    Normalize phone number to standard format.
    Keeps only digits and optionally the leading +.
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters except leading +
    phone = str(phone).strip()
    
    # Keep leading + if present
    has_plus = phone.startswith('+')
    digits = re.sub(r'\D', '', phone)
    
    if has_plus:
        return '+' + digits
    return digits
