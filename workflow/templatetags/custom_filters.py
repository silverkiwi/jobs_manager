from datetime import datetime

import pytz
from django import template
from django.utils import timezone

from accounts.models import Staff

register = template.Library()


# @register.filter
# def get_item(dictionary: Dict[Any, Any], key: Any) -> Optional[Any]:
#     return dictionary.get(key)


@register.filter(name="get_user_display_name")
def get_user_display_name(user_id: int) -> str:
    try:
        staff = Staff.objects.get(id=user_id)
        return staff.get_display_name()
    except Staff.DoesNotExist:
        return "Unknown"


@register.filter(name="is_aware")
def is_aware(value: datetime) -> bool:
    return timezone.is_aware(value)


@register.filter(name="utc_time")
def utc_time(value: datetime) -> datetime:
    if not timezone.is_aware(value):
        value = timezone.make_aware(value, pytz.UTC)
    return value.astimezone(pytz.UTC)


@register.filter(name="to_nz_time")
def to_nz_time(value: datetime) -> datetime:
    if not timezone.is_aware(value):
        value = timezone.make_aware(value, pytz.UTC)

    nz_tz = pytz.timezone("Pacific/Auckland")
    nz_time = value.astimezone(nz_tz)

    return nz_time


@register.filter(name="replace")
def replace(value: str, arg: str) -> str:
    """
    Replaces all occurrences of the first character in `arg` with the second character.
    Usage: {{ value|replace:"search|replace" }}
    """
    if not value or not arg:
        return value

    try:
        search, replace = arg.split("|")
        return value.replace(search, replace)
    except ValueError:
        return value


@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
