"""Unit tests for public pages that do not generate content."""

from datetime import datetime, timedelta

from django.test import TestCase

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
        self.assertNotContains(response, "<!DOCTYPE html>")


class TestContact(TestCase):
    def test_shows_the_form(self) -> None:
        response = self.client.get("/fr/contact/")

        self.assertContains(response, "Votre nom")
        self.assertContains(response, "<form")

    def test_rejects_an_incomplete_message(self) -> None:
        response = self.client.post(
            "/fr/contact/",
            {"name": "", "email": "not-an-email", "phone": "", "text": ""},
        )

        self.assertEqual(response.status_code, 200)
        shown = response.content.decode().replace("&#x27;", "'")
        self.assertIn(MAIL_INVALID_MESSAGE["fr"], shown)


class TestDocumentLanguage(TestCase):
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
