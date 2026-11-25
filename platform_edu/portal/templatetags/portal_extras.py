import os

from django import template

register = template.Library()


@register.filter
def dict_get(mapping, key):
    if not mapping:
        return ''
    return mapping.get(key, mapping.get(str(key), ''))


@register.filter
def basename(file_field):
    if not file_field:
        return ''
    return os.path.basename(file_field.name)
