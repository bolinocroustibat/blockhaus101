import random


def custom_captcha_challenge() -> tuple[str, str]:
    """
    Custom captcha challenge function.
    https://starcross.dev/blog/6/customising-django-simple-captcha/

    Returns:
        Plain output with no obfuscation as we are using a custom challenge
    """
    challenge: str = ""
    response: str = ""
    for i in range(4):
        digit = random.randint(0, 9)
        challenge += str(digit)
        response += str((digit + 1) % 10)
    # print(challenge, response)
    return challenge, response
