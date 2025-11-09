from django import template

register = template.Library()

@register.filter
def endswith(value, arg):
    """Check if value ends with arg"""
    if value:
        return str(value).lower().endswith(arg.lower())
    return False