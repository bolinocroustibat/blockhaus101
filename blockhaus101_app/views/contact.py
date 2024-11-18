from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render

from blockhaus101.settings import (
    MAIL_ERROR_MESSAGE,
    MAIL_INVALID_MESSAGE,
    MAIL_SUCCESS_MESSAGE,
    logger,
)
from blockhaus101_app.forms import FormContact


def contact(request, lang: str) -> HttpResponse:
    form = FormContact(request.POST or None)
    message = None
    if request.method == "POST":  # Checks to see if we get a POST back...
        if form.is_valid():  # Checks to see form is valid
            try:
                send_mail(
                    subject="Mail from Blockhaus101 website",
                    message="Sender: "
                    + form.cleaned_data["name"]
                    + " / Sender email: "
                    + form.cleaned_data["email"]
                    + " / Sender phone: "
                    + form.cleaned_data["phone"]
                    + " / Message text: "
                    + form.cleaned_data["text"],
                    from_email=form.cleaned_data["email"],
                    recipient_list=["me@adriencarpentier.com"],
                    fail_silently=False,
                    html_message="Sender : "
                    + form.cleaned_data["name"]
                    + " <br/> Sender email: "
                    + form.cleaned_data["email"]
                    + " <br/> Sender phone: "
                    + form.cleaned_data["phone"]
                    + " <br/> Message text: "
                    + form.cleaned_data["text"],
                )
                form = FormContact()
            except Exception as e:
                logger.error(f"Error while sending email: {str(e)}")
                message = MAIL_ERROR_MESSAGE[lang]
            else:
                logger.info("Contact email sent!")
                message = MAIL_SUCCESS_MESSAGE[lang]
        else:
            logger.warning("Form is not valid")
            message = MAIL_INVALID_MESSAGE[lang]
    return render(
        request,
        f"{lang}/contact.html",
        {"lang": lang, "form_contact": form, "message": message},
    )
