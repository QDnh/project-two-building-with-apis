from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

# One message for every failed sign-in, so it never confirms that a username exists.
INVALID_LOGIN_MESSAGE = "Your username or password was wrong. Please try again."
DUPLICATE_EMAIL_MESSAGE = "An account with this email address already exists."


class SignUpForm(UserCreationForm):
    """Sign-up with a public username, a unique email and a checked password."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return email


class SignInForm(AuthenticationForm):
    """Django's sign-in form with a single, generic failure message."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": INVALID_LOGIN_MESSAGE,
    }
