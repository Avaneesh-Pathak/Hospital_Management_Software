from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument."""
    return value * arg





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


