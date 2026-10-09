from django.urls import translate_url
from django.utils.translation import get_language

LANGUAGE_NAMES = {"en": "English", "ar": "العربية"}


def language_switch(request):
    """The other language and the same page's URL in it, for the header switch."""
    other = "en" if get_language() == "ar" else "ar"
    return {
        "other_language": {
            "code": other,
            "name": LANGUAGE_NAMES[other],
            "url": translate_url(request.get_full_path(), other),
        }
    }
