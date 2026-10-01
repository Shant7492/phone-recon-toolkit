import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from modules.dorks import generate_dorks

INDIA_CIRCLES = {
    "9810": "Delhi", "9811": "Delhi", "9818": "Delhi", "9871": "Delhi", "9910": "Delhi",
    "9820": "Mumbai", "9821": "Mumbai", "9819": "Mumbai", "9833": "Mumbai", "9920": "Mumbai",
    "9830": "Kolkata", "9831": "Kolkata", "9832": "West Bengal",
    "9840": "Chennai", "9841": "Chennai", "9842": "Tamil Nadu", "9843": "Tamil Nadu",
    "9844": "Karnataka (Bangalore)", "9845": "Karnataka (Bangalore)", "9880": "Karnataka",
    "9848": "Andhra Pradesh & Telangana", "9849": "Andhra Pradesh & Telangana",
    "9824": "Gujarat", "9825": "Gujarat", "9898": "Gujarat",
    "9826": "Madhya Pradesh & Chhattisgarh", "9827": "Madhya Pradesh & Chhattisgarh",
    "9828": "Rajasthan", "9829": "Rajasthan", "9414": "Rajasthan",
    "9838": "Uttar Pradesh (East)", "9839": "Uttar Pradesh (East)",
    "9837": "Uttar Pradesh (West)", "9897": "Uttar Pradesh (West)",
    "9835": "Bihar & Jharkhand", "9934": "Bihar & Jharkhand", "9431": "Bihar & Jharkhand",
    "9895": "Kerala", "9846": "Kerala", "9847": "Kerala",
    "9814": "Punjab", "9815": "Punjab", "9872": "Punjab",
    "9812": "Haryana", "9896": "Haryana",
    "9816": "Himachal Pradesh", "9418": "Himachal Pradesh",
    "9419": "Jammu & Kashmir", "9858": "Jammu & Kashmir",
    "9861": "Odisha", "9437": "Odisha",
    "9864": "Assam", "9435": "Assam",
    "9862": "North East", "9863": "North East"
}

def resolve_circle(national_number: str, default_region: str) -> str:
    clean = national_number.replace(" ", "").replace("-", "").lstrip("0")
    if len(clean) >= 4:
        prefix = clean[:4]
        if prefix in INDIA_CIRCLES:
            return INDIA_CIRCLES[prefix]
    return default_region or "India"

def calculate_risk(e164: str, national: str) -> dict:
    digits = [c for c in national if c.isdigit()]
    score = 0
    reasons = []
    
    # Check repeated digits
    if len(digits) >= 5:
        consecutive = 1
        for i in range(1, len(digits)):
            if digits[i] == digits[i-1]:
                consecutive += 1
                if consecutive >= 4:
                    score += 25
                    reasons.append("Repeated sequential digits pattern")
                    break
            else:
                consecutive = 1

    level = "LOW"
    if score >= 50:
        level = "HIGH"
    elif score >= 20:
        level = "MEDIUM"

    return {"score": score, "level": level, "reasons": reasons}

class PhoneAnalyzer:
    def analyze(self, raw_input: str, default_region: str = "IN") -> dict:
        parsed = phonenumbers.parse(raw_input, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return {"valid": False, "error": "Invalid phone number format"}

        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        clean_national = national.replace(" ", "").replace("-", "").lstrip("0")
        digits_only = e164.lstrip("+")

        raw_region = geocoder.description_for_number(parsed, "en")
        refined_circle = resolve_circle(national, raw_region)
        carrier_name = carrier.name_for_number(parsed, "en") or "Unknown"

        risk_result = calculate_risk(e164, national)
        dorks_list = generate_dorks(national, e164)

        direct_actions = [
            {"name": "WhatsApp Chat/Info", "url": f"https://wa.me/{digits_only}"},
            {"name": "Telegram Profile", "url": f"https://t.me/+{digits_only}"},
            {"name": "Truecaller Lookup", "url": f"https://www.truecaller.com/search/in/{clean_national}"}
        ]

        return {
            "valid": True,
            "metadata": {
                "e164": e164,
                "national": national,
                "international": international,
                "country_code": parsed.country_code,
                "carrier": carrier_name,
                "circle": refined_circle,
                "timezones": list(timezone.time_zones_for_number(parsed))
            },
            "direct_actions": direct_actions,
            "risk": risk_result,
            "dorks": dorks_list
        }

def analyze_phone(raw_input: str, default_region: str = "IN") -> dict:
    analyzer = PhoneAnalyzer()
    return analyzer.analyze(raw_input, default_region)
