"""Public profiles and the privacy rule behind them (Phase 9)."""

import pytest
from django.urls import reverse

from accounts.models import User
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


def make_user(username):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


def make_book(work_id, title):
    return Book.objects.create(work_id=work_id, title=title, authors="Someone")


def test_public_saves_query_returns_only_public_saves():
    alice, bob = make_user("alice"), make_user("bob")
    dune, emma, ulysses = (
        make_book("OL1W", "Dune"),
        make_book("OL2W", "Emma"),
        make_book("OL3W", "Ulysses"),
    )
    alice_public = SavedBook.objects.create(user=alice, book=dune, is_public=True)
    SavedBook.objects.create(user=alice, book=emma, is_public=False)
    bob_public = SavedBook.objects.create(user=bob, book=emma, is_public=True)
    SavedBook.objects.create(user=bob, book=ulysses, is_public=False)

    assert set(SavedBook.objects.public()) == {alice_public, bob_public}
    # It chains with other filters, so a profile can narrow it to one user.
    assert list(SavedBook.objects.filter(user=alice).public()) == [alice_public]


def test_profile_never_shows_private_saves_even_to_the_owner(client):
    alice = make_user("alice")
    shared = SavedBook.objects.create(
        user=alice,
        book=make_book("OL1W", "Dune"),
        status=SavedBook.Status.READING,
        rating=4,
        is_public=True,
    )
    SavedBook.objects.create(
        user=alice, book=make_book("OL2W", "Secret Diary"), is_public=False
    )
    client.force_login(alice)
    url = reverse("profile", args=["alice"])

    html = client.get(url).content.decode()
    assert "Dune" in html
    assert "Reading" in html
    assert "Rated 4 out of 5" in html
    assert "Secret Diary" not in html

    # Making a save private removes it from the profile right away.
    shared.is_public = False
    shared.save()
    html = client.get(url).content.decode()
    assert "Dune" not in html
    assert "no public books yet" in html


def test_unknown_username_is_not_found(client):
    response = client.get(reverse("profile", args=["nobody"]))

    assert response.status_code == 404


def test_logged_out_visitor_sees_only_that_users_public_saves(client):
    alice = make_user("alice")
    SavedBook.objects.create(
        user=alice, book=make_book("OL1W", "Dune"), rating=5, is_public=True
    )
    SavedBook.objects.create(
        user=alice, book=make_book("OL2W", "Secret Diary"), is_public=False
    )
    # Another user's public save doesn't belong on this profile.
    SavedBook.objects.create(
        user=make_user("bob"), book=make_book("OL3W", "Emma"), is_public=True
    )

    response = client.get(reverse("profile", args=["alice"]))

    html = response.content.decode()
    assert response.status_code == 200
    assert "Dune" in html
    assert "Rated 5 out of 5" in html
    assert "Want to read" in html
    assert "Secret Diary" not in html
    assert "Emma" not in html


def test_profile_with_no_public_saves_shows_empty_state(client):
    alice = make_user("alice")
    SavedBook.objects.create(
        user=alice, book=make_book("OL1W", "Secret Diary"), is_public=False
    )
    client.force_login(make_user("bob"))

    html = client.get(reverse("profile", args=["alice"])).content.decode()

    assert 'data-testid="no-public-books"' in html
    assert "alice has no public books yet." in html
    assert "Secret Diary" not in html


def test_profile_pages_12_at_a_time_and_htmx_gets_only_the_list(client):
    alice = make_user("alice")
    for n in range(13):
        SavedBook.objects.create(
            user=alice, book=make_book(f"OL{n + 1}W", f"Book {n:02}"), is_public=True
        )
    url = reverse("profile", args=["alice"])

    first = client.get(url).content.decode()
    assert first.count('data-testid="public-save"') == 12
    assert "Page 1 of 2" in first

    second = client.get(f"{url}?page=2", headers={"HX-Request": "true"})
    html = second.content.decode()
    assert html.count('data-testid="public-save"') == 1
    assert "<html" not in html
    assert "HX-Request" in second["Vary"]


def test_navbar_links_to_own_profile(client):
    client.force_login(make_user("alice"))

    html = client.get(reverse("books:saved_books")).content.decode()

    assert f'href="{reverse("profile", args=["alice"])}"' in html
