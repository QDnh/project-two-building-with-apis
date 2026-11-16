"""Sign-up, sign-in, sign-out and members-only redirects (Phase 1)."""

import pytest
from django.db import IntegrityError
from django.urls import reverse

from accounts.forms import DUPLICATE_EMAIL_MESSAGE, INVALID_LOGIN_MESSAGE
from accounts.models import User

pytestmark = pytest.mark.django_db

GOOD_PASSWORD = "quiet-river-lantern-42"


@pytest.fixture
def reader():
    return User.objects.create_user(
        username="reader", email="reader@example.com", password=GOOD_PASSWORD
    )


def sign_up(client, **overrides):
    data = {
        "username": "newreader",
        "email": "new@example.com",
        "password1": GOOD_PASSWORD,
        "password2": GOOD_PASSWORD,
        **overrides,
    }
    return client.post(reverse("signup"), data)


# --- Sign-up ---------------------------------------------------------------


def test_sign_up_creates_account_and_signs_in(client):
    response = sign_up(client)

    assert response.status_code == 302
    assert response.url == reverse("books:saved_books")
    user = User.objects.get(username="newreader")
    assert user.email == "new@example.com"
    assert user.check_password(GOOD_PASSWORD)
    assert client.get(reverse("books:saved_books")).status_code == 200


@pytest.mark.parametrize("missing", ["username", "email", "password1"])
def test_sign_up_requires_each_field(client, missing):
    response = sign_up(client, **{missing: ""})

    assert response.status_code == 200
    assert response.context["form"].errors[missing]
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "password",
    ["password123", "12345678901", "short1!", "newreader1"],
    ids=["common", "numeric", "too-short", "like-username"],
)
def test_sign_up_rejects_weak_passwords(client, password):
    response = sign_up(client, password1=password, password2=password)

    assert response.status_code == 200
    assert response.context["form"].errors["password2"]
    assert not User.objects.filter(username="newreader").exists()


def test_sign_up_rejects_duplicate_email_ignoring_case(client, reader):
    response = sign_up(client, email="READER@example.com")

    assert response.status_code == 200
    assert response.context["form"].errors["email"] == [DUPLICATE_EMAIL_MESSAGE]
    assert User.objects.count() == 1


def test_database_rejects_duplicate_email(reader):
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="someone-else", email="reader@example.com", password="x"
        )


def test_signed_in_user_visiting_sign_up_is_sent_to_saved_books(client, reader):
    client.force_login(reader)

    response = client.get(reverse("signup"))

    assert response.status_code == 302
    assert response.url == reverse("books:saved_books")


# --- Sign-in / sign-out ------------------------------------------------------


def test_sign_in_with_username_and_password(client, reader):
    response = client.post(
        reverse("login"), {"username": "reader", "password": GOOD_PASSWORD}
    )

    assert response.status_code == 302
    assert response.url == reverse("books:saved_books")
    assert int(client.session["_auth_user_id"]) == reader.pk


@pytest.mark.parametrize(
    ("username", "password"),
    [("reader", "wrong-password"), ("nobody", "wrong-password")],
    ids=["wrong-password", "unknown-username"],
)
def test_failed_sign_in_shows_the_same_generic_message(
    client, reader, username, password
):
    response = client.post(
        reverse("login"), {"username": username, "password": password}
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors() == [INVALID_LOGIN_MESSAGE]
    assert "_auth_user_id" not in client.session


def test_sign_out_ends_the_session(client, reader):
    client.force_login(reader)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert "_auth_user_id" not in client.session
    assert client.get(reverse("books:saved_books")).status_code == 302


# --- Members-only pages and navbar --------------------------------------------


def test_members_only_page_redirects_logged_out_visitor_to_sign_in(client):
    saved_books = reverse("books:saved_books")

    response = client.get(saved_books)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={saved_books}"


def test_sign_in_returns_visitor_to_the_page_they_wanted(client, reader):
    saved_books = reverse("books:saved_books")

    response = client.post(
        f"{reverse('login')}?next={saved_books}",
        {"username": "reader", "password": GOOD_PASSWORD, "next": saved_books},
    )

    assert response.url == saved_books


def test_navbar_for_logged_out_visitor(client):
    html = client.get(reverse("home")).content.decode()

    assert f'href="{reverse("login")}"' in html
    assert f'href="{reverse("signup")}"' in html
    assert "Sign out" not in html
    assert f'href="{reverse("books:saved_books")}"' not in html


def test_navbar_for_signed_in_user(client, reader):
    client.force_login(reader)

    html = client.get(reverse("home")).content.decode()

    assert "reader ▾" in html
    assert "Sign out" in html
    assert f'href="{reverse("books:saved_books")}"' in html
    assert f'href="{reverse("signup")}"' not in html


def test_base_layout_loads_local_css_and_htmx(client):
    html = client.get(reverse("home")).content.decode()

    assert "/static/css/tailwind.css" in html
    assert "/static/django_htmx/htmx-2.min.js" in html
    assert "cdn" not in html.lower()


def test_site_uses_the_dark_theme(client):
    html = client.get(reverse("home")).content.decode()

    assert '<html lang="en" data-theme="dark">' in html
