# _*_ coding: utf_8 _*_
from django import forms
from django.core import validators

class FormContact(forms.Form):
	name = forms.CharField(required=True, label='Votre nom', widget=forms.TextInput(attrs={'class' : 'input-name form-control'}))
	email = forms.EmailField(required=False, label='Votre e-mail', widget=forms.TextInput(attrs={'class' : 'input-email form-control'}))
	phone = forms.CharField(required=True, label='Votre téléphone', widget=forms.TextInput(attrs={'class' : 'input-phone form-control'}))
	text = forms.CharField(required=True, label='Pourquoi souhaitez-vous voir cet artiste', widget=forms.Textarea(attrs={'class' : 'input-text form-control'}))
	botcatcher = forms.CharField(required=False, widget=forms.HiddenInput, validators=[validators.MaxLengthValidator(0)])
