"""The app's API (Phase 10).

View-level tests fake the Open Library client's functions, so no HTTP request
is ever built.
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from books import openlibrary
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


def make_user(username):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


@pytest.fixture
def owner():
    return make_user("owner")


@pytest.fixture
def other():
    return make_user("other")


@pytest.fixture
def book():
    return Book.objects.create(
        work_id="OL893414W", title="Dune", authors="Frank Herbert"
    )


def client_for(user=None):
    # Unhandled errors come back as a 500 response, as a real client sees them.
    client = APIClient(raise_request_exception=False)
    if user is not None:
        client.force_authenticate(user)
    return client


def test_another_users_save_is_not_found_exactly_like_a_missing_one(owner, other, book):
    save = SavedBook.objects.create(user=owner, book=book, rating=4)
    client = client_for(other)
    url = f"/api/saved-books/{save.pk}/"
    missing_url = "/api/saved-books/999999/"

    responses = {
        "retrieve": client.get(url),
        "update": client.patch(url, {"rating": 1}, format="json"),
        "delete": client.delete(url),
    }
    missing = client.get(missing_url)

    for action, response in responses.items():
        assert response.status_code == 404, action
        assert response.json() == missing.json(), action
    save.refresh_from_db()
    assert save.rating == 4
    assert SavedBook.objects.filter(pk=save.pk).exists()


@pytest.fixture
def open_library_down(monkeypatch):
    """Fake Open Library as unavailable; records every fetch attempted."""
    calls = []

    def fake_fetch(work_id, **kwargs):
        calls.append(work_id)
        raise openlibrary.SearchError("Open Library is unavailable right now.")

    monkeypatch.setattr(openlibrary, "fetch_work", fake_fetch)
    return calls


def test_saving_a_new_book_while_open_library_is_down_returns_503(
    owner, book, open_library_down
):
    client = client_for(owner)

    new = client.post("/api/saved-books/", {"work_id": "OL45804W"}, format="json")
    existing = client.post(
        "/api/saved-books/", {"work_id": book.work_id}, format="json"
    )

    assert new.status_code == 503
    assert new.json() == {"detail": "Open Library is unavailable right now."}
    assert not Book.objects.filter(work_id="OL45804W").exists()
    assert existing.status_code == 201
    assert existing.json()["book"]["work_id"] == book.work_id
    assert open_library_down == ["OL45804W"]
    assert SavedBook.objects.filter(user=owner).count() == 1


def test_book_endpoint_returns_details_and_community_average_without_user_data(
    owner, other, book
):
    SavedBook.objects.create(user=owner, book=book, rating=5, is_public=True)
    SavedBook.objects.create(user=other, book=book, rating=4)  # private
    book.isbns = ["9780441013593"]
    book.subjects = ["Science fiction"]
    book.save()

    response = client_for().get(f"/api/books/{book.work_id}/")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "work_id",
        "title",
        "authors",
        "first_publish_year",
        "cover_id",
        "cover_url",
        "edition_count",
        "isbns",
        "subjects",
        "community_average",
        "rating_count",
    }
    assert data["authors"] == ["Frank Herbert"]
    assert data["isbns"] == ["9780441013593"]
    assert data["community_average"] == "4.5"
    assert data["rating_count"] == 2
    assert "owner" not in response.content.decode()
    assert "other" not in response.content.decode()
    assert client_for().get("/api/books/OL1W/").status_code == 404


def test_book_with_no_ratings_has_null_average_and_zero_count(book):
    data = client_for().get(f"/api/books/{book.work_id}/").json()

    assert data["community_average"] is None
    assert data["rating_count"] == 0


# --- Authentication -------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "post"])
def test_anonymous_calls_to_saved_books_get_401(method):
    response = getattr(client_for(), method)("/api/saved-books/")

    assert response.status_code == 401


def test_anonymous_call_to_a_single_save_gets_401(owner, book):
    save = SavedBook.objects.create(user=owner, book=book)

    assert client_for().get(f"/api/saved-books/{save.pk}/").status_code == 401


def test_token_from_username_and_password_authenticates_later_calls(owner, book):
    SavedBook.objects.create(user=owner, book=book)
    client = APIClient()

    token = client.post(
        "/api/token/", {"username": "owner", "password": "x"}, format="json"
    )
    assert token.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.json()['token']}")
    response = client.get("/api/saved-books/")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_token_endpoint_rejects_a_wrong_password(owner):
    response = APIClient().post(
        "/api/token/", {"username": "owner", "password": "wrong"}, format="json"
    )

    assert response.status_code == 400
    assert "token" not in response.json()


def test_browsable_api_works_with_a_website_session(client, owner):
    client.force_login(owner)

    response = client.get("/api/saved-books/", HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


def test_session_writes_need_a_csrf_token(owner, book):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)

    response = client.post(
        "/api/saved-books/", {"work_id": book.work_id}, format="json"
    )

    assert response.status_code == 403
    assert not SavedBook.objects.exists()


# --- Own saves ------------------------------------------------------------


def test_list_shows_only_the_requesters_saves(owner, other, book):
    second = Book.objects.create(work_id="OL45804W", title="Emma")
    mine = SavedBook.objects.create(user=owner, book=book)
    SavedBook.objects.create(user=other, book=second, is_public=True)

    data = client_for(owner).get("/api/saved-books/").json()

    assert data["count"] == 1
    item = data["results"][0]
    assert item["id"] == mine.pk
    assert item["book"]["work_id"] == "OL893414W"
    assert item["book"]["authors"] == ["Frank Herbert"]
    assert set(item) == {"id", "book", "status", "rating", "is_public", "saved_at"}


def test_create_with_a_new_work_id_fetches_details_from_open_library(
    owner, monkeypatch
):
    def fake_fetch(work_id, **kwargs):
        return openlibrary.SearchResult(
            work_id=work_id,
            title="Emma",
            authors=["Jane Austen"],
            first_publish_year=1815,
            cover_id=None,
            edition_count=3,
            isbns=[],
            subjects=[],
        )

    monkeypatch.setattr(openlibrary, "fetch_work", fake_fetch)

    response = client_for(owner).post(
        "/api/saved-books/",
        {"work_id": "OL45804W", "title": "Hacked", "authors": ["Mallory"]},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["book"]["title"] == "Emma"
    assert data["book"]["authors"] == ["Jane Austen"]
    assert (data["status"], data["rating"], data["is_public"]) == (
        "want_to_read",
        None,
        False,
    )
    assert Book.objects.get(work_id="OL45804W").title == "Emma"


def test_book_details_sent_with_a_known_work_id_are_ignored(
    owner, book, open_library_down
):
    response = client_for(owner).post(
        "/api/saved-books/",
        {
            "work_id": book.work_id,
            "title": "Hacked",
            "book": {"title": "Hacked"},
            "is_public": True,
            "rating": 5,
        },
        format="json",
    )

    assert response.status_code == 201
    book.refresh_from_db()
    assert book.title == "Dune"
    save = SavedBook.objects.get(user=owner)
    assert (save.is_public, save.rating) == (False, None)


def test_patching_book_details_changes_nothing_about_the_book(owner, book):
    save = SavedBook.objects.create(user=owner, book=book)

    response = client_for(owner).patch(
        f"/api/saved-books/{save.pk}/",
        {"book": {"title": "Hacked"}, "status": "reading"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["book"]["title"] == "Dune"
    book.refresh_from_db()
    assert book.title == "Dune"


def test_duplicate_save_is_a_400_with_a_clear_error(owner, book):
    SavedBook.objects.create(user=owner, book=book)

    response = client_for(owner).post(
        "/api/saved-books/", {"work_id": book.work_id}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {"work_id": ["This book is already in your Saved Books."]}
    assert SavedBook.objects.count() == 1


@pytest.mark.parametrize("payload", [{}, {"work_id": ""}, {"work_id": "dune"}])
def test_missing_or_malformed_work_id_is_a_400(owner, payload, open_library_down):
    response = client_for(owner).post("/api/saved-books/", payload, format="json")

    assert response.status_code == 400
    assert "work_id" in response.json()
    assert open_library_down == []


def test_owner_can_retrieve_update_and_delete_their_save(owner, book):
    save = SavedBook.objects.create(user=owner, book=book)
    client = client_for(owner)
    url = f"/api/saved-books/{save.pk}/"

    assert client.get(url).json()["id"] == save.pk
    updated = client.patch(
        url, {"status": "read", "rating": 5, "is_public": True}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] == 5
    save.refresh_from_db()
    assert (save.status, save.rating, save.is_public) == ("read", 5, True)

    cleared = client.patch(url, {"rating": None}, format="json")
    assert cleared.json()["rating"] is None

    assert client.delete(url).status_code == 204
    assert not SavedBook.objects.filter(pk=save.pk).exists()
    assert Book.objects.filter(pk=book.pk).exists()


def test_patch_changes_only_the_fields_sent(owner, book):
    save = SavedBook.objects.create(user=owner, book=book, rating=3, is_public=True)

    client_for(owner).patch(
        f"/api/saved-books/{save.pk}/", {"status": "reading"}, format="json"
    )

    save.refresh_from_db()
    assert (save.status, save.rating, save.is_public) == ("reading", 3, True)


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"status": "finished"}, "status"),
        ({"status": ["read"]}, "status"),
        ({"rating": 0}, "rating"),
        ({"rating": 6}, "rating"),
        ({"rating": "five"}, "rating"),
        ({"rating": 4.5}, "rating"),
        ({"is_public": "maybe"}, "is_public"),
        ({"is_public": []}, "is_public"),
    ],
)
def test_invalid_values_are_a_400_and_change_nothing(owner, book, payload, field):
    save = SavedBook.objects.create(user=owner, book=book, rating=3)

    response = client_for(owner).patch(
        f"/api/saved-books/{save.pk}/",
        {**payload, "status": payload.get("status", "read")},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()
    save.refresh_from_db()
    assert (save.status, save.rating) == ("want_to_read", 3)


def test_put_is_not_allowed(owner, book):
    save = SavedBook.objects.create(user=owner, book=book)

    response = client_for(owner).put(
        f"/api/saved-books/{save.pk}/", {"status": "read"}, format="json"
    )

    assert response.status_code == 405


# --- A user's public saves ------------------------------------------------


def test_public_saves_endpoint_lists_only_public_saves_to_anyone(owner, book):
    private_book = Book.objects.create(work_id="OL45804W", title="Secret Diary")
    SavedBook.objects.create(
        user=owner, book=book, is_public=True, status="reading", rating=4
    )
    SavedBook.objects.create(user=owner, book=private_book, rating=1)

    for viewer in (None, owner):
        response = client_for(viewer).get("/api/users/owner/saved-books/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        item = data["results"][0]
        assert item["book"]["work_id"] == "OL893414W"
        assert (item["status"], item["rating"]) == ("reading", 4)
        assert "Secret Diary" not in response.content.decode()


def test_making_a_save_private_removes_it_from_the_public_endpoint(owner, book):
    save = SavedBook.objects.create(user=owner, book=book, is_public=True)
    client = client_for(owner)

    client.patch(f"/api/saved-books/{save.pk}/", {"is_public": False}, format="json")

    assert client_for().get("/api/users/owner/saved-books/").json()["count"] == 0


def test_public_saves_endpoint_404s_for_unknown_users():
    assert client_for().get("/api/users/nobody/saved-books/").status_code == 404


def test_public_saves_endpoint_is_read_only(owner, book):
    response = client_for(owner).post(
        "/api/users/owner/saved-books/", {"work_id": book.work_id}, format="json"
    )

    assert response.status_code == 405
