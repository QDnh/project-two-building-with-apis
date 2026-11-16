# Book Catalog System

A Django web app and REST API where users search Open Library, save books to a private reading list, rate them, and choose which ones to share on a public profile.

## Stack

- Python 3.14, Django, Django REST Framework, SQLite
- uv for dependencies; Ruff for linting and formatting; pytest with pytest-django
- Tailwind CSS with DaisyUI via django-tailwind-cli
- HTMX via django-htmx's vendored copy (`{% htmx_script %}`), pinned by `uv.lock`; no CDN

## Commands

- Install: `uv sync`
- Database: `uv run python manage.py migrate`
- Dev server with live CSS rebuild: `uv run python manage.py tailwind runserver`
- Build CSS once: `uv run python manage.py tailwind build` (output `assets/css/tailwind.css` is git-ignored)
- Tests: `uv run pytest` (the full suite takes about 3 minutes, longer than the default 2-minute command timeout). While working, run only the relevant files (`uv run pytest tests/test_<area>.py`); run the full suite only when it's needed, such as once at the end of a phase before committing.
- Lint and format: `uv run ruff check .` and `uv run ruff format --check .`
- Demo data (DEBUG only, no network): `uv run python manage.py seed_demo`
- Remove books nobody has saved: `uv run python manage.py prune_books` (`--dry-run` lists them first)

## Conventions

- Settings come from environment variables loaded from `.env`; document new ones in `.env.example`.
- Templates live in the top-level `templates/` folder; `base.html` holds the navbar.
- The site uses DaisyUI's dark theme (set in `base.html`); style with DaisyUI's theme colours (`bg-base-100`, `text-base-content`, …), not fixed colours.
- Website views are class-based (Django generic views and mixins); the API uses DRF's class-based views and viewsets.
- Shared pagination lives in `templates/_pagination.html` (Previous / "Page X of Y" / Next); pass `page`, `num_pages`, `prev_url`, `next_url` and the HTMX `target`.
- HTMX views return only the partial for HTMX requests, but the full page for history-restore requests (`request.htmx.history_restore_request`), so back/refresh work. Use `HtmxPartialMixin` (`books/views.py`), which does this and sets `Vary: HX-Request` so the browser never shows a cached partial as the page.
- Tests live in the top-level `tests/` folder. An autouse fixture in `tests/conftest.py` fails any test that opens a real network connection.

## Architecture decisions

- Use a custom User model, created before the first migration.
- Store book data locally so saved books stay usable when Open Library is unavailable.
- Book details come only from Open Library, never from data sent by clients.
- The website and the API share the same logic and enforce the same privacy rules, defined in one place.
- Shared website/API logic lives in `books/services.py`; saving a book goes only through `services.save_book(user, work_id)`, and editing a save only through `services.update_saved_book(save, data)` (validates every field before saving anything; raises `InvalidUpdate`).
- The privacy rule is `SavedBook.objects.public()`: anything that lists saves to someone other than their owner (profiles, public API endpoints) uses it and nothing else. Owner-only views look saves up with `user=request.user`, so another user's save is a 404.
- The API (`books/api.py`, routes in `books/api_urls.py` under `/api/`) requires sign-in by default (token auth listed first, so anonymous calls get 401); public endpoints set `AllowAny` explicitly. Service errors map to HTTP the same way everywhere: `InvalidWorkId`/`AlreadySaved`/`InvalidUpdate` → 400, `SearchError` → 503.
- Open Library is the only external API.
- All Open Library calls go through `books/openlibrary.py`; it raises `SearchError` with a user-facing message. Client tests fake `requests.get`; view and API tests fake the client's functions.
- Tests must never call the real Open Library.

## References

- PRD: `prd/book-catalog-system.md`
- Implementation plan: `plans/book-catalog-system.md`
- Prototypes and their recorded decisions (UI convention, privacy rules): `prototypes/README.md`
- Open Library research: `docs/research/free-apis-for-catalog-app.md`

## Maintaining this file

- Only edit this file when the user asks. If something seems worth adding, suggest it instead.
- Add only durable, project-wide facts: verified commands, established conventions, and architecture decisions. Keep the file under ~70 lines.
- Feature rules, phase details, and one-off fixes belong in the PRD, plan, tests, or code, not here.
