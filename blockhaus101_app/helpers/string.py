import re

from django.template.defaultfilters import slugify

from blockhaus101_app.helpers.logger import logger


def correct_sentence(sentence: str) -> str:
    correction_dict = {  # we could also use "replace(old, new)": https://www.tutorialspoint.com/python/string_replace.htm
        "( ": "(",
        " )": ")",
        " à le ": " au ",
        " à les ": " aux ",
        " de a": " d’a",
        " de e": " d’e",
        " de ê": " d’ê",
        " de ê": " d’ê",
        " de é": " d’é",
        " de è": " d’è",
        " de h": " d’h",
        " de i": " d’i",
        " de u": " d’u",
        " de A": " d’A",
        " de E": " d’E",
        " de I": " d’I",
        " de de ": " de ",
        " de des ": " des ",
        " de le ": " du ",
        " de les ": " des ",
        " en la ": " en ",
        " en le ": " en ",
        " en les ": " en ",
        " la A": " l’A",
        " la E": " l’E",
        " la É": " l’É",
        " la I": " l’I",
        " la O": " l’O",
        " la U": " l’U",
        " le A": " l’A",
        " le E": " l’E",
        " le É": " l’É",
        " le I": " l’I",
        " le O": " l’O",
        " le U": " l’U",
        " le la ": " la ",
        " le le ": " le ",
        " le les ": " les ",
        " un l'": " un ",
        " un l’": " un ",
        " un la ": " une ",
        " un le ": " un ",
        " un les ": " des ",
        " son la ": " sa ",
        " son le ": " son ",
        " son l'": " son ",
        " son l’": " son ",
        " son les ": " ses ",
        " que a": " qu’a",
        " que e": " qu’e",
        " que i": " qu’i",
        " que u": " qu’u",
        " que A": " qu’A",
        " que E": " qu’E",
        " que I": " qu’I",
        " que U": " qu’U",
        " ,": ",",
    }
    sentence = _strtr(sentence, correction_dict)
    if sentence[0] == '"':  # if the first char is a double quote
        sentence = sentence[1].upper() + sentence[1:]  # capitalize second letter
    else:
        sentence = sentence[0].upper() + sentence[1:]  # capitalize first letter
    return sentence


def _strtr(string: str, correction_dict: dict) -> str:
    buffer = []
    i, n = 0, len(string)
    while i < n:
        match = False
        for s, r in correction_dict.items():
            if string[i : len(s) + i] == s:
                buffer.append(r)
                i = i + len(s)
                match = True
                break
        if not match:
            buffer.append(string[i])
            i = i + 1
    return "".join(buffer)


def unique_slugify(
    instance, value: str, slug_field_name="slug", queryset=None, slug_separator="-"
) -> None:
    """
    Taken from SmileyChris' post @ https://djangosnippets.org/snippets/690/
    Calculates a unique slug of ``value`` for an instance.

    ``slug_field_name`` should be a string matching the name of the field to
    store the slug in (and the field to check against for uniqueness).

    ``queryset`` usually doesn't need to be explicitly provided - it'll default
    to using the ``.all()`` queryset from the model's default manager.
    """
    slug_field = instance._meta.get_field(slug_field_name)

    slug = getattr(instance, slug_field.attname)
    slug_len = slug_field.max_length

    # Sort out the initial slug. Chop its length down if we need to.
    slug = slugify(value)
    if slug_len:
        slug = slug[:slug_len]
    slug = _slug_strip(slug, slug_separator)
    original_slug = slug

    # Create a queryset, excluding the current instance.
    if not queryset:
        queryset = instance.__class__._default_manager.all()
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    # Find a unique slug. If one matches, at '-2' to the end and try again
    # (then '-3', etc).
    next = 2
    while not slug or queryset.filter(**{slug_field_name: slug}):
        slug = original_slug
        end = "-%s" % next
        if slug_len and len(slug) + len(end) > slug_len:
            slug = slug[: slug_len - len(end)]
            slug = _slug_strip(slug, slug_separator)
        slug = "%s%s" % (slug, end)
        next += 1

    setattr(instance, slug_field.attname, slug)


def _slug_strip(value: str, separator=None) -> str:
    """
    Cleans up a slug by removing slug separator characters that occur at the beginning or end of a slug.
    If an alternate separator is used, it will also replace any instances of the default '-' separator with the new separator.
    """
    if separator == "-" or not separator:
        re_sep = "-"
    else:
        re_sep = "(?:-|%s)" % re.escape(separator)
        value = re.sub("%s+" % re_sep, separator, value)
    return re.sub(r"^%s+|%s+$" % (re_sep, re_sep), "", value)
