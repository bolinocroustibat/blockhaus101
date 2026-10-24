import re
from random import choice, randint

from django.db import models
from django.template.defaultfilters import slugify

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import correct_text, replace_text
from blockhaus101_app.models.exhibition_title import ExhibitionTitle


class ExhibitionText(models.Model):
    language = models.ForeignKey(Language, related_name="expotexts", on_delete=models.PROTECT)
    exhibition = models.ForeignKey(
        "Exhibition",
        related_name="expotexts",
        on_delete=models.CASCADE,
        verbose_name="exhibition",
    )
    text = models.TextField("exhibition text", max_length=3000)
    slug = models.SlugField(default=None, null=True, blank=True, max_length=150, verbose_name="URL")
    ip = models.GenericIPAddressField("creator IP address", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)
    ai_model = models.CharField(
        "AI model",
        max_length=32,
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return self.text[:60]

    class Meta:
        db_table = "blockhaus101_expotexts"
        verbose_name = "texte d'exposition"
        verbose_name_plural = "textes d'exposition"

    def generate(self, *args, **kwargs):
        self.ip = kwargs.get("ip", None)
        self.text = ""
        self.used_words: dict = {}
        if randint(1, 3) == 1:
            self.text = self._create_expo_sentence(position=1)
        self.text = self.text + " " + self._create_expo_sentence(position=2)
        if randint(1, 3) == 1:
            self.text = self.text + " " + self._create_expo_sentence(position=3)
        self.text = self.text + " " + self._create_expo_sentence(position=4)
        self.text = self.text + " " + self._create_expo_sentence(position=5)
        self.text = self.text + " " + self._create_expo_sentence(position=6)
        self.text = correct_text(
            text=self.text,
            lang=self.language.code,
            subject_gender=self.exhibition.artist.gender,
        )
        logger.debug(f"Used words for exhibition text: {self.used_words}")

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            exhibition_title = ExhibitionTitle.objects.get(
                exhibition=self.exhibition, language=self.language
            )
            slug: str | None = self._unique_slugify(
                value=f"{self.exhibition.artist.name}-{exhibition_title.text}",
                max_elements=10,
            )
            if not slug:
                return
            self.slug = slug
        super().save(*args, **kwargs)

    def _create_expo_sentence(self, position: int) -> str:
        structures = Data.objects.filter(
            language=self.language, data_type__name="phrases", position=position
        )
        sentence = choice(structures).text
        sentence = sentence.replace("[SELF]", self.exhibition.artist.name)
        sentence = sentence.replace(
            "[SELFDISCIPLINE]", self.exhibition.artist.get_discipline(lang=self.language.code)
        )
        exhibition_title = ExhibitionTitle.objects.get(
            exhibition=self.exhibition, language=self.language
        )
        sentence = sentence.replace("[SELFEXPO]", exhibition_title.text)
        sentence = sentence.replace("[EXPO]", self.exhibition.random_title_text(self.language.code))
        sentence, _used_words = replace_text(text=sentence, lang=self.language.code)
        sentence = correct_text(text=sentence, lang=self.language.code)
        return sentence

    def _unique_slugify(self, value: str, max_elements: int | None = None) -> str | None:
        """
        Modified from SmileyChris' post @ https://djangosnippets.org/snippets/690/
        Calculates a unique slug of ``value`` for an instance.
        WARNING: This create A LOT of queries to the database if some text have been created before, and thus should maybe be limited.
        """
        slug_len = getattr(self._meta.get_field("slug"), "max_length", None)

        # Sort out the initial slug. Chop its length down if we need to.
        slug = slugify(value)
        if slug_len:
            slug = slug[:slug_len]
        # Cleans up the slug by removing "-" that occur at the beginning or end.
        slug = re.sub(r"^-+|-+$", "", slug)
        original_slug = slug

        # Create a queryset, excluding the current instance.
        queryset = self.__class__._default_manager.filter(slug__startswith=original_slug)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        if (not max_elements) or (len(queryset) < max_elements):
            # Find a unique slug. If one matches, add '-2' to the end and try again
            # (then '-3', etc).
            next = 2
            while not slug or queryset.filter(slug=slug):
                slug = original_slug
                end = f"-{next}"
                if slug_len and len(slug) + len(end) > slug_len:
                    slug = slug[: slug_len - len(end)]
                    # Cleans up the slug by removing "-" that occur at the beginning or end.
                    slug = re.sub(r"^-+|-+$", "", slug)
                slug = f"{slug}{end}"
                next += 1
            return slug

        return None
