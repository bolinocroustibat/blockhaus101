from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def absolute_uri(context: template.Context, path: str = "") -> str:
    """Absolute URL of the current page, or of path when one is given."""
    request = context["request"]
    if path:
        return request.build_absolute_uri(path)
    return request.build_absolute_uri()


@register.simple_tag(takes_context=True)
def language_url(context: template.Context, lang: str) -> str:
    """Absolute URL of the current page in another language."""
    request = context["request"]
    match = request.resolver_match
    if match is None or not match.url_name:
        return request.build_absolute_uri()
    kwargs = dict(match.kwargs)
    kwargs["lang"] = lang
    url = reverse(match.url_name, args=match.args, kwargs=kwargs)
    query = request.META.get("QUERY_STRING", "")
    if query:
        url = f"{url}?{query}"
    return request.build_absolute_uri(url)
