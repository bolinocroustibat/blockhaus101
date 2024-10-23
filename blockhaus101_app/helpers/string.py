import re
from typing import Literal

from base_data_app.models import Data
from blockhaus101.settings import logger


def replace_text_translations(text: str, original_keywords: list[Data], lang: str) -> str:
    def translate_match(match: re.Match, original_keywords: list[Data], lang: str) -> str:
        """
        Replace a match with a translation of data from used_data
        """
        if original_keywords:
            data: Data = original_keywords.pop(0)
            try:
                word: str = Data.objects.get(language__lang=lang, translation=data).text
            except Data.DoesNotExist:
                logger.warning(f'Translation not found for data: "{data}" ({data.pk})')
                word = data.text  # Use the untranslated string
            return word
        return match.group(0)

    return re.sub(r"\[.*?\]", lambda match: translate_match(match, original_keywords, lang), text)


def replace_text(text: str, lang: str) -> tuple[str, list[Data]]:
    """
    Replace keywords in a text by random data from the database.
    Args:
        text: str: the text to modify
        language: Language: the language of the data to choose
    Returns:
        tuple: the modified text and the used words, the used words is a dict with the data type as key and the list of the used data as value
    """
    keywords: list = re.findall(r"\[[^][]*]", text)
    used_data: list[Data] = []
    for k in keywords:
        word_type: str = k.replace("[", "").replace("]", "")
        chosen_data = Data.choose_random_excluding(
            data_type=word_type, lang=lang, excluding=used_data
        )
        if chosen_data:
            chosen_word = chosen_data[0].text
            used_data = chosen_data[1]
            # only replace one occurence, we want the same keyword to be able to be replaced by another word
            text = text.replace(f"[{word_type}]", chosen_word, 1)
    return text, used_data


def correct_text(sentence: str, lang: str, subject_gender: Literal["f", "m"] | None = None) -> str:
    # Remove first and  end spaces
    sentence = "".join(sentence.rstrip().lstrip())

    # Remove all extra spaces
    sentence = " ".join(sentence.split())

    # Remove spaces before and after some characters
    sentence = _strtr(sentence, {"( ": "(", " )": ")", " ,": ",", " .": "."})

    # Correct the sentence
    CORRECTIONS_EN: dict = {}
    CORRECTIONS_FR: dict = {  # we could also use "replace(old, new)"
        "( ": "(",
        " )": ")",
        " ,": ",",
        " à le ": " au ",
        " à les ": " aux ",
        " de a": " d’a",
        " de e": " d’e",
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
    }
    if lang == "en":
        sentence = _strtr(sentence, CORRECTIONS_EN)
    elif lang == "fr":
        sentence = _strtr(sentence, CORRECTIONS_FR)
        if subject_gender == "f":
            sentence = sentence.replace(" il ", " elle ")
            sentence = sentence.replace("qu'il ", "qu'elle ")
            sentence = sentence.replace("Il ", "Elle ")
            sentence = sentence.replace(" né ", " née ")
            sentence = sentence.replace("Né ", "Née ")
            sentence = sentence.replace("iplômé ", "iplômée ")
            sentence = sentence.replace("marqué ", "marquée ")
            sentence = sentence.replace("obsédé ", "obsédée ")
    else:
        logger.error(f"Language not supported: {lang}")
    return capitalize_sentence(sentence)


def capitalize_sentence(sentence: str) -> str:
    if sentence[0] == '"':  # if the first char is a double quote
        return '"' + sentence[1].upper() + sentence[2:]  # capitalize second letter
    else:
        return sentence[0].upper() + sentence[1:]  # capitalize first letter


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
