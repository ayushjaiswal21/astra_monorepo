from django import template
from django.template.defaultfilters import stringfilter
import markdown

register = template.Library()

@register.filter
@stringfilter
def convert_markdown(value):
    """
    Converts markdown text to HTML.
    """
    return markdown.markdown(value, extensions=['fenced_code', 'codehilite'])
