# Phone Validation Architecture

## Overview

Householder v1.1 uses **Google's phonenumbers library** for professional international phone number validation and formatting. This provides:

- **131+ country support** with intelligent parsing
- **Multiple format support**: E164, national, international, RFC3966
- **Number type detection**: MOBILE, FIXED_LINE, TOLL_FREE, VOIP, etc.
- **Region detection**: Identifies country code and region for any valid number

---

## Why phonenumbers Library?

The phonenumbers library is the industry standard for phone validation:

1. **Professional**: Used by Google, Twilio, and major telecom platforms
2. **Comprehensive**: Validates numbers across 131+ countries
3. **Smart parsing**: Handles various formats (parentheses, dashes, spaces, +prefix)
4. **Type detection**: Identifies whether a number is mobile, fixed-line, toll-free, etc.
5. **Maintainable**: No custom regex patterns needed; library stays updated with country rules

---

## Implementation

### Code Location

File: `scripts/householder/phone_validation_service.py`

Functions:
- `validate_phone(phone_number, country='US')` — Full validation with details
- `is_valid_phone(phone_number, country='US')` — Simple boolean check
- `format_phone(phone_number, country='US', format_type='E164')` — Format to specific format

### Integration Point

File: `scripts/householder/issue_recalculation_service.py`

The issue recalculation service imports and uses `is_valid_phone()` for phone field validation:

```python
from .phone_validation_service import is_valid_phone

# In is_issue_resolved():
elif field == 'phone':
    return is_valid_phone(effective_str)
```

---

## Function Details

### validate_phone(phone_number, country='US')

Comprehensive validation returning all details.

**Parameters:**
- `phone_number` (str): Phone in any format (with/without +, parentheses, dashes)
- `country` (str): ISO 2-letter country code (e.g., 'US', 'GB', 'FR')

**Returns:**
```python
{
    'valid': bool,                  # Whether number is valid
    'formatted': '+14155552671',    # E164 format (if valid)
    'national': '(415) 555-2671',   # National format (if valid)
    'international': '+1 415-555-2671',  # International format
    'country_code': 1,              # Country code (if valid)
    'region': 'US',                 # Region/country (if valid)
    'number_type': 'MOBILE',        # Type: MOBILE, FIXED_LINE, TOLL_FREE, etc.
    'error': 'Phone parse error...' # Error message (if invalid)
}
```

**Examples:**

```python
# Valid US phone
result = validate_phone('(415) 555-2671', 'US')
# {
#     'valid': True,
#     'formatted': '+14155552671',
#     'country_code': 1,
#     'region': 'US',
#     'number_type': 'FIXED_LINE_OR_MOBILE'
# }

# Valid UK phone
result = validate_phone('2079460958', 'GB')
# {
#     'valid': True,
#     'formatted': '+442079460958',
#     'country_code': 44,
#     'region': 'GB'
# }

# Invalid: too short
result = validate_phone('555', 'US')
# {
#     'valid': False,
#     'error': 'Phone number parse error: ...'
# }
```

### is_valid_phone(phone_number, country='US')

Simple boolean check for phone validity.

**Parameters:**
- `phone_number` (str): Phone in any format
- `country` (str): ISO 2-letter country code

**Returns:**
- `True` if valid, `False` otherwise

**Examples:**

```python
is_valid_phone('(415) 555-2671', 'US')      # → True
is_valid_phone('+1 415 555 2671', 'US')     # → True
is_valid_phone('555', 'US')                  # → False
is_valid_phone('2079460958', 'GB')          # → True
```

### format_phone(phone_number, country='US', format_type='E164')

Format a valid phone number to a specific format.

**Parameters:**
- `phone_number` (str): Phone in any format
- `country` (str): ISO 2-letter country code
- `format_type` (str): One of 'E164', 'INTERNATIONAL', 'NATIONAL', 'RFC3966'

**Returns:**
- Formatted phone number (str), or `None` if invalid

**Examples:**

```python
format_phone('(415) 555-2671', 'US', 'E164')
# → '+14155552671'

format_phone('(415) 555-2671', 'US', 'NATIONAL')
# → '(415) 555-2671'

format_phone('(415) 555-2671', 'US', 'INTERNATIONAL')
# → '+1 415-555-2671'

format_phone('555', 'US', 'E164')
# → None
```

---

## Supported Formats

The phonenumbers library intelligently parses various formats:

### US Examples
- `5551234567` — Plain digits
- `555-123-4567` — With dashes
- `(555) 123-4567` — Parentheses and spaces
- `+1 555 123 4567` — International with country code
- `1 555 123 4567` — Leading 1

### International Examples
- `+442079460958` — UK with country code
- `2079460958` — UK without country code (if country param is 'GB')
- `+33140205050` — France
- `+61291234567` — Australia

---

## Supported Countries

The phonenumbers library supports 131+ countries including:

**Major regions:**
- North America: US, CA, MX
- Europe: UK, FR, DE, IT, ES, NL, BE, etc.
- Asia: CN, JP, IN, SG, HK, KR, etc.
- Oceania: AU, NZ
- South America: BR, AR, CL, CO, etc.
- Africa: ZA, EG, NG, etc.

For the complete list, refer to: https://github.com/daviddrysdale/python-phonenumbers/blob/dev/python/phonenumbers/data/region_code.txt

---

## Number Types

The phonenumbers library identifies these number types:

- `FIXED_LINE` — Landline
- `MOBILE` — Cell phone
- `FIXED_LINE_OR_MOBILE` — Could be either (region doesn't distinguish)
- `TOLL_FREE` — 1-800, 1-888, etc.
- `PREMIUM_RATE` — Paid services
- `SHARED_COST` — Shared cost numbers
- `VOIP` — VoIP numbers
- `PERSONAL_NUMBER` — Personal number services
- `PAGER` — Pager number
- `UAN` — Universal Access Number
- `VOICEMAIL` — Voicemail number
- `UNKNOWN` — Unknown type

---

## Integration with Issue Recalculation

When a phone field has a validation issue:

1. **Missing Issue**: Resolved if phone number becomes non-empty and valid
2. **Invalid Issue**: Resolved if phone is corrected to a valid format

**Example:**

```python
from householder.issue_recalculation_service import is_issue_resolved

# Missing phone resolved by adding valid number
is_issue_resolved('phone', '(415) 555-2671', 'missing')
# → True

# Empty still not resolved
is_issue_resolved('phone', '', 'missing')
# → False
```

---

## Test Coverage

All functions tested in: `tests/unit/test_phone_validation_service.py`

### Test Categories

- **Basic validation**: Valid/invalid US phones
- **Format variations**: Parentheses, dashes, spaces, +prefix
- **International**: UK, France, Canada, Australia
- **Edge cases**: Too short, too long, invalid format, empty
- **Format types**: E164, NATIONAL, INTERNATIONAL, RFC3966
- **Country-specific**: GB, CA, FR, AU, etc.

### Running Tests

```bash
# Run phone validation tests only
pytest tests/unit/test_phone_validation_service.py -v

# Run with coverage
pytest tests/unit/test_phone_validation_service.py --cov=householder.phone_validation_service
```

---

## Error Handling

The library raises `phonenumbers.NumberParseException` for unparseable input, which is caught and returned as `{'valid': False, 'error': '...'}`.

**Common errors:**
- Too short: "Invalid length for mobile number"
- Too long: "The string supplied is too long to be a phone number"
- Invalid format: "Could not interpret numbers after +"
- No digits: "No digits found in number"

---

## Future Enhancements

1. **Whitelist by country** — Restrict to supported regions
2. **Type-specific validation** — Reject toll-free for donor phones
3. **Real-time validation** — Check against telecom databases
4. **SMS delivery validation** — Verify sendability of numbers
5. **Carrier detection** — Identify carrier for number

---

## References

- **GitHub**: https://github.com/daviddrysdale/python-phonenumbers
- **PyPI**: https://pypi.org/project/phonenumbers/
- **Google's libphonenumber**: https://github.com/google/libphonenumber
- **Supported Regions**: https://github.com/daviddrysdale/python-phonenumbers/blob/dev/python/phonenumbers/data/region_code.txt
