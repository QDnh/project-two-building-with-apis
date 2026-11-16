"""The public book page (Phase 2)."""

import re

import pytest
from django.urls import reverse

from accounts.models import User
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def book():
    return Book.objects.create(
        work_id="OL893414W",
        title="Dune",
        authors="Frank Herbert",
        first_publish_year=1965,
        cover_id=11481354,
        edition_count=12,
        isbns=["9780441013593", "0441013597"],
        subjects=["Science fiction", "Arrakis"],
    )


def save_with_rating(book, username, rating, *, is_public):
    user = User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )
    return SavedBook.objects.create(
        user=user, book=book, rating=rating, is_public=is_public
    )


def page_html(client, book):
    response = client.get(reverse("books:book_detail", args=[book.work_id]))
    assert response.status_code == 200
    return response.content.decode()


# --- Community average ------------------------------------------------------


def test_book_page_shows_community_average_without_naming_raters(client, book):
    save_with_rating(book, "public_rater", 5, is_public=True)
    save_with_rating(book, "secret_rater", 4, is_public=False)
    save_with_rating(book, "third_rater", 4, is_public=False)
    save_with_rating(book, "unrated_reader", None, is_public=True)

    html = page_html(client, book)

    assert "4.3 ★ from 3 ratings" in html
    for username in ["public_rater", "secret_rater", "third_rater", "unrated_reader"]:
        assert username not in html


def test_book_page_says_no_ratings_yet(client, book):
    save_with_rating(book, "unrated_reader", None, is_public=True)

    html = page_html(client, book)

    assert "No ratings yet" in html
    assert "★ from" not in html


def test_book_page_uses_singular_for_one_rating(client, book):
    save_with_rating(book, "only_rater", 2, is_public=False)

    html = page_html(client, book)

    assert "2.0 ★ from 1 rating<" in html


# --- Details, access and cover ----------------------------------------------


def test_book_page_shows_the_stored_details_to_a_logged_out_visitor(client, book):
    html = page_html(client, book)

    for text in [
        "Dune",
        "Frank Herbert",
        "1965",
        "Science fiction",
        "Arrakis",
        "9780441013593",
        "0441013597",
        "OL893414W",
    ]:
        assert text in html


def test_book_page_works_for_a_signed_in_user(client, book):
    user = User.objects.create_user(
        username="reader", email="reader@example.com", password="x"
    )
    client.force_login(user)

    assert "Dune" in page_html(client, book)


def test_book_page_url_uses_the_work_id(book):
    assert book.get_absolute_url() == "/books/OL893414W/"


def test_unknown_work_id_returns_404(client):
    response = client.get(reverse("books:book_detail", args=["OL999999999W"]))

    assert response.status_code == 404


def test_cover_image_falls_back_to_a_hidden_placeholder(client, book):
    html = page_html(client, book)

    assert 'src="https://covers.openlibrary.org/b/id/11481354-L.jpg"' in html
    assert "onerror=" in html
    # The placeholder is in the page, hidden until the image fails to load.
    assert re.search(r'data-testid="cover-placeholder"\s+hidden', html)


def test_book_without_a_cover_shows_the_placeholder(client, book):
    book.cover_id = None
    book.save()

    html = page_html(client, book)

    assert "covers.openlibrary.org" not in html
    # Shown straight away: no `hidden` attribute.
    assert re.search(r'data-testid="cover-placeholder"\s*>', html)
