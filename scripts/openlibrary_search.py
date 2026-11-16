"""Search Open Library for books from the command line.

Usage:
    uv run python scripts/openlibrary_search.py

Optional: set OPENLIBRARY_CONTACT_EMAIL in a .env file (see .env.example).
Open Library asks apps to identify themselves with a contact email in the
User-Agent header, and allows 3 requests/second instead of 1 when they do.
Open Library needs no API key.
"""

import os

import requests
from dotenv import load_dotenv

SEARCH_URL = "https://openlibrary.org/search.json"
RESULT_LIMIT = 5
TIMEOUT_SECONDS = 10
APP_NAME = "BookCatalogSystem/0.1"
# Only ask Open Library for the fields we display, to keep responses small.
FIELDS = "key,title,author_name,first_publish_year"


class SearchError(Exception):
    """A search failed. The message is written to be shown to the user."""


def build_headers(contact_email):
    """Return request headers, including the contact email when we have one."""
    if contact_email:
        return {"User-Agent": f"{APP_NAME} ({contact_email})"}
    return {"User-Agent": APP_NAME}


def search_books(query, contact_email=None):
    """Search Open Library and return (total_matches, books).

    `books` is a list of dicts with the keys listed in FIELDS (any may be
    missing). Raises SearchError with a user-friendly message on failure.
    """
    params = {"q": query, "fields": FIELDS, "limit": RESULT_LIMIT}

    try:
        response = requests.get(
            SEARCH_URL,
            params=params,
            headers=build_headers(contact_email),
            timeout=TIMEOUT_SECONDS,
        )
    # Timeout must be checked before ConnectionError: a connect timeout is both.
    except requests.exceptions.Timeout:
        raise SearchError(
            f"Open Library did not respond within {TIMEOUT_SECONDS} seconds. "
            "Try again later."
        ) from None
    except requests.exceptions.ConnectionError:
        raise SearchError(
            "Could not connect to Open Library. Check your internet connection."
        ) from None
    except requests.exceptions.RequestException as error:
        raise SearchError(f"The request to Open Library failed: {error}") from None

    status = response.status_code
    if status == 429:
        raise SearchError(
            "Open Library says there have been too many requests (HTTP 429). "
            "Wait a minute and try again."
        )
    if status >= 500:
        raise SearchError(
            f"Open Library is unavailable right now (HTTP {status}). Try again later."
        )
    if status >= 400:
        raise SearchError(f"Open Library rejected the request (HTTP {status}).")

    try:
        data = response.json()
    except ValueError:
        raise SearchError(
            "Open Library sent back a response that wasn't valid JSON. Try again later."
        ) from None

    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise SearchError("Open Library sent back a response in an unexpected format.")

    books = data["docs"]
    total = data.get("numFound", len(books))
    return total, books


def format_book(number, book):
    """Return a book as display lines, filling in placeholders for missing data."""
    title = book.get("title") or "Untitled"
    year = book.get("first_publish_year")
    authors = book.get("author_name") or []
    work_id = (book.get("key") or "").removeprefix("/works/") or "unknown"

    year_text = f"({year})" if year else "(year unknown)"
    author_text = ", ".join(authors) if authors else "Unknown author"

    return f"{number}. {title} {year_text}\n   by {author_text}\n   ID: {work_id}"


def main():
    """Ask for a search phrase, run the search, and print the results.

    Returns an exit code: 0 on success (including "no results"), 1 on error.
    """
    contact_email = os.environ.get("OPENLIBRARY_CONTACT_EMAIL", "").strip()
    if not contact_email:
        print(
            "Note: OPENLIBRARY_CONTACT_EMAIL is not set, so requests are limited "
            "to 1 per second. See .env.example.\n"
        )

    try:
        query = input("Search Open Library for books: ").strip()
    except EOFError:
        query = ""

    if not query:
        print("Please enter a search phrase, such as a title or author.")
        return 1

    try:
        total, books = search_books(query, contact_email)
    except SearchError as error:
        print(f"Error: {error}")
        return 1

    if not books:
        print(f'No books found matching "{query}".')
        return 0

    print(f'\nShowing {len(books)} of {total:,} matches for "{query}":\n')
    for number, book in enumerate(books, start=1):
        print(format_book(number, book))
        print()
    return 0


if __name__ == "__main__":
    load_dotenv()  # Read OPENLIBRARY_CONTACT_EMAIL from .env, if the file exists.
    raise SystemExit(main())
