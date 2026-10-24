"""Unit tests for text cleanup and keyword replacement."""

from django.test import SimpleTestCase, TestCase

from base_data_app.models import Data, DataType
from blockhaus101_app.helpers import correct_text, replace_text, replace_text_translations
from blockhaus101_app.tests.factories import make_language


class TestCorrectText(SimpleTestCase):
    def test_strips_extra_spaces_and_capitalizes(self) -> None:
        self.assertEqual(correct_text("  hello   world  ", "en"), "Hello world")

    def test_removes_spaces_before_punctuation(self) -> None:
        self.assertEqual(correct_text("hello , world .", "en"), "Hello, world.")

    def test_capitalizes_the_letter_after_an_opening_quote(self) -> None:
        self.assertEqual(correct_text('"hello there"', "en"), '"Hello there"')

    def test_english_gender_swaps_possessive(self) -> None:
        self.assertEqual(
            correct_text("see his painting", "en", subject_gender="f"), "See her painting"
        )
        self.assertEqual(correct_text("His painting", "en", subject_gender="f"), "Her painting")

    def test_english_leaves_french_elisions_alone(self) -> None:
        self.assertEqual(correct_text("text de le museum", "en"), "Text de le museum")

    def test_french_elision_de_le(self) -> None:
        self.assertEqual(correct_text("texte de le musee", "fr"), "Texte du musee")

    def test_french_vowel_contraction(self) -> None:
        self.assertEqual(correct_text("parle de artiste", "fr"), "Parle d’artiste")

    def test_french_article_agreement(self) -> None:
        self.assertEqual(correct_text("c'est un la chose", "fr"), "C'est une chose")

    def test_french_feminine_agreement(self) -> None:
        self.assertEqual(
            correct_text("Et il est né ici", "fr", subject_gender="f"),
            "Et elle est née ici",
        )
        self.assertEqual(
            correct_text("Cet artiste expose", "fr", subject_gender="f"),
            "Cette artiste expose",
        )


class TestReplaceText(TestCase):
    def test_leaves_text_unchanged_when_there_is_no_keyword(self) -> None:
        text, used = replace_text("rien a remplacer", "fr")

        self.assertEqual(text, "rien a remplacer")
        self.assertEqual(used, [])

    def test_keeps_unknown_keywords(self) -> None:
        text, used = replace_text("un [MISSING] mot", "fr")

        self.assertEqual(text, "un [MISSING] mot")
        self.assertEqual(used, [])

    def test_replaces_each_keyword_with_one_random_entry(self) -> None:
        french = make_language("fr", "French")
        color_type = DataType.objects.create(name="COLOR")
        place_type = DataType.objects.create(name="PLACE")
        Data.objects.create(data_type=color_type, text="rouge", language=french)
        Data.objects.create(data_type=place_type, text="Paris", language=french)

        text, used = replace_text("une [COLOR] a [PLACE]", "fr")

        self.assertEqual(text, "une rouge a Paris")
        self.assertEqual([item.text for item in used], ["rouge", "Paris"])


class TestReplaceTextTranslations(TestCase):
    def test_replaces_placeholders_with_translations_in_order(self) -> None:
        french = make_language("fr", "French")
        english = make_language("en", "English")
        color_type = DataType.objects.create(name="COLOR")
        place_type = DataType.objects.create(name="PLACE")
        color = Data.objects.create(data_type=color_type, text="rouge", language=french)
        place = Data.objects.create(data_type=place_type, text="Paris", language=french)
        Data.objects.create(data_type=color_type, text="red", language=english, translation=color)
        Data.objects.create(data_type=place_type, text="Paris", language=english, translation=place)

        result = replace_text_translations("a [COLOR] in [PLACE]", [color, place], "en")

        self.assertEqual(result, "a red in Paris")

    def test_falls_back_to_the_original_word_when_translation_is_missing(self) -> None:
        french = make_language("fr", "French")
        make_language("en", "English")
        color_type = DataType.objects.create(name="COLOR")
        color = Data.objects.create(data_type=color_type, text="rouge", language=french)

        result = replace_text_translations("a [COLOR] canvas", [color], "en")

        self.assertEqual(result, "a rouge canvas")

    def test_leaves_extra_placeholders_untouched(self) -> None:
        french = make_language("fr", "French")
        english = make_language("en", "English")
        color_type = DataType.objects.create(name="COLOR")
        color = Data.objects.create(data_type=color_type, text="rouge", language=french)
        Data.objects.create(data_type=color_type, text="red", language=english, translation=color)

        result = replace_text_translations("a [COLOR] and [COLOR]", [color], "en")

        self.assertEqual(result, "a red and [COLOR]")
