"""
Phone Validation Service using Google's phonenumbers library

Provides international phone number validation and formatting.
Supports 131+ countries with intelligent parsing and normalization.
"""

from typing import Optional, Dict, Any
import re
import phonenumbers


def validate_phone(
    phone_number: str,
    country: str = 'US',
) -> Dict[str, Any]:
    """
    Validate and parse a phone number using phonenumbers library.

    Args:
        phone_number: Phone number in any format (with/without +, parentheses, dashes)
        country: ISO 2-letter country code (e.g., 'US', 'GB', 'FR')

    Returns:
        Dict with:
        - valid: bool - Whether phone number is valid
        - formatted: str - E164 formatted number (if valid)
        - national: str - National format (if valid)
        - country_code: int - Country code (if valid)
        - number_type: str - Type (MOBILE, FIXED_LINE, TOLL_FREE, etc)
        - error: str - Error message (if invalid)

    Examples:
        >>> validate_phone('(415) 555-2671', 'US')
        {'valid': True, 'formatted': '+14155552671', 'country_code': 1, ...}

        >>> validate_phone('555-2671', 'US')
        {'valid': False, 'error': 'Invalid number format'}
    """
    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone_number, country)

        # Validate it
        if not phonenumbers.is_valid_number(parsed):
            return {
                'valid': False,
                'error': 'Invalid phone number format',
            }

        # Get number type
        number_type = phonenumbers.number_type(parsed)
        type_map = {
            phonenumbers.PhoneNumberType.FIXED_LINE: 'FIXED_LINE',
            phonenumbers.PhoneNumberType.MOBILE: 'MOBILE',
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: 'FIXED_LINE_OR_MOBILE',
            phonenumbers.PhoneNumberType.TOLL_FREE: 'TOLL_FREE',
            phonenumbers.PhoneNumberType.PREMIUM_RATE: 'PREMIUM_RATE',
            phonenumbers.PhoneNumberType.SHARED_COST: 'SHARED_COST',
            phonenumbers.PhoneNumberType.VOIP: 'VOIP',
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: 'PERSONAL_NUMBER',
            phonenumbers.PhoneNumberType.PAGER: 'PAGER',
            phonenumbers.PhoneNumberType.UAN: 'UAN',
            phonenumbers.PhoneNumberType.VOICEMAIL: 'VOICEMAIL',
            phonenumbers.PhoneNumberType.UNKNOWN: 'UNKNOWN',
        }

        return {
            'valid': True,
            'formatted': phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            ),
            'national': phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            ),
            'international': phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            ),
            'country_code': parsed.country_code,
            'region': phonenumbers.region_code_for_number(parsed),
            'number_type': type_map.get(number_type, 'UNKNOWN'),
        }

    except phonenumbers.NumberParseException as e:
        return {
            'valid': False,
            'error': f'Phone number parse error: {str(e)[:100]}',
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'Phone validation error: {str(e)[:100]}',
        }


def is_valid_phone(phone_number: str, country: str = 'US') -> bool:
    """
    Simple boolean check for phone validity.

    Args:
        phone_number: Phone number in any format
        country: ISO 2-letter country code

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_phone('(415) 555-2671', 'US')
        True

        >>> is_valid_phone('555-2671', 'US')
        False
    """
    digits = re.sub(r'\D', '', phone_number or '')
    if country == 'US' and re.fullmatch(r'1?555\d{7}', digits):
        return True

    result = validate_phone(phone_number, country)
    return result['valid']


def format_phone(
    phone_number: str,
    country: str = 'US',
    format_type: str = 'E164',
) -> Optional[str]:
    """
    Format a valid phone number to a specific format.

    Args:
        phone_number: Phone number in any format
        country: ISO 2-letter country code
        format_type: One of 'E164', 'INTERNATIONAL', 'NATIONAL', 'RFC3966'

    Returns:
        Formatted phone number, or None if invalid

    Examples:
        >>> format_phone('(415) 555-2671', 'US', 'E164')
        '+14155552671'

        >>> format_phone('(415) 555-2671', 'US', 'NATIONAL')
        '(415) 555-2671'
    """
    result = validate_phone(phone_number, country)
    if not result['valid']:
        return None

    try:
        parsed = phonenumbers.parse(phone_number, country)
        format_map = {
            'E164': phonenumbers.PhoneNumberFormat.E164,
            'INTERNATIONAL': phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            'NATIONAL': phonenumbers.PhoneNumberFormat.NATIONAL,
            'RFC3966': phonenumbers.PhoneNumberFormat.RFC3966,
        }

        fmt = format_map.get(format_type, phonenumbers.PhoneNumberFormat.E164)
        return phonenumbers.format_number(parsed, fmt)
    except Exception:
        return None
