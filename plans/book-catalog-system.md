# Plan: Book Catalog System

> Source PRD: `prd/book-catalog-system.md` (UI and privacy decisions in `prototypes/README.md`)

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Python 3.14, Django, Django REST Framework, SQLite, uv, Ruff, pytest + pytest-django. Tailwind CSS + DaisyUI via django-tailwind-cli. HTMX vendored as a pinned static file, with django-htmx.
- **Owning apps**:
  - `accounts`: custom user model, sign-up, public profile pages.
  - `books`: Book and SavedBook models, Search Catalog, Saved Books, book page, the Open Library client module, the API, and management commands.
- **Models**:
  - `User` extends Django's abstract user, with a required, database-unique email. Created before the first migration. Sign-in is by username. Django's default password validators.
  - `Book`: one row per Open Library work. Work ID in short form (e.g. `OL893414W`), unique, used as the URL identifier. Title, authors (one text field, semicolon-separated), first publish year, cover ID, edition count, and ISBNs and subjects as JSON lists capped at 10 values.
  - `SavedBook`: FK to User and FK to Book (`on_delete=PROTECT`), unique per (user, book). `status` text choices (Want to read / Reading / Read, default Want to read), `rating` optional 1–5 (validators + database check constraint), `is_public` (default false), date saved.
  - Community average is never stored: one reusable query helper on Book returns the average (one decimal) and count of non-empty ratings from all saves.
- **Website URLs**:
  - `/catalog/`: Search Catalog (signed in)
  - `/saved/`: Saved Books (signed in, own saves only)
  - `/books/<work_id>/`: book page (anyone)
  - `/users/<username>/`: profile (anyone)
  - Django's built-in auth views for sign in / sign out, plus a sign-up page
- **API URLs**:
  - `/api/token/`: exchange username + password for a token
  - `/api/saved-books/` and `/api/saved-books/<id>/`: own saves; list, create, retrieve, partial update, delete
  - `/api/users/<username>/saved-books/`: a user's public saves (read-only, anyone)
  - `/api/books/<work_id>/`: book details + community average and count (read-only, anyone)
- **Authentication / authorization**: Django session auth for the website; logged-out users are redirected to sign in on members-only pages. The API uses DRF session + token authentication (tokens don't expire). Members-only API calls without credentials get 401. Another user's save returns 404, never 403.
- **Privacy rule**: lives in one custom SavedBook queryset method that returns public saves. Every profile view and public API endpoint uses it.
- **Open Library**: only the search endpoint, requesting only the needed fields, with a timeout and a User-Agent that includes `OPENLIBRARY_CONTACT_EMAIL` when set. Failures raise one search error whose message is written for users. One shared save-by-work-ID function serves the website and the API, and the server never trusts book details sent by a client.
- **UI convention**: "Shelf grid": top navbar, filter toolbar card, cover-forward card grid (2/3/4 columns), and a shared Previous / "Page X of Y" / Next pagination component.
- **Testing**: an autouse fixture fails any unfaked outgoing HTTP request. Client tests fake the HTTP call; view and API tests fake the client's search and save functions.

---

## Phase 1: Project skeleton and accounts

**User stories**: 1, 2, 3, 4, 5, 6, 7, 75

### What to build

A running Django project with the `accounts` and `books` apps, the custom User model created before the first migration, and a base layout (navbar, Tailwind/DaisyUI build, vendored HTMX, django-htmx). Visitors can sign up with email, username and password, sign in by username, and sign out. A members-only placeholder shows that logged-out visitors get redirected to sign in. pytest-django, Ruff and the network safety-net fixture are set up, and the existing Open Library script tests still pass.

### Acceptance criteria

- [ ] Sign-up requires a unique email, a username and a password. Weak or common passwords are rejected by Django's validators.
- [ ] A duplicate email is rejected by both the form and the database.
- [ ] A failed sign-in shows one generic "username or password was wrong" message.
- [ ] Sign-out works, and members-only pages redirect logged-out visitors to sign in.
- [ ] The navbar shows the right links for signed-in and signed-out users.
- [ ] Any test that makes an unfaked HTTP request fails immediately (the fixture itself is tested).
- [ ] `ruff check` and `ruff format --check` pass, and the test suite passes.

---

## Phase 2: Book model, book page and demo data

**User stories**: 43, 44, 45, 46, 47, 48, 71, 73, 74

### What to build

The Book and SavedBook models with their constraints, registered in the admin. A public book page at `/books/<work_id>/` shows the cover (with a placeholder when the image fails), title, authors, first publish year, subjects, ISBNs, and the community average ("4.3 ★ from 3 ratings" or "No ratings yet"). A seed-demo management command loads about 4 demo users and about 15 real books from a bundled data file, with a mix of statuses, ratings and public/private saves. It never touches the network, can be run repeatedly, and refuses to run unless DEBUG is on.

### Acceptance criteria

- [ ] A user can't save the same book twice. Ratings outside 1–5 are rejected by both the validators and the database check constraint.
- [ ] Deleting a Book that has saves raises a protected error.
- [ ] The community average helper ignores unrated saves, counts both private and public ratings, rounds to one decimal, and returns a count.
- [ ] The book page works for logged-out visitors, shows no information about who rated, and returns 404 for unknown work IDs.
- [ ] The cover falls back to a placeholder when the image can't load.
- [ ] Running the seed command twice doesn't create duplicates, it refuses when DEBUG is off, and it makes no network calls.

---

## Phase 3: Open Library client and basic Search Catalog

**User stories**: 8, 9, 10, 15, 18, 19, 21, 76

### What to build

Move the script's search function and error handling into the `books` app's Open Library client module. Expand the requested fields (work key, title, author names, first publish year, cover ID, ISBNs, subjects, edition count) and keep the User-Agent with the configured contact email. Build `/catalog/` for signed-in users: a search form, and one page of results shown as Shelf-grid cards (cover, title, authors, first publish year). ISBN-like input has its hyphens and spaces stripped. Empty searches are rejected with a helpful message and no request. Any Open Library failure shows an inline DaisyUI alert in the results area that links to Saved Books, and the technical error is logged on the server. Check the live API once by hand to confirm which fields come back and how ISBN queries behave.

### Acceptance criteria

- [ ] The client tests (carried over from the script) cover timeouts, connection failures, 429, 5xx, other 4xx, invalid JSON and unexpected response shapes.
- [ ] The User-Agent includes the contact email when it's configured.
- [ ] Searching by ISBN with hyphens or spaces sends the cleaned value.
- [ ] Empty queries show a message and never call the client.
- [ ] When Open Library fails, the results area shows the alert with a link to Saved Books.
- [ ] Logged-out visitors are redirected to sign in.

---

## Phase 4: Search paging over HTMX

**User stories**: 11, 12, 13, 14

### What to build

Search Catalog shows 20 results per page using the shared pagination component. The query and page number live in the URL, so refresh, the back button and bookmarks work. HTMX requests swap only the results area and push the URL, while full requests render the whole page. Paging stops at page 10, with a hint to try a more specific search.

### Acceptance criteria

- [ ] The client is called with the right page and limit.
- [ ] HTMX requests return only the results partial; normal requests return the full page.
- [ ] Previous and Next appear only when they make sense, and Next is never offered past page 10.
- [ ] Asking for a page above 10 is capped and shows the refine hint.

---

## Phase 5: Save by work ID

**User stories**: 16, 17, 20, 22, 23, 24, 25, 51, 52

### What to build

One shared save function that takes a user and a work ID. If the Book is already in the database it's reused with no network call. Otherwise the server looks the work up by key through the search endpoint, creates the Book (lists capped at 10), and then creates the SavedBook as private, Want to read and unrated. Search results show a Save button that saves through HTMX, or "Saved ✓" linking to the book page when the user already has it. A failed save shows an alert next to that book's Save button. The book page shows "Save to my library" to signed-in non-owners and "Sign in to save" to visitors.

### Acceptance criteria

- [ ] Saving a book already in the database works while Open Library is faked as down.
- [ ] Saving a book new to the app while Open Library is down raises an error that the view shows next to the button.
- [ ] Book details come only from Open Library, never from request data.
- [ ] A duplicate save tells the user the book is already in their Saved Books.
- [ ] New saves default to private, Want to read and unrated.
- [ ] Search results mark books the user has already saved as "Saved ✓" with a link to the book page.
- [ ] The book page shows the right save prompt for owners, non-owners and visitors.

---

## Phase 6: Saved Books list

**User stories**: 26, 27, 33, 36

### What to build

`/saved/` for signed-in users shows only their own saves, newest first, as Shelf-grid cards with cover, title, authors, year, rating, status and public/private badge. It shows 12 per page with the shared pagination component, and reads only from the local database.

### Acceptance criteria

- [ ] Only the requesting user's saves appear.
- [ ] The page works with no client calls (Open Library faked as down).
- [ ] Pagination shows 12 per page with "Page X of Y".
- [ ] There's an empty state for users with no saves.
- [ ] Logged-out visitors are redirected to sign in.

---

## Phase 7: Saved Books search, filters and sort

**User stories**: 28, 29, 30, 31, 32, 34, 35

### What to build

A filter toolbar card with a title/author search, filters for status, rating (1–5 or Unrated) and visibility, and sort options: recently saved (default), title, first published year, or my rating (unrated last). All of these rules live in one function that reads the query parameters. HTMX swaps only the list and pushes the URL so the settings can be bookmarked. When nothing matches, the page says "no saved books match these filters" with a clear-filters link.

### Acceptance criteria

- [ ] The filter/sort function is unit-tested for each filter, each sort (including unrated last), and combinations.
- [ ] Search matches title or author without caring about case.
- [ ] Invalid parameter values are ignored safely.
- [ ] HTMX requests return only the list partial, and the URL keeps the current settings.
- [ ] The empty state includes a working clear-filters link.

---

## Phase 8: Card quick edits

**User stories**: 37, 38, 39, 40, 41, 42

### What to build

One update view for the owner's save. It accepts any subset of status, rating (including clearing it) and the public flag, validates them in one place, and returns the right partial for HTMX requests. Cards get clickable 1–5 stars with a ✕ to clear, a status dropdown and a public/private toggle. An edit swaps only that card and shows a brief "Saved ✓". If the edited card no longer matches the current filters, it stays visible with a hint until the filters or page change.

### Acceptance criteria

- [ ] Partial updates change only the fields sent. Invalid status or rating values are rejected without saving anything.
- [ ] Clearing the rating sets it back to "Not rated".
- [ ] Editing someone else's save returns 404. Logged-out requests redirect to sign in.
- [ ] HTMX responses contain only the updated card with "Saved ✓".
- [ ] A card that no longer matches the filters shows the hint instead of disappearing.

---

## Phase 9: Book page owner controls and public profile

**User stories**: 49, 50, 53, 54, 55, 56, 57, 58, 59

### What to build

On the book page, owners see the full edit form (status, rating, sharing). It goes through the same update view, which returns the book-page form partial. Owners can also remove the book from their Saved Books; the Book row stays. Add the public-saves queryset method and the profile page at `/users/<username>/`, which shows that user's public saves with status and rating to anyone, or a "no public books yet" message.

### Acceptance criteria

- [ ] The update view returns the book-page form partial when called from the book page.
- [ ] Remove deletes only the user's SavedBook. The book page still works afterwards and shows "Save to my library".
- [ ] The public-saves query returns only `is_public` saves, and it is the only query the profile uses.
- [ ] Private saves never appear on profiles, including the owner viewing their own profile.
- [ ] Making a save private removes it from the profile right away.
- [ ] Unknown usernames return 404, and the empty state shows for users with no public saves.

---

## Phase 10: The app's API

**User stories**: 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70

### What to build

DRF with session and token authentication, and the `/api/token/` endpoint. `/api/saved-books/` is a viewset limited to the requesting user's own saves: list, create (only a work ID, through the shared save function), retrieve, partial update and delete. Status, rating and `is_public` are editable, and the nested book details are read-only, with authors returned as a list. Two read-only public endpoints: `/api/users/<username>/saved-books/` (using the public-saves query) and `/api/books/<work_id>/` (book details plus community average and count, with no user information).

### Acceptance criteria

- [ ] A token can be obtained with a username and password and used in later calls. The browsable API works with an existing session.
- [ ] Unauthenticated calls to `/api/saved-books/` return 401.
- [ ] Another user's save returns 404 for retrieve, update and delete.
- [ ] Create with a new work ID while Open Library is faked as down returns 503 with a message. A book already in the database saves fine.
- [ ] Invalid statuses, ratings outside 1–5 and duplicate saves return 400 with clear errors.
- [ ] Book details in requests are ignored.
- [ ] The public-saves endpoint returns only public saves and works for anyone.
- [ ] The book endpoint returns details, the average and the count, and contains no user fields.

---

## Phase 11: Prune command and README

**User stories**: 72 (plus the README requirements in the PRD's Further Notes)

### What to build

A prune-books management command that deletes books with zero saves. A dry-run flag lists them without deleting anything, and PROTECT guarantees saved books are never removed. The README covers setup (uv, Tailwind build, `.env`), how to run the app and the tests, the demo logins, the known limitations (no token expiry, no login rate limiting, no password reset, untuned mobile proportions), and the accepted privacy edge case (a book with a single rating shows that rating as its average, and only anonymous aggregates are public).

### Acceptance criteria

- [ ] The dry run lists unsaved books and deletes nothing.
- [ ] A normal run deletes only unsaved books. Their book page and API endpoint then return 404.
- [ ] Books with any save, public or private, survive.
- [ ] The README includes the demo logins, the known limitations and the privacy edge-case note.
