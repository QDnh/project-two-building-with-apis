# Book Catalog System

A Django web app and REST API for keeping a personal reading list. Signed-in
users search [Open Library](https://openlibrary.org), save books, set a reading
status (Want to read / Reading / Read), give an optional 1–5 star rating, and
choose book by book which saves appear on their public profile.

Saved books are stored locally, so Saved Books, book pages and profiles keep
working when Open Library is slow or down.

## Features

- **Search Catalog** (`/catalog/`): search Open Library by title, author,
  keywords or ISBN (hyphens and spaces are stripped). 20 results per page, up
  to 10 pages. Results you've already saved show "Saved ✓".
- **Saved Books** (`/saved/`): your own list, with title/author search, filters
  for status, rating (including Unrated) and visibility, four sort orders, and
  12 per page. Change status, rating and sharing straight from each card.
- **Book page** (`/books/<work_id>/`): open to anyone. Book details plus the
  **community average** rating (one decimal place, with a count). Owners can
  edit or remove their save here.
- **Profile** (`/users/<username>/`): open to anyone. Shows only that user's
  public saves.
- **API** (`/api/`): token or session authenticated create, list, update and
  delete for your own saves, plus read-only public endpoints for profiles and
  books.

Searching, filtering, sorting and paging use HTMX, so only the part of the
page that changes is swapped, and the URL keeps the current settings.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

django-tailwind-cli downloads the Tailwind CLI (with DaisyUI) the first time
it runs, so no Node.js install is needed. HTMX comes from django-htmx's
vendored copy, not a CDN.

## Setup

```sh
uv sync                                  # install dependencies
cp .env.example .env                     # then edit .env (see below)
uv run python manage.py migrate          # create the SQLite database
uv run python manage.py seed_demo        # optional: demo users and books
uv run python manage.py tailwind runserver
```

Then open <http://127.0.0.1:8000/>.

`tailwind runserver` starts Django's dev server and rebuilds the CSS as
templates change. To build the CSS once instead, run
`uv run python manage.py tailwind build` (the output, `assets/css/tailwind.css`,
is git-ignored).

### Environment variables

Settings are read from `.env` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `OPENLIBRARY_CONTACT_EMAIL` | Optional. Added to the User-Agent sent to Open Library, which gets the app the higher rate limit (about 3 requests per second instead of 1). |
| `DJANGO_SECRET_KEY` | Optional locally (a development-only key is used when unset). Set a long random value anywhere else. |
| `DJANGO_DEBUG` | `true` or `false`. Defaults to `true` for local development. |

## Demo data and logins

`seed_demo` loads 4 demo users and 15 real books from a bundled data file
(`books/data/demo_books.json`). It never contacts Open Library, can be run
again at any time (it resets the demo saves rather than duplicating them), and
refuses to run unless `DEBUG` is on.

Every demo user's password is **`shelf-demo-2026`**.

| Username | What it shows |
|---|---|
| `alice` | Public and private saves across all three statuses |
| `ben` | Mostly public saves; a private 2★ rating of *The Great Gatsby* |
| `chloe` | The largest list, mixing public and private |
| `dev` | Only private saves, so their profile shows "no public books yet" |

*Moby Dick* is loaded but saved by nobody, so it's a handy target for
`prune_books`.

## Management commands

| Command | What it does |
|---|---|
| `uv run python manage.py seed_demo` | Load the demo users, books and saves (DEBUG only, no network). |
| `uv run python manage.py prune_books --dry-run` | List books nobody has saved, without deleting anything. |
| `uv run python manage.py prune_books` | Delete books nobody has saved. |

Books with any save, public or private, are never pruned. The database backs
this up: a saved book's link to its Book is `PROTECT`, so deleting a book that
someone has saved raises an error.

## API

| Endpoint | Access | Methods |
|---|---|---|
| `/api/token/` | Anyone | `POST` username + password → token |
| `/api/saved-books/` | Signed in | `GET` your saves, `POST` `{"work_id": "OL893414W"}` |
| `/api/saved-books/<id>/` | Signed in, owner only | `GET`, `PATCH` (`status`, `rating`, `is_public`), `DELETE` |
| `/api/users/<username>/saved-books/` | Anyone | `GET` that user's public saves |
| `/api/books/<work_id>/` | Anyone | `GET` book details, community average and count |

Send the token as `Authorization: Token <token>`. In the browser, the
browsable API also works with your website session.

- Creating a save takes only the Open Library work ID. The server fills in the
  book details from Open Library; book details sent by the client are ignored.
- Another user's save returns 404, exactly like a save that doesn't exist.
- Calls to members-only endpoints without credentials return 401.
- Invalid statuses, ratings outside 1–5 and duplicate saves return 400.
- Saving a book that's new to the app while Open Library is unavailable
  returns 503. Books already in the database save fine during an outage.

Example:

```sh
curl -X POST http://127.0.0.1:8000/api/token/ -d "username=alice&password=shelf-demo-2026"
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/saved-books/
```

## Privacy

- Each save (status, rating, sharing) is **private** until its owner makes it
  public. Private saves never appear on profiles or in public API responses,
  including when the owner views their own profile.
- Book details and the **community average** are public. The average is built
  from every rating, public and private, and never shows who rated.
- The rule lives in one place, `SavedBook.objects.public()`, which every
  profile view and public API endpoint uses.

**Accepted edge case:** when only one person has rated a book, the community
average equals that person's rating, even if their save is private. (In the
demo data, *The Great Gatsby*'s only rating is `ben`'s private 2★.) This was a
deliberate decision: the average never identifies who rated, and only
anonymous aggregates (the average and the count) are ever made public.

## Development

```sh
uv run pytest                    # the full suite (takes about 3 minutes)
uv run pytest tests/test_api.py  # one area
uv run ruff check .
uv run ruff format --check .
```

Tests never contact the real Open Library. An autouse fixture in
`tests/conftest.py` fails any test that opens a network connection; client
tests fake the HTTP call and view and API tests fake the client's functions.

## Known limitations

- API tokens don't expire.
- There's no login rate limiting, password reset, email verification or
  two-factor authentication. Email addresses are stored only.
- Sign-in is by username, not email.
- Mobile proportions aren't tuned (for example, star tap targets and control
  density on cards).
- Stored book data isn't refreshed from Open Library after a book is first
  saved, and book descriptions aren't fetched.
- Saved Books can't be searched by ISBN, and there's no subject filtering.
- Covers load directly from Open Library's cover service, so they don't show
  during an outage (a placeholder is shown instead).

## Project documents

- PRD: `prd/book-catalog-system.md`
- Implementation plan: `plans/book-catalog-system.md`
- Prototypes and their recorded decisions: `prototypes/README.md`
- Open Library research: `docs/research/free-apis-for-catalog-app.md`
