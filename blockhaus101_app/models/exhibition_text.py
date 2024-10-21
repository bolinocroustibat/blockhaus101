import re
from random import choice, randint

from django.db import models
from django.template.defaultfilters import slugify

from base_data_app.models import Data, Language
from blockhaus101.settings import logger
from blockhaus101_app.helpers import correct_sentence
from blockhaus101_app.models.exhibition_title import ExhibitionTitle


class ExhibitionText(models.Model):
    language = models.ForeignKey(Language, related_name="expotexts", on_delete=models.PROTECT)
    text = models.TextField("exhibition text", max_length=3000)
    exhibition = models.ForeignKey(
        "Exhibition",
        related_name="expotexts",
        on_delete=models.CASCADE,
        verbose_name="exhibition",
    )
    slug = models.SlugField(default=None, null=True, blank=True, max_length=150, verbose_name="URL")
    ip = models.GenericIPAddressField("creator IP address", blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.text[:60]

    class Meta:
        db_table = "blockhaus101_expotexts"
        verbose_name = "texte d'exposition"
        verbose_name_plural = "textes d'exposition"

    def create(self, *args, **kwargs):
        super(ExhibitionText, self).__init__(*args, **kwargs)
        self.ip = kwargs.get("ip", None)
        self.text = ""
        self.used_words: dict = {}
        if randint(1, 3) == 1:
            self.text = self.create_expo_sentence(position=1)
        self.text = self.text + " " + self.create_expo_sentence(position=2)
        if randint(1, 3) == 1:
            self.text = self.text + " " + self.create_expo_sentence(position=3)
        self.text = self.text + " " + self.create_expo_sentence(position=4)
        self.text = self.text + " " + self.create_expo_sentence(position=5)
        self.text = self.text + " " + self.create_expo_sentence(position=6)
        if self.exhibition.artist.gender == "f":
            self.text = self.text.replace("Il ", "Elle ")
        logger.debug(f"Used words for exhibition text: {self.used_words}")

    def save(self, *args, **kwargs) -> None:
        exhibition_title = ExhibitionTitle.objects.get(
            exhibition=self.exhibition, language=self.language
        )
        slug_string = f"{self.exhibition.artist.name}-{exhibition_title.title}"
        # if this slug exists for others, add a number at the end of the slug attribute of the instance:
        slug: str | None = self.unique_slugify(value=slug_string, max_elements=10)
        if slug:
            self.slug = slug
            super(ExhibitionText, self).save(*args, **kwargs)

    def create_expo_sentence(self, position: int) -> str:
        structures = Data.objects.filter(data_type__name="phrases", position=position)
        sentence = choice(structures).text
        sentence = sentence.replace("[SELF]", self.exhibition.artist.name)
        sentence = sentence.replace("[SELFDISCIPLINE]", self.exhibition.artist.discipline_text())
        sentence = sentence.replace("[SELFEXPO]", self.exhibition.title)
        sentence = sentence.replace("[EXPO]", self.exhibition.generate_title(self.language))
        keywords: list = re.findall(r"\[[^][]*]", sentence)
        for k in keywords:
            word_type = k.replace("[", "").replace("]", "")
            chosen_data = Data.choose_random_excluding(
                data_type=word_type, language=self.language, excluding=self.used_words
            )
            if chosen_data:
                chosen_word = chosen_data[0]
                self.used_words = chosen_data[1]
                # only replace one occurence, we want the same keyword to be able to be replaced by another word
                sentence = sentence.replace(f"[{word_type}]", chosen_word, 1)
        sentence = correct_sentence(lang=self.language.lang, sentence=sentence)
        return sentence

    def unique_slugify(self, value: str, max_elements: int | None = None) -> str | None:
        """
        Modified from SmileyChris' post @ https://djangosnippets.org/snippets/690/
        Calculates a unique slug of ``value`` for an instance.
        WARNING: This create A LOT of queries to the database if some text have been created before, and thus should maybe be limited.
        """
        slug_len = self._meta.get_field("slug").max_length

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
            while not slug or queryset.filter(**{"slug": slug}):
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
