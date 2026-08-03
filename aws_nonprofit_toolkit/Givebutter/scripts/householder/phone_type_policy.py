"""Stable product-facing phone number type labels."""

import phonenumbers


def phone_type_name(parsed: phonenumbers.PhoneNumber) -> str:
    type_map = {
        phonenumbers.PhoneNumberType.FIXED_LINE: "FIXED_LINE",
        phonenumbers.PhoneNumberType.MOBILE: "MOBILE",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
        phonenumbers.PhoneNumberType.TOLL_FREE: "TOLL_FREE",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
        phonenumbers.PhoneNumberType.SHARED_COST: "SHARED_COST",
        phonenumbers.PhoneNumberType.VOIP: "VOIP",
        phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
        phonenumbers.PhoneNumberType.PAGER: "PAGER",
        phonenumbers.PhoneNumberType.UAN: "UAN",
        phonenumbers.PhoneNumberType.VOICEMAIL: "VOICEMAIL",
        phonenumbers.PhoneNumberType.UNKNOWN: "UNKNOWN",
    }
    return type_map.get(phonenumbers.number_type(parsed), "UNKNOWN")
