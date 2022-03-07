from datetime import datetime


def format_date(date: datetime.date, lang: str) -> str:
    """
    Could also do:
    https://stackoverflow.com/questions/18593661/how-do-i-strftime-a-date-object-in-a-different-locale
    """
    if lang == "fr":
        mois = [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]
        return date.strftime(f"%-d {mois[date.month-1]} %Y")
    if lang == "en":
        return date.strftime("%B %-d %Y")
