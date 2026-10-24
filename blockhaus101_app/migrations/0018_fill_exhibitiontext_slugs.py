from django.db import migrations
from django.db.models import Q


def fill_empty_slugs(apps, schema_editor) -> None:
    from blockhaus101_app.models import ExhibitionText, ExhibitionTitle

    empty = ExhibitionText.objects.filter(Q(slug__isnull=True) | Q(slug=""))
    for text in empty.select_related("exhibition__artist", "language"):
        try:
            title = ExhibitionTitle.objects.get(exhibition=text.exhibition, language=text.language)
        except ExhibitionTitle.DoesNotExist:
            continue
        slug = text._unique_slugify(
            value=f"{text.exhibition.artist.name}-{title.text}",
            max_elements=10,
        )
        if slug:
            ExhibitionText.objects.filter(pk=text.pk).update(slug=slug)


class Migration(migrations.Migration):
    dependencies = [
        ("blockhaus101_app", "0017_exhibition_location"),
    ]

    operations = [
        migrations.RunPython(fill_empty_slugs, migrations.RunPython.noop),
    ]
