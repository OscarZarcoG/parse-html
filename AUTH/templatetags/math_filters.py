from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divide value by arg.
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calculate percentage of value from total.
    Usage: {{ value|percentage:total }}
    """
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, ZeroDivisionError, TypeError):
        return 0