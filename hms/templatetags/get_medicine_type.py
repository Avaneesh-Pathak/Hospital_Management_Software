from django import template
from ..models import Medicine

register = template.Library()

@register.filter
def get_medicine_type(medicine_id):
    try:
        return Medicine.objects.get(id=medicine_id).medicine_type
    except Medicine.DoesNotExist:
        return ''