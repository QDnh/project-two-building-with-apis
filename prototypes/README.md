# Prototypes

Throwaway code used to answer design questions. Not production code; don't import from here.

## saved-books-ui.html: Saved Books UI convention (2026-11-16)

**Question:** Which of three structurally different Saved Books layouts becomes the UI convention for the whole app?

**Chosen: Variant A, "Shelf grid".**
- Top navbar, a filter toolbar card (search, status, rating, visibility, sort, clear), a cover-forward card grid (2/3/4 columns), and Previous / "Page X of Y" / Next pagination.
- Each card has every quick control: **clickable 1–5 stars with a ✕ to clear**, a status dropdown, and a Public toggle.
- Card edits swap only that card and show "Saved ✓". An edited card that no longer matches the filters stays visible with a hint until the filters or page change.
- Search Catalog, the book page and profiles follow this convention.

**Why:** Variant A was the clearest and most browsable layout, and having all the controls on the card felt natural. Rating moved onto the cards (it was book page only) because the shared update view and card partial already support it, and the card shows the result immediately, so a mistake is easy to undo.

**Not chosen:** B (sidebar + sortable table with status tabs) and C (filter rail + list + detail panel).

**Known limitation:** mobile proportions of the cards (star tap targets, control density) were not tuned. Out of scope for this project.

## privacy-logic.html: privacy and visibility rules (2026-11-16)

**Question:** Do the privacy rules hold up? For each viewer (owner, another user, a logged-out visitor), what can they see on every page and API endpoint as saves are created, edited, shared, removed and pruned?

**Result: the rules were confirmed with no changes.**
- An individual save (status, rating) is visible only to its owner unless `is_public`. Public saves appear on `/users/<username>/` and `GET /api/users/<username>/saved-books/`, for anyone.
- Book pages and `GET /api/books/<work_key>/` are visible to anyone. They show book facts plus the community average and count, built from **all** ratings, public and private, with no user information.
- Someone else's save, or a removed one, returns **404** on the API (not 403). Logged-out modifications get 401 (API) or a redirect to sign-in (website).
- Saving a book already in the database works while Open Library is down. A book new to the app gets a 503 with a friendly message.
- `on_delete=PROTECT` blocks deleting a saved book. Removing the last save keeps the book. `prune_books` deletes only unsaved books, after which their page and API endpoint return 404.
- Ratings outside 1–5 and duplicate saves are rejected with 400.

**Accepted edge case:** when only one person has rated a book, the community average equals their rating ("2.0 ★ from 1 rating"), even if their save is private. This is acceptable because the average never says who rated. It should be noted in the README.
