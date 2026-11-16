"""Django settings for the Book Catalog System.

Values that differ between machines (secret key, debug flag, Open Library
contact email) come from environment variables, loaded from a `.env` file
when one exists. See `.env.example`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default):
    """Read a true/false environment variable such as DJANGO_DEBUG."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# The fallback key is only for local development; set DJANGO_SECRET_KEY elsewhere.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-key-do-not-use-in-production",
)
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third-party
    "django_htmx",
    "rest_framework",
    "rest_framework.authtoken",
    "django_tailwind_cli",
    # Project apps
    "accounts",
    "books",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "books:saved_books"
LOGOUT_REDIRECT_URL = "home"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Django REST Framework (the app's API)

# Session auth lets signed-in website users use the browsable API; token auth
# is for scripts and tools. Token auth comes first so an unauthenticated call
# gets 401 (with a WWW-Authenticate header) rather than 403. Tokens don't expire.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "assets"]

# Tailwind CSS + DaisyUI, built locally by django-tailwind-cli
# (`python manage.py tailwind build`, or `tailwind runserver` while developing).
TAILWIND_CLI_USE_DAISY_UI = True
TAILWIND_CLI_VERSION = "2.10.34"


# Email (nothing is sent; the project only stores addresses)

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}


# Open Library

# Sent in the User-Agent so Open Library allows 3 requests/second instead of 1.
OPENLIBRARY_CONTACT_EMAIL = os.environ.get("OPENLIBRARY_CONTACT_EMAIL", "").strip()
