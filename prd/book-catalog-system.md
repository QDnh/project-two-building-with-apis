# PRD: Book Catalog System

## Problem Statement

Readers want one personal place to keep track of books they've found: what they want to read, what they're reading, what they've finished, and what they thought of each one. Open Library has the book data, but it doesn't give a reader a private, rated reading list that they control and can choose to show to friends.

Readers also need that list to stay usable when the outside book service is slow or down. A reading list that disappears whenever Open Library has an outage isn't one they can rely on.

Finally, a reader wants control over privacy. By default their list is nobody's business, but they'd like to be able to show off particular books to friends, including friends who don't have an account, without exposing everything else.

## Solution

The Book Catalog System is a Django web application with its own REST API. Signed-in users:

1. Search Open Library from the **Search Catalog** page.
2. **Save** books they find. The app stores enough book information locally that everything a user has saved keeps working when Open Library is unavailable.
3. Manage their **Saved Books**: set a reading status (Want to read / Reading / Read), give an optional 1–5 whole-star rating, and choose per book whether it's **public**. They can search, filter, sort and page through the list, all against local data.
4. Share a **public profile** that anyone, even someone without an account, can open to see that user's public books, along with their statuses and ratings.

Every book has a **book page**, viewable by anyone, showing the stored book details and a **community average** rating (one decimal place, with a count) built from all users' ratings without revealing who rated.

The app's own API provides token or session authenticated create, list, update and delete for a user's own saved books, plus read-only public endpoints for profiles and books. The website and the API enforce the same privacy rules.

When Open Library fails, users see a clear message where the failure happened, plus a reminder that their saved books are still available.

## User Stories

### Accounts

1. As a new visitor, I want to sign up with an email address, a public username and a password, so that I can start saving books.
2. As a new visitor, I want weak or common passwords rejected at sign-up, so that my account is harder to break into.
3. As a user, I want my email address to be unique to my account, so that two accounts can't share one email.
4. As a returning user, I want to sign in with my username and password, so that I can reach my saved books.
5. As a user, I want a failed sign-in to say only that the username or password was wrong, so that attackers can't confirm which usernames exist.
6. As a signed-in user, I want to sign out, so that others using my device can't change my data.
7. As a logged-out visitor, I want to be redirected to sign in when I open a members-only page, so that I understand why I can't see it.

### Search Catalog (Open Library search)

8. As a signed-in user, I want to search Open Library by title, author or keywords, so that I can find books to save.
9. As a signed-in user, I want to search by ISBN, with or without hyphens or spaces, so that I can find the exact book I'm holding.
10. As a signed-in user, I want each result to show the cover, title, authors and first publish year, so that I can tell similar books apart.
11. As a signed-in user, I want results shown 20 per page with Previous and Next buttons, so that I can look past the first few matches.
12. As a signed-in user, I want the search and page number kept in the URL, so that refresh, the back button and bookmarks work.
13. As a signed-in user, I want only the results area to update when I page through results, so that the page doesn't fully reload.
14. As a signed-in user, I want paging to stop after 10 pages with a hint to try a more specific search, so that I'm steered toward better queries and the app stays within Open Library's rate limits.
15. As a signed-in user, I want an empty search rejected with a helpful message, so that I don't trigger a pointless request.
16. As a signed-in user, I want books I've already saved to show "Saved ✓" linking to their book page instead of a Save button, so that I don't try to save them twice.
17. As a signed-in user, I want to click Save on a result and have it added to my Saved Books, so that I can track it.
18. As a signed-in user, I want a clear message where the results would be when Open Library is slow, unreachable, rate-limiting or returning errors, so that I know what went wrong and what to do.
19. As a signed-in user, I want that message to remind me that my saved books are still available, with a link, so that I know the outage doesn't affect my list.
20. As a signed-in user, I want a clear message next to a book's Save button if saving it fails because Open Library is unavailable, so that I know to try again later.
21. As a logged-out visitor, I want to be sent to sign in if I open Search Catalog, so that I know an account is required.

### Saving books

22. As a signed-in user, I want a newly saved book to start as private, "Want to read" and unrated, so that nothing is shared or assumed without my choice.
23. As a signed-in user, I want saving a book that already exists in the app to work even when Open Library is down, so that outages affect me as little as possible.
24. As a signed-in user, I want to be told if a book is already in my Saved Books, so that I don't create duplicates.
25. As a user, I want book details to always come from Open Library, not from what another user's browser or API client sends, so that nobody can corrupt the book information everyone sees.

### Saved Books (my list)

26. As a signed-in user, I want a Saved Books page showing only my own saved books, so that I have a personal reading list.
27. As a signed-in user, I want each saved book shown as a card with its cover, title, authors, year, my rating, my status and whether it's public, so that I can see everything at a glance.
28. As a signed-in user, I want to search my saved books by title or author, so that I can find one quickly.
29. As a signed-in user, I want to filter my saved books by status, so that I can see what I'm reading or want to read.
30. As a signed-in user, I want to filter by my rating, including "Unrated", so that I can find favourites or books I haven't rated yet.
31. As a signed-in user, I want to filter by public or private, so that I can review what I'm sharing.
32. As a signed-in user, I want to sort by recently saved (the default), title, year first published, or my rating (unrated last), so that I can order the list the way I need.
33. As a signed-in user, I want my saved books shown 12 per page with Previous and Next, so that long lists stay manageable.
34. As a signed-in user, I want search, filter, sort and paging to update only the list without a full page reload, while the URL keeps the current settings, so that it's fast and still bookmarkable.
35. As a signed-in user, I want a "no saved books match these filters" message with a way to clear filters, so that I'm never stuck on an empty page.
36. As a signed-in user, I want Saved Books to work completely while Open Library is down, so that I can always reach my list.
37. As a signed-in user, I want to change a book's status from its card, so that I can update my progress quickly.
38. As a signed-in user, I want to set a 1–5 star rating by clicking stars on a card, so that rating is quick.
39. As a signed-in user, I want to clear a rating with a small ✕ on the card, so that I can go back to "Not rated".
40. As a signed-in user, I want to switch a book between public and private from its card, so that I can manage sharing quickly.
41. As a signed-in user, I want only the card I changed to update, with a brief "Saved ✓", so that I know the change was stored.
42. As a signed-in user, I want a card I just edited to stay on screen, with a hint, even if it no longer matches my filters, until I change filters or pages, so that I can undo a mistaken change.

### Book page

43. As anyone, including a logged-out visitor, I want to open a book's page from a profile or my list, so that I can see more about the book.
44. As anyone, I want the book page to show the cover, title, authors, first publish year, subjects and ISBNs, so that I can identify the book.
45. As anyone, I want the book page to show the community average rating to one decimal place with the number of ratings, or "No ratings yet", so that I can see what readers think.
46. As a user who rated a book privately, I want the community average never to reveal who rated, so that my private rating stays anonymous.
47. As anyone, I want the book page to work when Open Library is down, with a placeholder if the cover image can't load, so that the page is always usable.
48. As a book page link holder, I want the URL to use the book's Open Library ID, so that links stay valid after the database is reset or reseeded.
49. As a signed-in user who has saved the book, I want the book page to show a form to edit my status, rating and sharing, so that I can manage it there too.
50. As a signed-in user who has saved the book, I want to remove it from my Saved Books from the book page, so that I can drop books I no longer want to track.
51. As a signed-in user who hasn't saved the book, I want a "Save to my library" button, so that I can save books I found on a friend's profile.
52. As a logged-out visitor, I want a "Sign in to save" prompt instead of a Save button, so that I know how to start my own list.

### Public profiles and sharing

53. As a user, I want each saved book to be private until I mark it public, so that nothing is shared by accident.
54. As a user, I want to choose book by book which saves are public, so that I can build a profile showing only what I want.
55. As a user, I want my profile at a URL with my username, so that I can send it to friends.
56. As anyone, including a logged-out visitor, I want to see a user's public saved books with their status and rating on that user's profile, so that I can see what they're reading and recommend.
57. As a user, I want my private saves never to appear on my profile, in any public API response, or anywhere else visible to others, so that my private reading stays private.
58. As a user, I want a book to disappear from my profile as soon as I make it private, so that I stay in control of what I share.
59. As a profile visitor, I want a "no public books yet" message when a user shares nothing, so that the page doesn't look broken.

### The app's API

60. As an API client, I want to exchange a username and password for a token, so that I can call the API from scripts and tools.
61. As a signed-in website user, I want the browsable API to work with my existing session, so that I can explore the API without managing a token.
62. As an API client, I want to list my own saved books, so that I can read my list programmatically.
63. As an API client, I want to save a book by sending only its Open Library work ID, so that the server fills in the book details itself.
64. As an API client, I want a 503 with a clear message when I save a book new to the app while Open Library is unavailable, so that I know to retry later.
65. As an API client, I want to view, update (status, rating, public) and delete my own saved books, so that I can manage my list without the website.
66. As an API client, I want invalid statuses, ratings outside 1–5, and duplicate saves rejected with clear validation errors, so that bad data is never stored.
67. As a user, I want someone else's request for my saved book to get "not found", exactly like a book that doesn't exist, so that the API doesn't even confirm my private saves exist.
68. As an anonymous API client, I want an authentication error when I call members-only endpoints, so that I know to sign in or send a token.
69. As anyone, I want a read-only API endpoint listing a user's public saved books, so that the sharing feature works in the API as on the website.
70. As anyone, I want a read-only API endpoint for a book by its Open Library ID, returning book details and the community average and count with no user information, so that the API matches the book page.

### Operations, demo and testing

71. As an administrator, I want the database to refuse to delete a book that anyone has saved, so that users never lose saved entries by accident.
72. As an administrator, I want a management command that removes books nobody has saved, with a dry-run option that lists what would be removed, so that I can tidy the database safely.
73. As a developer or grader, I want a management command that loads demo users, real books and a mix of statuses, ratings and public/private saves without any network access, so that the app can be demoed right away.
74. As a developer or grader, I want the demo command to be safe to run more than once and to refuse to run outside debug mode, so that demo data never reaches a real deployment.
75. As a developer, I want the test suite to fail immediately if any test tries to contact the real Open Library, so that tests are fast, reliable and never use the real API's rate limit.
76. As a developer, I want the app to identify itself to Open Library with a contact email from configuration when one is provided, so that the app gets the higher rate limit and follows Open Library's guidelines.

## Implementation Decisions

### Stack
- Python 3.14, Django, Django REST Framework, SQLite, uv for dependencies, Ruff for linting and formatting, pytest with pytest-django for tests.
- Tailwind CSS with DaisyUI, built locally through django-tailwind-cli.
- HTMX served as a vendored, version-pinned static file (not a CDN), with the django-htmx package so views can tell HTMX requests from full page loads.
- The only external assets are Open Library cover images, loaded directly from Open Library's cover service.

### Project structure
- A project configuration package plus two Django apps:
  - **accounts**: the custom user model, sign-up, and public profile pages.
  - **books**: the book and saved-book models, Search Catalog, Saved Books, book pages, the Open Library client module, the API (serializers, views, routes), and the management commands.
- Features are grouped by app, as long as that doesn't lead to constant cross-imports. Profile views use the books app's public-saves query, so the privacy rule stays in one place.

### Models
- **User**: a custom user model extending Django's abstract user, with a required, database-unique email. Created before the first migration. Users sign in by username. Django's default password validators are used.
- **Book** (shared, one row per Open Library work):
  - Work ID stored in short form (e.g. `OL893414W`), unique, and used as the URL identifier.
  - Title; authors as one text field joined with a semicolon separator (searchable with case-insensitive containment).
  - First publish year; Open Library cover ID; edition count.
  - ISBNs and subjects as JSON lists, each capped at the first 10 values.
- **SavedBook** (per user):
  - Links a user to a book; each user can save a given book only once.
  - Reading status: a text-choices field with Want to read, Reading and Read; defaults to Want to read.
  - Rating: optional small positive integer 1–5, enforced by validators and a database check constraint (empty or 1–5).
  - Public flag: defaults to private.
  - Date saved.
  - The link to Book uses PROTECT on delete, so a saved book can't be deleted.
- The community average isn't stored. It's computed from saved-book ratings (unrated saves ignored) and rounded to one decimal, along with the count, through one reusable query helper on Book.

### Privacy model
- An individual save (status, rating, sharing) is visible only to its owner unless public.
- Public saves are visible to anyone on the owner's profile and the public profile API endpoint.
- Book facts and the anonymous community average (from all ratings, public and private) are public.
- The rule lives in one place: a custom saved-book queryset method returning public saves, used by every profile view and public API endpoint.
- There's no page listing every book in the database. That's a scope decision, not a privacy one.

### Open Library integration
- One endpoint is used: Open Library's search endpoint, requesting only the fields needed (work key, title, author names, first publish year, cover ID, ISBNs, subjects, edition count).
- Requests send a User-Agent identifying the app, including a contact email from environment configuration when set. Requests have a timeout.
- The existing script's search function and error handling move into the books app's Open Library client module. Timeouts, connection failures, HTTP 429, HTTP 5xx, other 4xx, invalid JSON and unexpected response shapes raise a search error whose message is written for users.
- **Saving by work ID**: one shared save function used by both the website and the API. The client sends only the work ID. If the Book already exists locally, it's reused with no network call. Otherwise the server looks the work up through the same search endpoint by key, creates the Book, then creates the SavedBook. The server never trusts book details sent by a client.
- Search Catalog strips hyphens and spaces from ISBN-like input before searching.
- To verify against the live API during the build: that the requested fields (ISBNs, subjects, cover ID) are returned, that a key query returns exactly one work, and that a bare ISBN query finds the right book (otherwise use the ISBN-specific parameter).

### Website pages and behaviour

| Page | Access | Behaviour |
|---|---|---|
| Search Catalog | Signed in | Open Library search; 20 results per page; Previous/Next; query and page in the URL; HTMX swaps only the results; capped at 10 pages with a refine hint; empty queries rejected; Save button or "Saved ✓" per result |
| Saved Books | Signed in, own books only | Search by title or author; filters for status, rating (1–5 or Unrated) and visibility; sort by recently saved (default), title, first published year, or my rating (unrated last); 12 per page; all filter, search and sort rules in one function that reads the query parameters; HTMX swaps the list and the URL updates |
| Book page | Anyone | Local data plus community average; full edit form (status, rating, sharing) and Remove for owners; "Save to my library" for signed-in non-owners; "Sign in to save" for visitors; cover placeholder when the image fails |
| Profile | Anyone | That user's public saves with status and rating; empty-state message |

- **UI convention**: the "Shelf grid" layout from the UI prototype. Top navbar, a filter toolbar card, a cover-forward card grid (2/3/4 columns by screen width), and a shared Previous / "Page X of Y" / Next pagination component used on both Saved Books and Search Catalog. Search Catalog, the book page and profiles follow the same convention.
- **Card controls** on Saved Books: clickable 1–5 stars with a ✕ to clear, a status dropdown, and a public/private toggle.
- **One update view** handles edits from both cards and the book page. It accepts any subset of status, rating and public flag, validates them in one place, and returns the right partial (card or book-page form) for HTMX requests.
- **After a card edit**, HTMX swaps only that card and shows a brief "Saved ✓". The list isn't re-filtered: an edited card that no longer matches the filters stays visible with a hint until the filters or page change.
- **Open Library errors** appear as an inline DaisyUI alert where the failure happened (the results area, or next to a book's Save button). The alert links to Saved Books ("your saved books are still available"), and the technical error is logged on the server. There's no separate retry button: the search form and Save button already do that.
- Logged-out users who open members-only pages are redirected to sign in.

### API
- Authentication: DRF session authentication (for the browsable API) and DRF token authentication. A token endpoint exchanges username and password for a token. Tokens don't expire.
- **Saved books** (full create, list, retrieve, partial update and delete): signed-in only, scoped to the requesting user's own saves. Create takes only the work ID. Editable fields are status, rating and public flag. Book details are nested and read-only. Another user's save returns 404, not 403. Saving a book new to the app while Open Library is unavailable returns 503 with a message. Invalid values and duplicates return 400.
- **A user's public saves**: read-only, open to anyone, using the same public-saves query as the profile page.
- **A book by work ID**: read-only, open to anyone. Returns book details plus community average and count, and never includes user information.
- Unauthenticated calls to members-only endpoints return 401.
- Authors can be returned as a list by splitting on the semicolon separator.

### Management commands
- **Prune books**: deletes books with zero saves, with a dry-run flag that lists them without deleting. PROTECT guarantees saved books can't be deleted.
- **Seed demo data**: creates about 4 demo users with known passwords and about 15 real books from a bundled data file (never calls the network). Users get a mix of statuses, ratings, and public and private saves. It's safe to run repeatedly and refuses to run unless debug mode is on. Demo logins are documented in the README.

### Testing
- pytest with pytest-django.
- Two faking layers:
  - Open Library client tests fake the HTTP call with canned responses and errors (the existing script's tests are carried over).
  - View and API tests fake the client's search and save functions at the function level.
- An autouse safety-net fixture makes any unfaked outgoing HTTP request fail the test immediately. Tests must never call the real Open Library.
- Coverage focus: the privacy rules (public-saves query, 404 for other users' saves, logged-out access, the book endpoint without user data), the save-by-work-ID flow (local hit, fetch, 503), validation (status, rating range, duplicates, the database constraint), the filter/search/sort function, community average computation, the update view's partial handling, and the management commands.

## Out of Scope

- **Book descriptions.** Fetching each work's full record is future work; saving uses only search-result fields.
- **Community Catalog.** A page listing every book saved by anyone, plus a book list API endpoint.
- **ISBN search on Saved Books.** Only the first 10 ISBNs are stored, so doing this properly needs edition tracking.
- **Subject filtering** and multi-select filters on Saved Books.
- **"Did not finish"** or any other statuses beyond the three.
- **Token expiry**, login rate limiting, password reset, email verification, and two-factor authentication. Email is stored only.
- **Logging in with email** instead of username.
- **Downloading or self-hosting cover images.** Covers are loaded from Open Library's cover service.
- **Refreshing stored book data** from Open Library after it's saved.
- **Tuned mobile proportions** for the cards, such as star tap targets and control density.
- Deployment, email delivery, and any external API other than Open Library.

## Further Notes

- **External API research**: Open Library was chosen because it needs no key, encourages caching, and asserts no new copyright over its data, which suits storing saved books locally. Documented limits are about 1 request per second, or 3 with an identifying User-Agent. Covers looked up by cover ID avoid the stricter ISBN-based cover limit. See the research document in the repository's docs folder.
- **Prototypes**: the UI convention ("Shelf grid", including stars on cards) and the privacy rules were validated with throwaway prototypes in the prototypes folder. Their decisions are recorded in that folder's README.
- **Accepted privacy edge case**: when only one person has rated a book, the community average equals that person's rating, even if their save is private. This is accepted because the average never identifies who rated. It should be explained in the project README so graders see it was a deliberate decision. The same note should explain that only anonymous aggregates are public.
- **"Enough information locally"**: interpreted as every field the site displays (title, authors, year, cover ID, ISBNs, subjects, edition count). Saved Books, book pages and profiles work entirely from the local database.
- **Naming**: these names are used consistently across the UI, the code and the documentation:
  - Search Catalog (Open Library search)
  - Saved Books (the user's own list)
  - Book page
  - Profile
  - Public save
  - Community average
  - Community Catalog (future work)
- **README**: should list the known limitations above (token expiry, login rate limiting, password reset, mobile proportions) and the demo logins.
