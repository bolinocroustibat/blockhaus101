from blockhaus101.settings import logger


def correct_sentence(lang: str, sentence: str) -> str:
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
