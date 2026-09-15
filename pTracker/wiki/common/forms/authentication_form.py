from django import forms
from django.utils.translation import gettext, gettext_lazy as _

class LoginForm(forms.Form):
    email = forms.EmailField(label=_('email'), min_length=3, max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        email = cleaned_data.get('email')
        if email in ('', 'None', None):
            self._errors["email"] = self.error_class(
                ['Please enter your Email address'])
            if email in cleaned_data:
                del cleaned_data["email"]

        password = cleaned_data.get('password')
        if password in ('', 'None', None):
            self._errors["password"] = self.error_class(
                ['Please enter your password'])
            if password in cleaned_data:
                del cleaned_data["password"]
        return cleaned_data

class TwoFactorVerificationForm(forms.Form):
    two_fa_token = forms.CharField(label='Token', max_length=10)

    def clean(self):
        cleaned_data = super(TwoFactorVerificationForm, self).clean()
        two_fa_token = cleaned_data.get('two_fa_token')
        if two_fa_token in ('', 'None', None):
            self._errors["two_fa_token"] = self.error_class(
                ['Expected an OTP.'])
            if two_fa_token in cleaned_data:
                del cleaned_data["two_fa_token"]
        return cleaned_data