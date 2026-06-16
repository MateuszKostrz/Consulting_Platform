import os

from django import template

register = template.Library()


@register.filter
def basename(file_field):
    if not file_field:
        return ''
    return os.path.basename(file_field.name)
