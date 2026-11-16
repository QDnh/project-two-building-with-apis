"""Open Library client: the only module that talks to Open Library.

Only the search endpoint is used. Open Library needs no API key, but asks apps
to identify themselves with a contact email in the User-Agent header, and
allows 3 requests/second instead of 1 when they do. The email comes from the
OPENLIBRARY_CONTACT_EMAIL setting (see `.env.example`).

Checked against the live API (2026-11-16): the requested fields below are all
returned; a bare ISBN in `q` (e.g. `9780441013593`) finds the right work, so
the ISBN-specific parameter isn't needed; and `q=key:/works/OL893414W` returns
exactly that one work.

Every failure raises SearchError, whose message is written to be shown to the
user. The underlying exception, if any, is kept as `__cause__` for logging.
"""

import re
from dataclasses import dataclass, field

import requests
from django.conf import settings

from .models import COVER_URL, MAX_LIST_VALUES

SEARCH_URL = "https://openlibrary.org/search.json"
TIMEOUT_SECONDS = 10
APP_NAME = "BookCatalogSystem/0.1"
RESULTS_PER_PAGE = 20
# Only ask Open Library for the fields we use, to keep responses small.
FIELDS = "key,title,author_name,first_publish_year,cover_i,isbn,subject,edition_count"

# Digits with optional hyphens/spaces, ending in a digit or X (ISBN-10 check digit).
_ISBN_LIKE = re.compile(r"^[\d\s-]+[\dXx]$")


class SearchError(Exception):
    """A search failed. The message is written to be shown to the user."""


@dataclass
class SearchResult:
    """One work from a search, with the attribute names the templates use."""

    work_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    first_publish_year: int | None = None
    cover_id: int | None = None
    edition_count: int = 0
    isbns: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)

    @property
    def author_list(self):
        return self.authors

    @property
    def cover_url_large(self):
        if self.cover_id is None:
            return None
        return COVER_URL.format(cover_id=self.cover_id, size="L")


@dataclass
class SearchPage:
    """One page of search results plus the total number of matches."""

    total: int
    results: list[SearchResult]


def build_headers(contact_email):
    """Return request headers, including the contact email when we have one."""
    if contact_email:
        return {"User-Agent": f"{APP_NAME} ({contact_email})"}
    return {"User-Agent": APP_NAME}


def clean_query(query):
    """Trim a search, and strip hyphens and spaces from ISBN-like input.

    "978-0-441-01359-3" becomes "9780441013593"; ordinary text is only trimmed.
    """
    query = (query or "").strip()
    if _ISBN_LIKE.match(query):
        digits = re.sub(r"[\s-]", "", query).upper()
        if len(digits) in (10, 13):
            return digits
    return query


def parse_result(doc):
    """Turn one search `doc` into a SearchResult, or None if it has no work key."""
    work_id = (doc.get("key") or "").removeprefix("/works/")
    if not work_id:
        return None
    year = doc.get("first_publish_year")
    cover_id = doc.get("cover_i")
    return SearchResult(
        work_id=work_id,
        title=doc.get("title") or "Untitled",
        authors=list(doc.get("author_name") or []),
        first_publish_year=year if isinstance(year, int) else None,
        cover_id=cover_id if isinstance(cover_id, int) and cover_id > 0 else None,
        edition_count=doc.get("edition_count") or 0,
        isbns=list(doc.get("isbn") or [])[:MAX_LIST_VALUES],
        subjects=list(doc.get("subject") or [])[:MAX_LIST_VALUES],
    )


def search_books(query, *, page=1, limit=RESULTS_PER_PAGE, contact_email=None):
    """Search Open Library and return a SearchPage.

    `contact_email` defaults to the OPENLIBRARY_CONTACT_EMAIL setting.
    Raises SearchError with a user-friendly message on any failure.
    """
    if contact_email is None:
        contact_email = settings.OPENLIBRARY_CONTACT_EMAIL
    params = {"q": query, "fields": FIELDS, "page": page, "limit": limit}

    try:
        response = requests.get(
            SEARCH_URL,
            params=params,
            headers=build_headers(contact_email),
            timeout=TIMEOUT_SECONDS,
        )
    # Timeout must be checked before ConnectionError: a connect timeout is both.
    except requests.exceptions.Timeout as error:
        raise SearchError(
            f"Open Library did not respond within {TIMEOUT_SECONDS} seconds. "
            "Try again later."
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise SearchError(
            "Could not connect to Open Library. Check your internet connection "
            "or try again later."
        ) from error
    except requests.exceptions.RequestException as error:
        raise SearchError(
            "The request to Open Library failed. Try again later."
        ) from error

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
    except ValueError as error:
        raise SearchError(
            "Open Library sent back a response that wasn't valid JSON. Try again later."
        ) from error

    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise SearchError("Open Library sent back a response in an unexpected format.")

    docs = [doc for doc in data["docs"] if isinstance(doc, dict)]
    results = [result for doc in docs if (result := parse_result(doc))]
    total = data.get("numFound")
    if not isinstance(total, int):
        total = len(results)
    return SearchPage(total=total, results=results)
