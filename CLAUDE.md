# Book Catalog System

A Django web app and REST API where users search Open Library, save books to a private reading list, rate them, and choose which ones to share on a public profile.

## Stack

- Python 3.14, Django, Django REST Framework, SQLite
- uv for dependencies; Ruff for linting and formatting; pytest with pytest-django
- Tailwind CSS with DaisyUI via django-tailwind-cli
- HTMX as a vendored, version-pinned static file (no CDN), with django-htmx

## Architecture decisions

- Use a custom User model, created before the first migration.
- Store book data locally so saved books stay usable when Open Library is unavailable.
- Book details come only from Open Library, never from data sent by clients.
- The website and the API share the same logic and enforce the same privacy rules, defined in one place.
- Open Library is the only external API.
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
