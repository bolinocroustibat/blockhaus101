"""Unit tests for public pages that do not generate content."""

import tempfile
from datetime import datetime, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from blockhaus101.settings import MAIL_INVALID_MESSAGE
from blockhaus101_app.models import (
    Artist,
    ArtistBiography,
    Exhibition,
    ExhibitionText,
    ExhibitionTitle,
)
from blockhaus101_app.tests.factories import make_artist, make_exhibition, make_language


class TestRedirects(TestCase):
    def test_old_paths_redirect_to_french_pages(self) -> None:
        cases = {
            "/": "/fr",
            "/past-exhibitions/": "/fr/past-exhibitions",
            "/infos-pratiques/": "/fr/contact",
        }
        for path, location in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], location)

    def test_unknown_language_is_not_found(self) -> None:
        response = self.client.get("/de/")

        self.assertEqual(response.status_code, 404)


class TestPastExhibitions(TestCase):
    def setUp(self) -> None:
        self.french = make_language("fr", "French")
        self.now = datetime.now()

    def _past(self, name: str, days_ago: int) -> tuple[Artist, Exhibition]:
        artist = make_artist(name=name, language=self.french)
        end = self.now - timedelta(days=days_ago)
        exhibition = make_exhibition(
            artist,
            startdate=end - timedelta(days=7),
            enddate=end,
        )
        return artist, exhibition

    def test_says_when_there_is_nothing_past(self) -> None:
        current_artist = make_artist(name="Still Showing", language=self.french)
        make_exhibition(
            current_artist,
            startdate=self.now - timedelta(days=1),
            enddate=self.now + timedelta(days=6),
        )

        response = self.client.get("/fr/past-exhibitions/")

        self.assertContains(response, "Il n'y a pas encore d'expositions passées.")
        self.assertNotContains(response, "Still Showing")

    def test_english_empty_state_uses_the_plural(self) -> None:
        make_language("en", "English")

        response = self.client.get("/en/past-exhibitions/")

        self.assertContains(response, "There are no past exhibitions yet.")

    def test_lists_past_exhibitions_newest_first(self) -> None:
        recent_artist, recent = self._past("Recent Artist", days_ago=1)
        _middle_artist, middle = self._past("Middle Artist", days_ago=3)
        _old_artist, old = self._past("Old Artist", days_ago=5)
        ExhibitionTitle.objects.create(language=self.french, exhibition=recent, text="Recent title")
        ExhibitionTitle.objects.create(language=self.french, exhibition=middle, text="Middle title")
        ArtistBiography.objects.create(
            language=self.french, artist=recent_artist, text="A short biography"
        )
        ExhibitionText.objects.create(
            language=self.french, exhibition=recent, text="A short exhibition text"
        )

        response = self.client.get("/fr/past-exhibitions/")

        self.assertContains(response, "Recent Artist")
        self.assertContains(response, "Recent title")
        self.assertContains(response, "A short biography")
        self.assertContains(response, "A short exhibition text")
        self.assertContains(response, "Du ")
        self.assertContains(response, " au ")
        self.assertContains(response, 'class="expo-text"')
        self.assertNotContains(response, 'class="text"')
        self.assertContains(response, "Middle Artist")
        self.assertNotContains(response, "Old Artist")
        body = response.content.decode()
        self.assertLess(body.index("Recent Artist"), body.index("Middle Artist"))

        page_two = self.client.get("/fr/past-exhibitions/?page=2")

        self.assertContains(page_two, "Old Artist")
        self.assertContains(page_two, f"Exhibition {old.pk} (no title)")
        self.assertNotContains(page_two, "Recent Artist")

    def test_htmx_returns_only_the_next_batch(self) -> None:
        self._past("Recent Artist", days_ago=1)

        response = self.client.get("/fr/past-exhibitions/", HTTP_HX_REQUEST="true")

        self.assertContains(response, "Recent Artist")
        self.assertContains(response, 'class="expo-text"')
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_next_page_is_one_link_replaced_in_place(self) -> None:
        self._past("Recent Artist", days_ago=1)
        self._past("Middle Artist", days_ago=3)
        self._past("Old Artist", days_ago=5)

        page = self.client.get("/fr/past-exhibitions/")
        partial = self.client.get("/fr/past-exhibitions/", HTTP_HX_REQUEST="true")
        last_page = self.client.get("/fr/past-exhibitions/?page=2")

        for response in (page, partial):
            html = response.content.decode()
            self.assertIn('href="?page=2"', html)
            self.assertIn('hx-get="?page=2"', html)
            self.assertIn('hx-swap="outerHTML"', html)
            self.assertIn("Chargement...", html)
            self.assertRegex(html, r'<a\b[^>]*class="loading-trigger"')
            self.assertNotIn('hx-swap="afterend"', html)
            self.assertNotIn("loading-indicator", html)
            self.assertEqual(html.count("loading-trigger"), 1)

        last_html = last_page.content.decode()
        self.assertNotIn("loading-trigger", last_html)
        self.assertNotIn('hx-swap="afterend"', last_html)


class TestContact(TestCase):
    def test_shows_the_form(self) -> None:
        response = self.client.get("/fr/contact/")

        self.assertContains(response, "Votre nom")
        self.assertContains(response, "<form")

    def test_rejects_an_incomplete_message(self) -> None:
        response = self.client.post(
            "/fr/contact/",
            {"name": "", "email": "not-an-email", "phone": "06 12 34 56 78", "text": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")
        self.assertContains(response, "not-an-email")
        self.assertContains(response, "06 12 34 56 78")
        self.assertContains(response, "Ce champ est obligatoire.")
        self.assertEqual(response.content.decode().count("Saisissez une adresse e-mail valide."), 1)
        self.assertContains(response, "errorlist")
        self.assertNotContains(response, "message-success")
        shown = response.content.decode().replace("&#x27;", "'")
        self.assertIn(MAIL_INVALID_MESSAGE["fr"], shown)

    def test_english_form_uses_english_labels(self) -> None:
        response = self.client.post(
            "/en/contact/",
            {"name": "Ada", "email": "not-an-email", "phone": "+33 6 12 34 56 78", "text": ""},
        )

        self.assertContains(response, "<form")
        self.assertContains(response, "Your name")
        self.assertContains(response, "Your phone")
        self.assertContains(response, "Why do you want to see this artist")
        self.assertNotContains(response, "Votre nom")
        self.assertContains(response, 'name="phone"')
        self.assertContains(response, "+33 6 12 34 56 78")
        self.assertContains(response, "This field is required.")
        self.assertEqual(response.content.decode().count("Enter a valid email address."), 1)
        self.assertNotContains(response, 'type="number"')


class TestDocumentLanguage(TestCase):
    def test_navigation_items_have_no_loose_separators(self) -> None:
        for path in ("/fr/contact/", "/en/contact/"):
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertNotContains(response, "&nbsp;&nbsp;|&nbsp;&nbsp;")
                self.assertEqual(response.content.decode().count("<nav>"), 1)

    def test_english_pages_are_marked_english(self) -> None:
        response = self.client.get("/en/contact/")

        self.assertContains(response, '<html lang="en">')
        self.assertContains(
            response,
            'rel="canonical" href="http://testserver/en/contact/"',
        )
        self.assertContains(response, 'property="og:url" content="http://testserver/en/contact/"')
        self.assertContains(response, 'property="og:locale" content="en_US"')
        self.assertContains(
            response,
            'hreflang="fr" href="http://testserver/fr/contact/"',
        )
        self.assertContains(
            response,
            'hreflang="en" href="http://testserver/en/contact/"',
        )
        self.assertContains(
            response,
            'hreflang="x-default" href="http://testserver/fr/contact/"',
        )
        self.assertContains(
            response,
            "Visits to the søren bollinger gallery, by appointment only.",
        )
        self.assertNotContains(response, 'property="og:image" content=""')

    def test_french_archive_describes_the_page(self) -> None:
        make_language("fr", "French")

        response = self.client.get("/fr/past-exhibitions/")

        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, "Expositions précédentes de la galerie søren bollinger.")
        self.assertNotContains(response, 'name="description" content=""')

    def test_language_alternates_keep_the_page_query(self) -> None:
        french = make_language("fr", "French")
        now = datetime.now()
        for days_ago in (1, 3, 5):
            artist = make_artist(name=f"Artist {days_ago}", language=french)
            end = now - timedelta(days=days_ago)
            make_exhibition(
                artist,
                startdate=end - timedelta(days=7),
                enddate=end,
            )

        response = self.client.get("/fr/past-exhibitions/?page=2")

        self.assertContains(
            response,
            'rel="canonical" href="http://testserver/fr/past-exhibitions/?page=2"',
        )
        self.assertContains(
            response,
            'hreflang="en" href="http://testserver/en/past-exhibitions/?page=2"',
        )

    def test_current_show_shares_its_image(self) -> None:
        french = make_language("fr", "French")
        now = datetime.now()
        artist = make_artist(name="Ada Lovelace", language=french)
        exhibition = make_exhibition(
            artist,
            startdate=now - timedelta(days=1),
            enddate=now + timedelta(days=6),
        )
        exhibition.image1 = "exhibitions_imgs/show.jpg"
        exhibition.save()
        ExhibitionTitle.objects.create(
            language=french, exhibition=exhibition, text="oiseaux de verre"
        )
        ArtistBiography.objects.create(language=french, artist=artist, text="Née à Paris.")
        ExhibitionText.objects.create(
            language=french, exhibition=exhibition, text="Une salle blanche."
        )

        response = self.client.get("/fr/")

        image = "http://testserver/media/exhibitions_imgs/show.jpg"
        self.assertContains(response, f'property="og:image" content="{image}"')
        self.assertContains(
            response, 'property="og:image:alt" content="Ada Lovelace — Oiseaux de verre"'
        )
        self.assertContains(response, 'property="og:description" content="Une salle blanche."')
        self.assertContains(response, 'href="/media/exhibitions_imgs/show.jpg"')
        self.assertContains(response, 'alt="Ada Lovelace — Oiseaux de verre"')
        self.assertContains(response, 'class="expo-image-fallback"')
        self.assertNotContains(response, 'loading="lazy"')


def _jpeg(width: int, height: int) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="JPEG")
    return SimpleUploadedFile("show.jpg", buffer.getvalue(), content_type="image/jpeg")


class TestExhibitionPage(TestCase):
    def setUp(self) -> None:
        self.french = make_language("fr", "French")
        self.english = make_language("en", "English")
        self.now = datetime.now()
        self.artist = make_artist(name="Ada Lovelace", language=self.french)
        self.exhibition = make_exhibition(
            self.artist,
            startdate=self.now - timedelta(days=1),
            enddate=self.now + timedelta(days=6),
        )
        ExhibitionTitle.objects.create(
            language=self.french, exhibition=self.exhibition, text="oiseaux de verre"
        )
        ExhibitionTitle.objects.create(
            language=self.english, exhibition=self.exhibition, text="glass birds"
        )
        ArtistBiography.objects.create(
            language=self.french, artist=self.artist, text="Née à Paris."
        )
        ArtistBiography.objects.create(
            language=self.english, artist=self.artist, text="Born in Paris."
        )
        self.french_text = ExhibitionText.objects.create(
            language=self.french,
            exhibition=self.exhibition,
            text="Une salle blanche.",
        )
        self.english_text = ExhibitionText.objects.create(
            language=self.english,
            exhibition=self.exhibition,
            text="A white room.",
        )

    def test_french_slug_shows_the_exhibition(self) -> None:
        response = self.client.get("/fr/ada-lovelace-oiseaux-de-verre/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, "Oiseaux de verre")
        self.assertContains(response, "Une salle blanche.")
        self.assertContains(
            response,
            'hreflang="en" href="http://testserver/en/ada-lovelace-glass-birds/"',
        )
        self.assertContains(
            response,
            'hreflang="fr" href="http://testserver/fr/ada-lovelace-oiseaux-de-verre/"',
        )

    def test_unknown_slug_is_not_found(self) -> None:
        response = self.client.get("/fr/unknown-show/")

        self.assertEqual(response.status_code, 404)

    def test_other_language_slug_redirects_to_the_matching_text(self) -> None:
        response = self.client.get("/en/ada-lovelace-oiseaux-de-verre/")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/en/ada-lovelace-glass-birds/")

    def test_other_language_slug_shows_the_page_without_a_translation(self) -> None:
        self.english_text.delete()

        response = self.client.get("/en/ada-lovelace-oiseaux-de-verre/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, "Glass birds")
        self.assertContains(response, "Born in Paris.")
        self.assertNotContains(response, "A white room.")

    def test_homepage_card_links_to_the_exhibition(self) -> None:
        response = self.client.get("/fr/")
        html = response.content.decode()

        self.assertIn('href="/fr/ada-lovelace-oiseaux-de-verre/"', html)
        self.assertIn("Ada Lovelace", html)
        self.assertIn("Oiseaux de verre", html)
        self.assertIn("Une salle blanche.", html)
        self.assertIn('class="exhibition-date exhibition-page-link"', html)
        self.assertIn('class="expo-text-wrapper exhibition-page-link"', html)

    def test_archive_card_links_to_the_exhibition(self) -> None:
        past_end = self.now - timedelta(days=1)
        self.exhibition.startdate = past_end - timedelta(days=7)
        self.exhibition.enddate = past_end
        self.exhibition.save()

        response = self.client.get("/fr/past-exhibitions/")
        html = response.content.decode()

        self.assertIn('href="/fr/ada-lovelace-oiseaux-de-verre/"', html)
        self.assertIn("Ada Lovelace", html)
        self.assertIn("Oiseaux de verre", html)
        self.assertIn("Une salle blanche.", html)
        self.assertIn('class="exhibition-date exhibition-page-link"', html)
        self.assertIn('class="expo-text-wrapper exhibition-page-link"', html)

    def test_english_cards_link_when_only_a_french_text_exists(self) -> None:
        self.english_text.delete()

        home = self.client.get("/en/").content.decode()
        self.assertIn('href="/en/ada-lovelace-oiseaux-de-verre/"', home)
        self.assertIn("Ada Lovelace", home)
        self.assertIn("Glass birds", home)
        self.assertIn('class="exhibition-date exhibition-page-link"', home)

        past_end = self.now - timedelta(days=1)
        self.exhibition.startdate = past_end - timedelta(days=7)
        self.exhibition.enddate = past_end
        self.exhibition.save()

        archive = self.client.get("/en/past-exhibitions/").content.decode()
        self.assertIn('href="/en/ada-lovelace-oiseaux-de-verre/"', archive)
        self.assertIn("Ada Lovelace", archive)
        self.assertIn("Glass birds", archive)
        self.assertIn('class="exhibition-date exhibition-page-link"', archive)


class TestExhibitionImages(TestCase):
    def test_current_show_image_reserves_its_ratio(self) -> None:
        french = make_language("fr", "French")
        now = datetime.now()
        artist = make_artist(name="Ada Lovelace", language=french)
        exhibition = make_exhibition(
            artist,
            startdate=now - timedelta(days=1),
            enddate=now + timedelta(days=6),
        )
        ExhibitionTitle.objects.create(
            language=french, exhibition=exhibition, text="oiseaux de verre"
        )
        ArtistBiography.objects.create(language=french, artist=artist, text="Née à Paris.")
        ExhibitionText.objects.create(
            language=french, exhibition=exhibition, text="Une salle blanche."
        )
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            exhibition.image1.save("show.jpg", _jpeg(8, 16), save=True)
            response = self.client.get("/fr/")

        page = response.content.decode()
        self.assertIn(f'href="{exhibition.image1.url}"', page)
        self.assertIn('alt="Ada Lovelace — Oiseaux de verre"', page)
        self.assertIn('width="8"', page)
        self.assertIn('height="16"', page)
        self.assertNotIn('loading="lazy"', page)
        self.assertNotIn("expo-image-fallback", page)

    def test_archive_image_loads_later(self) -> None:
        french = make_language("fr", "French")
        now = datetime.now()
        artist = make_artist(name="Recent Artist", language=french)
        end = now - timedelta(days=1)
        exhibition = make_exhibition(
            artist,
            startdate=end - timedelta(days=7),
            enddate=end,
        )
        ExhibitionTitle.objects.create(language=french, exhibition=exhibition, text="titre long")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            exhibition.image1.save("show.jpg", _jpeg(8, 16), save=True)
            page = self.client.get("/fr/past-exhibitions/")
            partial = self.client.get("/fr/past-exhibitions/", HTTP_HX_REQUEST="true")

        html = page.content.decode()
        fragment = partial.content.decode()
        for body in (html, fragment):
            self.assertIn(f'href="{exhibition.image1.url}"', body)
            self.assertIn('alt="Recent Artist — Titre long"', body)
            self.assertIn('width="8"', body)
            self.assertIn('height="16"', body)
            self.assertIn('loading="lazy"', body)
            self.assertNotIn("expo-image-fallback", body)
