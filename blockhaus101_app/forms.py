from captcha.fields import CaptchaField
from django import forms
from django.core import validators


class FormContact(forms.Form):
    name = forms.CharField(
        required=True,
        label="Votre nom *",
        widget=forms.TextInput(attrs={"class": "input-name form-control"}),
    )
    email = forms.EmailField(
        required=False,
        label="Votre e-mail",
        widget=forms.TextInput(attrs={"class": "input-email form-control"}),
        validators=[validators.validate_email],
    )
    phone = forms.CharField(
        required=True,
        label="Votre téléphone *",
        widget=forms.NumberInput(attrs={"class": "input-phone form-control"}),
    )
    text = forms.CharField(
        required=True,
        label="Pourquoi souhaitez-vous voir cet artiste *",
        widget=forms.Textarea(attrs={"class": "input-text form-control"}),
    )
    captcha = CaptchaField()
