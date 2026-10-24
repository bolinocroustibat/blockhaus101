"""Small persisted builders shared by unit tests."""

from datetime import datetime

from base_data_app.models import Data, DataType, Language
from blockhaus101_app.models import Artist, Exhibition


def make_language(code: str, name: str) -> Language:
    language, _created = Language.objects.get_or_create(code=code, defaults={"name": name})
    return language


def make_artist(
    *,
    name: str = "Ada Lovelace",
    gender: str = "f",
    discipline_text: str = "painting",
    language: Language | None = None,
) -> Artist:
    data_type, _created = DataType.objects.get_or_create(name="DISCIPLINE")
    if language is None:
        language = make_language("en", "English")
    discipline = Data.objects.create(
        data_type=data_type,
        text=discipline_text,
        language=language,
    )
    return Artist.objects.create(name=name, gender=gender, discipline=discipline)


def make_exhibition(
    artist: Artist,
    *,
    startdate: datetime | None = None,
    enddate: datetime | None = None,
) -> Exhibition:
    return Exhibition.objects.create(artist=artist, startdate=startdate, enddate=enddate)
