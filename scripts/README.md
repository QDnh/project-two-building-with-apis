# API client script

`api_client.py` is a command-line client for the Book Catalog API. It talks to
a running Django server over HTTP, so it does not import Django or touch the
database directly.

It has two commands:

| Command  | Endpoint(s)                                             | Sign-in needed |
|----------|---------------------------------------------------------|----------------|
| `list`   | `GET /api/users/<username>/saved-books/?page=N`         | No             |
| `update` | `POST /api/token/`, then `GET` and `PATCH /api/saved-books/<id>/` | Yes (token) |

## 1. Start the server

Run each command from the project root (the folder that holds `manage.py`).

```
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo                # optional demo data (DEBUG only)
uv run python manage.py tailwind runserver       # leave this running
```

Open a second terminal for the script. By default it talks to
`http://127.0.0.1:8000`.

## 2. Set up credentials

`list` needs no credentials, because public saves are open to anyone.

`update` signs in as a user and changes that user's own saves. You need an
account:

- **Demo data:** `seed_demo` creates `alice`, `ben`, `chloe` and `dev`, all with
  the password `shelf-demo-2026`.
- **Your own account:** sign up at http://127.0.0.1:8000/accounts/signup/ and
  save at least one book.

The script finds the password in this order:

1. The `--password` option.
2. The `BOOK_API_PASSWORD` environment variable.
3. A prompt that hides what you type (used if neither of the above is set).

Setting the environment variable keeps the password out of your shell history:

```
# PowerShell
$env:BOOK_API_PASSWORD = "shelf-demo-2026"

# Git Bash / macOS / Linux
export BOOK_API_PASSWORD=shelf-demo-2026
```

The script exchanges the username and password for a token at `/api/token/`. It
then sends `Authorization: Token <token>` with every request that needs sign-in.
Tokens don't expire, and the script doesn't save the token anywhere.

## 3. Run it

### List a user's public saves

```
uv run python scripts/api_client.py list alice
uv run python scripts/api_client.py list alice --page 2
uv run python scripts/api_client.py list alice --verbose   # also print the full JSON
```

Example output:

```
GET http://127.0.0.1:8000/api/users/alice/saved-books/?page=1
3 public save(s) for alice:
  - Dune (OL893414W) - read, 5/5
  - The Hobbit (OL27482W) - read, 4/5
  - The Left Hand of Darkness (OL59800W) - reading, not rated
Previous page: none
Next page:     none
```

### Update a save's rating

```
uv run python scripts/api_client.py update --username alice --rating 3
uv run python scripts/api_client.py update --username alice --rating 3 --save-id 2
```

- `--rating` must be 1 to 5.
- `--save-id` picks which save to change. Leave it out to change your newest
  save. You can find save IDs at http://127.0.0.1:8000/api/saved-books/ (after
  signing in) or in the `id` field of the script's JSON output.

The script prints a one-line summary of the save before and after the change,
then the full JSON of both:

```
PATCH http://127.0.0.1:8000/api/saved-books/135/  {'rating': 3}
Before: Dune (OL893414W) - read, 5/5
After:  Dune (OL893414W) - read, 3/5
```

To undo changes to the demo data, run `uv run python manage.py seed_demo` again.

## Options

| Option / variable                    | Applies to | Meaning                                            |
|--------------------------------------|------------|----------------------------------------------------|
| `--base-url` or `BOOK_API_URL`       | both       | Server address (default `http://127.0.0.1:8000`)   |
| `--page`                             | `list`     | Page number (20 saves per page, default 1)         |
| `--verbose`                          | `list`     | Also print the full JSON response                  |
| `--username`                         | `update`   | Account to sign in as (required)                   |
| `--password` or `BOOK_API_PASSWORD`  | `update`   | That account's password (prompted for if missing)  |
| `--rating`                           | `update`   | New rating, 1 to 5 (required)                      |
| `--save-id`                          | `update`   | Save to change (default: your newest)              |

`--base-url` goes **before** the command name, for example
`uv run python scripts/api_client.py --base-url http://127.0.0.1:8765 list alice`.

Run `uv run python scripts/api_client.py --help` (or `list --help`,
`update --help`) for the full usage.

## Errors

If a request fails, the script prints the HTTP status and the API's error body
to stderr, then exits with code 1:

| Message                                                   | Cause                                  |
|-----------------------------------------------------------|----------------------------------------|
| `Could not reach http://127.0.0.1:8000/...`               | The server isn't running, or the URL is wrong |
| `POST .../api/token/ returned 400: ...Unable to log in...`| Wrong username or password             |
| `returned 404: {"detail":"No User matches the given query."}` | Unknown username (`list`)          |
| `returned 404: {"detail":"Invalid page."}`                | The page number is past the last page  |
| `returned 404: {"detail":"No SavedBook matches the given query."}` | The save ID doesn't exist or belongs to someone else |
