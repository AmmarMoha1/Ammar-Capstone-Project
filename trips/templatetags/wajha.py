from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def tr(value):
    """Translate a catalog value from the database (city, country, interest, description).

    Catalog rows are stored in English; their Arabic text lives in locale/ar/LC_MESSAGES/django.po.
    """
    return gettext(str(value)) if value else value
