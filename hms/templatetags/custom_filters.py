from django import template
from ..models import Medicine
register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def get_value(vitals, field_name):
    if vitals:
        for vital in vitals:
            return getattr(vital, field_name, '')
    return ''


@register.filter
def get_vital(existing_vitals_dict, key):
    """
    Retrieves the vital value based on the field name and time slot.
    `key` is passed as "field_name,time"
    """
    try:
        field_name, time = key.split(",")  # Extract the field and time
        vital = existing_vitals_dict.get(time)  # Get the NICUVitals object for this time slot
        if vital:
            return getattr(vital, field_name, "")  # Get the field value
    except Exception as e:
        print(f"Error in get_vital filter: {e}")  # Debugging in console
    return ""

@register.filter
def get_dict_value(dictionary, key):
    """Safely get a value from a dictionary."""
    return dictionary.get(key, "")

@register.filter
def replace_underscore(value):
    """Replaces underscores with spaces and capitalizes words."""
    return value.replace("_", " ").title()

@register.filter
def subtract(value, arg):
    try:
        value = float(value)  # Convert value to float
        arg = float(arg)      # Convert arg to float
        return value - arg
    except (ValueError, TypeError):
        return 0  # Return 0 if conversion fails
    

@register.filter
def get_patient_info(bed_patient_info, bed_number):
    """Returns patient details for the given bed number."""
    return bed_patient_info.get(bed_number, {})


register = template.Library()
@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})