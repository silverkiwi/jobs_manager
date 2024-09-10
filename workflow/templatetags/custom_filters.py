from django import template
from workflow.models import Staff  # Make sure to import the Staff model
from django.utils import timezone
import pytz

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='get_user_display_name')
def get_user_display_name(user_id):
    try:
        staff = Staff.objects.get(id=user_id)
        return staff.get_display_name()
    except Staff.DoesNotExist:
        return 'Unknown'

@register.filter(name='is_aware')
def is_aware(value):
    return timezone.is_aware(value)

@register.filter(name='utc_time')
def utc_time(value):
    if not timezone.is_aware(value):
        value = timezone.make_aware(value, pytz.UTC)
    return value.astimezone(pytz.UTC)


@register.filter(name='to_nz_time')
def to_nz_time(value):
    if not timezone.is_aware(value):
        value = timezone.make_aware(value, pytz.UTC)

    nz_tz = pytz.timezone('Pacific/Auckland')
    nz_time = value.astimezone(nz_tz)

    return nz_time
