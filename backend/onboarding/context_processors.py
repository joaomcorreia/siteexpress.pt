import re

from django.conf import settings


def _safe_external_url(setting_name):
    value = getattr(settings, setting_name, "").strip()
    if value.startswith(("https://", "http://")):
        return value
    return ""


def public_site_contact(request):
    whatsapp_number = getattr(settings, "SITEEXPRESS_WHATSAPP_NUMBER", "").strip()
    whatsapp_digits = re.sub(r"\D", "", whatsapp_number)

    return {
        "siteexpress_contact": {
            "email": "info@siteexpress.pt",
            "whatsapp_number": whatsapp_number,
            "whatsapp_url": (
                f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else ""
            ),
            "facebook_url": _safe_external_url("SITEEXPRESS_FACEBOOK_URL"),
            "instagram_url": _safe_external_url("SITEEXPRESS_INSTAGRAM_URL"),
            "linkedin_url": _safe_external_url("SITEEXPRESS_LINKEDIN_URL"),
            "google_business_url": _safe_external_url(
                "SITEEXPRESS_GOOGLE_BUSINESS_URL"
            ),
        }
    }
