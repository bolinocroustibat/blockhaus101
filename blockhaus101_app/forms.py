from captcha.fields import CaptchaField
from django import forms

_COPY = {
    "fr": {
        "name": "Votre nom *",
        "email": "Votre e-mail",
        "phone": "Votre téléphone *",
        "text": "Pourquoi souhaitez-vous voir cet artiste *",
        "captcha": (
            "Merci de vérifiez que vous n'êtes pas un robot.\n"
            "Ajoutez 1 à chaque chiffre du ci-après. Par exemple, pour 1234, "
            "vous devez entrer 2345."
        ),
        "required": "Ce champ est obligatoire.",
        "invalid_email": "Saisissez une adresse e-mail valide.",
        "invalid_captcha": "Code de vérification incorrect.",
    },
    "en": {
        "name": "Your name *",
        "email": "Your email",
        "phone": "Your phone *",
        "text": "Why do you want to see this artist *",
        "captcha": (
            "Please check that you are not a robot.\n"
            "Add 1 to each digit below. For example, for 1234, enter 2345."
        ),
        "required": "This field is required.",
        "invalid_email": "Enter a valid email address.",
        "invalid_captcha": "Incorrect verification code.",
    },
}


class FormContact(forms.Form):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "input-name form-control"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.TextInput(attrs={"class": "input-email form-control"}),
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "input-phone form-control", "inputmode": "tel"}),
    )
    text = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"class": "input-text form-control"}),
    )
    captcha = CaptchaField()

    def __init__(self, *args, lang: str = "fr", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        copy = _COPY.get(lang, _COPY["fr"])
        for field_name in ("name", "email", "phone", "text", "captcha"):
            self.fields[field_name].label = copy[field_name]
            self.fields[field_name].error_messages["required"] = copy["required"]
        self.fields["email"].error_messages["invalid"] = copy["invalid_email"]
        self.fields["captcha"].error_messages["invalid"] = copy["invalid_captcha"]
