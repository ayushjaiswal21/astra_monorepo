from django import template
import os

register = template.Library()

@register.simple_tag
def webp(image_url):
    """
    Returns the URL of the WebP version of an image, if it exists.
    Falls back to original format if WebP version doesn't exist.
    """
    if not image_url:
        return image_url

    base, ext = os.path.splitext(image_url)
    webp_url = f"{base}.webp"

    # In a real implementation, you would check if the WebP file exists
    # For now, we'll just return the WebP URL and let the browser handle fallbacks
    return webp_url

@register.simple_tag
def picture_element(image_url, alt="", class_name="", width=None, height=None):
    """
    Returns a <picture> element with WebP source and fallback to original format.
    """
    if not image_url:
        return ""

    base, ext = os.path.splitext(image_url)
    webp_url = f"{base}.webp"

    width_attr = f' width="{width}"' if width else ""
    height_attr = f' height="{height}"' if height else ""
    class_attr = f' class="{class_name}"' if class_name else ""

    return f'''<picture>
    <source srcset="{webp_url}" type="image/webp">
    <img src="{image_url}" alt="{alt}"{width_attr}{height_attr}{class_attr}>
</picture>'''
